import path from "node:path";
import fs from "node:fs/promises";
import pptxgen from "pptxgenjs";

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
}

function addRounded(slide, x, y, w, h, fill, line, radius = 0.08) {
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: radius,
    fill,
    line
  });
}

function addPill(slide, text, x, y, w, h, options = {}) {
  addRounded(
    slide,
    x,
    y,
    w,
    h,
    { color: options.fill || "EAF0FA" },
    { color: options.stroke || options.fill || "EAF0FA", pt: options.pt || 0.8 },
    options.radius || 0.08
  );
  slide.addText(text, {
    x,
    y: y + 0.03,
    w,
    h: h - 0.04,
    fontFace: options.fontFace || "Microsoft YaHei",
    fontSize: options.fontSize || 9.8,
    color: options.color || "1B3559",
    bold: options.bold ?? true,
    align: "center",
    valign: "mid",
    margin: 0
  });
}

function addLabelChip(slide, text, x, y, fill, color = "FFFFFF", w = 0.56) {
  addRounded(
    slide,
    x,
    y,
    w,
    0.32,
    { color: fill },
    { color: fill, transparency: 100 },
    0.06
  );
  slide.addText(text, {
    x,
    y: y + 0.04,
    w,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 8.6,
    color,
    bold: true,
    align: "center",
    margin: 0
  });
}

function addModule(slide, config) {
  const {
    x,
    y,
    w,
    h,
    accent,
    light,
    title,
    body,
    code
  } = config;
  addRounded(slide, x, y, w, h, { color: "FFFFFF" }, { color: accent, pt: 1.15 }, 0.08);
  slide.addShape("rect", {
    x: x + 0.16,
    y: y + 0.12,
    w: w - 0.32,
    h: 0.26,
    fill: { color: light },
    line: { color: light, transparency: 100 }
  });
  if (code) {
    addLabelChip(slide, code, x - 0.28, y + 0.11, "20344A", "FFFFFF", 0.38);
  }
  slide.addText(title, {
    x: x + 0.2,
    y: y + 0.13,
    w: w - 0.4,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 11.8,
    color: "20344A",
    bold: true,
    margin: 0.01
  });
  slide.addText(body.join("\n"), {
    x: x + 0.22,
    y: y + 0.54,
    w: w - 0.42,
    h: h - 0.66,
    fontFace: "Microsoft YaHei",
    fontSize: 9.2,
    color: "2D3641",
    margin: 0.01,
    breakLine: false
  });
}

function addArrow(slide, x1, y1, x2, y2, color, pt = 1.5) {
  slide.addShape("line", {
    x: x1,
    y: y1,
    w: x2 - x1,
    h: y2 - y1,
    line: {
      color,
      pt,
      endArrowType: "triangle"
    }
  });
}

function addCenterHub(slide) {
  slide.addShape("ellipse", {
    x: 4.4,
    y: 2.45,
    w: 4.48,
    h: 2.16,
    fill: { color: "F8FBFF" },
    line: { color: "8FA8D6", pt: 1.15 }
  });
  slide.addShape("ellipse", {
    x: 5.22,
    y: 2.96,
    w: 2.84,
    h: 1.12,
    fill: { color: "2E58A6" },
    line: { color: "2E58A6", transparency: 100 }
  });
  slide.addText("核心科学问题", {
    x: 5.52,
    y: 3.1,
    w: 2.24,
    h: 0.2,
    fontFace: "Microsoft YaHei",
    fontSize: 15.2,
    color: "FFFFFF",
    bold: true,
    align: "center",
    margin: 0
  });
  slide.addText("HQQD 能否通过调控 CLUH/mTOR-\n自噬轴及炎症相关通路改善 MDR-KP 肺损伤？", {
    x: 4.86,
    y: 3.44,
    w: 3.56,
    h: 0.54,
    fontFace: "Microsoft YaHei",
    fontSize: 9.4,
    color: "FFFFFF",
    align: "center",
    valign: "mid",
    margin: 0.02
  });

  const orbit = [
    { x: 4.18, y: 2.2, w: 1.22, h: 0.34, text: "临床获益", fill: "EAF0FA", color: "2E58A6" },
    { x: 7.88, y: 2.2, w: 1.22, h: 0.34, text: "组学线索", fill: "F6EAF2", color: "A34775" },
    { x: 3.96, y: 4.38, w: 1.44, h: 0.34, text: "动物验证", fill: "EEF7EC", color: "2B8A5D" },
    { x: 7.66, y: 4.38, w: 1.44, h: 0.34, text: "细胞闭环", fill: "FFF1E3", color: "B46918" }
  ];
  orbit.forEach((item) => {
    addPill(slide, item.text, item.x, item.y, item.w, item.h, {
      fill: item.fill,
      stroke: item.fill,
      color: item.color,
      fontSize: 9.2
    });
  });

  addArrow(slide, 4.86, 2.6, 5.36, 2.9, "7B95C7", 1.2);
  addArrow(slide, 8.12, 2.6, 7.7, 2.9, "BA6A93", 1.2);
  addArrow(slide, 5.12, 4.35, 5.52, 4.05, "63A17D", 1.2);
  addArrow(slide, 8.14, 4.35, 7.76, 4.05, "CC8B39", 1.2);
}

