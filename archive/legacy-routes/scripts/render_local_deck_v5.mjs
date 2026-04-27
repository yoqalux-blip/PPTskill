import fs from "node:fs";
import fsp from "node:fs/promises";
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

function resolveDrawioAsset(deckSlide) {
  const candidates = [];
  if (deckSlide.drawio_asset?.path) candidates.push(deckSlide.drawio_asset);
  if (deckSlide.drawio_backend?.exported_asset?.path) candidates.push(deckSlide.drawio_backend.exported_asset);
  if (Array.isArray(deckSlide.drawio_backend?.exported_assets)) {
    candidates.push(...deckSlide.drawio_backend.exported_assets);
  }
  for (const candidate of candidates) {
    if (!candidate?.path) continue;
    if (fs.existsSync(candidate.path)) {
      return {
        path: candidate.path,
        format: candidate.format || path.extname(candidate.path).slice(1).toLowerCase()
      };
    }
  }
  return null;
}

function addContainedAssetPanel(slide, template, x, y, w, h, asset) {
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: "FFFDFC" },
    line: { color: "D4C6B7", pt: 1.05 }
  });
  slide.addImage({
    path: asset.path,
    x: x + 0.1,
    y: y + 0.1,
    w: w - 0.2,
    h: h - 0.2,
    sizing: {
      type: "contain",
      w: w - 0.2,
      h: h - 0.2
    }
  });
}

function drawioCaption(deckSlide, asset) {
  const label = asset.format === "svg" ? "draw.io SVG 导出图" : "draw.io PNG 导出图";
  if (deckSlide.visual_type === "process-flow") return `${label}：技术路线图已切换为 draw.io 正式后端。`;
  if (deckSlide.visual_type === "study-design") return `${label}：研究设计图已切换为 draw.io 正式后端。`;
  if (deckSlide.visual_type === "evidence-chain") return `${label}：证据链整合图已切换为 draw.io 正式后端。`;
  return label;
}

function resolveGeminiHybrid(deckSlide) {
  if (deckSlide.visual_route !== "gemini-editable-hybrid") return null;
  return deckSlide.gemini_hybrid || null;
}

function resolvePageRasterAsset(deckSlide) {
  if (deckSlide.visual_route !== "gemini-page-raster") return null;
  const asset = deckSlide.raster_asset;
  if (asset?.path && fs.existsSync(asset.path)) return asset;
  return null;
}

function resolveTemplateAsset(template, relativePath) {
  if (!relativePath) return null;
  if (path.isAbsolute(relativePath)) return relativePath;
  const templateDir = template.__templateDir || process.cwd();
  return path.resolve(templateDir, relativePath);
}

function addBrandOverlay(slide, template) {
  const brand = template.brand;
  if (!brand) return;
  const erase = brand.eraseZone;
  if (erase) {
    slide.addShape("rect", {
      x: erase.x,
      y: erase.y,
      w: erase.w,
      h: erase.h,
      fill: { color: "FFFFFF" },
      line: { color: "FFFFFF", transparency: 100 }
    });
  }
  const logoPath = resolveTemplateAsset(template, brand.logoPath);
  if (logoPath && fs.existsSync(logoPath) && brand.logoRect) {
    slide.addImage({
      path: logoPath,
      x: brand.logoRect.x,
      y: brand.logoRect.y,
      w: brand.logoRect.w,
      h: brand.logoRect.h
    });
  }
  if (brand.nameZh && brand.textZhRect) {
    slide.addText(brand.nameZh, {
      x: brand.textZhRect.x,
      y: brand.textZhRect.y,
      w: brand.textZhRect.w,
      h: brand.textZhRect.h,
      fontFace: template.titleFont,
      fontSize: 11.5,
      color: brand.textColor || template.accentColor,
      bold: true,
      margin: 0,
      align: "left"
    });
  }
  if (brand.nameEn && brand.textEnRect) {
    slide.addText(brand.nameEn, {
      x: brand.textEnRect.x,
      y: brand.textEnRect.y,
      w: brand.textEnRect.w,
      h: brand.textEnRect.h,
      fontFace: template.bodyFont,
      fontSize: 5.8,
      color: brand.textColor || template.accentColor,
      bold: false,
      margin: 0,
      align: "left"
    });
  }
}

