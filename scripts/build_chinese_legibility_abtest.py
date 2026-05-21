from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Callable, Iterable

import fitz
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "runs" / "chinese-text-legibility-abtest"

BLUE = "#0B4F9C"
BLUE_DARK = "#12314F"
BLUE_MID = "#2E75B5"
BLUE_LIGHT = "#EAF3FC"
RED = "#B51F2A"
TEAL = "#128C8C"
ORANGE = "#B66A2E"
GREY = "#E7EAF0"
INK = "#142536"
PAPER = "#F6F8FB"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def blend(color: str, background: str, alpha: float) -> str:
    fg = hex_to_rgb(color)
    bg = hex_to_rgb(background)
    mixed = tuple(round(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def text_width(draw: ImageDraw.ImageDraw, text: str, font_obj: ImageFont.ImageFont) -> int:
    return int(draw.textlength(text, font=font_obj))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font_obj: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw in text.split("\n"):
        raw = raw.strip()
        if not raw:
            lines.append("")
            continue
        current = ""
        for char in raw:
            trial = current + char
            if current and text_width(draw, trial, font_obj) > max_width:
                lines.append(current)
                current = char
            else:
                current = trial
        if current:
            lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font_obj: ImageFont.ImageFont,
    fill: str = INK,
    line_gap: int = 10,
    max_lines: int | None = None,
    align: str = "left",
) -> None:
    x0, y0, x1, y1 = box
    lines = wrap_text(draw, text, font_obj, x1 - x0)
    if max_lines is not None:
        lines = lines[:max_lines]
    y = y0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_obj)
        line_h = bbox[3] - bbox[1]
        if y + line_h > y1:
            break
        if align == "center":
            x = x0 + ((x1 - x0) - text_width(draw, line, font_obj)) // 2
        else:
            x = x0
        draw.text((x, y), line, font=font_obj, fill=fill)
        y += line_h + line_gap


def draw_centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font_obj: ImageFont.ImageFont,
    fill: str = INK,
    line_gap: int = 8,
) -> None:
    x0, y0, x1, y1 = box
    lines = wrap_text(draw, text, font_obj, x1 - x0 - 8)
    line_boxes = [draw.textbbox((0, 0), line, font=font_obj) for line in lines]
    heights = [bbox[3] - bbox[1] for bbox in line_boxes]
    total_h = sum(heights) + line_gap * max(0, len(lines) - 1)
    y = y0 + ((y1 - y0) - total_h) // 2
    for line, h in zip(lines, heights):
        x = x0 + ((x1 - x0) - text_width(draw, line, font_obj)) // 2
        draw.text((x, y), line, font=font_obj, fill=fill)
        y += h + line_gap


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = BLUE_MID,
    width: int = 6,
    head: int = 24,
) -> None:
    draw.line([start, end], fill=color, width=width)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy) or 1
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    points = [
        end,
        (int(end[0] - ux * head + px * head * 0.45), int(end[1] - uy * head + py * head * 0.45)),
        (int(end[0] - ux * head - px * head * 0.45), int(end[1] - uy * head - py * head * 0.45)),
    ]
    draw.polygon(points, fill=color)


def round_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str = "#B9C7D6",
    width: int = 3,
    radius: int = 24,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def card(
    visual: ImageDraw.ImageDraw,
    text: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    lines: Iterable[str],
    accent: str = BLUE,
    fill: str = "#FFFFFF",
    title_fill: str | None = None,
) -> None:
    x0, y0, x1, y1 = box
    title_fill = title_fill or blend(accent, "#FFFFFF", 0.13)
    round_box(visual, box, fill=fill, outline=blend(accent, "#FFFFFF", 0.55), width=3, radius=22)
    visual.rounded_rectangle((x0 + 18, y0 + 18, x1 - 18, y0 + 70), radius=14, fill=title_fill)
    visual.rectangle((x0, y0, x0 + 10, y1), fill=accent)
    text.text((x0 + 36, y0 + 27), title, font=font(34, True), fill=INK)
    body = "\n".join(f"- {line}" for line in lines)
    draw_wrapped(text, (x0 + 36, y0 + 96, x1 - 34, y1 - 24), body, font(25), fill=INK, line_gap=8)


def chip(
    visual: ImageDraw.ImageDraw,
    text: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    fill: str,
    fg: str = "#FFFFFF",
) -> None:
    round_box(visual, box, fill=fill, outline=blend(fill, "#FFFFFF", 0.7), width=2, radius=18)
    draw_centered(text, box, label, font(24, True), fill=fg)


