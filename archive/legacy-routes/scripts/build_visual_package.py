from __future__ import annotations

import argparse
import copy
import json
import re
from html import escape
from pathlib import Path

from common_io import ensure_parent, read_json, write_json


WIDTH = 1600
HEIGHT = 900
FONT_STACK = "'Microsoft YaHei','PingFang SC','Segoe UI',sans-serif"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def infer_intervention(title: str) -> str:
    match = re.match(r"(.+?)(?:治疗|干预|改善)", normalize(title))
    return match.group(1) if match else "该干预方案"


def infer_condition(title: str) -> str:
    match = re.search(r"(?:治疗|干预|改善)(.+?)(?:的临床与机制研究|的机制研究|研究)$", normalize(title))
    if match:
        return match.group(1)
    return "目标疾病场景"


def compact_condition(condition: str) -> str:
    condition = normalize(condition)
    condition = condition.replace("多重耐药肺炎克雷伯菌", "MDR-KP")
    condition = condition.replace("所致", "")
    condition = condition.replace("MDR-KP（MDR-KP）", "MDR-KP")
    condition = condition.replace("MDR-KP(MDR-KP)", "MDR-KP")
    return condition


def add_density_bullet(slide: dict) -> None:
    title = slide.get("title", "")
    bullets = slide.get("bullets", [])
    if len(bullets) >= 4 or slide.get("layout") in {"title", "section"}:
        return

    density_map = {
        "研究背景": "因此，需要通过连续研究设计把临床价值与机制解释统一起来。",
        "问题提出与研究缺口": "这也构成了本论文从临床观察走向机制验证的直接起点。",
        "研究目标": "三个层面的目标共同服务于论文主结论，而不是彼此割裂展开。",
        "整体研究设计": "各研究层次之间并非并列堆砌，而是前后递进、相互支撑。",
        "研究局限性": "主动说明边界有助于增强结论的可信度与学术克制感。",
        "总体结论一": "这一层结论主要回答方案是否值得被认可与继续推进。",
        "总体结论二": "这一层结论主要回答论文最终留下的机制解释与学术价值。",
        "研究展望": "后续研究应继续围绕临床转化价值与机制精细化两个方向推进。",
        "论文讨论一：结果如何解释": "讨论部分的重点是解释证据一致性，而不是再次逐条报告结果。",
        "论文讨论二：价值何在": "价值页更适合从临床意义、学术意义和方法意义三个层次去讲。",
    }
    extra = density_map.get(title)
    if extra and extra not in bullets:
        slide["bullets"] = bullets + [extra]


def svg_header(theme: dict) -> list[str]:
    return [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{WIDTH}' height='{HEIGHT}' viewBox='0 0 {WIDTH} {HEIGHT}'>",
        "<defs>",
        f"<marker id='arrow' markerWidth='14' markerHeight='14' refX='11' refY='7' orient='auto'>"
        f"<path d='M0,0 L14,7 L0,14 z' fill='#{theme['accentColor']}'/></marker>",
        f"<marker id='arrow-soft' markerWidth='14' markerHeight='14' refX='11' refY='7' orient='auto'>"
        f"<path d='M0,0 L14,7 L0,14 z' fill='#{theme['mutedStroke']}'/></marker>",
        "</defs>",
        f"<rect width='{WIDTH}' height='{HEIGHT}' fill='#{theme['canvas']}'/>",
    ]


def svg_footer() -> list[str]:
    return ["</svg>"]


def svg_text(x: int, y: int, text: str, size: int = 28, color: str = "1C2A39", weight: int = 400, anchor: str = "start") -> str:
    return (
        f"<text x='{x}' y='{y}' font-family={json.dumps(FONT_STACK)} font-size='{size}' "
        f"font-weight='{weight}' fill='#{color}' text-anchor='{anchor}'>{escape(text)}</text>"
    )


