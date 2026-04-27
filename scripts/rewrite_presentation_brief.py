from __future__ import annotations

import argparse
import re
from pathlib import Path

from common_io import read_json, write_json

PHRASE_REPLACEMENTS = [
    (r"Monocyte HLA-DR expression", "单核细胞HLA-DR表达"),
    (r"sepsis-induced immunosuppression", "脓毒症诱导的免疫抑制"),
    (r"septic shock", "脓毒性休克"),
    (r"septic patients", "脓毒症患者"),
    (r"sepsis", "脓毒症"),
    (r"hyperinflammation", "高炎症反应"),
    (r"immunosuppression", "免疫抑制"),
    (r"ICU-acquired infections?", "ICU获得性感染"),
    (r"prolonged stays in ICU", "ICU住院时间延长"),
    (r"increased mortality", "死亡率升高"),
    (r"immunostimulant therapies", "免疫刺激治疗"),
    (r"clinical trials", "临床试验"),
    (r"effective stratification", "有效分层"),
    (r"immune dysfunction", "免疫功能障碍"),
    (r"real-world", "真实世界"),
    (r"cohort study", "队列研究"),
    (r"flow cytometry", "流式细胞术"),
    (r"Primary outcomes included", "主要结局包括"),
    (r"day-28", "28天"),
    (r"day-90", "90天"),
    (r"mortality", "死亡率"),
    (r"Kaplan-Meier survival curves", "Kaplan-Meier生存曲线"),
    (r"trajectory clustering", "轨迹聚类"),
    (r"multivariate analyses", "多变量分析"),
    (r"this study confirms that", "本研究证实"),
    (r"This large real-world study confirms that", "这项大样本真实世界研究证实"),
    (r"time-course analysis suggests that", "时间序列分析提示"),
    (r"higher risk of adverse outcomes", "不良结局风险更高"),
]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def clip(text: str, limit: int = 320) -> str:
    text = normalize_whitespace(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def replace_phrases(text: str) -> str:
    localized = text
    for pattern, replacement in PHRASE_REPLACEMENTS:
        localized = re.sub(pattern, replacement, localized, flags=re.IGNORECASE)
    localized = localized.replace("patients", "患者")
    localized = localized.replace("Methods", "方法")
    localized = localized.replace("Results", "结果")
    localized = localized.replace("Conclusions", "结论")
    localized = localized.replace("Conclusion", "结论")
    localized = localized.replace("Purpose", "研究目的")
    localized = localized.replace("Background", "研究背景")
    localized = localized.replace("This association held across", "这一关联在以下分析中均保持稳定：")
    localized = localized.replace("was significantly associated with", "与以下结局显著相关：")
    localized = localized.replace("Importantly,", "更重要的是，")
    localized = localized.replace("collectively", "综合来看")
    return normalize_whitespace(localized)


def localize_text(text: str, prefix: str | None = None) -> str:
    text = normalize_whitespace(text)
    if not text:
        return ""
    if contains_cjk(text):
        body = text
    else:
        body = replace_phrases(text)
    if prefix:
        return clip(f"{prefix}{body}")
    return clip(body)


def localize_title(title: str) -> str:
    title = normalize_whitespace(title)
    if contains_cjk(title):
        return title
    return title


def localize_limitations(limitations: list[str]) -> list[str]:
    if not limitations:
        return ["目前抽取结果未能稳定识别原文明确局限性，正式汇报时应主动强调观察性研究的边界。"]
    localized = [localize_text(item) for item in limitations if item]
    if not localized:
        return ["目前抽取结果未能稳定识别原文明确局限性，正式汇报时应主动强调观察性研究的边界。"]
    localized = [
        "目前抽取结果未能稳定识别原文明确局限性，正式汇报时应主动强调研究边界，避免过度外推。"
        if text.startswith("Primary paper does not state limitations clearly")
        else text
        for text in localized
    ]
    return localized


def choose_section_text(extraction: dict, analysis: dict, section: str, fallback: str) -> str:
    chunk_map = {chunk["id"]: chunk for chunk in extraction.get("chunks", [])}
    chunk_ids = analysis.get("evidence_map", {}).get(section, [])
    preferred = []
    for chunk_id in chunk_ids:
        chunk = chunk_map.get(chunk_id)
        if not chunk:
            continue
        text = normalize_whitespace(chunk.get("text", ""))
        if not text:
            continue
        preferred.append(text)
    for text in preferred:
        if contains_cjk(text) and len(text) >= 20:
            return text
    primary_source = analysis.get("primary_source")
    exact_matches = []
    label_matches = []
    heuristic_matches: list[tuple[int, str]] = []
    for chunk in extraction.get("chunks", []):
        if primary_source and chunk.get("source") != primary_source:
            continue
        text = normalize_whitespace(chunk.get("text", ""))
        if not text or not contains_cjk(text) or len(text) < 20:
            continue
        section_hint = chunk.get("section_hint", "")
        section_label = chunk.get("section_label", "")
        if section_hint == section:
            exact_matches.append(text)
            continue
        if section == "results" and section_label == "results":
            label_matches.append(text)
            continue
        if section == "conclusion" and section_label == "conclusion":
            label_matches.append(text)
            continue
        if section == "results" and any(token in text for token in ("结果显示", "显著", "升高", "降低", "改善", "逆转")):
            score = 0
            if "显著" in text:
                score += 10
            if any(token in text for token in ("改善", "升高", "降低", "逆转")):
                score += 6
            heuristic_matches.append((score, text))
            continue
        if section == "conclusion" and any(token in text for token in ("结论", "表明", "提示", "安全有效", "机制")):
            score = 0
            if text.startswith(("1.", "一、", "（一）")):
                score += 10
            if any(token in text for token in ("安全有效", "表明", "提示")):
                score += 8
            if "机制" in text:
                score += 4
            heuristic_matches.append((score, text))
            continue
    for bucket in (exact_matches, label_matches):
        if bucket:
            return bucket[0]
    if heuristic_matches:
        heuristic_matches.sort(key=lambda item: (-item[0], len(item[1])))
        return heuristic_matches[0][1]
    return fallback


def build_contributions(analysis: dict) -> list[str]:
    method_summary = analysis.get("method_summary", "")
    results_summary = analysis.get("results_summary", "")
    contributions = [
        "贡献一：围绕主论文重新组织论述主线，避免附件文献替代核心结论。",
        "贡献二：突出可用于汇报的关键证据，而不是堆叠背景知识。",
    ]
    lowered_method = method_summary.lower()
    lowered_results = results_summary.lower()
    if "1023" in method_summary or "20-year" in lowered_method:
        contributions[0] = "贡献一：基于20年、1023例脓毒性休克患者的真实世界队列，系统评估mHLA-DR的分层价值。"
    if "mortality" in lowered_results or "死亡率" in results_summary:
        contributions[1] = "贡献二：说明低mHLA-DR与死亡率及ICU获得性感染风险升高之间存在稳定关联。"
    return contributions


def build_slide_claims(analysis: dict) -> dict:
    return {
        "positioning": "汇报主线应始终围绕主论文展开，附件文献仅用于补充机制背景与旁证。",
        "problem": localize_text(analysis.get("research_problem", ""), prefix="核心问题："),
        "method": localize_text(analysis.get("method_summary", ""), prefix="研究设计："),
        "results": localize_text(analysis.get("results_summary", ""), prefix="核心结果："),
        "conclusion": localize_text(analysis.get("conclusion_summary", ""), prefix="结论提炼："),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite extraction analysis into a Chinese-first presentation brief.")
    parser.add_argument("--analysis-file", required=True)
    parser.add_argument("--extraction-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--presentation-language", default="zh-CN")
    args = parser.parse_args()

    analysis = read_json(Path(args.analysis_file))
    extraction = read_json(Path(args.extraction_file))

    presentation_language = args.presentation_language or extraction.get("manifest", {}).get("presentation_language") or "zh-CN"
    title = localize_title(analysis.get("title", extraction.get("document_title", "未命名课题")))
    scene = analysis.get("scene", extraction.get("scene", "graduation-defense"))
    research_problem = choose_section_text(extraction, analysis, "background", analysis.get("research_problem", ""))
    method_summary = choose_section_text(extraction, analysis, "method", analysis.get("method_summary", ""))
    results_summary = choose_section_text(extraction, analysis, "results", analysis.get("results_summary", ""))
    conclusion_summary = choose_section_text(extraction, analysis, "conclusion", analysis.get("conclusion_summary", ""))

    payload = {
        "schema_version": "0.1",
        "title": title,
        "source_title": analysis.get("title", title),
        "scene": scene,
        "language": presentation_language,
        "source_language": extraction.get("language", analysis.get("language", "auto")),
        "presentation_language": presentation_language,
        "primary_source": analysis.get("primary_source"),
        "review_required": analysis.get("review_required", True),
        "subtitle": "中文为主的汇报稿草案",
        "research_problem": localize_text(research_problem, prefix="本研究关注的问题是："),
        "method_summary": localize_text(method_summary, prefix="在研究设计上，"),
        "results_summary": localize_text(results_summary, prefix="主要结果显示，"),
        "conclusion_summary": localize_text(conclusion_summary, prefix="综合结论可以概括为："),
        "contributions": build_contributions(analysis),
        "limitations": localize_limitations(analysis.get("limitations", [])),
        "narrative_arc": [
            "先讲清为什么这个临床或科研问题值得做",
            "再说明现有识别或分层方法的关键缺口",
            "随后交代本研究如何设计、如何取证",
            "最后收束到最强结果、研究边界与答辩口径",
        ],
        "open_questions": [
            "哪一张图最能代表主论文的核心证据？",
            "哪些背景内容应保留在附录而不是正文？",
            "答辩时需要主动说明的局限性是什么？",
        ],
        "risk_flags": [
            "所有核心结论必须优先回到主论文，不让附件文献替代主结论。",
            "若原文只是相关性研究，汇报中不要扩展成因果性或疗效性结论。",
        ],
        "supporting_context": [
            "附件文献的作用是补充背景、机制与旁证，不承担主结论表达。",
        ],
        "slide_claims": build_slide_claims(analysis),
        "evidence_map": analysis.get("evidence_map", {}),
    }
    write_json(Path(args.output_file), payload)


if __name__ == "__main__":
    main()
