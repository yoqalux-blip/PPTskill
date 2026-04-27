import fs from "node:fs/promises";
import path from "node:path";
import pptxgen from "pptxgenjs";

function parseArgs(argv) {
  const parsed = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    parsed[token.slice(2)] = argv[i + 1];
    i += 1;
  }
  return parsed;
}

function sectionLabelForTitle(title) {
  if ((title || "").includes("：")) return title.split("：")[0];
  return "";
}

function estimateBodyFontSize(deckSlide) {
  const bullets = deckSlide.bullets || [];
  const maxLen = bullets.reduce((max, item) => Math.max(max, item.length), 0);
  if (bullets.length >= 4 || maxLen >= 54) return 15;
  if (bullets.length >= 3 || maxLen >= 40) return 16;
  if (bullets.length === 1 && maxLen <= 24) return 20;
  return 18;
}

function addHeaderChrome(slide, template, title, sectionLabel = "") {
  slide.addText(" ", {
    x: 0,
    y: 0,
    w: 13.333,
    h: 0.14,
    margin: 0,
    fill: { color: template.accentColor },
    line: { color: template.accentColor }
  });
  slide.addText(title, {
    x: 0.6,
    y: 0.45,
    w: 11.4,
    h: 0.5,
    fontFace: template.titleFont,
    fontSize: 22,
    color: template.titleColor,
    bold: true
  });
  slide.addText(" ", {
    x: 0.62,
    y: 1.0,
    w: 1.2,
    h: 0.03,
    margin: 0,
    fill: { color: template.accentColor },
    line: { color: template.accentColor }
  });
  if (sectionLabel) {
    slide.addText(sectionLabel, {
      x: 10.2,
      y: 0.48,
      w: 2.3,
      h: 0.22,
      fontFace: template.bodyFont,
      fontSize: 9,
      color: template.accentColor,
      align: "right",
      bold: true
    });
  }
}

function addTitleSlide(slide, deckSlide, template) {
  slide.addText(" ", {
    x: 0,
    y: 0,
    w: 13.333,
    h: 0.18,
    margin: 0,
    fill: { color: template.accentColor },
    line: { color: template.accentColor }
  });
  slide.addText(deckSlide.title, {
    x: 0.7,
    y: 1.25,
    w: 11.8,
    h: 1.0,
    fontFace: template.titleFont,
    fontSize: 26,
    color: template.heroTitleColor || template.titleColor,
    bold: true,
    align: "center"
  });
  slide.addText(deckSlide.subtitle || "", {
    x: 1.3,
    y: 2.7,
    w: 10.5,
    h: 0.5,
    fontFace: template.bodyFont,
    fontSize: 15,
    color: template.heroSubtitleColor || template.bodyColor,
    align: "center"
  });
}

function addFooter(slide, index, total, template) {
  slide.addText(" ", {
    x: 0.7,
    y: 6.9,
    w: 11.9,
    h: 0.01,
    margin: 0,
    fill: { color: "D8CFC3" },
    line: { color: "D8CFC3" }
  });
  slide.addText(template.displayName, {
    x: 0.72,
    y: 7.0,
    w: 2.4,
    h: 0.2,
    fontFace: template.bodyFont,
    fontSize: 8,
    color: template.accentColor
  });
  slide.addText(`${index} / ${total}`, {
    x: 11.2,
    y: 7.0,
    w: 1.2,
    h: 0.2,
    fontFace: template.bodyFont,
    fontSize: 8,
    color: template.accentColor,
    align: "right"
  });
}

function addTakeawayBox(slide, takeaway, template, y = 5.95, h = 0.72) {
  if (!takeaway) return;
  slide.addShape("roundRect", {
    x: 0.82,
    y,
    w: 11.65,
    h,
    rectRadius: 0.08,
    fill: { color: "F3E8DE" },
    line: { color: template.accentColor, pt: 1.2 }
  });
  slide.addText(`关键提示：${takeaway}`, {
    x: 1.0,
    y: y + 0.14,
    w: 11.15,
    h: h - 0.18,
    fontFace: template.bodyFont,
    fontSize: 12,
    color: template.bodyColor,
    bold: true,
    margin: 0.02
  });
}

function addFigureCaption(slide, caption, template, x, y, w) {
  if (!caption) return;
  slide.addText(caption, {
    x,
    y,
    w,
    h: 0.32,
    fontFace: template.bodyFont,
    fontSize: 9,
    color: template.accentColor,
    italic: true,
    margin: 0.01
  });
}

function addBadge(slide, text, x, y, template, w = 1.55) {
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h: 0.28,
    rectRadius: 0.08,
    fill: { color: "EFE4D9" },
    line: { color: "EFE4D9", transparency: 100 }
  });
  slide.addText(text, {
    x,
    y: y + 0.025,
    w,
    h: 0.2,
    fontFace: template.bodyFont,
    fontSize: 8.5,
    color: template.accentColor,
    bold: true,
    align: "center",
    margin: 0
  });
}

