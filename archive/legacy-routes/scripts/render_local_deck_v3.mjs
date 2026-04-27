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

function addBackgroundImage(slide, deckSlide) {
  if (!deckSlide.background_image?.path) return;
  slide.addImage({
    path: deckSlide.background_image.path,
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5,
    transparency: deckSlide.background_image.transparency ?? 0
  });
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
  if (deckSlide.background_image?.path) {
    slide.addImage({
      path: deckSlide.background_image.path,
      x: 0,
      y: 0,
      w: 13.333,
      h: 7.5,
      transparency: deckSlide.background_image.transparency ?? 0
    });
    slide.addShape("rect", {
      x: 0,
      y: 0,
      w: 13.333,
      h: 7.5,
      fill: { color: template.heroBackgroundColor || template.backgroundColor, transparency: 34 },
      line: { color: template.heroBackgroundColor || template.backgroundColor, transparency: 100 }
    });
  }
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

function addOverlay(slide, overlay, template) {
  if (overlay.type === "label") {
    if (overlay.style === "chip") {
      slide.addShape("roundRect", {
        x: overlay.x,
        y: overlay.y,
        w: overlay.w,
        h: overlay.h,
        rectRadius: 0.08,
        fill: { color: "FFF7F1", transparency: 8 },
        line: { color: template.accentColor, pt: 1.2 }
      });
      slide.addText(overlay.text, {
        x: overlay.x + 0.08,
        y: overlay.y + 0.08,
        w: overlay.w - 0.16,
        h: overlay.h - 0.12,
        fontFace: template.bodyFont,
        fontSize: 13,
        color: template.titleColor,
        bold: true,
        align: "center",
        valign: "mid",
        margin: 0
      });
      return;
    }
    if (overlay.style === "hero-card") {
      slide.addShape("roundRect", {
        x: overlay.x,
        y: overlay.y,
        w: overlay.w,
        h: overlay.h,
        rectRadius: 0.1,
        fill: { color: template.heroBackgroundColor || "1C2A39", transparency: 8 },
        line: { color: template.accentColor, pt: 1.2 }
      });
      slide.addText(overlay.text, {
        x: overlay.x + 0.12,
        y: overlay.y + 0.12,
        w: overlay.w - 0.24,
        h: overlay.h - 0.2,
        fontFace: template.bodyFont,
        fontSize: 13,
        color: template.heroTitleColor || "F6F2EB",
        bold: true,
        align: "center",
        valign: "mid",
        margin: 0
      });
      return;
    }
  }
  if (overlay.type === "line") {
    slide.addShape("line", {
      x: overlay.x,
      y: overlay.y,
      w: overlay.w,
      h: overlay.h,
      line: {
        color: overlay.color || template.accentColor,
        pt: overlay.pt || 1.5,
        beginArrowType: overlay.beginArrowType || "none",
        endArrowType: overlay.endArrowType || "none"
      }
    });
  }
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

function addFigureRightSlide(slide, deckSlide, template, index, total) {
  const fontSize = Math.max(estimateBodyFontSize(deckSlide) - 1, 14);
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 0.88,
    y: 1.32,
    w: 5.45,
    h: 4.35,
    fontFace: template.bodyFont,
    fontSize,
    color: template.bodyColor,
    margin: 0.07,
    valign: "top"
  });
  slide.addShape("roundRect", {
    x: 6.7,
    y: 1.28,
    w: 5.2,
    h: 4.25,
    rectRadius: 0.06,
    fill: { color: "FFFDFC" },
    line: { color: "D8CFC3", pt: 1 }
  });
  slide.addImage({
    path: deckSlide.figure.path,
    x: 6.85,
    y: 1.43,
    w: 4.9,
    h: 3.82
  });
  addFigureCaption(slide, deckSlide.figure.caption, template, 6.9, 5.34, 4.88);
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.0, 0.68);
  addFooter(slide, index, total, template);
}

function addFigureFullSlide(slide, deckSlide, template, index, total) {
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  slide.addShape("roundRect", {
    x: 0.82,
    y: 1.22,
    w: 11.7,
    h: 3.95,
    rectRadius: 0.06,
    fill: { color: "FFFDFC", transparency: 4 },
    line: { color: "D8CFC3", pt: 1 }
  });
  if (deckSlide.figure?.backdrop_path) {
    slide.addImage({
      path: deckSlide.figure.backdrop_path,
      x: 0.95,
      y: 1.34,
      w: 11.42,
      h: 3.66,
      transparency: deckSlide.figure.backdrop_transparency ?? 0
    });
  }
  slide.addImage({
    path: deckSlide.figure.path,
    x: 0.98,
    y: 1.38,
    w: 11.38,
    h: 3.62
  });
  for (const overlay of deckSlide.figure?.overlays || []) {
    addOverlay(slide, overlay, template);
  }
  addFigureCaption(slide, deckSlide.figure.caption, template, 0.98, 5.04, 11.2);
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 0.95,
    y: 5.42,
    w: 10.95,
    h: 0.95,
    fontFace: template.bodyFont,
    fontSize: 13.5,
    color: template.bodyColor,
    margin: 0.04,
    valign: "top"
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.38, 0.48);
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
    addBackgroundImage(slide, deckSlide);

    if (deckSlide.layout === "title") {
      addTitleSlide(slide, deckSlide, template);
    } else if (deckSlide.layout === "section") {
      addSectionSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.figure && deckSlide.layout_hint === "figure-right") {
      addFigureRightSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.figure && deckSlide.layout_hint === "figure-full") {
      addFigureFullSlide(slide, deckSlide, template, index + 1, totalSlides);
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
