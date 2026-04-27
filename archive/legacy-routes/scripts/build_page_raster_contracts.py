from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from common_io import read_json, write_json


PAGE_ROLE_ORDER = [
    "agenda",
    "background-text",
    "gap-problem",
    "goal-innovation",
    "overall-design",
    "route-board",
    "module-section",
    "study-design-board",
    "evidence-results",
    "stage-conclusion",
    "evidence-chain-board",
    "mechanism-board",
    "discussion",
    "conclusion",
    "outlook",
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def infer_role(index: int, slide: dict[str, Any]) -> str:
    title = normalize(slide.get("title", ""))
    if index == 1:
        return "cover"
    if index == 2:
        return "agenda"
    if "技术路线" in title:
        return "route-board"
    if "整体证据链整合" in title:
        return "evidence-chain-board"
    if "机制模型归纳" in title:
        return "mechanism-board"
    if re.match(r"研究内容[一二三四五六七八九十].*设计与对象", title):
        return "study-design-board"
    if re.match(r"研究内容[一二三四五六七八九十].*阶段结论", title):
        return "stage-conclusion"
    if re.match(r"研究内容[一二三四五六七八九十]\b", title):
        return "module-section"
    if re.match(r"研究内容[一二三四五六七八九十].*(观察指标与证据|核心结果)", title):
        return "evidence-results"
    if "研究背景" in title:
        return "background-text"
    if "问题提出与研究缺口" in title:
        return "gap-problem"
    if any(keyword in title for keyword in ["研究目标", "核心科学问题", "创新点"]):
        return "goal-innovation"
    if any(keyword in title for keyword in ["整体研究设计", "论文总体结构"]):
        return "overall-design"
    if "讨论" in title or "价值" in title or "局限" in title:
        return "discussion"
    if "结论" in title:
        return "conclusion"
    if "展望" in title:
        return "outlook"
    return "background-text"


TITLE_MAP = {
    "汇报提纲": "Outline",
    "研究背景": "Research Background",
    "问题提出与研究缺口": "Problem Statement and Research Gap",
    "研究目标": "Research Goals",
    "核心科学问题": "Key Scientific Questions",
    "论文创新点": "Main Innovations",
    "整体研究设计": "Overall Study Design",
    "技术路线": "Technical Route",
    "论文总体结构": "Thesis Structure",
    "整体证据链整合": "Integrated Evidence Chain",
    "机制模型归纳": "Mechanism Model Summary",
    "论文讨论一：结果如何解释": "Discussion I · Interpreting the Findings",
    "论文讨论二：价值何在": "Discussion II · Academic and Clinical Value",
    "论文创新点再提炼": "Innovation Highlights Revisited",
    "论文学术与应用价值": "Academic and Translational Value",
    "研究局限性": "Limitations",
    "总体结论一": "General Conclusions I",
    "总体结论二": "General Conclusions II",
    "研究展望": "Future Outlook",
}


def english_title_for_slide(index: int, role: str, slide: dict[str, Any]) -> str:
    title = slide.get("title", "")
    if title in TITLE_MAP:
        return TITLE_MAP[title]
    if role == "agenda":
        return "Outline"
    if role == "module-section":
        title_n = normalize(title)
        if "临床" in title_n:
            return "Module I · Clinical Efficacy and Safety Evaluation"
        if "免疫炎症" in title_n or "差异蛋白" in title_n:
            return "Module II · Immune Inflammation and Differential Proteins"
        if "动物模型" in title_n:
            return "Module III · Animal Model Mechanism Validation"
        if "细胞" in title_n:
            return "Module IV · Cellular Protection and Molecular Validation"
        return f"Module {index - 10}"
    if role == "study-design-board":
        return "Design and Subjects"
    if role == "evidence-results":
        if "观察指标与证据" in title:
            return "Observed Endpoints and Evidence"
        return "Key Findings"
    if role == "stage-conclusion":
        return "Stage Conclusion"
    if role == "background-text":
        return "Research Background"
    if role == "gap-problem":
        return "Problem Statement and Research Gap"
    if role == "goal-innovation":
        if "科学问题" in title:
            return "Key Scientific Questions"
        if "创新点" in title:
            return "Main Innovations"
        return "Research Goals"
    if role == "overall-design":
        return "Overall Study Design"
    if role == "route-board":
        return "Technical Route"
    if role == "evidence-chain-board":
        return "Integrated Evidence Chain"
    if role == "mechanism-board":
        return "Mechanism Model Summary"
    if role == "discussion":
        return "Discussion"
    if role == "conclusion":
        return "General Conclusions"
    if role == "outlook":
        return "Future Outlook"
    return title or f"Slide {index:02d}"


def content_layout(role: str) -> dict[str, Any]:
    mapping = {
        "agenda": {"variant": "agenda-list", "slots": ["title_band", "left_anchor", "outline_list", "logo_zone"]},
        "background-text": {"variant": "text-plus-supporting-figure", "slots": ["title_band", "left_text", "right_visual", "footer_band"]},
        "gap-problem": {"variant": "problem-callout", "slots": ["title_band", "left_problem", "right_gap_box", "footer_band"]},
        "goal-innovation": {"variant": "goal-card-grid", "slots": ["title_band", "top_summary", "three_cards", "footer_band"]},
        "overall-design": {"variant": "overview-board", "slots": ["title_band", "summary_strip", "central_board", "footer_band"]},
        "route-board": {"variant": "dense-route-board", "slots": ["title_band", "left_rail", "center_board", "right_rail", "output_band", "footer_band"]},
        "module-section": {"variant": "section-highlight", "slots": ["title_band", "module_badge", "summary_block", "key_chips", "footer_band"]},
        "study-design-board": {"variant": "stacked-design-board", "slots": ["title_band", "summary_strip", "vertical_design_cards", "footer_band"]},
        "evidence-results": {"variant": "evidence-led-results", "slots": ["title_band", "main_findings", "support_cards", "optional_figure_slot", "footer_band"]},
        "stage-conclusion": {"variant": "conclusion-card", "slots": ["title_band", "two_claim_blocks", "footer_band"]},
        "evidence-chain-board": {"variant": "radial-evidence-board", "slots": ["title_band", "center_hub", "support_quadrants", "footer_band"]},
        "mechanism-board": {"variant": "mechanism-summary-board", "slots": ["title_band", "three_panel_flow", "bridge_callout", "footer_band"]},
        "discussion": {"variant": "discussion-two-block", "slots": ["title_band", "left_argument", "right_implication", "footer_band"]},
        "conclusion": {"variant": "highlight-conclusion", "slots": ["title_band", "main_claims", "supportive_chips", "footer_band"]},
        "outlook": {"variant": "future-directions", "slots": ["title_band", "three_future_paths", "footer_band"]},
    }
    return mapping[role]


def reference_roles(role: str) -> list[str]:
    mapping = {
        "agenda": ["agenda"],
        "background-text": ["background-text", "split-text-figure"],
        "gap-problem": ["background-text", "split-text-figure"],
        "goal-innovation": ["split-text-figure", "three-part-cards"],
        "overall-design": ["overall-design", "split-text-figure"],
        "route-board": ["route-board", "split-text-figure"],
        "module-section": ["conclusion-highlight"],
        "study-design-board": ["split-text-figure", "three-part-cards"],
        "evidence-results": ["split-text-figure", "content-card-grid"],
        "stage-conclusion": ["conclusion-highlight"],
        "evidence-chain-board": ["route-board", "content-card-grid"],
        "mechanism-board": ["route-board", "content-card-grid"],
        "discussion": ["conclusion-highlight", "split-text-figure"],
        "conclusion": ["conclusion-highlight"],
        "outlook": ["three-part-cards", "conclusion-highlight"],
    }
    return mapping.get(role, ["split-text-figure"])


def visual_blocks(role: str, slide: dict[str, Any]) -> list[dict[str, Any]]:
    base = {
        "agenda": ["numbered-outline", "logo-anchor"],
        "background-text": ["soft-academic-visual", "one-support-panel"],
        "gap-problem": ["gap-box", "structured-callout"],
        "goal-innovation": ["goal-cards", "small-icons"],
        "overall-design": ["overview-board", "support-badges"],
        "route-board": ["dense-route-board", "center-hub", "ordered-connectors"],
        "module-section": ["section-chip", "module-tag"],
        "study-design-board": ["vertical-design-cards", "number-rail", "clean-connectors"],
        "evidence-results": ["result-cards", "optional-source-figure"],
        "stage-conclusion": ["claim-boxes", "supportive-mini-tags"],
        "evidence-chain-board": ["radial-evidence-board", "central-claim"],
        "mechanism-board": ["three-panel-mechanism", "ordered-bridge"],
        "discussion": ["argument-box", "implication-box"],
        "conclusion": ["highlight-chips", "summary-panel"],
        "outlook": ["future-direction-cards", "light-flow-markers"],
    }
    return [{"type": item} for item in base[role]]


def block_from_points(slot: str, points: list[str], instruction: str, max_words: int) -> dict[str, Any]:
    return {
        "slot": slot,
        "source_points_zh": [item for item in points if item],
        "rewrite_instruction": instruction,
        "max_words": max_words,
    }


def content_blocks(role: str, slide: dict[str, Any]) -> list[dict[str, Any]]:
    bullets = slide.get("bullets", [])
    takeaway = slide.get("takeaway", "")
    if role in {"background-text", "gap-problem", "discussion", "conclusion", "outlook"}:
        return [
            block_from_points(
                "main_body",
                bullets[:3],
                "Rewrite the source points as concise academic English bullets. Preserve order and meaning. Do not add new claims.",
                55,
            ),
            block_from_points(
                "support_callout",
                [takeaway] if takeaway else bullets[3:4],
                "Condense this into one short English takeaway sentence.",
                18,
            ),
        ]
    if role == "agenda":
        return [
            block_from_points(
                "outline_list",
                bullets[:4],
                "Rewrite as a clean English agenda with 4 short items.",
                24,
            )
        ]
    if role in {"goal-innovation", "overall-design", "stage-conclusion"}:
        return [
            block_from_points(
                "top_summary",
                bullets[:1],
                "Rewrite as a short English summary line.",
                16,
            ),
            block_from_points(
                "main_cards",
                bullets[1:4] or bullets[:3],
                "Rewrite as 2-3 compact English card statements, one idea per card.",
                36,
            ),
        ]
    if role == "module-section":
        return [
            block_from_points(
                "module_scope",
                bullets[:3],
                "Rewrite as a short English section intro with three compact scope points.",
                36,
            )
        ]
    if role == "route-board":
        diagram = slide.get("diagram_v5", {})
        cards = diagram.get("cards", [])
        outputs = diagram.get("outputs", [])
        blocks = [
            {
                "slot": "center_hub",
                "source_points_zh": [diagram.get("center", {}).get("body", "")],
                "rewrite_instruction": "Rewrite as one short English center claim.",
                "max_words": 20,
            }
        ]
        for idx, card in enumerate(cards[:4], start=1):
            blocks.append(
                {
                    "slot": f"route_card_{idx}",
                    "source_points_zh": [card.get("title", ""), *(card.get("body", []) or [])],
                    "rewrite_instruction": "Rewrite into one short English card title and one supporting short line.",
                    "max_words": 14,
                }
            )
        blocks.append(
            {
                "slot": "output_band",
                "source_points_zh": outputs[:3],
                "rewrite_instruction": "Rewrite as three short English output labels.",
                "max_words": 12,
            }
        )
        return blocks
    if role == "study-design-board":
        return [
            block_from_points(
                "summary_strip",
                bullets[:1],
                "Rewrite as one short English summary strip.",
                14,
            ),
            block_from_points(
                "design_cards",
                bullets[:4],
                "Rewrite as four stacked English design cards with one short statement per card.",
                34,
            ),
        ]
    if role == "evidence-results":
        return [
            block_from_points(
                "result_findings",
                bullets[:3],
                "Rewrite as key findings in concise English. Each finding should be short and declarative.",
                48,
            ),
            block_from_points(
                "evidence_takeaway",
                [takeaway] if takeaway else bullets[3:4],
                "Rewrite as one short English finding summary.",
                14,
            ),
        ]
    if role == "evidence-chain-board":
        return [
            block_from_points(
                "central_claim",
                [takeaway] if takeaway else bullets[:1],
                "Rewrite as one short English central conclusion.",
                16,
            ),
            block_from_points(
                "support_quadrants",
                bullets[:4],
                "Rewrite as four short English support modules around the center.",
                28,
            ),
        ]
    if role == "mechanism-board":
        return [
            block_from_points(
                "mechanism_panels",
                bullets[:3],
                "Rewrite as three short English panel labels for trigger, dysregulation, and rescue.",
                24,
            ),
            block_from_points(
                "bridge_callout",
                [takeaway] if takeaway else bullets[0:1],
                "Rewrite as one short English bridge callout.",
                16,
            ),
        ]
    return [
        block_from_points(
            "main_body",
            bullets[:3],
            "Rewrite as concise academic English bullets without adding new claims.",
            40,
        )
    ]


def figure_source_refs(role: str, slide: dict[str, Any], figure_ref_dir: Path | None) -> list[dict[str, Any]]:
    if not figure_ref_dir or role not in {"route-board", "study-design-board", "evidence-results", "evidence-chain-board", "mechanism-board"}:
        return []
    items: list[dict[str, Any]] = []
    stem_parts = [slide.get("id", ""), slide.get("title", "")]
    for path in sorted(figure_ref_dir.rglob("*")):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".svg"}:
            continue
        key = normalize(path.stem)
        if any(part and normalize(part) in key for part in stem_parts):
            items.append(
                {
                    "file": str(path.resolve()),
                    "allowed_slots": ["optional_figure_slot", "support_figure", "mechanism_reference"],
                    "treatment": "crop-soften-frame",
                }
            )
    return items[:2]