def make_layers(width: int, height: int) -> tuple[Image.Image, Image.Image, ImageDraw.ImageDraw, ImageDraw.ImageDraw]:
    base = Image.new("RGB", (width, height), PAPER)
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    visual = ImageDraw.Draw(base)
    text = ImageDraw.Draw(text_layer)
    visual.rectangle((0, 0, width, height), fill=PAPER)
    for x in range(-120, width, 180):
        visual.line([(x, 0), (x + 420, height)], fill="#EEF2F7", width=2)
    return base, text_layer, visual, text


def header(visual: ImageDraw.ImageDraw, text: ImageDraw.ImageDraw, width: int, title: str, subtitle: str, variant: str) -> None:
    visual.rectangle((0, 0, width, 16), fill=BLUE)
    text.text((90, 58), title, font=font(52, True), fill=BLUE_DARK)
    visual.rectangle((92, 132, 360, 142), fill=RED)
    text.text((90, 157), subtitle, font=font(25, True), fill=ORANGE)
    visual.rounded_rectangle((width - 520, 62, width - 92, 112), radius=18, fill="#FFFFFF", outline="#CAD6E2", width=2)
    draw_centered(text, (width - 520, 62, width - 92, 112), variant, font(23, True), fill=BLUE_DARK)


def footer(visual: ImageDraw.ImageDraw, text: ImageDraw.ImageDraw, width: int, height: int, note: str) -> None:
    visual.line((90, height - 110, width - 90, height - 110), fill="#C7D2DF", width=4)
    visual.rounded_rectangle((90, height - 88, width - 90, height - 34), radius=18, fill="#FFFFFF", outline="#CBD8E6", width=2)
    text.text((118, height - 76), note, font=font(25, True), fill=BLUE_DARK)


def draw_content_page(visual: ImageDraw.ImageDraw, text: ImageDraw.ImageDraw, width: int, height: int, variant: str) -> None:
    header(visual, text, width, "研究背景：MDR-KP重症肺炎的临床挑战", "普通内容页 - 结构密度替代微小字", variant)
    visual.rounded_rectangle((90, 210, width - 90, 310), radius=24, fill="#FFFFFF", outline="#BFCFE0", width=3)
    text.text((125, 235), "核心问题：耐药感染使治疗窗口缩短，炎症失衡与组织损伤进一步放大预后风险。", font=font(34, True), fill=BLUE_DARK)

    card(
        visual,
        text,
        (100, 360, 780, 835),
        "临床负担",
        ["MDR-KP感染与机械通气、ICU住院和死亡风险密切相关", "经验治疗常受耐药谱限制，早期控制窗口更窄", "需要兼顾抗感染、炎症控制与肺损伤保护"],
        accent=BLUE,
    )
    card(
        visual,
        text,
        (850, 360, 1530, 835),
        "病理机制",
        ["细菌毒力与宿主免疫激活共同驱动炎症风暴", "自噬、线粒体稳态和炎症小体可能形成联动通路", "机制证据需要从细胞、动物和临床层面整合"],
        accent=TEAL,
    )
    card(
        visual,
        text,
        (1600, 360, 2280, 835),
        "研究切入",
        ["藿芩清胆汤具有清热化湿、调节炎症反应的理论基础", "围绕症状改善、预后指标和机制通路建立证据链", "以多层数据支撑临床疗效与作用机制解释"],
        accent=ORANGE,
    )

    center = (1190, 980, 1370, 1160)
    visual.ellipse(center, fill=BLUE, outline="#FFFFFF", width=8)
    draw_centered(text, center, "研究\n假设", font(34, True), fill="#FFFFFF")
    items = [
        ((250, 970, 570, 1040), "耐药感染"),
        ((650, 1120, 970, 1190), "炎症失衡"),
        ((1590, 1120, 1910, 1190), "肺损伤"),
        ((1990, 970, 2310, 1040), "结局改善"),
    ]
    for box, label in items:
        chip(visual, text, box, label, BLUE_MID if label != "结局改善" else RED)
    arrow(visual, (570, 1005), (1188, 1048), BLUE_MID, 7)
    arrow(visual, (970, 1155), (1198, 1090), TEAL, 7)
    arrow(visual, (1590, 1155), (1370, 1090), TEAL, 7)
    arrow(visual, (1370, 1048), (1990, 1005), RED, 7)
    footer(visual, text, width, height, "可读性目标：保持模块、关系和结论密度，但避免把中文正文压成模糊小字。")


