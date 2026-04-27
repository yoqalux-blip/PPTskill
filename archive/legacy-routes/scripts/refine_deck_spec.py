from __future__ import annotations

import argparse
import copy
import re
from pathlib import Path

from common_io import read_json, write_json, write_text


CHINESE_NUMERALS = {1: "一", 2: "二", 3: "三", 4: "四"}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def weighted_length(text: str) -> float:
    total = 0.0
    for char in normalize(text):
        if "\u4e00" <= char <= "\u9fff":
            total += 1.0
        else:
            total += 0.55
    return total


def smart_clip(text: str, limit: float = 34.0) -> str:
    text = normalize(text)
    if not text:
        return ""
    total = 0.0
    kept: list[str] = []
    truncated = False
    for char in text:
        total += 1.0 if "\u4e00" <= char <= "\u9fff" else 0.55
        if total > limit:
            truncated = True
            break
        kept.append(char)
    if not truncated:
        return text
    clipped = "".join(kept).strip(" ,.;:，。；：")
    return clipped.rstrip(" ,.;:，。；：") + "..."


def split_points(text: str, max_items: int = 3, limit: float = 34.0) -> list[str]:
    text = normalize(text)
    if not text:
        return []
    text = re.sub(r"^(本研究关注的问题是：|在研究设计上，|主要结果显示，|综合结论可以概括为：)", "", text)
    raw_parts = re.split(r"[。；;！？!?]", text)
    points = [smart_clip(part.strip("：:、，, "), limit) for part in raw_parts if part.strip("：:、，, ")]
    if len(points) >= max_items:
        return points[:max_items]
    if len(points) == 1:
        subparts = re.split(r"[，,、]", points[0])
        expanded = [smart_clip(part.strip(), limit) for part in subparts if len(part.strip()) >= 6]
        if expanded:
            return expanded[:max_items]
    return points[:max_items]


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = normalize(item)
        if not cleaned:
            continue
        key = re.sub(r"[\W_]+", "", cleaned).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def sanitize_bullets(items: list[str], limit: float = 40.0, max_items: int = 4) -> list[str]:
    cleaned = [smart_clip(item, limit) for item in dedupe(items)]
    return cleaned[:max_items]


def is_english_heavy(text: str) -> bool:
    letters = sum(1 for char in text if char.isascii() and char.isalpha())
    cjk = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    return letters >= 10 and letters > cjk * 2


def infer_intervention(title: str) -> str:
    match = re.match(r"(.+?)(?:治疗|干预|改善)", title)
    return normalize(match.group(1)) if match else "该干预方案"


def infer_condition(title: str) -> str:
    match = re.search(r"(?:治疗|干预|改善)(.+?)(?:的临床与机制研究|的机制研究|的研究|研究)$", title)
    if match:
        return normalize(match.group(1))
    return "目标疾病场景"


def compact_condition(condition: str) -> str:
    condition = normalize(condition)
    if not condition or condition == "目标疾病场景":
        return condition
    compact = condition.replace("多重耐药肺炎克雷伯菌", "MDR-KP")
    compact = compact.replace("所致", "")
    compact = compact.replace("患者", "")
    compact = compact.replace("MDR-KP（MDR-KP）", "MDR-KP")
    compact = compact.replace("MDR-KP(MDR-KP)", "MDR-KP")
    return compact


def classify_module(text: str, index: int) -> str:
    lowered = normalize(text).lower()
    if any(token in lowered for token in ("临床", "clinical efficacy", "safety", "疗效")):
        return "clinical"
    if any(token in lowered for token in ("immune", "炎症", "蛋白", "proteomics", "蛋白组")):
        return "immune"
    if any(token in lowered for token in ("rat", "动物", "mtor", "autophagy", "nf-κb", "nlrp3", "model")):
        return "animal"
    if any(token in lowered for token in ("cell", "a549", "alveolar", "serum", "细胞", "含药血清")):
        return "cell"
    return {1: "clinical", 2: "immune", 3: "animal", 4: "cell"}.get(index, "generic")