def svg_multiline_text(x: int, y: int, lines: list[str], size: int, color: str, line_gap: int = 38, anchor: str = "start") -> list[str]:
    items: list[str] = []
    for idx, line in enumerate(lines):
        items.append(svg_text(x, y + idx * line_gap, line, size=size, color=color, anchor=anchor))
    return items


def svg_card(x: int, y: int, w: int, h: int, title: str, lines: list[str], theme: dict, fill: str | None = None, accent: bool = False) -> list[str]:
    fill_color = fill or ("FFFFFF" if not accent else theme["softAccent"])
    stroke = theme["accentColor"] if accent else theme["mutedStroke"]
    title_color = theme["titleColor"]
    body_color = theme["bodyColor"]
    elements = [
        f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='26' fill='#{fill_color}' stroke='#{stroke}' stroke-width='2'/>",
        f"<rect x='{x + 18}' y='{y + 18}' width='{w - 36}' height='56' rx='16' fill='#{theme['headerFill']}'/>",
        svg_text(x + 36, y + 56, title, size=24, color=title_color, weight=700),
    ]
    elements.extend(svg_multiline_text(x + 36, y + 122, lines, size=20, color=body_color, line_gap=34))
    return elements


def svg_arrow(x1: int, y1: int, x2: int, y2: int, theme: dict, soft: bool = False) -> str:
    color = theme["mutedStroke"] if soft else theme["accentColor"]
    marker = "arrow-soft" if soft else "arrow"
    return f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#{color}' stroke-width='6' marker-end='url(#{marker})'/>"


def svg_badge(x: int, y: int, label: str, theme: dict, fill: str | None = None) -> list[str]:
    color = fill or theme["accentColor"]
    return [
        f"<rect x='{x}' y='{y}' width='166' height='42' rx='20' fill='#{color}' opacity='0.12'/>",
        svg_text(x + 83, y + 29, label, size=18, color=theme["accentColor"], weight=700, anchor="middle"),
    ]


def figure_filename(slide_id: str, visual_type: str) -> str:
    slug = visual_type.replace("_", "-")
    return f"{slide_id}-{slug}.svg"


def write_svg(path: Path, elements: list[str]) -> None:
    ensure_parent(path)
    path.write_text("\n".join(elements), encoding="utf-8")


def theme_from_template(template: dict) -> dict:
    return {
        "canvas": template.get("backgroundColor", "F6F2EB"),
        "hero": template.get("heroBackgroundColor", "1C2A39"),
        "titleColor": template.get("titleColor", "1C2A39"),
        "bodyColor": template.get("bodyColor", "2C343C"),
        "accentColor": template.get("accentColor", "8A5A44"),
        "softAccent": "F2E6DE",
        "headerFill": "EEE7DE",
        "mutedStroke": "B6A999",
        "heroText": template.get("heroTitleColor", "F6F2EB"),
        "heroSubtle": template.get("heroSubtitleColor", "D5DDE5"),
    }


def build_process_flow(title: str, steps: list[str], theme: dict) -> tuple[list[str], dict]:
    cards = []
    elements = svg_header(theme)
    elements.append(svg_text(110, 110, title, size=42, color=theme["titleColor"], weight=700))
    elements.extend(svg_badge(110, 138, "TECHNICAL ROUTE", theme))

    xs = [110, 465, 820, 1175]
    labels = ["阶段一", "阶段二", "阶段三", "阶段四"]
    payload_nodes = []
    for idx, step in enumerate(steps[:4]):
        card_lines = [step, "形成下一阶段的研究入口"]
        elements.extend(svg_card(xs[idx], 270, 300, 260, labels[idx], card_lines, theme, accent=(idx == 0)))
        if idx < 3:
            elements.append(svg_arrow(xs[idx] + 300, 400, xs[idx + 1] - 25, 400, theme))
        payload_nodes.append({"label": step, "section": labels[idx]})

    elements.append(svg_text(800, 700, "从临床评价到机制验证，形成逐层递进的答辩主线", size=28, color=theme["accentColor"], weight=600, anchor="middle"))
    elements.extend(svg_footer())
    return elements, {"nodes": payload_nodes, "flow": "horizontal"}