def review_checks(role: str) -> list[str]:
    checks = [
        "Respect the Tongji-blue title band and top-right logo safe zone.",
        "Keep all visible text inside the template body safe zone.",
        "Do not let arrows or labels float without clear alignment.",
        "Keep layout ordered and committee-friendly rather than poster-like chaos.",
    ]
    if role in {"route-board", "study-design-board", "evidence-chain-board", "mechanism-board"}:
        checks.append("The core structural reading path must be obvious within 2 seconds.")
    return checks


def build_recipe(index: int, slide: dict[str, Any], profile: dict[str, Any], figure_ref_dir: Path | None) -> dict[str, Any]:
    role = infer_role(index, slide)
    if role == "cover":
        return {}
    layout = content_layout(role)
    return {
        "slide_id": slide.get("id", f"slide-{index:02d}"),
        "slide_number": index,
        "page_role": role,
        "english_title": english_title_for_slide(index, role, slide),
        "source_title_zh": slide.get("title", ""),
        "core_claim": slide.get("takeaway") or (slide.get("bullets") or [""])[0],
        "content_blocks": content_blocks(role, slide),
        "visual_blocks": visual_blocks(role, slide),
        "layout_slots": layout,
        "safe_zone_rules": profile["safe_zones"],
        "template_constraints": {
            "template_id": profile["template_id"],
            "fonts": profile["theme"]["fonts"],
            "primary_accent": profile["theme"]["colors"].get("accent1", "2E75B5"),
            "secondary_accents": [
                profile["theme"]["colors"].get("accent2", "77ACDC"),
                profile["theme"]["colors"].get("accent3", "A4C8E8"),
                profile["theme"]["colors"].get("accent6", "B56E2E"),
            ],
            "style_mode": profile["chrome_rules"]["style_mode"],
        },
        "template_reference_roles": reference_roles(role),
        "forbidden_patterns": [
            "No Chinese text.",
            "Do not alter the title band or logo area.",
            "No random arrows or unstructured connectors.",
            "No unsupported numeric charts or fabricated plots.",
            "Do not turn local figure references into a full-page collage.",
        ],
        "figure_source_refs": figure_source_refs(role, slide, figure_ref_dir),
        "review_checks": review_checks(role),
        "word_budget_total": sum(block["max_words"] for block in content_blocks(role, slide)),
    }