def draw_route_page(visual: ImageDraw.ImageDraw, text: ImageDraw.ImageDraw, width: int, height: int, variant: str) -> None:
    header(visual, text, width, "技术路线图：藿芩清胆汤干预MDR-KP重症肺炎", "技术路线页 - 高密度学术路线图语法", variant)
    visual.rounded_rectangle((90, 200, width - 90, 1240), radius=26, fill="#FFFFFF", outline="#B8C9DA", width=3)
    visual.rectangle((150, 235, width - 150, 300), fill=BLUE)
    draw_centered(text, (150, 235, width - 150, 300), "围绕临床疗效、组学筛选、动物验证和细胞机制构建闭环证据链", font(32, True), fill="#FFFFFF")

    left_rail = (130, 350, 210, 1110)
    right_rail = (width - 210, 350, width - 130, 1110)
    visual.rounded_rectangle(left_rail, radius=28, fill=BLUE, outline=BLUE, width=2)
    visual.rounded_rectangle(right_rail, radius=28, fill=RED, outline=RED, width=2)
    draw_centered(text, left_rail, "临床\n证据\n牵引", font(30, True), fill="#FFFFFF")
    draw_centered(text, right_rail, "机制\n验证\n闭环", font(30, True), fill="#FFFFFF")

    hub = (1050, 520, 1510, 910)
    visual.ellipse(hub, fill="#F8FBFF", outline=BLUE, width=12)
    visual.ellipse((1125, 595, 1435, 835), fill=blend(BLUE, "#FFFFFF", 0.12), outline=RED, width=8)
    draw_centered(text, (1135, 615, 1425, 815), "核心假设\n调控自噬\n缓解炎症\n改善肺损伤", font(35, True), fill=BLUE_DARK)

    panels = [
        ((270, 360, 900, 605), "一、临床评价", ["多中心随机化对照设计", "症状改善、预后指标和安全性", "形成疗效与适用人群判断"], BLUE),
        ((1660, 360, 2290, 605), "二、蛋白组学筛选", ["差异蛋白与富集通路识别", "锁定CLUH/mTOR/自噬轴", "筛选关键机制候选靶点"], TEAL),
        ((270, 825, 900, 1085), "三、动物模型验证", ["MDR-KP肺炎模型建立", "炎症因子、病理评分和生存结局", "验证干预对肺损伤的保护作用"], ORANGE),
        ((1660, 825, 2290, 1085), "四、细胞机制解析", ["巨噬细胞感染与药物干预", "自噬通量、mTOR信号和炎症小体", "完成从通路到功能的因果支撑"], RED),
    ]
    for box, title, lines, accent in panels:
        card(visual, text, box, title, lines, accent=accent, fill="#FBFDFF")

    for start, end, color in [
        ((900, 485), (1050, 650), BLUE),
        ((1660, 485), (1510, 650), TEAL),
        ((900, 955), (1050, 790), ORANGE),
        ((1660, 955), (1510, 790), RED),
    ]:
        arrow(visual, start, end, color, 8, 28)

    chip_labels = [
        ((410, 650, 700, 710), "纳入标准"),
        ((760, 650, 1050, 710), "结局指标"),
        ((1510, 650, 1800, 710), "差异蛋白"),
        ((1860, 650, 2150, 710), "通路富集"),
        ((410, 740, 700, 800), "模型构建"),
        ((760, 740, 1050, 800), "干预评估"),
        ((1510, 740, 1800, 800), "自噬通量"),
        ((1860, 740, 2150, 800), "炎症小体"),
    ]
    for index, (box, label) in enumerate(chip_labels):
        chip(visual, text, box, label, BLUE_MID if index < 4 else TEAL, "#FFFFFF")

    visual.rounded_rectangle((520, 1130, 2040, 1210), radius=24, fill=blend(RED, "#FFFFFF", 0.12), outline=RED, width=4)
    draw_centered(text, (520, 1130, 2040, 1210), "最终整合：临床疗效 - 关键通路 - 实验验证 - 机制解释共同支撑答辩主线", font(30, True), fill=RED)
    footer(visual, text, width, height, "可读性目标：复杂度来自路线层级、证据模块和连接关系，而不是堆叠不可读小字。")