def build_study_design(title: str, phase: str, condition: str, theme: dict) -> tuple[list[str], dict]:
    elements = svg_header(theme)
    elements.append(svg_text(100, 102, title, size=40, color=theme["titleColor"], weight=700))
    elements.extend(svg_badge(100, 128, phase, theme))

    columns = [
        ("研究对象", [condition, "明确纳入与排除标准"]),
        ("分组设计", ["设置对照与干预比较", "保证观察路径清晰"]),
        ("干预实施", ["统一研究流程", "围绕关键节点推进"]),
        ("评价指标", ["结局指标 + 机制指标", "服务最终答辩主结论"]),
    ]
    xs = [90, 470, 850, 1230]
    payload_nodes = []
    for idx, (label, lines) in enumerate(columns):
        elements.extend(svg_card(xs[idx], 250, 280, 330, label, lines, theme, accent=(idx in {0, 3})))
        if idx < len(columns) - 1:
            elements.append(svg_arrow(xs[idx] + 280, 415, xs[idx + 1] - 24, 415, theme, soft=True))
        payload_nodes.append({"label": label, "lines": lines})

    elements.append(svg_text(800, 745, "设计图用于把对象、分组、干预与指标压成一眼看懂的结构。", size=28, color=theme["bodyColor"], anchor="middle"))
    elements.extend(svg_footer())
    return elements, {"nodes": payload_nodes, "phase": phase}


def build_evidence_chain(title: str, intervention: str, theme: dict) -> tuple[list[str], dict]:
    elements = svg_header(theme)
    elements.append(svg_text(100, 106, title, size=40, color=theme["titleColor"], weight=700))
    elements.extend(svg_badge(100, 132, "EVIDENCE CHAIN", theme))

    bands = [
        ("临床层", ["症状改善", "预后指标向好", "安全性基础明确"], True),
        ("分子层", ["免疫炎症缓解", "差异蛋白筛选", "通路线索收敛"], False),
        ("动物层", ["关键通路异常可复现", "干预后出现逆转趋势"], False),
        ("细胞层", ["ROS下降", "炎症与凋亡减轻", "保护作用得到巩固"], True),
    ]
    ys = [220, 390, 560, 730]
    payload_nodes = []
    for idx, (label, lines, accent) in enumerate(bands):
        elements.extend(svg_card(120, ys[idx], 1360, 120, label, lines, theme, accent=accent))
        if idx < len(bands) - 1:
            elements.append(svg_arrow(800, ys[idx] + 120, 800, ys[idx + 1] - 16, theme))
        payload_nodes.append({"label": label, "lines": lines})

    elements.append(svg_text(1330, 120, f"{intervention}贯穿四层证据", size=24, color=theme["accentColor"], weight=700))
    elements.extend(svg_footer())
    return elements, {"nodes": payload_nodes, "orientation": "vertical"}