function resolveGeminiAsset(deckSlide, slotId = null) {
  const hybrid = resolveGeminiHybrid(deckSlide);
  if (!hybrid || !Array.isArray(hybrid.generated_assets)) return null;
  for (const asset of hybrid.generated_assets) {
    if (slotId && asset.slot_id !== slotId) continue;
    if (asset?.path && fs.existsSync(asset.path)) return asset;
  }
  return null;
}

function fontScaleFromSchema(schema) {
  return schema?.density_mode === "compact" ? 0.92 : 1.0;
}

function addHybridAsset(slide, asset, slot) {
  if (!asset || !slot) return;
  slide.addImage({
    path: asset.path,
    x: slot.x,
    y: slot.y,
    w: slot.w,
    h: slot.h
  });
}

function addRailPanel(slide, x, y, w, h, title, items, fill, stroke, textColor, template) {
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: fill },
    line: { color: stroke, pt: 1.0 }
  });
  slide.addText(title, {
    x: x + 0.08,
    y: y + 0.1,
    w: w - 0.16,
    h: 0.28,
    fontFace: template.bodyFont,
    fontSize: 9.6,
    color: textColor,
    bold: true,
    align: "center",
    margin: 0
  });
  slide.addText((items || []).join("\n"), {
    x: x + 0.06,
    y: y + 0.48,
    w: w - 0.12,
    h: h - 0.58,
    fontFace: template.bodyFont,
    fontSize: 8.1,
    color: template.bodyColor,
    align: "center",
    margin: 0.01
  });
}

function addConnectorLine(slide, connector, from, to) {
  addArrowConnector(slide, from.x, from.y, to.x, to.y, connector?.color || "8A5A44", 1.25);
}

function addChip(slide, text, x, y, w, h, fill, color, fontSize = 9, lineColor = null) {
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: fill },
    line: { color: lineColor || fill, transparency: lineColor ? 0 : 100, pt: 1.0 }
  });
  slide.addText(text, {
    x,
    y: y + 0.04,
    w,
    h: h - 0.04,
    fontFace: "Aptos",
    fontSize,
    color,
    bold: true,
    align: "center",
    margin: 0.01
  });
}

function addCenterHub(slide, template, x, y, w, h, title, body) {
  slide.addShape("ellipse", {
    x,
    y,
    w,
    h,
    fill: { color: "FFFDFC" },
    line: { color: template.accentColor, pt: 1.6 }
  });
  slide.addText(title, {
    x: x + 0.2,
    y: y + 0.18,
    w: w - 0.4,
    h: 0.2,
    fontFace: template.bodyFont,
    fontSize: 13,
    color: template.titleColor,
    bold: true,
    align: "center",
    margin: 0
  });
  slide.addText(body, {
    x: x + 0.24,
    y: y + 0.45,
    w: w - 0.48,
    h: h - 0.6,
    fontFace: template.bodyFont,
    fontSize: 9.5,
    color: template.bodyColor,
    align: "center",
    valign: "mid",
    margin: 0.02
  });
}

function addDenseBoardFrame(slide, x, y, w, h) {
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: "FFFDFC" },
    line: { color: "D8CBBE", pt: 1.0 }
  });
}

function addRouteBoardAssetSlide(slide, deckSlide, template, index, total, asset) {
  const diagram = deckSlide.diagram_v5;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addDenseBoardFrame(slide, 0.82, 1.22, 11.72, 4.95);
  addBadge(slide, diagram.badge, 1.0, 1.46, template, 1.9);
  addSummaryLine(slide, diagram.summary, 1.0, 1.82, 10.9, template, { fontSize: 10.3 });
  addContainedAssetPanel(slide, template, 1.0, 2.18, 10.96, 3.42, asset);
  addFigureCaption(slide, drawioCaption(deckSlide, asset), template, 1.04, 5.66, 10.9);
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.18, 0.56);
  addFooter(slide, index, total, template);
}