def draw_mechanism_page(visual: ImageDraw.ImageDraw, text: ImageDraw.ImageDraw, width: int, height: int, variant: str) -> None:
    header(visual, text, width, "机制整合：自噬调控与炎症缓解证据链", "机制/证据链页 - 图形密度与文字层分离", variant)
    visual.rounded_rectangle((90, 205, width - 90, 1235), radius=26, fill="#FFFFFF", outline="#B8C9DA", width=3)

    visual.ellipse((890, 390, 1670, 1010), fill="#F9FCFF", outline=BLUE, width=10)
    visual.arc((930, 430, 1630, 970), start=20, end=150, fill=TEAL, width=16)
    visual.arc((930, 430, 1630, 970), start=160, end=280, fill=RED, width=16)
    visual.arc((930, 430, 1630, 970), start=292, end=355, fill=ORANGE, width=16)
    visual.ellipse((1120, 560, 1440, 840), fill=BLUE, outline="#FFFFFF", width=8)
    draw_centered(text, (1130, 580, 1430, 820), "CLUH/mTOR\n自噬轴\n炎症调控", font(34, True), fill="#FFFFFF")

    nodes = [
        ((405, 355, 775, 570), "感染触发", ["MDR-KP刺激巨噬细胞", "ROS升高与线粒体压力", "炎症信号快速放大"], RED),
        ((405, 780, 775, 995), "细胞损伤", ["屏障破坏与肺泡炎症", "病理评分和湿干比升高", "组织修复能力下降"], ORANGE),
        ((1785, 355, 2155, 570), "通路失衡", ["mTOR异常活化", "自噬通量受阻", "NLRP3相关炎症加剧"], BLUE),
        ((1785, 780, 2155, 995), "干预逆转", ["藿芩清胆汤调节通路", "恢复自噬与代谢稳态", "炎症反应趋于缓解"], TEAL),
    ]
    for box, title, lines, accent in nodes:
        card(visual, text, box, title, lines, accent=accent, fill="#FBFDFF")

    arrow(visual, (775, 465), (1040, 650), RED, 8, 30)
    arrow(visual, (1785, 465), (1520, 650), BLUE, 8, 30)
    arrow(visual, (775, 890), (1045, 800), ORANGE, 8, 30)
    arrow(visual, (1785, 890), (1520, 800), TEAL, 8, 30)

    evidence = [
        ((670, 1085, 945, 1155), "临床结局改善"),
        ((975, 1085, 1250, 1155), "蛋白组学支持"),
        ((1280, 1085, 1555, 1155), "动物实验验证"),
        ((1585, 1085, 1860, 1155), "细胞机制闭环"),
    ]
    for box, label in evidence:
        chip(visual, text, box, label, BLUE_MID)
    for x in (945, 1250, 1555):
        arrow(visual, (x + 12, 1120), (x + 45, 1120), BLUE_MID, 5, 18)

    side_labels = [
        ((150, 615, 330, 685), "炎症因子"),
        ((150, 715, 330, 785), "肺组织病理"),
        ((2230, 615, 2410, 685), "自噬标志"),
        ((2230, 715, 2410, 785), "通路蛋白"),
    ]
    for box, label in side_labels:
        chip(visual, text, box, label, RED if box[0] > 2000 else BLUE)
    visual.rounded_rectangle((760, 265, 1800, 330), radius=22, fill=blend(BLUE, "#FFFFFF", 0.12), outline="#CBD8E6", width=2)
    draw_centered(text, (760, 265, 1800, 330), "证据链逻辑：感染触发 -> 通路失衡 -> 干预调节 -> 结局改善", font(29, True), fill=BLUE_DARK)
    footer(visual, text, width, height, "可读性目标：机制复杂度由中心环路、外围证据和底部闭环承载，中文标签保持清晰。")


PAGE_BUILDERS: dict[str, tuple[str, Callable[[ImageDraw.ImageDraw, ImageDraw.ImageDraw, int, int, str], None]]] = {
    "content": ("普通内容页", draw_content_page),
    "route": ("技术路线页", draw_route_page),
    "mechanism": ("机制/证据链页", draw_mechanism_page),
}

VARIANTS = {
    "prompt-only": "prompt-only | 直接生成中文小字模拟",
    "postprocess": "postprocess | 不改字号的锐化增强",
    "deterministic-text-layer": "deterministic-text-layer | 本地清晰中文文字层",
}


def soften_text_layer(layer: Image.Image) -> Image.Image:
    width, height = layer.size
    reduced = layer.resize((int(width * 0.62), int(height * 0.62)), Image.Resampling.BICUBIC)
    restored = reduced.resize((width, height), Image.Resampling.BICUBIC)
    return restored.filter(ImageFilter.GaussianBlur(radius=0.55))


def sharpen_image(image: Image.Image) -> Image.Image:
    enhanced = ImageEnhance.Contrast(image).enhance(1.08)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.18)
    return enhanced.filter(ImageFilter.UnsharpMask(radius=1.1, percent=165, threshold=2))