def build_mechanism_pathway(title: str, intervention: str, theme: dict) -> tuple[list[str], dict]:
    elements = svg_header(theme)
    elements.append(svg_text(100, 110, title, size=40, color=theme["titleColor"], weight=700))
    elements.extend(svg_badge(100, 136, "MECHANISM MODEL", theme))

    boxes = [
        ("感染触发", ["MDR-KP感染", "炎症与损伤起始"], 110, 300, 240),
        ("自噬失衡", ["CLUH下调", "mTOR失衡 / 自噬受抑"], 420, 260, 280),
        ("炎症放大", ["TLR4/NF-kB/NLRP3激活", "炎症因子释放"], 780, 260, 310),
        ("损伤结局", ["ROS升高", "细胞损伤与凋亡加重"], 1160, 300, 250),
    ]
    payload_nodes = []
    for idx, (label, lines, x, y, w) in enumerate(boxes):
        elements.extend(svg_card(x, y, w, 220, label, lines, theme, accent=(idx in {1, 2})))
        if idx < len(boxes) - 1:
            elements.append(svg_arrow(x + w, y + 110, boxes[idx + 1][2] - 26, boxes[idx + 1][3] + 110, theme))
        payload_nodes.append({"label": label, "lines": lines})

    elements.extend(
        [
            f"<rect x='535' y='605' width='530' height='150' rx='32' fill='#{theme['hero']}'/>",
            svg_text(800, 663, intervention, size=32, color=theme["heroText"], weight=700, anchor="middle"),
            svg_text(800, 710, "调控自噬与炎症通路，减轻肺损伤", size=24, color=theme["heroSubtle"], anchor="middle"),
            f"<path d='M 800 605 C 800 560, 800 525, 920 495' fill='none' stroke='#{theme['accentColor']}' stroke-width='6' marker-end='url(#arrow)'/>",
            f"<path d='M 680 605 C 680 560, 630 540, 580 505' fill='none' stroke='#{theme['accentColor']}' stroke-width='6' marker-end='url(#arrow)'/>",
        ]
    )
    elements.extend(svg_footer())
    return elements, {"nodes": payload_nodes, "intervention": intervention}


def visual_targets(spec: dict, condition: str) -> list[dict]:
    targets: list[dict] = []
    for slide in spec.get("slides", []):
        title = slide.get("title", "")
        if title == "技术路线":
            targets.append(
                {
                    "slide_id": slide["id"],
                    "slide_title": title,
                    "visual_type": "process-flow",
                    "layout_hint": "figure-full",
                    "caption": "论文技术路线图：从临床评价到机制验证。",
                    "takeaway": "整篇论文按“临床评价—通路线索筛选—动物验证—细胞验证”四层推进。",
                    "generator": lambda theme, slide=slide, _title=title: build_process_flow(_title, slide.get("bullets", []), theme),
                }
            )
        elif title == "研究内容一：设计与对象":
            targets.append(
                {
                    "slide_id": slide["id"],
                    "slide_title": title,
                    "visual_type": "study-design",
                    "layout_hint": "figure-right",
                    "caption": "临床研究设计图：对象、分组、干预与结局评价。",
                    "takeaway": "方法页的重点不是堆信息，而是把对象、分组和结局的逻辑一次讲清。",
                    "generator": lambda theme, _title=title, _condition=condition: build_study_design(_title, "CLINICAL DESIGN", _condition, theme),
                }
            )
        elif title == "研究内容二：设计与对象":
            targets.append(
                {
                    "slide_id": slide["id"],
                    "slide_title": title,
                    "visual_type": "study-design",
                    "layout_hint": "figure-right",
                    "caption": "免疫炎症与蛋白组学分析路径图。",
                    "takeaway": "这一模块的关键是说明指标体系如何为后续机制验证筛选方向。",
                    "generator": lambda theme, _title=title: build_study_design(_title, "OMICS & IMMUNE", "样本检测与蛋白组学分析", theme),
                }
            )
        elif title == "研究内容三：设计与对象":
            targets.append(
                {
                    "slide_id": slide["id"],
                    "slide_title": title,
                    "visual_type": "study-design",
                    "layout_hint": "figure-right",
                    "caption": "动物模型设计图：建模、分组、检测与通路验证。",
                    "takeaway": "动物实验承担的是把临床线索推进到整体机制层面的任务。",
                    "generator": lambda theme, _title=title: build_study_design(_title, "ANIMAL MODEL", "MDR-KP感染动物模型", theme),
                }
            )
        elif title == "研究内容四：设计与对象":
            targets.append(
                {
                    "slide_id": slide["id"],
                    "slide_title": title,
                    "visual_type": "study-design",
                    "layout_hint": "figure-right",
                    "caption": "细胞实验设计图：感染、干预、表型评价与机制验证。",
                    "takeaway": "细胞实验用于完成机制闭环，并把保护作用落实到细胞层面。",
                    "generator": lambda theme, _title=title: build_study_design(_title, "CELL MODEL", "肺泡上皮细胞感染模型", theme),
                }
            )
        elif title == "整体证据链整合":
            targets.append(
                {
                    "slide_id": slide["id"],
                    "slide_title": title,
                    "visual_type": "evidence-chain",
                    "layout_hint": "figure-full",
                    "caption": "整篇论文的四层证据链整合图。",
                    "takeaway": "临床、分子、动物与细胞层面的结果在同一主线上收束。",
                    "generator": lambda theme, _title=title, _intervention=infer_intervention(spec.get("title", "")): build_evidence_chain(_title, _intervention, theme),
                }
            )
        elif title == "机制模型归纳":
            targets.append(
                {
                    "slide_id": slide["id"],
                    "slide_title": title,
                    "visual_type": "mechanism-pathway",
                    "layout_hint": "figure-full",
                    "caption": "机制模型图：感染、自噬失衡、炎症放大与干预逆转。",
                    "takeaway": "机制图负责把零散实验结果压缩成一条可讲、可记、可追问的主轴。",
                    "generator": lambda theme, _title=title, _intervention=infer_intervention(spec.get("title", "")): build_mechanism_pathway(_title, _intervention, theme),
                }
            )
    return targets