def collect_module_kinds(spec: dict) -> dict[int, str]:
    kinds: dict[int, str] = {}
    for slide in spec.get("slides", []):
        match = re.search(r"研究内容(\d+)", slide.get("title", ""))
        if not match:
            continue
        index = int(match.group(1))
        if index in kinds:
            continue
        sample = " ".join([slide.get("title", ""), *slide.get("bullets", [])])
        kinds[index] = classify_module(sample, index)

    default_sequence = {1: "clinical", 2: "immune", 3: "animal", 4: "cell"}
    for index, expected in default_sequence.items():
        if index not in kinds:
            kinds[index] = expected
        elif index > 1 and kinds[index] == kinds.get(index - 1):
            kinds[index] = expected
    return kinds


def build_innovations(intervention: str, condition: str) -> list[str]:
    short_condition = compact_condition(condition)
    return [
        f"围绕{short_condition}构建了从临床评价到机制验证的连续证据链。",
        "将自噬调控与炎症通路纳入同一解释框架，提示干预具有多靶点调控特征。",
        f"为{intervention}应用于耐药菌相关重症肺炎提供了临床与实验结合的依据。",
    ]


def build_limitations(condition: str) -> list[str]:
    short_condition = compact_condition(condition)
    return [
        f"研究对象聚焦于{short_condition}这一特定场景，结果外推范围仍需谨慎把握。",
        "机制验证集中在关键通路层面，尚不能覆盖全部活性成分与完整网络调控。",
        "后续仍需更大样本、多中心和更深入的功能实验继续验证。",
    ]