def update_slide_spec(slide: dict[str, Any], recipe_file: Path, role: str) -> dict[str, Any]:
    updated = dict(slide)
    if slide.get("id") != "slide-01":
        updated["visual_route"] = "gemini-page-raster"
        updated["page_role"] = role
        updated["recipe_file"] = str(recipe_file.resolve())
        updated["raster_asset"] = None
        updated["review_state"] = {"status": "pending", "attempts": 0}
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Build strict per-page raster recipes so Gemini generates controllable Tongji-blue review pages.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--template-profile-file", required=True)
    parser.add_argument("--recipes-dir", required=True)
    parser.add_argument("--output-manifest-file", required=True)
    parser.add_argument("--output-spec-file", required=True)
    parser.add_argument("--figure-ref-dir")
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    profile = read_json(Path(args.template_profile_file))
    recipes_dir = Path(args.recipes_dir).resolve()
    figure_ref_dir = Path(args.figure_ref_dir).resolve() if args.figure_ref_dir else None

    manifest: list[dict[str, Any]] = []
    updated_slides: list[dict[str, Any]] = []
    for index, slide in enumerate(spec.get("slides", []), start=1):
        role = infer_role(index, slide)
        if role == "cover":
            updated_slides.append(dict(slide))
            manifest.append(
                {
                    "slide_id": slide.get("id", f"slide-{index:02d}"),
                    "slide_number": index,
                    "page_role": "cover",
                    "english_title": slide.get("title", ""),
                }
            )
            continue
        recipe = build_recipe(index, slide, profile, figure_ref_dir)
        recipe_file = recipes_dir / f"{slide.get('id', f'slide-{index:02d}')}.json"
        write_json(recipe_file, recipe)
        updated_slides.append(update_slide_spec(slide, recipe_file, role))
        manifest.append(
            {
                "slide_id": recipe["slide_id"],
                "slide_number": index,
                "page_role": role,
                "english_title": recipe["english_title"],
                "recipe_file": str(recipe_file.resolve()),
                "template_reference_roles": recipe["template_reference_roles"],
            }
        )

    updated_spec = dict(spec)
    updated_spec["template"] = "tongji-blue"
    updated_spec["slides"] = updated_slides
    updated_spec["page_raster_v1"] = {
        "strategy": "strict-page-contracts",
        "template_profile_file": str(Path(args.template_profile_file).resolve()),
        "manifest_file": str(Path(args.output_manifest_file).resolve()),
        "recipes_dir": str(recipes_dir),
        "allowed_page_roles": PAGE_ROLE_ORDER,
    }
    write_json(Path(args.output_manifest_file).resolve(), manifest)
    write_json(Path(args.output_spec_file).resolve(), updated_spec)


if __name__ == "__main__":
    main()