function addStudyBoardAssetSlide(slide, deckSlide, template, index, total, asset) {
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 0.86,
    y: 1.38,
    w: 5.35,
    h: 4.95,
    fontFace: template.bodyFont,
    fontSize: 14.5,
    color: template.bodyColor,
    margin: 0.06,
    valign: "top"
  });

  addDenseBoardFrame(slide, 6.35, 1.3, 5.88, 4.95);
  addBadge(slide, deckSlide.diagram_v5.badge, 6.68, 1.6, template, 1.72);
  addSummaryLine(slide, deckSlide.diagram_v5.summary, 6.68, 1.98, 4.95, template, { fontSize: 9.8 });
  addContainedAssetPanel(slide, template, 6.68, 2.28, 5.22, 3.22, asset);
  addFigureCaption(slide, drawioCaption(deckSlide, asset), template, 6.72, 5.58, 5.1);
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.42, 0.5);
  addFooter(slide, index, total, template);
}

function addEvidenceBoardAssetSlide(slide, deckSlide, template, index, total, asset) {
  const diagram = deckSlide.diagram_v5;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addDenseBoardFrame(slide, 0.84, 1.24, 11.7, 4.45);
  addBadge(slide, diagram.badge, 1.02, 1.5, template, 1.72);
  addSummaryLine(slide, diagram.summary, 1.02, 1.86, 10.9, template, { fontSize: 10.0 });
  addContainedAssetPanel(slide, template, 1.04, 2.2, 10.96, 2.86, asset);
  addFigureCaption(slide, drawioCaption(deckSlide, asset), template, 1.08, 5.12, 10.7);
  slide.addText((deckSlide.bullets || []).slice(0, 2).map((item) => `- ${item}`).join("\n"), {
    x: 1.02,
    y: 5.44,
    w: 10.9,
    h: 0.42,
    fontFace: template.bodyFont,
    fontSize: 11.2,
    color: template.bodyColor,
    margin: 0.01
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.12, 0.5);
  addFooter(slide, index, total, template);
}

function addGeminiHybridRouteBoardSlide(slide, deckSlide, template, index, total) {
  const hybrid = resolveGeminiHybrid(deckSlide);
  const schema = hybrid?.layout_schema;
  const asset = resolveGeminiAsset(deckSlide, "route-plate");
  if (!schema || !asset) {
    addRouteBoardSlide(slide, deckSlide, template, index, total);
    return;
  }
  const diagram = deckSlide.diagram_v5;
  const scale = fontScaleFromSchema(schema);
  const board = schema.canvas_regions.board;
  const summary = schema.canvas_regions.summary;
  const leftRail = schema.canvas_regions.left_rail;
  const rightRail = schema.canvas_regions.right_rail;
  const center = schema.canvas_regions.center_hub;
  const cards = schema.cards || [];
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addDenseBoardFrame(slide, board.x, board.y, board.w, board.h);
  addBadge(slide, diagram.badge, 1.02, 1.42, template, 1.9);
  addSummaryLine(slide, diagram.summary, summary.x, summary.y, summary.w, template, { fontSize: summary.font_size || 10.0 });
  addHybridAsset(slide, asset, schema.background_asset_slots?.[0]);
  addRailPanel(slide, leftRail.x, leftRail.y, leftRail.w, leftRail.h, diagram.left_rail?.title, diagram.left_rail?.items, "F4F8FF", "5A86C4", "2E58A6", template);
  addRailPanel(slide, rightRail.x, rightRail.y, rightRail.w, rightRail.h, diagram.right_rail?.title, diagram.right_rail?.items, "FAF4FB", "B275B7", "8A4C92", template);

  cards.slice(0, 4).forEach((slot, idx) => {
    const card = diagram.cards?.[idx];
    if (!card) return;
    addCard(slide, template, slot.x, slot.y, slot.w, slot.h, card, {
      headerH: 0.24,
      titleFontSize: 11.2 * scale,
      bodyFontSize: 9.0 * scale,
      fill: "FFFFFF",
      stroke: slot.stroke,
      headerFill: slot.header_fill,
    });
    const from = { x: slot.x + slot.w / 2, y: slot.y + slot.h + 0.02 };
    const toY = schema.connector_style === "outer" ? center.y + 0.2 : center.y + center.h / 2;
    const to = { x: center.x + (idx + 0.5) * (center.w / 4), y: toY };
    addConnectorLine(slide, schema.connectors?.[idx], from, to);
  });

  addCenterHub(slide, template, center.x, center.y, center.w, center.h, diagram.center?.title, diagram.center?.body);

  const outputTitles = ["疗效层结论", "机制层结论", "整合层结论"];
  cards.slice(4, 7).forEach((slot, idx) => {
    addCard(slide, template, slot.x, slot.y, slot.w, slot.h, {
      title: outputTitles[idx],
      body: [diagram.outputs?.[idx] || ""],
    }, {
      headerH: 0.22,
      titleFontSize: 10.8 * scale,
      bodyFontSize: 8.8 * scale,
      fill: "FFFFFF",
      stroke: slot.stroke,
      headerFill: slot.header_fill,
    });
    const from = { x: center.x + center.w / 2, y: center.y + center.h - 0.02 };
    const to = { x: slot.x + slot.w / 2, y: slot.y - 0.02 };
    addConnectorLine(slide, schema.connectors?.[idx + 4], from, to);
  });

  addTakeawayBox(slide, deckSlide.takeaway, template, schema.text_slots?.takeaway?.y || 0.5);
  addFooter(slide, index, total, template);
}

function addGeminiHybridStudyBoardSlide(slide, deckSlide, template, index, total) {
  const hybrid = resolveGeminiHybrid(deckSlide);
  const schema = hybrid?.layout_schema;
  const asset = resolveGeminiAsset(deckSlide, "study-plate");
  if (!schema || !asset) {
    addStudyBoardSlide(slide, deckSlide, template, index, total);
    return;
  }
  const diagram = deckSlide.diagram_v5;
  const scale = fontScaleFromSchema(schema);
  const board = schema.canvas_regions.board;
  const summary = schema.canvas_regions.summary;
  const leftText = schema.canvas_regions.left_text;
  const rail = schema.canvas_regions.rail;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: leftText.x,
    y: leftText.y,
    w: leftText.w,
    h: leftText.h,
    fontFace: template.bodyFont,
    fontSize: leftText.font_size || 14.0,
    color: template.bodyColor,
    margin: 0.06,
    valign: "top"
  });
  addDenseBoardFrame(slide, board.x, board.y, board.w, board.h);
  addBadge(slide, diagram.badge, 6.68, 1.54, template, 1.72);
  addSummaryLine(slide, diagram.summary, summary.x, summary.y, summary.w, template, { fontSize: summary.font_size || 9.8 });
  addHybridAsset(slide, asset, schema.background_asset_slots?.[0]);
  slide.addShape("line", {
    x: rail.x,
    y: rail.y,
    w: 0,
    h: rail.h,
    line: { color: "CDBBA9", pt: 1.2 }
  });
  (schema.cards || []).forEach((slot, idx) => {
    const card = diagram.cards?.[idx];
    if (!card) return;
    addChip(slide, card.stage, rail.x - 0.18, slot.y + 0.16, 0.34, 0.24, "1C2A39", "F6F2EB", 8.6);
    addCard(slide, template, slot.x, slot.y, slot.w, slot.h, card, {
      headerH: 0.2,
      titleFontSize: 10.8 * scale,
      bodyFontSize: 8.7 * scale,
      fill: "FFFFFF",
      stroke: slot.stroke,
      headerFill: slot.header_fill,
    });
    if (idx < schema.cards.length - 1) {
      addArrowConnector(slide, rail.x, slot.y + slot.h, rail.x, schema.cards[idx + 1].y, "B49D86", 1.0);
    }
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, schema.text_slots?.takeaway?.y || 0.5);
  addFooter(slide, index, total, template);
}