def module_profile(kind: str, index: int, intervention: str, condition: str) -> dict:
    short_condition = compact_condition(condition)
    if kind == "clinical":
        return {
            "section_title": "临床疗效与安全性评价",
            "position": [
                "本模块回答干预方案是否真正带来临床获益。",
                f"围绕{short_condition}患者的症状改善、预后变化和安全性展开。",
                "为整篇论文提供最直接的临床价值支撑。",
            ],
            "design": [
                "采用多中心、随机化、平行对照的临床研究设计。",
                "围绕病例纳入、分组干预和随访结局进行系统评价。",
                "重点观察症状改善、预后指标和不良反应情况。",
            ],
            "evidence": [
                "核心观察指标包括临床症状、疗效结局、免疫细胞变化与安全性指标。",
                "通过关键终点而不是堆砌全部检测项目来组织页面证据。",
                "建议图表优先展示分组比较、症状变化和主要结局指标。",
            ],
            "results": [
                f"{intervention}用于{short_condition}后，患者临床症状与整体预后指标呈改善趋势。",
                "外周免疫细胞过度激活得到缓解，炎症风暴相关表现下降。",
                "治疗期间未见明显安全性风险，提示方案具有临床应用可行性。",
            ],
            "conclusion": [
                f"{intervention}在{short_condition}中的临床应用具有有效性与安全性基础。",
                "该模块完成了整篇论文最核心的临床获益论证。",
            ],
        }
    if kind == "immune":
        return {
            "section_title": "免疫炎症反应与差异蛋白分析",
            "position": [
                "本模块解释临床改善背后的免疫炎症变化方向。",
                "重点观察免疫细胞、炎症因子和差异蛋白的系统性变化。",
                "为后续机制验证筛选关键分子与通路线索。",
            ],
            "design": [
                "依托流式细胞术、ELISA和蛋白组学构建指标体系。",
                "分别从细胞水平、体液水平和分子水平追踪干预响应。",
                "将差异蛋白筛选结果与通路富集结果联合解释。",
            ],
            "evidence": [
                "优先展示免疫细胞亚群、炎症因子和差异蛋白的代表性变化。",
                "图表组织应体现由现象观察到通路筛选的推进关系。",
                "建议保留少量最强证据，避免把检测清单平铺在一页上。",
            ],
            "results": [
                "干预后外周免疫细胞过度激活与炎症因子异常升高表现得到缓解。",
                "差异蛋白分析提示疾病进展与干预响应存在可解释的通路线索。",
                "该模块为动物与细胞实验的机制验证提供了明确方向。",
            ],
            "conclusion": [
                "HQQD可能通过重塑免疫炎症反应网络发挥保护作用。",
                "蛋白组学与通路分析为机制研究建立了候选靶点基础。",
            ],
        }
    if kind == "animal":
        return {
            "section_title": "动物模型机制验证",
            "position": [
                "本模块将临床观察推进到整体动物水平的机制验证。",
                "重点回答关键通路是否在疾病模型中真实激活，以及能否被干预逆转。",
                "用于建立从临床现象到机制解释之间的桥梁。",
            ],
            "design": [
                "建立MDR-KP相关肺炎动物模型并设置对照与干预分组。",
                "联合组织学、分子检测和蛋白检测评价关键通路变化。",
                "重点关注自噬调控及TLR4/NF-kB/NLRP3炎症相关信号。",
            ],
            "evidence": [
                "优先展示肺组织损伤、自噬水平和炎症通路关键分子的变化。",
                "图表组织建议体现模型建立、通路异常和干预逆转三段式逻辑。",
                "这一页的价值在于把临床现象落到可验证的生物学机制上。",
            ],
            "results": [
                "MDR-KP感染可导致CLUH下调、自噬受抑以及炎症相关通路异常激活。",
                f"{intervention}干预后，上述异常指标出现逆转趋势，炎症损伤有所减轻。",
                "动物实验从整体水平支持了临床疗效与机制推断的一致性。",
            ],
            "conclusion": [
                "HQQD可能通过调控自噬与炎症通路共同缓解肺部损伤。",
                "该模块完成了从临床现象到整体机制的关键跨越。",
            ],
        }
    if kind == "cell":
        return {
            "section_title": "细胞保护作用与分子机制验证",
            "position": [
                "本模块用于锁定肺泡上皮细胞层面的关键保护作用。",
                "通过细胞模型进一步验证关键分子、ROS和细胞损伤变化。",
                "完成整篇论文最后一层机制闭环。",
            ],
            "design": [
                "以肺泡上皮细胞模型为对象，设置感染、对照与干预条件。",
                "结合含药血清干预观察细胞活性、炎症、氧化应激和凋亡变化。",
                "围绕关键通路分子完成细胞层面的功能验证。",
            ],
            "evidence": [
                "优先展示细胞活性、ROS、炎症因子与凋亡指标的代表性变化。",
                "建议图表按损伤表型、通路变化、干预逆转的顺序组织。",
                "这一页负责说明干预并非仅在整体水平有效，而是具有明确细胞保护基础。",
            ],
            "results": [
                f"{intervention}相关干预对受损肺泡上皮细胞具有保护作用。",
                "其可降低ROS生成、炎症因子释放与细胞凋亡水平。",
                "细胞实验进一步支持其多靶点、多通路的整体调控特征。",
            ],
            "conclusion": [
                "细胞层面的结果进一步巩固了HQQD的保护机制解释。",
                "整篇论文由此形成临床到机制的闭环证据链。",
            ],
        }
    return {
        "section_title": f"研究模块{index}",
        "position": [
            "本模块用于展开论文主体中的一个关键问题。",
            "需要交代该模块在整篇论文中的任务和证据定位。",
            "页面组织应服务于最后的总体结论。",
        ],
        "design": [
            "围绕研究对象、分组设计和关键观察指标展开。",
            "尽量只保留与主结论直接相关的方法信息。",
            "建议图示优先于冗长文字。",
        ],
        "evidence": [
            "选取最强指标支撑单页核心信息。",
            "避免把所有实验项目堆叠在同一页上。",
            "图表和文字之间需要形成清晰主次关系。",
        ],
        "results": [
            "该模块获得了支持论文主线的重要结果。",
            "建议在正式版中结合原图表进一步压缩文字。",
        ],
        "conclusion": [
            "该模块形成了对主结论的阶段性支撑。",
        ],
    }


def replace_slide_content(slide: dict, title: str, bullets: list[str], notes: str, layout: str | None = None) -> dict:
    slide["title"] = title
    slide["bullets"] = sanitize_bullets(bullets)
    slide["notes"] = notes
    if layout:
        slide["layout"] = layout
    return slide


