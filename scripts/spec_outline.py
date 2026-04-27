from __future__ import annotations

import argparse
import re
from pathlib import Path

from common_io import read_json, write_json, write_text


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clip(text: str, limit: int = 68) -> str:
    text = normalize_whitespace(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def split_points(text: str, max_items: int = 3, item_limit: int = 68) -> list[str]:
    text = normalize_whitespace(text)
    if not text:
        return []
    text = re.sub(r"^(本研究关注的问题是：|在研究设计上，|主要结果显示，|综合结论可以概括为：|核心问题：|研究设计：|核心结果：|结论提炼：)", "", text)
    parts = re.split(r"[。；;!?！？]", text)
    cleaned = [clip(part.strip("：:，, "), item_limit) for part in parts if part.strip("：:，, ")]
    if len(cleaned) >= max_items:
        return cleaned[:max_items]
    if len(cleaned) == 1:
        subparts = re.split(r"[，,、]", cleaned[0])
        expanded = [clip(part.strip(), item_limit) for part in subparts if len(part.strip()) >= 6]
        if expanded:
            return expanded[:max_items]
    return cleaned[:max_items]


def numbered_prefix(text: str) -> int | None:
    stripped = normalize_whitespace(text)
    if not stripped:
        return None
    digit_match = re.match(r"^(\d{1,2})(?:[\.、．)]|\s|(?=[A-Za-z\u4e00-\u9fff]))", stripped)
    if digit_match:
        return int(digit_match.group(1))
    chinese_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    chinese_match = re.match(r"^[（(]?([一二三四五六七八九十])[）)]?[、\.]?", stripped)
    if chinese_match:
        return chinese_map.get(chinese_match.group(1))
    return None


def strip_numbering(text: str) -> str:
    stripped = normalize_whitespace(text)
    stripped = re.sub(r"^\d{1,2}(?:[\.、．)]|\s)?", "", stripped)
    stripped = re.sub(r"^[（(]?[一二三四五六七八九十][）)]?[、\.]?", "", stripped)
    return stripped.strip(" ：:.")


def first_meaningful_point(texts: list[str], fallback: str) -> str:
    for text in texts:
        points = split_points(text, max_items=1)
        if points:
            return points[0]
    return fallback


def build_modules(extraction: dict, brief: dict) -> list[dict]:
    primary_source = brief.get("primary_source")
    chunks = [chunk for chunk in extraction.get("chunks", []) if not primary_source or chunk.get("source") == primary_source]
    modules: dict[int, dict] = {}

    for chunk in chunks:
        hint = chunk.get("section_hint")
        if hint not in {"method", "results", "conclusion"}:
            continue
        text = normalize_whitespace(chunk.get("text", ""))
        index = numbered_prefix(text)
        if not index or index > 6:
            continue
        module = modules.setdefault(
            index,
            {
                "index": index,
                "title": "",
                "method_texts": [],
                "result_texts": [],
                "conclusion_texts": [],
            },
        )
        content = strip_numbering(text)
        if hint == "method":
            module["method_texts"].append(content)
            if not module["title"] and len(content) >= 8:
                module["title"] = clip(content, 36)
        elif hint == "results":
            module["result_texts"].append(content)
        elif hint == "conclusion":
            module["conclusion_texts"].append(content)

    ordered = []
    for index in sorted(modules):
        module = modules[index]
        if not module["title"]:
            module["title"] = f"研究内容{index}"
        module["display_title"] = localize_module_title(module["title"], index)
        ordered.append(module)

    if ordered:
        return ordered[:4]

    fallback_titles = [
        "研究背景与问题界定",
        "研究设计与技术路径",
        "核心结果与证据链",
        "结论提炼与价值归纳",
    ]
    fallback_texts = [
        [brief.get("research_problem", "")],
        [brief.get("method_summary", "")],
        [brief.get("results_summary", "")],
        [brief.get("conclusion_summary", "")],
    ]
    synthetic = []
    for index, title in enumerate(fallback_titles, start=1):
        synthetic.append(
            {
                "index": index,
                "title": title,
                "display_title": title,
                "method_texts": fallback_texts[index - 1] if index == 2 else [],
                "result_texts": fallback_texts[index - 1] if index == 3 else [],
                "conclusion_texts": fallback_texts[index - 1] if index == 4 else [],
            }
        )
    return synthetic


def localize_module_title(title: str, index: int) -> str:
    lowered = title.lower()
    if any(token in lowered for token in ("clinical efficacy", "临床疗效")):
        return "临床疗效评价"
    if any(token in lowered for token in ("immune cells", "differentially expressed proteins", "immune/inflammatory")):
        return "免疫炎症与差异蛋白分析"
    if any(token in lowered for token in ("rat model", "cluh/mtor", "动物模型")):
        return "动物模型与通路验证"
    if any(token in lowered for token in ("mechanism validation", "containing serum", "alveolar epithelial", "细胞模型")):
        return "细胞模型保护作用与机制验证"
    return f"研究模块{index}"


def module_position_bullets(module: dict) -> list[str]:
    title = module["display_title"]
    if "临床" in title:
        return [
            f"模块主题：{title}",
            "围绕临床疗效、安全性和预后改善展开评价。",
            "这一模块负责回答‘方案是否有效、是否安全’。",
        ]
    if "免疫炎症" in title:
        return [
            f"模块主题：{title}",
            "重点观察免疫细胞、炎症因子与差异蛋白变化。",
            "这一模块负责从多维指标解释干预后的系统变化。",
        ]
    if "动物模型" in title:
        return [
            f"模块主题：{title}",
            "通过动物模型验证关键通路与组织水平效应。",
            "这一模块负责把临床发现进一步推进到机制层。",
        ]
    if "细胞模型" in title:
        return [
            f"模块主题：{title}",
            "通过细胞模型与干预验证锁定关键分子机制。",
            "这一模块负责完成最终的靶点与机制闭环。",
        ]
    return [
        f"模块主题：{title}",
        first_meaningful_point(module["method_texts"], "说明该模块在整篇论文中的位置。"),
        "交代该模块解决的是哪一个具体问题。",
    ]


def module_design_bullets(module: dict, fallback_points: list[str]) -> list[str]:
    title = module["display_title"]
    if "临床" in title:
        return [
            "采用临床研究设计，围绕病例纳入、分组和干预展开。",
            "重点交代主要结局、次要结局和安全性指标。",
            "建议配套病例流程图与结局指标表。",
        ]
    if "免疫炎症" in title:
        return [
            "采集关键样本，检测免疫细胞、炎症因子和差异蛋白。",
            "结合蛋白组学与富集分析筛选核心通路。",
            "建议配套样本来源图与指标体系图。",
        ]
    if "动物模型" in title:
        return [
            "建立动物模型，观察组织水平和通路水平变化。",
            "结合RT-qPCR、蛋白检测和组织染色完成验证。",
            "建议配套分组示意图和实验时间线。",
        ]
    if "细胞模型" in title:
        return [
            "构建细胞损伤模型，观察增殖、炎症和凋亡变化。",
            "通过含药血清或敲低验证锁定关键机制。",
            "建议配套细胞实验设计图和机制验证流程图。",
        ]
    return fallback_points[:4]


def make_slide(slide_id: int, title: str, bullets: list[str], notes: str) -> dict:
    cleaned = [clip(item, 72) for item in bullets if normalize_whitespace(item)]
    if not cleaned:
        cleaned = ["待结合原文进一步细化该页内容。"]
    return {
        "id": f"slide-{slide_id:02d}",
        "layout": "bullets",
        "title": title,
        "bullets": cleaned[:4],
        "notes": notes,
    }


def build_longform_slides(brief: dict, extraction: dict | None, template: str) -> list[dict]:
    slide_claims = brief.get("slide_claims", {})
    contributions = brief.get("contributions", []) or ["创新点仍需结合原文进一步压缩表达。"]
    limitations = brief.get("limitations", []) or ["需进一步回到原文明确局限性。"]
    modules = build_modules(extraction or {}, brief)

    slides = [
        {
            "id": "slide-01",
            "layout": "title",
            "title": brief["title"],
            "subtitle": brief.get("subtitle", "35页完整论文汇报框架"),
            "notes": "补充作者、单位、导师、专业与答辩时间信息。"
        },
        make_slide(
            2,
            "汇报提纲",
            [
                "研究背景与问题提出",
                "研究目标、创新点与整体设计",
                "各研究模块的方法、结果与机制整合",
                "结论、价值、不足与展望",
            ],
            "第二页先给全局地图，让后续35页的展开更好跟进。",
        ),
        make_slide(
            3,
            "研究背景",
            split_points(brief.get("research_problem", ""), max_items=3),
            "背景页先讲临床/学术场景，再自然过渡到本论文切入点。",
        ),
        make_slide(
            4,
            "问题提出与研究缺口",
            [
                first_meaningful_point([slide_claims.get("problem", ""), brief.get("research_problem", "")], "需要进一步明确现有研究的关键缺口。"),
                "强调现有方案或认识中的不足，而不是泛泛综述。",
                "把论文要解决的核心矛盾收束成一到两个问题。",
            ],
            "这一页建议搭配文献脉络或临床痛点示意图。",
        ),
        make_slide(
            5,
            "研究目标",
            split_points(brief.get("method_summary", ""), max_items=3),
            "把研究目标拆成临床评价、机制探索、方法验证等层次。",
        ),
        make_slide(
            6,
            "核心科学问题",
            [
                "本论文真正想回答什么问题？",
                "研究对象、干预手段与核心观察指标之间是什么关系？",
                "最终希望形成怎样的机制解释或应用结论？",
            ],
            "这一页适合作为目标与创新之间的桥梁。",
        ),
        make_slide(
            7,
            "论文创新点",
            contributions[:3],
            "创新点不要写成口号，要和后文证据一一对应。",
        ),
        make_slide(
            8,
            "整体研究设计",
            split_points(brief.get("method_summary", ""), max_items=4),
            "概括研究类型、对象、关键技术和总体验证路径。",
        ),
        make_slide(
            9,
            "技术路线",
            [
                "先完成总体研究设计与研究对象纳入",
                "再依次展开各研究模块的证据获取",
                "最后完成机制整合、结论提炼与价值讨论",
            ],
            "后续可替换为真正的流程图或技术路线图。",
        ),
        make_slide(
            10,
            "论文总体结构",
            [f"研究内容{module['index']}：{module['display_title']}" for module in modules[:4]],
            "这里把整篇论文的章节主线说清楚，为后文展开做铺垫。",
        ),
    ]

    next_id = 11
    for module in modules[:4]:
        module_name = f"研究内容{module['index']}"
        method_points = []
        for text in module["method_texts"]:
            method_points.extend(split_points(text, max_items=2))
        result_points = []
        for text in module["result_texts"]:
            result_points.extend(split_points(text, max_items=2))
        conclusion_points = []
        for text in module["conclusion_texts"]:
            conclusion_points.extend(split_points(text, max_items=2))

        if not method_points:
            method_points = split_points(brief.get("method_summary", ""), max_items=2)
        if not result_points:
            result_points = split_points(brief.get("results_summary", ""), max_items=2)
        if not conclusion_points:
            conclusion_points = split_points(brief.get("conclusion_summary", ""), max_items=2)

        slides.extend(
            [
                make_slide(
                    next_id,
                    f"{module_name}：研究定位",
                    module_position_bullets(module),
                    "先讲模块任务，再说明它和总课题的关系。",
                ),
                make_slide(
                    next_id + 1,
                    f"{module_name}：设计与对象",
                    module_design_bullets(module, method_points),
                    "这一页适合配样本流程图、分组图或实验设计图。",
                ),
                make_slide(
                    next_id + 2,
                    f"{module_name}：观察指标与证据",
                    [
                        "围绕最关键指标展开，不把所有检测项目一股脑堆上去。",
                        *method_points[:3],
                    ],
                    "用指标体系解释为什么这个模块能支撑论文主结论。",
                ),
                make_slide(
                    next_id + 3,
                    f"{module_name}：核心结果",
                    result_points[:4],
                    "结果页优先放最强图表，文字只做结论性补充。",
                ),
                make_slide(
                    next_id + 4,
                    f"{module_name}：阶段结论",
                    conclusion_points[:4],
                    "每个研究模块都要形成一句清晰的阶段结论。",
                ),
            ]
        )
        next_id += 5

    closing_slides = [
        ("整体证据链整合", [
            "把临床、机制、模型和验证结果串成一条完整证据链。",
            first_meaningful_point([brief.get("results_summary", "")], "回到最关键的证据链进行归纳。"),
            first_meaningful_point([brief.get("conclusion_summary", "")], "把证据最后收束到论文主结论。"),
        ], "这一页是整篇论文的枢纽页，建议后续做成总图。"),
        ("机制模型归纳", [
            "建议把关键通路、关键因子和干预作用点画成机制示意图。",
            first_meaningful_point([brief.get("conclusion_summary", "")], "用一句话讲清机制主轴。"),
            "机制页只保留最核心链条，避免节点过多。",
        ], "这里后续最适合接入流程图工具。"),
        ("论文讨论一：结果如何解释", [
            "解释为什么这些结果能够支持你的核心判断。",
            "把结果与已有研究做对照，突出一致性与差异性。",
            "讨论页强调解释力，不重复报结果。",
        ], "讨论页建议围绕问题-证据-解释三段式展开。"),
        ("论文讨论二：价值何在", [
            contributions[0],
            contributions[1] if len(contributions) > 1 else "进一步提炼论文的学术和应用价值。",
            "明确论文对本领域认知或实践的推进意义。",
        ], "这里既可以讲学术价值，也可以讲应用意义。"),
        ("论文创新点再提炼", [
            *contributions[:3],
            "创新点必须和前文具体证据一一对应。",
        ], "如果创新点较多，建议压缩成2-3个最硬的点。"),
        ("论文学术与应用价值", [
            "说明论文对理论认识、研究路径或评价方法的贡献。",
            "说明论文对临床、工程或应用实践的潜在价值。",
            "尽量避免空泛表达，回到具体证据支撑。",
        ], "这一页更偏价值表达，不重复方法与结果细节。"),
        ("研究局限性", [
            limitations[0],
            "局限性表述要主动、克制、专业。",
            "说明局限性不会推翻主结论，但会影响外推边界。",
        ], "局限性页不要回避，是博士答辩必须讲稳的一页。"),
        ("总体结论一", split_points(brief.get("conclusion_summary", ""), max_items=3), "结论页先讲最重要的一层结论。"),
        ("总体结论二", [
            first_meaningful_point(brief.get("contributions", []), "把主结论进一步提炼为一句话 take-away。"),
            "回到主论文，不让任何旁支内容盖过中心结论。",
            "形成听众离场时最容易记住的结论表述。",
        ], "这一页更像最终 take-away。"),
        ("研究展望", [
            "未来研究可围绕样本扩大、验证深化和机制细化继续推进。",
            "展望页既要延续论文逻辑，也要体现博士课题的发展空间。",
            "不需要展开成附录，只保留最核心的后续方向。",
        ], "最后一页以前瞻性收束，而不是新增信息负担。"),
    ]

    for title, bullets, notes in closing_slides:
        slides.append(make_slide(next_id, title, bullets, notes))
        next_id += 1

    return slides


def outline_markdown(brief: dict, slides: list[dict]) -> str:
    lines = [f"# {brief['title']} 汇报页纲", ""]
    for index, slide in enumerate(slides, start=1):
        lines.append(f"## {index}. {slide['title']}")
        if slide.get("subtitle"):
            lines.append(f"- {slide['subtitle']}")
        for bullet in slide.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def speaker_notes(brief: dict, slides: list[dict]) -> str:
    lines = ["# 讲稿备注", "", "## 总体建议"]
    lines.append("- 全程用中文讲述，英文术语只作为补充标注。")
    lines.append("- 35页的节奏要保持“背景简洁、方法清楚、结果充实、讨论克制”。")
    lines.append("- 每个研究模块都要有一句阶段结论，最后再回到总结论。")
    lines.append("")
    lines.append("## 逐段提醒")
    lines.append("- 前10页负责建立问题、目标、创新与总体设计。")
    lines.append("- 中间模块页负责完整展开论文主体，是整场汇报的重心。")
    lines.append(f"- 局限性建议明确表达为：{brief['limitations'][0]}")
    lines.append(f"- 当前框架共 {len(slides)} 页，不含附录和备答页。")
    return "\n".join(lines) + "\n"


def defense_qa(brief: dict) -> str:
    return f"""# 答辩问答

1. 这篇论文最核心的贡献是什么？
   - {brief["contributions"][0]}

2. 为什么你的研究设计能够支撑论文主结论？
   - 需要把总体设计、研究模块和关键证据链串起来回答。

3. 汇报中哪几页是最关键的证据页？
   - 优先回到各研究模块的“核心结果”页和“整体证据链整合”页。

4. 这项研究最需要主动说明的边界是什么？
   - {brief["limitations"][0]}
"""


def _compact_slide_bullets(slides: list[dict], max_items: int = 4) -> list[str]:
    collected: list[str] = []
    for slide in slides:
        for bullet in slide.get("bullets", []):
            text = str(bullet).strip()
            if text and text not in collected:
                collected.append(text)
    return collected[:max_items] or ["待结合原文继续压缩和打磨。"]


def _compact_slide_notes(slides: list[dict], fallback: str) -> str:
    notes = []
    for slide in slides:
        note = str(slide.get("notes", "")).strip()
        if note and note not in notes:
            notes.append(note)
    return " ".join(notes) if notes else fallback


def compact_longform_to_35(slides: list[dict]) -> list[dict]:
    if len(slides) <= 35:
        return slides

    fixed = [dict(slide) for slide in slides[:32]]
    tail = [dict(slide) for slide in slides[32:]]

    fixed.append(
        make_slide(
            33,
            "讨论与价值",
            _compact_slide_bullets(tail[:3]),
            _compact_slide_notes(tail[:3], "把结果解释、创新意义和应用价值收成一页。"),
        )
    )
    fixed.append(
        make_slide(
            34,
            "局限性与总体结论",
            _compact_slide_bullets(tail[3:6] if len(tail) >= 6 else tail[3:]),
            _compact_slide_notes(tail[3:6] if len(tail) >= 6 else tail[3:], "先交代边界，再回到总体结论。"),
        )
    )
    fixed.append(
        make_slide(
            35,
            "研究展望",
            _compact_slide_bullets(tail[6:] if len(tail) > 6 else tail[-1:]),
            _compact_slide_notes(tail[6:] if len(tail) > 6 else tail[-1:], "最后一页以前瞻性和整体收束结束。"),
        )
    )
    return fixed


def build_spec(brief: dict, extraction: dict | None, template: str) -> dict:
    slides = compact_longform_to_35(build_longform_slides(brief, extraction, template))
    return {
        "schema_version": "0.3",
        "title": brief["title"],
        "scene": brief.get("scene", "graduation-defense"),
        "language": brief.get("presentation_language", brief.get("language", "zh-CN")),
        "template": template,
        "slides": slides,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create long-form deck outline/spec and speaking artifacts.")
    parser.add_argument("--analysis-file", required=True)
    parser.add_argument("--outline-file", required=True)
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--notes-file", required=True)
    parser.add_argument("--qa-file", required=True)
    parser.add_argument("--template", default="cdutcm-defense")
    parser.add_argument("--extraction-file")
    args = parser.parse_args()

    brief = read_json(Path(args.analysis_file))
    extraction = read_json(Path(args.extraction_file)) if args.extraction_file else None
    spec = build_spec(brief, extraction, args.template)
    write_text(Path(args.outline_file), outline_markdown(brief, spec["slides"]))
    write_text(Path(args.notes_file), speaker_notes(brief, spec["slides"]))
    write_text(Path(args.qa_file), defense_qa(brief))
    write_json(Path(args.spec_file), spec)


if __name__ == "__main__":
    main()