function addSideRail(slide, x, title, items, fill, accent) {
  addRounded(slide, x, 1.52, 0.84, 4.9, { color: fill }, { color: accent, pt: 0.9 }, 0.08);
  slide.addText(title, {
    x: x + 0.14,
    y: 1.8,
    w: 0.56,
    h: 0.42,
    fontFace: "Microsoft YaHei",
    fontSize: 10.8,
    color: accent,
    bold: true,
    align: "center",
    margin: 0,
    rotate: 270
  });
  items.forEach((item, idx) => {
    addPill(slide, item, x + 0.12, 2.26 + idx * 0.78, 0.6, 0.34, {
      fill: "FFFFFF",
      stroke: accent,
      color: accent,
      fontSize: 8.1
    });
  });
}

function addBottomOutput(slide, x, title, body, accent, light) {
  addRounded(slide, x, 5.48, 2.74, 0.92, { color: "FFFFFF" }, { color: accent, pt: 1.0 }, 0.08);
  addPill(slide, title, x + 0.16, 5.6, 1.14, 0.28, {
    fill: light,
    stroke: light,
    color: accent,
    fontSize: 8.8
  });
  slide.addText(body.join("\n"), {
    x: x + 0.18,
    y: 5.94,
    w: 2.34,
    h: 0.32,
    fontFace: "Microsoft YaHei",
    fontSize: 8.8,
    color: "273341",
    margin: 0.01,
    align: "center"
  });
}