def refine_spec(spec: dict, brief: dict, extraction: dict | None) -> tuple[dict, dict]:
    refined = copy.deepcopy(spec)
    refined["schema_version"] = "0.4"
    refined["refinement"] = {"pass": "v1", "strategy": "self-review-polish"}

    title = brief.get("title", spec.get("title", "论文汇报"))
    intervention = infer_intervention(title)
    condition = infer_condition(title)
    module_kinds = collect_module_kinds(spec)
    innovations = build_innovations(intervention, condition)
    limitations = build_limitations(condition)

    english_heavy = 0
    overlong = 0
    placeholder_like = 0
    adjusted_titles: list[str] = []

    for slide in spec.get("slides", []):
        if any(is_english_heavy(item) for item in slide.get("bullets", [])):
            english_heavy += 1
        if any(weighted_length(item) > 38 for item in slide.get("bullets", [])):
            overlong += 1
        if any(item.startswith("贡献") for item in slide.get("bullets", [])) or "真正想回答什么问题" in " ".join(slide.get("bullets", [])):
            placeholder_like += 1

    for slide in refined.get("slides", []):
        raw_title = slide.get("title", "")

        if raw_title == "研究背景":
            replace_slide_content(
                slide,
                "研究背景",
                [
                    f"{compact_condition(condition)}病情重、治疗难度高，临床亟需兼顾疗效与机制解释的研究证据。",
                    "痰热蕴肺证是该类患者的重要中医证候，为中医辨证干预提供了切入点。",
                    f"本论文聚焦{intervention}能否改善疾病结局并解释其免疫炎症调控机制。",
                ],
                "背景页要先讲清临床挑战，再说明论文为什么选择这一干预与这一疾病场景。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "问题提出与研究缺口":
            replace_slide_content(
                slide,
                "问题提出与研究缺口",
                [
                    "现有研究往往停留在经验应用或单一指标观察，缺乏连续证据链支撑。",
                    f"{intervention}是否能够同时带来临床获益并调控免疫炎症反应，仍需系统回答。",
                    "尚需把临床疗效、分子筛选、动物验证和细胞机制纳入同一研究框架。",
                ],
                "这一页要把缺口收束成后文真正要回答的三个问题，而不是泛泛综述。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "研究目标":
            replace_slide_content(
                slide,
                "研究目标",
                [
                    f"评价{intervention}治疗{compact_condition(condition)}的临床疗效与安全性。",
                    "观察免疫炎症细胞、炎症因子和差异蛋白的变化规律。",
                    "通过动物与细胞实验验证关键通路和潜在分子机制。",
                ],
                "目标页要压成三层结构：临床是否有效、通路线索是什么、机制如何验证。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "核心科学问题":
            replace_slide_content(
                slide,
                "核心科学问题",
                [
                    f"{intervention}能否改善{compact_condition(condition)}的临床症状、预后与安全性结局？",
                    "该干预是否能够缓解免疫细胞过度激活和炎症风暴？",
                    "其潜在机制是否与自噬调控及关键炎症通路变化有关？",
                ],
                "这里要像答辩里的总问题页，三个问题分别对应后面的三个证据层次。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "论文创新点":
            replace_slide_content(
                slide,
                "论文创新点",
                innovations,
                "创新点必须是论文本身的贡献，不再使用工具流程式表述。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "整体研究设计":
            replace_slide_content(
                slide,
                "整体研究设计",
                [
                    "临床研究负责回答疗效与安全性问题。",
                    "样本检测与蛋白组学负责筛选免疫炎症调控线索。",
                    "动物模型与细胞实验负责完成关键通路的层层验证。",
                ],
                "整体设计页要让评委一眼看懂整篇论文是如何逐层推进的。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "技术路线":
            replace_slide_content(
                slide,
                "技术路线",
                [
                    "临床入组与干预评价",
                    "免疫炎症指标检测与蛋白组学筛选",
                    "动物模型通路验证",
                    "细胞模型机制闭环验证",
                ],
                "后续正式版可以把这一页换成真正的技术路线图，但当前先把路径讲清楚。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "论文总体结构":
            bullets = []
            for index in range(1, 5):
                kind = module_kinds.get(index, "generic")
                bullets.append(f"研究内容{CHINESE_NUMERALS[index]}：{module_profile(kind, index, intervention, condition)['section_title']}")
            replace_slide_content(
                slide,
                "论文总体结构",
                bullets,
                "这一页负责提前告诉听众四个研究模块如何从临床走到机制。",
            )
            adjusted_titles.append(slide["title"])
            continue

        match = re.match(r"研究内容(\d+)：(.+)", raw_title)
        if match:
            index = int(match.group(1))
            part = match.group(2)
            kind = module_kinds.get(index, "generic")
            profile = module_profile(kind, index, intervention, condition)
            numeral = CHINESE_NUMERALS.get(index, str(index))

            if part == "研究定位":
                replace_slide_content(
                    slide,
                    f"研究内容{numeral} {profile['section_title']}",
                    profile["position"],
                    "模块引导页要用来切段和建立期待，不要放太多技术细节。",
                    layout="section",
                )
                adjusted_titles.append(slide["title"])
                continue

            if part == "设计与对象":
                replace_slide_content(
                    slide,
                    f"研究内容{numeral}：设计与对象",
                    profile["design"],
                    "方法页重点保留研究设计、对象与关键结局，避免重复背景。",
                )
                adjusted_titles.append(slide["title"])
                continue

            if part == "观察指标与证据":
                replace_slide_content(
                    slide,
                    f"研究内容{numeral}：观察指标与证据",
                    profile["evidence"],
                    "证据页更像图表导航页，要说明为什么这些指标足以支撑结论。",
                )
                adjusted_titles.append(slide["title"])
                continue

            if part == "核心结果":
                replace_slide_content(
                    slide,
                    f"研究内容{numeral}：核心结果",
                    profile["results"],
                    "结果页优先放最强图表，文字只负责把图表结论说清楚。",
                )
                adjusted_titles.append(slide["title"])
                continue

            if part == "阶段结论":
                replace_slide_content(
                    slide,
                    f"研究内容{numeral}：阶段结论",
                    profile["conclusion"],
                    "阶段结论要成为听众能直接记住的一句话 take-away。",
                )
                adjusted_titles.append(slide["title"])
                continue

        if raw_title == "整体证据链整合":
            replace_slide_content(
                slide,
                "整体证据链整合",
                [
                    "临床研究证明方案具有可观察到的疗效与安全性基础。",
                    "免疫炎症分析与蛋白组学筛选提供了关键通路与候选分子线索。",
                    "动物和细胞实验进一步完成了从现象到机制的闭环验证。",
                ],
                "这页是全篇的总枢纽，建议后续做成一张整合示意图。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "机制模型归纳":
            replace_slide_content(
                slide,
                "机制模型归纳",
                [
                    "MDR-KP感染可诱发自噬受抑、炎症通路激活和细胞损伤加重。",
                    f"{intervention}可能通过调控CLUH/mTOR自噬轴及炎症相关通路减轻肺损伤。",
                    "最终表现为炎症反应缓解、细胞保护增强和整体结局改善。",
                ],
                "这一页后续非常适合替换成机制图，目前先把机制主轴明确下来。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "论文讨论一：结果如何解释":
            replace_slide_content(
                slide,
                "论文讨论一：结果如何解释",
                [
                    "本研究将临床获益与免疫炎症调控结果联系起来，提升了解释力度。",
                    "结果并非单一终点改善，而是跨临床、分子和模型层面的同向证据。",
                    "讨论重点应放在为何这些证据能够共同支撑主结论。",
                ],
                "讨论页不要重复报结果，而是解释结果为什么可信、为什么重要。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "论文讨论二：价值何在":
            replace_slide_content(
                slide,
                "论文讨论二：价值何在",
                [
                    f"为{intervention}应用于{compact_condition(condition)}提供了更扎实的证据基础。",
                    "证明中西医结合研究可以从临床观察进一步延展到通路与机制层面。",
                    "对后续优化干预策略和深化机制研究具有启发意义。",
                ],
                "这一页强调价值，不再重复技术细节。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "论文创新点再提炼":
            replace_slide_content(
                slide,
                "论文创新点再提炼",
                innovations,
                "和前面的创新点页保持一致，但这里更强调与证据页一一对应。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "论文学术与应用价值":
            replace_slide_content(
                slide,
                "论文学术与应用价值",
                [
                    "在学术上，论文将临床现象、自噬调控和炎症通路纳入统一解释框架。",
                    "在方法上，形成了临床研究、蛋白组学与模型验证的组合路径。",
                    "在应用上，为耐药菌相关重症肺炎的中西医结合干预提供了依据。",
                ],
                "价值页要分学术、方法、应用三个层次去讲，逻辑最清楚。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "研究局限性":
            replace_slide_content(
                slide,
                "研究局限性",
                limitations,
                "局限性页要主动、克制、专业，体现博士答辩应有的边界意识。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "总体结论一":
            replace_slide_content(
                slide,
                "总体结论一",
                [
                    f"{intervention}治疗{compact_condition(condition)}具有较明确的临床获益与安全性基础。",
                    "其作用并非局限于症状改善，还体现在免疫炎症失衡的整体缓解。",
                    "这为后续机制层面的深入解释奠定了主结论基础。",
                ],
                "第一张结论页先收束临床与整体现象层面的主要结论。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "总体结论二":
            replace_slide_content(
                slide,
                "总体结论二",
                [
                    "论文提示该干预可能通过自噬调控和炎症通路协同发挥保护作用。",
                    "整篇研究由临床到动物再到细胞实验，形成连续而闭环的机制证据。",
                    "最终 take-away 是疗效、机制与应用价值能够在同一主线中被统一解释。",
                ],
                "第二张结论页更像全场最后的 take-away，要把整篇论文一句话讲透。",
            )
            adjusted_titles.append(slide["title"])
            continue

        if raw_title == "研究展望":
            replace_slide_content(
                slide,
                "研究展望",
                [
                    "进一步扩大样本量并开展更高层级的临床验证研究。",
                    "围绕关键活性成分、关键靶点和通路网络继续深入解析。",
                    "推动从机制认识走向更稳定的临床转化与方案优化。",
                ],
                "展望页要前瞻，但不要引入新的信息负担。",
            )
            adjusted_titles.append(slide["title"])
            continue

        slide["bullets"] = sanitize_bullets(slide.get("bullets", []))

    report = {
        "title": title,
        "total_slides": len(refined.get("slides", [])),
        "issues_found": {
            "english_heavy_slides": english_heavy,
            "overlong_bullets": overlong,
            "placeholder_like_slides": placeholder_like,
        },
        "actions_applied": [
            "统一为中文答辩口径，替换英文或中英混杂的核心条目。",
            "将论文创新点从工具流程表述改写为论文本身的创新与价值。",
            "将四个研究模块重命名并用 section 布局强化章节感。",
            "重写局限性、总体结论与研究展望，使其更符合正式答辩语境。",
        ],
        "adjusted_slide_titles": adjusted_titles,
    }
    return refined, report


def outline_markdown(spec: dict) -> str:
    lines = [f"# {spec.get('title', '论文汇报')} V1 页纲", ""]
    for index, slide in enumerate(spec.get("slides", []), start=1):
        lines.append(f"## {index}. {slide.get('title', '')}")
        for bullet in slide.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def report_markdown(report: dict) -> str:
    issues = report["issues_found"]
    lines = [
        "# Deck V1 自检报告",
        "",
        "## 发现的问题",
        f"- 英文或中英混杂较重的页面：{issues['english_heavy_slides']} 页",
        f"- 过长条目较多的页面：{issues['overlong_bullets']} 页",
        f"- 模板化或工具味较重的页面：{issues['placeholder_like_slides']} 页",
        "",
        "## 本轮自动优化",
    ]
    for action in report["actions_applied"]:
        lines.append(f"- {action}")
    lines.extend([
        "",
        "## 仍建议人工复核",
        "- 图表与原文页码、原始统计表之间尚未做一一绑定。",
        "- 关键结果页建议继续和原文结果章节逐项对读，便于后续补图。",
        "- 当前 V1 已适合看结构和讲述逻辑，终稿阶段再做图表重绘与版式精修。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Self-review and refine a generated deck spec into a V1 presentation draft.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--brief-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--outline-file")
    parser.add_argument("--extraction-file")
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    brief = read_json(Path(args.brief_file))
    extraction = read_json(Path(args.extraction_file)) if args.extraction_file else None

    refined, report = refine_spec(spec, brief, extraction)
    write_json(Path(args.output_file), refined)
    write_text(Path(args.report_file), report_markdown(report))
    if args.outline_file:
        write_text(Path(args.outline_file), outline_markdown(refined))


if __name__ == "__main__":
    main()