def render_page(kind: str, variant: str, width: int, height: int) -> Image.Image:
    base, text_layer, visual, text = make_layers(width, height)
    _, builder = PAGE_BUILDERS[kind]
    builder(visual, text, width, height, VARIANTS[variant])
    if variant == "prompt-only":
        layer = soften_text_layer(text_layer)
        base.paste(layer, (0, 0), layer)
        return base
    if variant == "postprocess":
        layer = soften_text_layer(text_layer)
        base.paste(layer, (0, 0), layer)
        return sharpen_image(base)
    base.paste(text_layer, (0, 0), text_layer)
    return base


def build_contact_sheet(slide_files: list[Path], output_file: Path) -> None:
    thumb_w, thumb_h = 620, 349
    label_h = 62
    pad = 32
    sheet_w = pad * 4 + thumb_w * 3
    sheet_h = pad * 4 + (thumb_h + label_h) * 3
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#F2F5FA")
    draw = ImageDraw.Draw(sheet)
    ordered = sorted(slide_files, key=lambda p: p.name)
    for idx, image_file in enumerate(ordered):
        row = idx // 3
        col = idx % 3
        x = pad + col * (thumb_w + pad)
        y = pad + row * (thumb_h + label_h + pad)
        image = Image.open(image_file).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y))
        draw.rounded_rectangle((x, y + thumb_h + 8, x + thumb_w, y + thumb_h + label_h), radius=14, fill="#FFFFFF", outline="#CAD6E2", width=2)
        label = image_file.stem.replace("-", " ")
        draw_centered(draw, (x + 8, y + thumb_h + 12, x + thumb_w - 8, y + thumb_h + label_h - 2), label, font(22, True), fill=BLUE_DARK)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_file)


def export_pdf(slide_files: list[Path], output_pdf: Path) -> Path:
    doc = fitz.open()
    for image_path in slide_files:
        img_doc = fitz.open(image_path)
        rect = img_doc[0].rect
        page = doc.new_page(width=rect.width, height=rect.height)
        page.insert_image(page.rect, filename=str(image_path))
        img_doc.close()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    save_path = output_pdf
    if output_pdf.exists():
        try:
            output_pdf.unlink()
        except PermissionError:
            save_path = output_pdf.with_name(f"{output_pdf.stem}.new{output_pdf.suffix}")
            if save_path.exists():
                save_path.unlink()
    doc.save(save_path, deflate=True, garbage=4)
    doc.close()
    return save_path


def write_report(output_dir: Path, slide_files: list[Path], width: int, height: int, pdf_file: Path) -> None:
    lines = [
        "# Chinese Text Legibility AB Test",
        "",
        "This experiment keeps page density high without solving legibility by simply making all Chinese text larger.",
        "",
        "## Output",
        "",
        f"- Canvas: `{width} x {height}`",
        f"- Slides: `{len(slide_files)}` PNG files",
        f"- PDF: `{pdf_file.name}`",
        "- Contact sheet: `contact-sheet.png`",
        "",
        "## Variants",
        "",
        "- `prompt-only`: local simulation of an image-model page where the model paints Chinese text into the raster image.",
        "- `postprocess`: the same simulated raster text with contrast and sharpening only; word count and font scale are not changed.",
        "- `deterministic-text-layer`: visual structure is raster-like, but Chinese title, labels, body copy, and chips are drawn by local fonts at export resolution.",
        "",
        "## Recommendation",
        "",
        "If the deterministic text layer is visibly clearer, promote it as the next production candidate: image2 should create the dense visual board, while local rendering draws small Chinese text crisply before the final PDF export.",
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- `{path.relative_to(output_dir)}`" for path in slide_files)
    (output_dir / "readability-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build PNG/PDF Chinese text legibility comparisons for the image2 raster route.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=2560)
    parser.add_argument("--height", type=int, default=1440)
    args = parser.parse_args()

    output_dir = args.output_dir
    slides_dir = output_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    slide_files: list[Path] = []
    for kind in ("content", "route", "mechanism"):
        for variant in ("prompt-only", "postprocess", "deterministic-text-layer"):
            image = render_page(kind, variant, args.width, args.height)
            out_file = slides_dir / f"{kind}-{variant}.png"
            image.save(out_file)
            slide_files.append(out_file)

    build_contact_sheet(slide_files, output_dir / "contact-sheet.png")
    pdf_file = export_pdf(slide_files, output_dir / "readability-test.pdf")
    write_report(output_dir, slide_files, args.width, args.height, pdf_file)

    print(output_dir)


if __name__ == "__main__":
    main()