function addSummaryLine(slide, text, x, y, w, template, opts = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h: opts.h || 0.32,
    fontFace: template.bodyFont,
    fontSize: opts.fontSize || 10.5,
    color: opts.color || template.bodyColor,
    margin: 0.02,
    italic: !!opts.italic,
    align: opts.align || "left"
  });
}

function addArrowConnector(slide, x1, y1, x2, y2, color = "8A5A44", pt = 1.8) {
  slide.addShape("line", {
    x: x1,
    y: y1,
    w: x2 - x1,
    h: y2 - y1,
    line: {
      color,
      pt,
      beginArrowType: "none",
      endArrowType: "triangle"
    }
  });
}

function addCard(slide, template, x, y, w, h, card, opts = {}) {
  const headerH = opts.headerH || 0.36;
  const fill = opts.fill || "FFFDFC";
  const stroke = opts.stroke || "D4C6B7";
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: fill },
    line: { color: stroke, pt: opts.pt || 1.1 }
  });
  slide.addShape("roundRect", {
    x: x + 0.1,
    y: y + 0.1,
    w: w - 0.2,
    h: headerH,
    rectRadius: 0.06,
    fill: { color: opts.headerFill || "F3E8DE" },
    line: { color: opts.headerFill || "F3E8DE", transparency: 100 }
  });
  if (card.stage) {
    slide.addShape("roundRect", {
      x: x + 0.12,
      y: y - 0.18,
      w: 0.46,
      h: 0.26,
      rectRadius: 0.08,
      fill: { color: template.heroBackgroundColor || "1C2A39" },
      line: { color: template.heroBackgroundColor || "1C2A39", transparency: 100 }
    });
    slide.addText(card.stage, {
      x: x + 0.12,
      y: y - 0.145,
      w: 0.46,
      h: 0.16,
      fontFace: template.bodyFont,
      fontSize: 8.5,
      color: template.heroTitleColor || "F6F2EB",
      bold: true,
      align: "center",
      margin: 0
    });
  }
  slide.addText(card.title, {
    x: x + 0.18,
    y: y + 0.14,
    w: w - 0.36,
    h: 0.2,
    fontFace: template.bodyFont,
    fontSize: opts.titleFontSize || 12.5,
    color: template.titleColor,
    bold: true,
    margin: 0.01
  });
  slide.addText((card.body || []).join("\n"), {
    x: x + 0.18,
    y: y + 0.56,
    w: w - 0.34,
    h: h - 0.68,
    fontFace: template.bodyFont,
    fontSize: opts.bodyFontSize || 10.5,
    color: template.bodyColor,
    margin: 0.02,
    valign: "top"
  });
}

function addImagePanel(slide, template, x, y, w, h, panel) {
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: "FFFDFC" },
    line: { color: "D4C6B7", pt: 1.1 }
  });
  slide.addImage({
    path: panel.path,
    x: x + 0.08,
    y: y + 0.12,
    w: w - 0.16,
    h: h - 0.24
  });
}

function addBulletSlide(slide, deckSlide, template, index, total) {
  const fontSize = estimateBodyFontSize(deckSlide);
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 0.9,
    y: 1.35,
    w: 10.7,
    h: 4.95,
    fontFace: template.bodyFont,
    fontSize,
    color: template.bodyColor,
    margin: 0.08,
    valign: "top"
  });
  addTakeawayBox(slide, deckSlide.takeaway, template);
  addFooter(slide, index, total, template);
}

function addSectionSlide(slide, deckSlide, template, index, total) {
  slide.addText(" ", {
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5,
    margin: 0,
    fill: { color: template.heroBackgroundColor || template.backgroundColor },
    line: { color: template.heroBackgroundColor || template.backgroundColor }
  });
  slide.addText(" ", {
    x: 0.85,
    y: 0.8,
    w: 0.18,
    h: 4.6,
    margin: 0,
    fill: { color: template.accentColor },
    line: { color: template.accentColor }
  });
  slide.addText(deckSlide.title, {
    x: 1.35,
    y: 1.05,
    w: 9.2,
    h: 1.1,
    fontFace: template.titleFont,
    fontSize: 24,
    color: template.heroTitleColor || "FFFFFF",
    bold: true
  });
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 1.4,
    y: 2.35,
    w: 8.8,
    h: 3.0,
    fontFace: template.bodyFont,
    fontSize: 16,
    color: template.heroSubtitleColor || "E8EDF2",
    margin: 0.05,
    valign: "top"
  });
  addFooter(slide, index, total, {
    ...template,
    accentColor: template.heroSubtitleColor || template.accentColor
  });
}