async function main() {
  const args = parseArgs(process.argv);
  const outputFile = path.resolve(
    args["output-file"] || "d:/PPTskills/paper-to-defense-ppt/runs/reference-route-map-sample/reference-route-map-sample.pptx"
  );

  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "Codex";
  pptx.subject = "Reference route map sample";
  pptx.company = "paper-to-defense-ppt";
  pptx.theme = {
    headFontFace: "Microsoft YaHei",
    bodyFontFace: "Microsoft YaHei",
    lang: "zh-CN"
  };

  const slide = pptx.addSlide();
  slide.background = { color: "FFFFFF" };

  slide.addText("技术路线图样板：HQQD 干预 MDR-KP 重症肺炎", {
    x: 0.48,
    y: 0.24,
    w: 8.4,
    h: 0.44,
    fontFace: "Microsoft YaHei",
    fontSize: 21.5,
    color: "20344A",
    bold: true,
    margin: 0
  });
  slide.addShape("line", {
    x: 0.5,
    y: 0.96,
    w: 3.2,
    h: 0,
    line: { color: "8A5A44", pt: 2.2 }
  });
  slide.addText("TECHNICAL ROUTE MAP", {
    x: 10.3,
    y: 0.36,
    w: 2.2,
    h: 0.18,
    fontFace: "Aptos",
    fontSize: 12.6,
    color: "8A5A44",
    bold: true,
    align: "right",
    margin: 0
  });

  addRounded(slide, 0.54, 1.14, 12.18, 5.98, { color: "FCFBF8" }, { color: "D3C6B7", pt: 1.0 }, 0.08);
  slide.addShape("rect", {
    x: 0.82,
    y: 1.36,
    w: 11.62,
    h: 0.18,
    fill: { color: "2E58A6" },
    line: { color: "2E58A6", transparency: 100 }
  });
  slide.addText("围绕“临床获益是否可被机制证据链支撑”构建高密度技术路线看板：上层交代研究起点，中层压缩核心科学问题，底层汇总机制与转化输出。", {
    x: 1.56,
    y: 1.65,
    w: 9.86,
    h: 0.34,
    fontFace: "Microsoft YaHei",
    fontSize: 10.6,
    color: "334152",
    margin: 0
  });

  addSideRail(slide, 0.78, "研究维度", ["临床层", "分子层", "动物层", "细胞层"], "F4F8FF", "2E58A6");
  addSideRail(slide, 11.72, "转化输出", ["获益", "通路", "结论", "汇报"], "FAF4FB", "8A4C92");

  const topModules = [
    {
      x: 1.86,
      y: 2.08,
      w: 2.18,
      h: 1.08,
      accent: "2E58A6",
      light: "EAF0FA",
      title: "研究起点",
      body: ["MDR-KP 重症肺炎", "高炎症、高死亡风险"],
      code: "01"
    },
    {
      x: 4.33,
      y: 2.08,
      w: 2.18,
      h: 1.08,
      accent: "7B61D1",
      light: "F0EBFF",
      title: "临床研究",
      body: ["随机平行对照", "症状与预后结局"],
      code: "02"
    },
    {
      x: 6.8,
      y: 2.08,
      w: 2.18,
      h: 1.08,
      accent: "C25B84",
      light: "F8EAF1",
      title: "组学筛选",
      body: ["蛋白组差异筛选", "CLUH-自噬轴候选"],
      code: "03"
    },
    {
      x: 9.27,
      y: 2.08,
      w: 2.18,
      h: 1.08,
      accent: "D58A2D",
      light: "FFF0DF",
      title: "机制验证",
      body: ["动物 + 细胞模型", "通路与功能逆转"],
      code: "04"
    }
  ];
  topModules.forEach((item) => addModule(slide, item));

  addArrow(slide, 2.96, 3.16, 5.2, 4.2, "7B95C7", 1.2);
  addArrow(slide, 5.44, 3.16, 5.9, 4.14, "8B74D8", 1.2);
  addArrow(slide, 7.9, 3.16, 7.22, 4.14, "C56E93", 1.2);
  addArrow(slide, 10.38, 3.16, 8.56, 4.2, "D09039", 1.2);

  addCenterHub(slide);

  addModule(slide, {
    x: 2.18,
    y: 4.86,
    w: 2.42,
    h: 0.92,
    accent: "2B8A5D",
    light: "EEF7EC",
    title: "疗效层结论",
    body: ["症状改善", "预后向好 + 安全可控"]
  });
  addModule(slide, {
    x: 5.48,
    y: 4.86,
    w: 2.42,
    h: 0.92,
    accent: "A34775",
    light: "F7E9F0",
    title: "机制层结论",
    body: ["自噬恢复", "炎症与 ROS 负荷下降"]
  });
  addModule(slide, {
    x: 8.78,
    y: 4.86,
    w: 2.42,
    h: 0.92,
    accent: "B46918",
    light: "FFF1E3",
    title: "整合层结论",
    body: ["形成连续证据链", "支撑论文主结论"]
  });

  addArrow(slide, 6.64, 4.66, 3.42, 4.86, "63A17D", 1.0);
  addArrow(slide, 6.64, 4.66, 6.68, 4.86, "A34775", 1.0);
  addArrow(slide, 6.64, 4.66, 9.9, 4.86, "CC8B39", 1.0);

  addBottomOutput(slide, 1.78, "临床获益", ["症状改善", "预后向好"], "2E58A6", "EAF0FA");
  addBottomOutput(slide, 4.78, "机制主线", ["CLUH/mTOR 自噬轴", "TLR4-NF-kB-NLRP3"], "7B61D1", "F0EBFF");
  addBottomOutput(slide, 7.78, "研究价值", ["疗效与机制合一", "形成完整答辩主线"], "C25B84", "F8EAF1");

  slide.addText("参考学习后的视觉语法：高密度信息分层、中心核问题、四向支撑、色彩分组、底部输出带。当前这张是“单页技术路线看板样板”，用于验证我们后续母版是否能往参考图那种方向逼近。", {
    x: 0.82,
    y: 6.72,
    w: 11.2,
    h: 0.28,
    fontFace: "Microsoft YaHei",
    fontSize: 9.2,
    color: "8A5A44",
    margin: 0
  });

  await fs.mkdir(path.dirname(outputFile), { recursive: true });
  await pptx.writeFile({ fileName: outputFile });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