function addGeminiHybridEvidenceBoardSlide(slide, deckSlide, template, index, total) {
  const hybrid = resolveGeminiHybrid(deckSlide);
  const schema = hybrid?.layout_schema;
  const asset = resolveGeminiAsset(deckSlide, "evidence-plate");
  if (!schema || !asset) {
    addEvidenceBoardSlide(slide, deckSlide, template, index, total);
    return;
  }
  const diagram = deckSlide.diagram_v5;
  const scale = fontScaleFromSchema(schema);
  const board = schema.canvas_regions.board;
  const summary = schema.canvas_regions.summary;
  const center = schema.canvas_regions.center_hub;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addDenseBoardFrame(slide, board.x, board.y, board.w, board.h);
  addBadge(slide, diagram.badge, 1.02, 1.48, template, 1.72);
  addSummaryLine(slide, diagram.summary, summary.x, summary.y, summary.w, template, { fontSize: summary.font_size || 10.0 });
  addHybridAsset(slide, asset, schema.background_asset_slots?.[0]);
  (schema.cards || []).forEach((slot, idx) => {
    const card = diagram.cards?.[idx];
    if (!card) return;
    addCard(slide, template, slot.x, slot.y, slot.w, slot.h, card, {
      headerH: 0.24,
      titleFontSize: 10.8 * scale,
      bodyFontSize: 8.9 * scale,
      fill: "FFFFFF",
      stroke: slot.stroke,
      headerFill: slot.header_fill,
    });
    addConnectorLine(slide, schema.connectors?.[idx], { x: slot.x + slot.w / 2, y: slot.y + slot.h / 2 }, { x: center.x + center.w / 2, y: center.y + center.h / 2 });
  });
  addCenterHub(slide, template, center.x, center.y, center.w, center.h, diagram.center?.title, diagram.center?.body);
  slide.addText((deckSlide.bullets || []).slice(0, 2).map((item) => `- ${item}`).join("\n"), {
    x: schema.canvas_regions.bullet_strip.x,
    y: schema.canvas_regions.bullet_strip.y,
    w: schema.canvas_regions.bullet_strip.w,
    h: schema.canvas_regions.bullet_strip.h,
    fontFace: template.bodyFont,
    fontSize: schema.canvas_regions.bullet_strip.font_size || 11.0,
    color: template.bodyColor,
    margin: 0.01
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, schema.text_slots?.takeaway?.y || 0.5);
  addFooter(slide, index, total, template);
}

function addGeminiHybridMechanismBoardSlide(slide, deckSlide, template, index, total) {
  const hybrid = resolveGeminiHybrid(deckSlide);
  const schema = hybrid?.layout_schema;
  const asset = resolveGeminiAsset(deckSlide, "mechanism-plate");
  if (!schema || !asset) {
    addMechanismPanelsCleanSlide(slide, deckSlide, template, index, total);
    return;
  }
  const diagram = deckSlide.diagram_v5;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addDenseBoardFrame(slide, schema.canvas_regions.board.x, schema.canvas_regions.board.y, schema.canvas_regions.board.w, schema.canvas_regions.board.h);
  addSummaryLine(slide, diagram.summary, schema.canvas_regions.summary.x, schema.canvas_regions.summary.y, schema.canvas_regions.summary.w, template, {
    fontSize: schema.canvas_regions.summary.font_size || 10.0,
    color: template.accentColor
  });
  addHybridAsset(slide, asset, schema.background_asset_slots?.[0]);
  (schema.overlay_labels || []).forEach((item) => {
    addChip(slide, item.text, item.x, item.y, item.w, item.h, "F3E8DE", template.accentColor, 9.0);
  });
  (schema.connectors || []).forEach((connector) => {
    addArrowConnector(slide, connector.x1, connector.y1, connector.x2, connector.y2, connector.color || template.accentColor, 1.8);
  });
  slide.addShape("roundRect", {
    x: schema.canvas_regions.bridge.x,
    y: schema.canvas_regions.bridge.y,
    w: schema.canvas_regions.bridge.w,
    h: schema.canvas_regions.bridge.h,
    rectRadius: 0.08,
    fill: { color: "1C2A39", transparency: 6 },
    line: { color: template.accentColor, pt: 1.0 }
  });
  slide.addText(diagram.bridge_text, {
    x: schema.canvas_regions.bridge.x + 0.12,
    y: schema.canvas_regions.bridge.y + 0.1,
    w: schema.canvas_regions.bridge.w - 0.24,
    h: schema.canvas_regions.bridge.h - 0.14,
    fontFace: template.bodyFont,
    fontSize: 11.0,
    color: "F6F2EB",
    bold: true,
    align: "center",
    margin: 0
  });
  slide.addText((deckSlide.bullets || []).slice(0, 2).map((item) => `- ${item}`).join("\n"), {
    x: schema.canvas_regions.bullet_strip.x,
    y: schema.canvas_regions.bullet_strip.y,
    w: schema.canvas_regions.bullet_strip.w,
    h: schema.canvas_regions.bullet_strip.h,
    fontFace: template.bodyFont,
    fontSize: schema.canvas_regions.bullet_strip.font_size || 11.3,
    color: template.bodyColor,
    margin: 0.02
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, schema.text_slots?.takeaway?.y || 0.56);
  addFooter(slide, index, total, template);
}

function addGeminiPageRasterSlide(slide, deckSlide, template, index, total) {
  const asset = resolvePageRasterAsset(deckSlide);
  if (!asset) {
    addBulletSlide(slide, deckSlide, template, index, total);
    return;
  }
  slide.addImage({
    path: asset.path,
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5
  });
}

function addRouteBoardSlide(slide, deckSlide, template, index, total) {
  const drawioAsset = resolveDrawioAsset(deckSlide);
  if (drawioAsset) {
    addRouteBoardAssetSlide(slide, deckSlide, template, index, total, drawioAsset);
    return;
  }
  const diagram = deckSlide.diagram_v5;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addDenseBoardFrame(slide, 0.82, 1.22, 11.72, 4.95);
  addBadge(slide, diagram.badge, 1.0, 1.46, template, 1.9);
  addSummaryLine(slide, diagram.summary, 1.0, 1.82, 10.9, template, { fontSize: 10.3 });

  const chipColors = ["E9F1FA", "F3E8DE", "EFE8F7", "E8F1EB"];
  const chipTextColors = ["436B94", template.accentColor, "7A6291", "5D7A64"];
  (diagram.goal_chips || []).forEach((item, idx) => {
    addChip(slide, item, 1.02 + idx * 2.56, 2.16, 2.22, 0.32, chipColors[idx], chipTextColors[idx], 9.2);
  });

  slide.addShape("roundRect", {
    x: 1.0,
    y: 2.75,
    w: 1.48,
    h: 1.2,
    rectRadius: 0.08,
    fill: { color: "FAF3EC" },
    line: { color: template.accentColor, pt: 1.1 }
  });
  addChip(slide, diagram.left_rail.title, 1.12, 2.88, 1.24, 0.28, template.accentColor, "F6F2EB", 8.5);
  slide.addText((diagram.left_rail.items || []).join("\n"), {
    x: 1.16,
    y: 3.22,
    w: 1.16,
    h: 0.6,
    fontFace: template.bodyFont,
    fontSize: 8.8,
    color: template.bodyColor,
    margin: 0.01,
    align: "center"
  });

  slide.addShape("roundRect", {
    x: 10.06,
    y: 2.75,
    w: 1.48,
    h: 1.2,
    rectRadius: 0.08,
    fill: { color: "F8F1FB" },
    line: { color: "A77FA4", pt: 1.1 }
  });
  addChip(slide, diagram.right_rail.title, 10.18, 2.88, 1.24, 0.28, "A77FA4", "F6F2EB", 8.5);
  slide.addText((diagram.right_rail.items || []).join("\n"), {
    x: 10.2,
    y: 3.22,
    w: 1.14,
    h: 0.6,
    fontFace: template.bodyFont,
    fontSize: 8.8,
    color: template.bodyColor,
    margin: 0.01,
    align: "center"
  });

  addCenterHub(slide, template, 4.73, 2.52, 3.06, 1.48, diagram.center.title, diagram.center.body);
  addArrowConnector(slide, 2.52, 3.35, 4.58, 3.35, template.accentColor, 1.5);
  addArrowConnector(slide, 7.88, 3.35, 9.92, 3.35, "A77FA4", 1.5);

  const xs = [1.18, 3.93, 6.68, 9.43];
  const fills = ["F9EFE7", "EEF4FB", "F3EDF9", "EEF5F1"];
  const strokes = [template.accentColor, "6B92BA", "8F77A4", "6E8E7B"];
  (diagram.cards || []).forEach((card, idx) => {
    addCard(slide, template, xs[idx], 4.1, 2.18, 1.15, card, {
      headerH: 0.24,
      titleFontSize: 11.5,
      bodyFontSize: 9.3,
      fill: fills[idx],
      stroke: strokes[idx]
    });
    addArrowConnector(slide, 6.26, 4.0, xs[idx] + 1.09, 4.08, idx < 2 ? template.accentColor : "8F77A4", 1.2);
  });

  addSummaryLine(slide, "四级主线并非平铺堆积，而是围绕同一个核心问题逐层推进。", 1.02, 5.42, 7.6, template, {
    fontSize: 10.2,
    color: template.accentColor
  });
  (diagram.outputs || []).forEach((item, idx) => {
    addChip(slide, item, 7.88 + idx * 1.47, 5.34, 1.32, 0.3, "1C2A39", "F6F2EB", 8.2);
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.36, 0.46);
  addFooter(slide, index, total, template);
}

function addStudyBoardSlide(slide, deckSlide, template, index, total) {
  const drawioAsset = resolveDrawioAsset(deckSlide);
  if (drawioAsset) {
    addStudyBoardAssetSlide(slide, deckSlide, template, index, total, drawioAsset);
    return;
  }
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  slide.addText((deckSlide.bullets || []).map((item) => `- ${item}`).join("\n"), {
    x: 0.86,
    y: 1.38,
    w: 5.35,
    h: 4.95,
    fontFace: template.bodyFont,
    fontSize: 14.5,
    color: template.bodyColor,
    margin: 0.06,
    valign: "top"
  });

  addDenseBoardFrame(slide, 6.35, 1.3, 5.88, 4.95);
  addBadge(slide, deckSlide.diagram_v5.badge, 6.68, 1.6, template, 1.72);
  addSummaryLine(slide, deckSlide.diagram_v5.summary, 6.68, 1.98, 4.95, template, { fontSize: 9.8 });

  slide.addShape("line", {
    x: 6.98,
    y: 2.38,
    w: 0,
    h: 2.85,
    line: { color: "CDBBA9", pt: 1.4 }
  });

  (deckSlide.diagram_v5.cards || []).forEach((card, idx) => {
    const y = 2.32 + idx * 0.78;
    addChip(slide, card.stage, 6.82, y + 0.12, 0.34, 0.24, "1C2A39", "F6F2EB", 8.6);
    addCard(slide, template, 7.28, y, 4.56, 0.68, card, {
      headerH: 0.2,
      titleFontSize: 10.9,
      bodyFontSize: 8.8,
      fill: idx % 2 === 0 ? "FAF3EC" : "FFFDFC",
      stroke: idx % 2 === 0 ? template.accentColor : "D4C6B7"
    });
    if (idx < 3) {
      slide.addShape("line", {
        x: 6.98,
        y: y + 0.36,
        w: 0,
        h: 0.42,
        line: { color: "CDBBA9", pt: 1.2, endArrowType: "triangle" }
      });
    }
  });

  (deckSlide.diagram_v5.bottom_chips || []).forEach((item, idx) => {
    addChip(slide, item, 7.16 + idx * 1.12, 5.62, 0.98, 0.26, "EFE4D9", template.accentColor, 8.0);
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.42, 0.5);
  addFooter(slide, index, total, template);
}

function addEvidenceBoardSlide(slide, deckSlide, template, index, total) {
  const drawioAsset = resolveDrawioAsset(deckSlide);
  if (drawioAsset) {
    addEvidenceBoardAssetSlide(slide, deckSlide, template, index, total, drawioAsset);
    return;
  }
  const diagram = deckSlide.diagram_v5;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addDenseBoardFrame(slide, 0.84, 1.24, 11.7, 4.45);
  addBadge(slide, diagram.badge, 1.02, 1.5, template, 1.72);
  addSummaryLine(slide, diagram.summary, 1.02, 1.86, 10.9, template, { fontSize: 10.0 });

  const positions = [
    { x: 1.1, y: 2.25, fill: "F9EFE7", stroke: template.accentColor },
    { x: 8.18, y: 2.25, fill: "EEF4FB", stroke: "6B92BA" },
    { x: 1.1, y: 4.0, fill: "F3EDF9", stroke: "8F77A4" },
    { x: 8.18, y: 4.0, fill: "EEF5F1", stroke: "6E8E7B" }
  ];
  (diagram.cards || []).forEach((card, idx) => {
    const pos = positions[idx];
    addCard(slide, template, pos.x, pos.y, 3.05, 1.08, card, {
      headerH: 0.24,
      titleFontSize: 11.0,
      bodyFontSize: 9.2,
      fill: pos.fill,
      stroke: pos.stroke
    });
  });

  addCenterHub(slide, template, 4.68, 3.0, 3.0, 1.0, diagram.center.title, diagram.center.body);
  addArrowConnector(slide, 4.12, 2.82, 4.66, 3.18, template.accentColor, 1.2);
  addArrowConnector(slide, 8.12, 2.82, 7.72, 3.18, "6B92BA", 1.2);
  addArrowConnector(slide, 4.12, 4.52, 4.66, 3.84, "8F77A4", 1.2);
  addArrowConnector(slide, 8.12, 4.52, 7.72, 3.84, "6E8E7B", 1.2);

  slide.addText((deckSlide.bullets || []).slice(0, 2).map((item) => `- ${item}`).join("\n"), {
    x: 1.02,
    y: 5.84,
    w: 10.9,
    h: 0.42,
    fontFace: template.bodyFont,
    fontSize: 11.5,
    color: template.bodyColor,
    margin: 0.01
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.38, 0.46);
  addFooter(slide, index, total, template);
}

function addMechanismPanelsCleanSlide(slide, deckSlide, template, index, total) {
  const diagram = deckSlide.diagram_v5;
  addHeaderChrome(slide, template, deckSlide.title, sectionLabelForTitle(deckSlide.title || ""));
  addDenseBoardFrame(slide, 0.84, 1.24, 11.7, 4.15);
  addSummaryLine(slide, diagram.summary, 1.02, 1.45, 10.9, template, { fontSize: 10.0, color: template.accentColor });

  const xs = [1.02, 4.24, 7.46];
  (diagram.panels || []).forEach((panel, idx) => {
    addChip(slide, panel.label, xs[idx] + 0.52, 1.74, 1.8, 0.28, "F3E8DE", template.accentColor, 9.0);
    addImagePanel(slide, template, xs[idx], 2.05, 2.9, 2.45, panel);
    if (idx < 2) {
      addArrowConnector(slide, xs[idx] + 2.98, 3.25, xs[idx + 1] - 0.08, 3.25, template.accentColor, 1.8);
    }
  });

  slide.addShape("roundRect", {
    x: 4.08,
    y: 4.68,
    w: 4.42,
    h: 0.32,
    rectRadius: 0.08,
    fill: { color: "1C2A39", transparency: 6 },
    line: { color: template.accentColor, pt: 1.0 }
  });
  slide.addText(diagram.bridge_text, {
    x: 4.2,
    y: 4.75,
    w: 4.18,
    h: 0.12,
    fontFace: template.bodyFont,
    fontSize: 11.0,
    color: "F6F2EB",
    bold: true,
    align: "center",
    margin: 0
  });
  slide.addText((deckSlide.bullets || []).slice(0, 2).map((item) => `- ${item}`).join("\n"), {
    x: 1.02,
    y: 5.18,
    w: 10.8,
    h: 0.54,
    fontFace: template.bodyFont,
    fontSize: 11.8,
    color: template.bodyColor,
    margin: 0.02
  });
  addTakeawayBox(slide, deckSlide.takeaway, template, 6.08, 0.54);
  addFooter(slide, index, total, template);
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
    fsp.readFile(args["spec-file"], "utf-8"),
    fsp.readFile(args["template-file"], "utf-8")
  ]);
  const spec = JSON.parse(specRaw);
  const template = JSON.parse(templateRaw);
  template.__templateDir = path.dirname(path.resolve(args["template-file"]));

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
    } else if (deckSlide.visual_route === "gemini-page-raster") {
      addGeminiPageRasterSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.visual_route === "gemini-editable-hybrid" && deckSlide.gemini_hybrid?.page_kind === "route-board") {
      addGeminiHybridRouteBoardSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.visual_route === "gemini-editable-hybrid" && deckSlide.gemini_hybrid?.page_kind === "study-board") {
      addGeminiHybridStudyBoardSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.visual_route === "gemini-editable-hybrid" && deckSlide.gemini_hybrid?.page_kind === "evidence-board") {
      addGeminiHybridEvidenceBoardSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.visual_route === "gemini-editable-hybrid" && deckSlide.gemini_hybrid?.page_kind === "mechanism-board") {
      addGeminiHybridMechanismBoardSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.diagram_v5?.kind === "route-board") {
      addRouteBoardSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.diagram_v5?.kind === "study-board") {
      addStudyBoardSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.diagram_v5?.kind === "evidence-board") {
      addEvidenceBoardSlide(slide, deckSlide, template, index + 1, totalSlides);
    } else if (deckSlide.diagram_v5?.kind === "mechanism-panels-clean") {
      addMechanismPanelsCleanSlide(slide, deckSlide, template, index + 1, totalSlides);
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
  await fsp.mkdir(path.dirname(outputFile), { recursive: true });
  await pptx.writeFile({ fileName: outputFile });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