function addRouteHorizontalSlide(slide, deckSlide, template, index, total) {
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addBadge(slide, deckSlide.diagram_v4.badge, 0.86, 1.12, template, 1.68);
  addSummaryLine(slide, deckSlide.diagram_v4.summary, 0.9, 1.48, 11.1, template, { fontSize: 10.5 });
  const cards = deckSlide.diagram_v4.cards || [];
  const xs = [0.92, 3.62, 6.32, 9.02];
  for (const [idx, card] of cards.entries()) {
    addCard(slide, template, xs[idx], 2.08, 2.1, 2.0, card, {
      fill: idx === 0 ? "F8EEE6" : "FFFDFC",
      stroke: idx === 0 ? template.accentColor : "D4C6B7",
      bodyFontSize: 10.4
    });
    if (idx < cards.length - 1) {
      addArrowConnector(slide, xs[idx] + 2.18, 3.08, xs[idx + 1] - 0.14, 3.08, template.accentColor, 1.7);
    }
  }
  addSummaryLine(slide, "临床 → 通路线索 → 动物验证 → 细胞闭环", 0.92, 4.38, 10.8, template, {
    fontSize: 11.2,
    color: template.accentColor
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 5.95, 0.72);
  addFooter(slide, index, total, template);
}

function addStudyStackRightSlide(slide, deckSlide, template, index, total) {
  const fontSize = 16;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 0.88,
    y: 1.42,
    w: 5.55,
    h: 4.35,
    fontFace: template.bodyFont,
    fontSize,
    color: template.bodyColor,
    margin: 0.07,
    valign: "top"
  });
  slide.addShape("roundRect", {
    x: 6.62,
    y: 1.32,
    w: 5.42,
    h: 4.62,
    rectRadius: 0.08,
    fill: { color: "FFFDFC" },
    line: { color: "D9CCBE", pt: 1.0 }
  });
  addBadge(slide, deckSlide.diagram_v4.badge, 6.9, 1.56, template, 1.6);
  addSummaryLine(slide, deckSlide.diagram_v4.summary, 6.92, 1.93, 4.5, template, { fontSize: 9.8 });
  const cards = deckSlide.diagram_v4.cards || [];
  const cardX = 7.05;
  const cardW = 4.62;
  const cardY0 = 2.28;
  const cardH = 0.73;
  for (const [idx, card] of cards.entries()) {
    const y = cardY0 + idx * 0.82;
    slide.addShape("line", {
      x: 6.88,
      y: y + 0.08,
      w: 0,
      h: cardH,
      line: { color: idx === 0 ? template.accentColor : "C9B8A6", pt: 2.0 }
    });
    slide.addShape("roundRect", {
      x: 6.74,
      y: y + 0.2,
      w: 0.32,
      h: 0.24,
      rectRadius: 0.06,
      fill: { color: template.heroBackgroundColor || "1C2A39" },
      line: { color: template.heroBackgroundColor || "1C2A39", transparency: 100 }
    });
    slide.addText(card.stage, {
      x: 6.74,
      y: y + 0.23,
      w: 0.32,
      h: 0.12,
      fontFace: template.bodyFont,
      fontSize: 7.8,
      color: template.heroTitleColor || "F6F2EB",
      bold: true,
      align: "center",
      margin: 0
    });
    addCard(slide, template, cardX, y, cardW, cardH, card, {
      headerH: 0.22,
      titleFontSize: 11.4,
      bodyFontSize: 9.2,
      fill: idx % 2 === 0 ? "FAF3EC" : "FFFDFC",
      stroke: idx % 2 === 0 ? template.accentColor : "D4C6B7",
      pt: 0.95
    });
    if (idx < cards.length - 1) {
      addArrowConnector(slide, 6.9, y + cardH, 6.9, y + 0.82, "B49D86", 1.2);
    }
  }
  addFigureCaption(slide, "V4 原生方法结构图：文字、卡片与箭头全部由 PPT 原生对象构成。", template, 6.9, 5.84, 4.9);
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.15, 0.68);
  addFooter(slide, index, total, template);
}