def attach_visuals(spec: dict, targets: list[dict], assets_dir: Path, theme: dict) -> tuple[dict, dict]:
    refined = copy.deepcopy(spec)
    target_map = {target["slide_id"]: target for target in targets}
    assets: list[dict] = []

    for slide in refined.get("slides", []):
        add_density_bullet(slide)
        target = target_map.get(slide.get("id"))
        if not target:
            continue

        svg_elements, payload = target["generator"](theme)
        asset_path = (assets_dir / figure_filename(target["slide_id"], target["visual_type"])).resolve()
        write_svg(asset_path, svg_elements)

        slide["layout_hint"] = target["layout_hint"]
        slide["visual_type"] = target["visual_type"]
        slide["takeaway"] = target["takeaway"]
        slide["figure"] = {
            "path": str(asset_path),
            "caption": target["caption"],
            "placement": "full" if target["layout_hint"] == "figure-full" else "right",
        }

        assets.append(
            {
                "slide_id": target["slide_id"],
                "slide_title": target["slide_title"],
                "visual_type": target["visual_type"],
                "layout_hint": target["layout_hint"],
                "asset_path": str(asset_path),
                "caption": target["caption"],
                "takeaway": target["takeaway"],
                "review_targets": {
                    "max_label_chars": 18,
                    "max_nodes": 8,
                    "palette_size": 4,
                    "distance_readable": True,
                },
                "payload": payload,
            }
        )

    refined["schema_version"] = "0.5"
    refined["visual_pass"] = {"stage": "v2", "strategy": "visual-planning-and-svg"}

    plan = {
        "schema_version": "0.1",
        "theme": theme,
        "asset_count": len(assets),
        "assets": assets,
    }
    return refined, plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich a deck spec with visual planning, generated SVG figures, and adaptive density polish.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--brief-file", required=True)
    parser.add_argument("--template-file", required=True)
    parser.add_argument("--output-spec-file", required=True)
    parser.add_argument("--assets-dir", required=True)
    parser.add_argument("--plan-file", required=True)
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    brief = read_json(Path(args.brief_file))
    template = read_json(Path(args.template_file))
    theme = theme_from_template(template)

    condition = compact_condition(infer_condition(brief.get("title", spec.get("title", ""))))
    targets = visual_targets(spec, condition)
    refined, plan = attach_visuals(spec, targets, Path(args.assets_dir), theme)

    write_json(Path(args.output_spec_file), refined)
    write_json(Path(args.plan_file), plan)


if __name__ == "__main__":
    main()