function addEvidenceHorizontalSlide(slide, deckSlide, template, index, total) {
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addBadge(slide, deckSlide.diagram_v4.badge, 0.86, 1.12, template, 1.55);
  addSummaryLine(slide, deckSlide.diagram_v4.summary, 0.9, 1.48, 11.2, template, { fontSize: 10.5 });
  const xs = [0.92, 3.72, 6.52, 9.32];
  const cards = deckSlide.diagram_v4.cards || [];
  for (const [idx, card] of cards.entries()) {
    addCard(slide, template, xs[idx], 2.08, 2.32, 1.95, card, {
      fill: idx % 2 === 0 ? "F8EEE6" : "FFFDFC",
      stroke: idx % 2 === 0 ? template.accentColor : "D4C6B7",
      bodyFontSize: 10.2,
      titleFontSize: 12.2
    });
    if (idx < cards.length - 1) {
      addArrowConnector(slide, xs[idx] + 2.4, 3.03, xs[idx + 1] - 0.12, 3.03, template.accentColor, 1.6);
    }
  }
  addSummaryLine(slide, "四层证据并不是平铺堆叠，而是沿同一主线逐层收束。", 0.94, 4.35, 11.0, template, {
    fontSize: 11,
    color: template.accentColor
  });
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 0.95,
    y: 4.72,
    w: 10.95,
    h: 0.9,
    fontFace: template.bodyFont,
    fontSize: 12.8,
    color: template.bodyColor,
    margin: 0.03,
    valign: "top"
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.12, 0.58);
  addFooter(slide, index, total, template);
}

function addMechanismPanelsSlide(slide, deckSlide, template, index, total) {
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  slide.addShape("roundRect", {
    x: 0.82,
    y: 1.22,
    w: 11.72,
    h: 3.95,
    rectRadius: 0.08,
    fill: { color: "FFFDFC" },
    line: { color: "D4C6B7", pt: 1.0 }
  });
  const panels = deckSlide.diagram_v4.panels || [];
  const xs = [0.96, 4.2, 7.44];
  for (const [idx, panel] of panels.entries()) {
    addBadge(slide, panel.label, xs[idx] + 0.32, 1.52, template, 1.9);
    addImagePanel(slide, template, xs[idx], 1.84, 3.02, 2.95, panel);
    if (idx < panels.length - 1) {
      addArrowConnector(slide, xs[idx] + 3.12, 3.32, xs[idx + 1] - 0.14, 3.32, template.accentColor, 1.9);
    }
  }
  slide.addShape("roundRect", {
    x: 3.98,
    y: 4.5,
    w: 4.56,
    h: 0.52,
    rectRadius: 0.1,
    fill: { color: template.heroBackgroundColor || "1C2A39", transparency: 10 },
    line: { color: template.accentColor, pt: 1.1 }
  });
  slide.addText(deckSlide.diagram_v4.bridge_text, {
    x: 4.12,
    y: 4.63,
    w: 4.28,
    h: 0.18,
    fontFace: template.bodyFont,
    fontSize: 12.4,
    color: template.heroTitleColor || "F6F2EB",
    bold: true,
    align: "center",
    margin: 0
  });
  addFigureCaption(slide, "V4 元素拼装机制图：三块无字图像元素 + 外部箭头 + 可编辑中文标签。", template, 0.96, 5.05, 8.8);
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 0.95,
    y: 5.35,
    w: 10.95,
    h: 0.95,
    fontFace: template.bodyFont,
    fontSize: 13.2,
    color: template.bodyColor,
    margin: 0.03,
    valign: "top"
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.2, 0.55);
  addFooter(slide, index, total, template);
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args["spec-file"] || !args["template-file"] || !args["output-file"]) {
    throw new Error("Expected --spec-file, --template-file, and --output-file.");
  }

  const [specRaw, templateRaw] = await Promise.all([
    fs.readFile(args["spec-file"], "utf-8"),
    fs.readFile(args["template-file"], "utf-8")
  ]);
  const spec = JSON.parse(specRaw);
  const template = JSON.parse(templateRaw);

  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "Codex";
  pptx.subject = spec.title || "Defense Deck";
  pptx.company = "paper-to-defense-ppt";
  pptx.theme = {
    headFontFace: template.titleFont,
    bodyFontFace: template.bodyFont,
    lang: "zh-CN"
  };

  const totalSlides = (spec.slides || []).length;
  for (const [index, deckSlide] of (spec.slides || []).entries()) {
    const slide = pptx.addSlide();
    const bg = deckSlide.layout === "title" ? (template.heroBackgroundColor || template.backgroundColor) : template.backgroundColor;
    slide.background = { color: bg };

    if (deckSlide.layout === "title") {
      addTitleSlide(slide, deckSlide, template);
    } else if (deckSlide.layout === "section") {
      addSectionSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.diagram_v4?.kind === "route-horizontal") {
      addRouteHorizontalSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.diagram_v4?.kind === "study-stack-right") {
      addStudyStackRightSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.diagram_v4?.kind === "evidence-horizontal") {
      addEvidenceHorizontalSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.diagram_v4?.kind === "mechanism-panels") {
      addMechanismPanelsSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else {
      addBulletSlide(slide, deckSlide, template, index + 1, totalSlides);
    }

    if (deckSlide.notes) {
      slide.addNotes(deckSlide.notes);
    }
  }

  const outputFile = path.resolve(args["output-file"]);
  await fs.mkdir(path.dirname(outputFile), { recursive: true });
  await pptx.writeFile({ fileName: outputFile });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
