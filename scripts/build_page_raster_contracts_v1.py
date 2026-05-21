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

MODULE_TITLE_BY_SLIDE = {
    11: "Module I - Clinical Efficacy and Safety Evaluation",
    16: "Module II - Immune Inflammation and Differential Proteins",
    21: "Module III - Animal Model Mechanism Validation",
    26: "Module IV - Cellular Protection and Molecular Validation",
}

ENGLISH_TITLE_BY_SLIDE = {
    2: "Outline",
    3: "Research Background",
    4: "Problem Statement and Research Gap",
    5: "Research Goals",
    6: "Key Scientific Questions",
    7: "Main Innovations",
    8: "Overall Study Design",
    9: "Technical Route",
    10: "Thesis Structure",
    12: "Design and Subjects",
    13: "Key Findings I",
    14: "Key Findings II",
    15: "Stage Conclusion",
    17: "Design and Subjects",
    18: "Key Findings I",
    19: "Key Findings II",
    20: "Stage Conclusion",
    22: "Design and Subjects",
    23: "Key Findings I",
    24: "Key Findings II",
    25: "Stage Conclusion",
    27: "Design and Subjects",
    28: "Key Findings I",
    29: "Key Findings II",
    30: "Stage Conclusion",
    31: "Integrated Evidence Chain",
    32: "Mechanism Model Summary",
    33: "Discussion and Value",
    34: "Limitations and Overall Conclusions",
    35: "Future Outlook",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def infer_role(index: int, slide: dict[str, Any]) -> str:
    title = normalize(slide.get("title", ""))
    if index == 1:
        return "cover"
    if index == 2:
        return "agenda"
    if index == 3:
        return "background-text"
    if index == 4:
        return "gap-problem"
    if index in {5, 6, 7}:
        return "goal-innovation"
    if index in {8, 10}:
        return "overall-design"
    if index == 9:
        return "route-board"
    if index in {11, 16, 21, 26}:
        return "module-section"
    if index in {12, 17, 22, 27}:
        return "study-design-board"
    if index in {13, 14, 18, 19, 23, 24, 28, 29}:
        return "evidence-results"
    if index in {15, 20, 25, 30}:
        return "stage-conclusion"
    if index == 31:
        return "evidence-chain-board"
    if index == 32:
        return "mechanism-board"
    if index == 33:
        return "discussion"
    if index == 34:
        return "conclusion"
    if index == 35:
        return "outlook"
    if "技术路线" in title:
        return "route-board"
    if "证据链" in title:
        return "evidence-chain-board"
    if "机制模型" in title or "机制归纳" in title:
        return "mechanism-board"
    if "设计与对象" in title:
        return "study-design-board"
    if "阶段结论" in title:
        return "stage-conclusion"
    if "讨论" in title or "价值" in title or "局限" in title:
        return "discussion"
    if "结论" in title:
        return "conclusion"
    if "展望" in title:
        return "outlook"
    return "background-text"


def english_title_for_slide(index: int, role: str, slide: dict[str, Any]) -> str:
    if index in MODULE_TITLE_BY_SLIDE:
        return MODULE_TITLE_BY_SLIDE[index]
    if index in ENGLISH_TITLE_BY_SLIDE:
        return ENGLISH_TITLE_BY_SLIDE[index]
    if role == "evidence-results":
        return "Key Findings"
    if role == "study-design-board":
        return "Design and Subjects"
    if role == "stage-conclusion":
        return "Stage Conclusion"
    if role == "module-section":
        return "Module Overview"
    return slide.get("title", "") or f"Slide {index:02d}"


def _merged_bullets(slides: list[dict[str, Any]], max_items: int = 4) -> list[str]:
    collected: list[str] = []
    for slide in slides:
        for bullet in slide.get("bullets", []):
            text = str(bullet).strip()
            if text and text not in collected:
                collected.append(text)
        takeaway = str(slide.get("takeaway", "")).strip()
        if takeaway and takeaway not in collected:
            collected.append(takeaway)
    return collected[:max_items] or ["待结合原始讲稿进一步补强。"]


def _merged_notes(slides: list[dict[str, Any]], fallback: str) -> str:
    parts: list[str] = []
    for slide in slides:
        note = str(slide.get("notes", "")).strip()
        if note and note not in parts:
            parts.append(note)
    return " ".join(parts) if parts else fallback


def compact_to_35_slides(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(slides) <= 35:
        return slides

    fixed = [dict(slide) for slide in slides[:32]]
    tail = [dict(slide) for slide in slides[32:]]

    discussion_sources = tail[:3]
    conclusion_sources = tail[3:6] if len(tail) >= 6 else tail[3:]
    outlook_sources = tail[6:] if len(tail) > 6 else tail[-1:]

    fixed.append(
        {
            "id": "slide-33",
            "layout": "bullets",
            "title": "讨论与价值",
            "bullets": _merged_bullets(discussion_sources),
            "notes": _merged_notes(discussion_sources, "把结果解释、创新意义和应用价值收成一页。"),
        }
    )
    fixed.append(
        {
            "id": "slide-34",
            "layout": "bullets",
            "title": "局限性与总体结论",
            "bullets": _merged_bullets(conclusion_sources),
            "notes": _merged_notes(conclusion_sources, "先交代边界，再回到总体结论。"),
        }
    )
    fixed.append(
        {
            "id": "slide-35",
            "layout": "bullets",
            "title": "研究展望",
            "bullets": _merged_bullets(outlook_sources),
            "notes": _merged_notes(outlook_sources, "最后一页以前瞻性和整体收束结束。"),
        }
    )
    return fixed


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


def layout_freedom(role: str) -> list[str]:
    mapping = {
        "agenda": [
            "Use a restrained outline composition with strong hierarchy.",
            "You may choose a clean vertical list or a lightly modular summary board.",
        ],
        "background-text": [
            "Keep the text-first reading order, but choose a refined split or layered composition freely.",
        ],
        "gap-problem": [
            "You may choose a split comparison board, a structured problem panel, or a staged gap narrative.",
        ],
        "goal-innovation": [
            "Use a committee-facing summary board with richer cards, not a slogan page.",
        ],
        "overall-design": [
            "You may use a hub-and-spoke, staged pipeline, layered board, or bridged module composition.",
        ],
        "route-board": [
            "You must include all required workstreams and synthesis logic, but you may choose a braided, radial, tiered, orbital, or asymmetric board composition.",
            "Favor sophisticated thesis-route-map grammar over rigid box chaining.",
        ],
        "module-section": [
            "Use a calm section-divider style with one dominant title zone and controlled supporting tags.",
        ],
        "study-design-board": [
            "You must preserve subject, grouping, intervention, and evaluation order, but may choose stepped cards, a ladder board, tiered panels, or a structured clinical flow layout.",
        ],
        "evidence-results": [
            "Keep one main result hierarchy and supporting evidence modules, but composition may vary between split board and evidence grid.",
        ],
        "stage-conclusion": [
            "Use a concise highlight composition with strong claims and compact support.",
        ],
        "evidence-chain-board": [
            "You must preserve the integrated evidence logic, but may use concentric, orbital, clustered, or radial synthesis layouts.",
        ],
        "mechanism-board": [
            "You must preserve trigger-to-dysregulation-to-rescue logic, but may choose a layered graphical-summary composition with nested callouts and secondary loops.",
        ],
        "discussion": [
            "Keep the argumentative structure clear, but allow a more editorial discussion layout.",
        ],
        "conclusion": [
            "Use a high-clarity summary composition with enough density to survive later Chinese compression.",
        ],
        "outlook": [
            "Use a forward-looking structured board rather than a sparse three-icon page.",
        ],
    }
    return mapping.get(role, ["Keep the page ordered and presentation-ready while allowing tasteful compositional freedom."])


def must_include_elements(role: str) -> list[str]:
    mapping = {
        "route-board": [
            "one dominant scientific question or route theme",
            "four major workstreams or evidence streams",
            "clear cross-stream linkage or feedback logic",
            "a final synthesis/output zone",
        ],
        "study-design-board": [
            "study subjects or cohort definition",
            "grouping strategy",
            "intervention or procedure path",
            "evaluation endpoints or readouts",
        ],
        "evidence-chain-board": [
            "one integrated central claim",
            "multiple surrounding evidence domains",
            "visible aggregation or convergence cues",
            "a hierarchy between core and peripheral evidence",
        ],
        "mechanism-board": [
            "disease or trigger layer",
            "core dysregulation module",
            "injury or inflammatory consequence layer",
            "intervention/rescue layer",
        ],
    }
    return mapping.get(role, [])


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


def visual_blocks(role: str) -> list[dict[str, Any]]:
    base = {
        "agenda": ["numbered-outline", "logo-anchor"],
        "background-text": ["soft-academic-visual", "one-support-panel"],
        "gap-problem": ["gap-box", "structured-callout"],
        "goal-innovation": ["goal-cards", "small-icons"],
        "overall-design": ["overview-board", "support-badges"],
        "route-board": [
            "dense-route-board",
            "center-question-hub",
            "four-workstream-panels",
            "cross-connectors",
            "side-pillars",
            "output-ribbon",
            "micro-evidence-tags",
        ],
        "module-section": ["section-chip", "module-tag"],
        "study-design-board": [
            "vertical-design-cards",
            "number-rail",
            "clean-connectors",
            "summary-strip",
            "evaluation-badges",
        ],
        "evidence-results": ["result-cards", "optional-source-figure"],
        "stage-conclusion": ["claim-boxes", "supportive-mini-tags"],
        "evidence-chain-board": [
            "radial-evidence-board",
            "central-claim",
            "domain-rings",
            "peripheral-support-labels",
            "aggregation-connectors",
        ],
        "mechanism-board": [
            "trigger-layer",
            "autophagy-dysregulation-core",
            "inflammasome-axis",
            "cell-injury-consequences",
            "intervention-rescue-layer",
            "supportive-callout-bubbles",
            "feedback-arrows",
        ],
        "discussion": ["argument-box", "implication-box"],
        "conclusion": ["highlight-chips", "summary-panel"],
        "outlook": ["future-direction-cards", "light-flow-markers"],
    }
    return [{"type": item} for item in base[role]]


def block_from_points(slot: str, points: list[str], instruction: str, base_words: int) -> dict[str, Any]:
    min_words = max(12, base_words * 2)
    max_words = max(min_words + 8, int(base_words * 2.6))
    return {
        "slot": slot,
        "source_points_zh": [item for item in points if item],
        "rewrite_instruction": instruction,
        "base_words": base_words,
        "min_words": min_words,
        "max_words": max_words,
    }


def complexity_target(role: str) -> dict[str, Any]:
    mapping = {
        "agenda": {
            "visual_intensity": "medium",
            "min_structural_groups": 2,
            "min_connectors": 0,
            "min_layers": 2,
            "notes": "Keep it polished but restrained. The hierarchy must be stronger than a plain list."
        },
        "background-text": {
            "visual_intensity": "medium",
            "min_structural_groups": 3,
            "min_connectors": 0,
            "min_layers": 3,
            "notes": "The page should feel fuller than a simple title-plus-bullets slide."
        },
        "gap-problem": {
            "visual_intensity": "medium-high",
            "min_structural_groups": 4,
            "min_connectors": 1,
            "min_layers": 3,
            "notes": "Use grouped callouts and contrast blocks rather than a sparse problem statement."
        },
        "goal-innovation": {
            "visual_intensity": "high",
            "min_structural_groups": 4,
            "min_connectors": 0,
            "min_layers": 3,
            "notes": "Innovation pages must look decisive and full, with dense information cards rather than airy placeholders."
        },
        "overall-design": {
            "visual_intensity": "high",
            "min_structural_groups": 5,
            "min_connectors": 4,
            "min_layers": 4,
            "notes": "Prefer a full board-like overview instead of a light summary slide."
        },
        "route-board": {
            "visual_intensity": "very-high",
            "min_structural_groups": 7,
            "min_connectors": 10,
            "min_layers": 4,
            "notes": "Must read like a dense technical route board with central problem, four major workstreams, and an output band."
        },
        "module-section": {
            "visual_intensity": "medium-high",
            "min_structural_groups": 4,
            "min_connectors": 0,
            "min_layers": 3,
            "notes": "Section pages should still carry dense section framing, not just one title and one paragraph."
        },
        "study-design-board": {
            "visual_intensity": "high",
            "min_structural_groups": 6,
            "min_connectors": 4,
            "min_layers": 4,
            "notes": "Design boards need a structured rail, four cards, and a visible study flow."
        },
        "evidence-results": {
            "visual_intensity": "high",
            "min_structural_groups": 5,
            "min_connectors": 2,
            "min_layers": 4,
            "notes": "Result pages should feel full and evidence-led, not like a loose text summary."
        },
        "stage-conclusion": {
            "visual_intensity": "medium-high",
            "min_structural_groups": 4,
            "min_connectors": 0,
            "min_layers": 3,
            "notes": "Stage conclusions must still show a synthesized board feeling."
        },
        "evidence-chain-board": {
            "visual_intensity": "very-high",
            "min_structural_groups": 8,
            "min_connectors": 10,
            "min_layers": 4,
            "notes": "Must show a center claim plus four evidence domains and peripheral support labels."
        },
        "mechanism-board": {
            "visual_intensity": "extreme",
            "min_structural_groups": 9,
            "min_connectors": 12,
            "min_layers": 5,
            "notes": "Mechanism pages must feel like a dense journal graphical summary, not a simple three-panel strip."
        },
        "discussion": {
            "visual_intensity": "high",
            "min_structural_groups": 4,
            "min_connectors": 1,
            "min_layers": 3,
            "notes": "Discussion pages should use argument blocks and implication structure, not loose text."
        },
        "conclusion": {
            "visual_intensity": "high",
            "min_structural_groups": 4,
            "min_connectors": 0,
            "min_layers": 3,
            "notes": "Conclusion pages should look authoritative and full, with reinforced hierarchy."
        },
        "outlook": {
            "visual_intensity": "medium-high",
            "min_structural_groups": 4,
            "min_connectors": 2,
            "min_layers": 3,
            "notes": "Outlook pages should still look structured and forward-looking, not sparse."
        },
    }
    return mapping[role]


def legibility_policy(role: str) -> dict[str, Any]:
    """Keep density high without asking the image model to draw unreadable microtext."""
    complex_roles = {"route-board", "study-design-board", "evidence-chain-board", "mechanism-board"}
    return {
        "primary_goal": "high-density Chinese pages with crisp, reviewable text",
        "density_strategy": [
            "preserve density with structural groups, hierarchy bands, chips, connectors, and visual layers",
            "split long Chinese statements into short readable labels and stacked cards",
            "use diagrams and module geometry to carry complexity instead of shrinking prose",
        ],
        "text_rendering_preference": "deterministic-local-text-layer-when-small-text-is-needed",
        "do_not_solve_by": [
            "simply increasing all font sizes",
            "packing dense Chinese microtext into one small image-model text area",
            "letting labels blur into decorative texture",
        ],
        "minimum_visual_density": "very-high" if role in complex_roles else "medium-high",
        "small_text_rule": "small labels are allowed only when they remain crisp after PDF export; otherwise split or promote them into chips",
    }


def content_blocks(index: int, role: str, slide: dict[str, Any]) -> list[dict[str, Any]]:
    bullets = slide.get("bullets", [])
    takeaway = slide.get("takeaway", "")
    if role in {"background-text", "gap-problem", "discussion", "conclusion", "outlook"}:
        return [
            block_from_points(
                "main_body",
                bullets[:3],
                "Rewrite the source points as fuller academic English bullets. Preserve order and meaning. Expand each idea into a denser committee-facing line without inventing claims.",
                55,
            ),
            block_from_points(
                "support_callout",
                [takeaway] if takeaway else bullets[3:4],
                "Rewrite this as one fuller English takeaway sentence that still stays concise.",
                18,
            ),
        ]
    if role == "agenda":
        return [
            block_from_points(
                "outline_list",
                bullets[:4],
                "Rewrite as a clean English agenda with four fuller items, each long enough to feel substantial but still one line.",
                24,
            )
        ]
    if role in {"goal-innovation", "overall-design", "stage-conclusion"}:
        return [
            block_from_points(
                "top_summary",
                bullets[:1],
                "Rewrite as one fuller English summary line with stronger academic tone.",
                16,
            ),
            block_from_points(
                "main_cards",
                bullets[1:4] or bullets[:3],
                "Rewrite as two or three fuller English card statements, one idea per card, with stronger information density.",
                36,
            ),
        ]
    if role == "module-section":
        return [
            block_from_points(
                "module_scope",
                bullets[:3],
                "Rewrite as a fuller English section intro with three denser scope points.",
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
                "base_words": 20,
                "min_words": 40,
                "max_words": 56,
            }
        ]
        for card_index, card in enumerate(cards[:4], start=1):
            blocks.append(
                {
                    "slot": f"route_card_{card_index}",
                    "source_points_zh": [card.get("title", ""), *(card.get("body", []) or [])],
                    "rewrite_instruction": "Rewrite into one English card title and one fuller supporting line with denser content.",
                    "base_words": 14,
                    "min_words": 28,
                    "max_words": 40,
                }
            )
        blocks.append(
            {
                "slot": "output_band",
                "source_points_zh": outputs[:3],
                "rewrite_instruction": "Rewrite as three fuller English output labels that still remain banner-friendly.",
                "base_words": 12,
                "min_words": 24,
                "max_words": 32,
            }
        )
        return blocks
    if role == "study-design-board":
        return [
            block_from_points(
                "summary_strip",
                bullets[:1],
                "Rewrite as one fuller English summary strip.",
                14,
            ),
            block_from_points(
                "design_cards",
                bullets[:4],
                "Rewrite as four stacked English design cards with one fuller statement per card.",
                34,
            ),
        ]
    if role == "evidence-results":
        result_label = "Key Findings"
        if index in {13, 18, 23, 28}:
            result_label = "Primary Findings"
        return [
            block_from_points(
                "result_findings",
                [result_label, *bullets[:3]],
                "Rewrite as fuller English findings. Each finding should be committee-facing, denser, and still declarative.",
                48,
            ),
            block_from_points(
                "evidence_takeaway",
                [takeaway] if takeaway else bullets[3:4],
                "Rewrite as one fuller English finding summary.",
                14,
            ),
        ]
    if role == "evidence-chain-board":
        return [
            block_from_points(
                "central_claim",
                [takeaway] if takeaway else bullets[:1],
                "Rewrite as one fuller English central conclusion.",
                16,
            ),
            block_from_points(
                "support_quadrants",
                bullets[:4],
                "Rewrite as four fuller English support modules around the center.",
                28,
            ),
        ]
    if role == "mechanism-board":
        return [
            block_from_points(
                "mechanism_panels",
                bullets[:3],
                "Rewrite as three fuller English panel labels for trigger, dysregulation, and rescue, with more mechanistic specificity.",
                24,
            ),
            block_from_points(
                "bridge_callout",
                [takeaway] if takeaway else bullets[0:1],
                "Rewrite as one fuller English bridge callout.",
                16,
            ),
        ]
    return [
        block_from_points(
            "main_body",
            bullets[:3],
            "Rewrite as fuller academic English bullets without adding new claims.",
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
        "Respect the title band, top-right quiet zone, and footer band.",
        "Keep all visible text inside the template body safe zone.",
        "Do not let arrows or labels float without clear alignment.",
        "Keep layout ordered and committee-friendly rather than poster-like chaos.",
        "Chinese content should stay intentionally dense and complete, not hollow or overly abbreviated.",
        "Do not preserve density by making Chinese text tiny; preserve density with more structure, modules, chips, connectors, and visual layers.",
        "Small Chinese labels must remain crisp after PDF export; long text should be split into multiple readable cards.",
        "Do not show school names, school logos, watermark-like marks, or header branding of any kind.",
        "Do not leak internal schema labels, slot names, or development metadata.",
    ]
    if role in {"route-board", "study-design-board", "evidence-chain-board", "mechanism-board"}:
        checks.append("The core structural reading path must be obvious within two seconds.")
        checks.append("The page must hit a high-complexity board standard rather than a simple four-box layout.")
    return checks


def build_recipe(index: int, slide: dict[str, Any], profile: dict[str, Any], figure_ref_dir: Path | None) -> dict[str, Any]:
    role = infer_role(index, slide)
    if role == "cover":
        return {}
    blocks = content_blocks(index, role, slide)
    layout = content_layout(role)
    if role == "goal-innovation":
        main_cards = next((block for block in blocks if block["slot"] == "main_cards"), None)
        if main_cards and len(main_cards.get("source_points_zh", [])) <= 2:
            layout = {
                "variant": "goal-card-grid-2up",
                "slots": ["title_band", "top_summary", "two_cards", "footer_band"],
            }
    return {
        "slide_id": slide.get("id", f"slide-{index:02d}"),
        "slide_number": index,
        "page_role": role,
        "render_language": "zh-CN",
        "density_policy": "zh-primary-dense-readable",
        "legibility_policy": legibility_policy(role),
        "composition_policy": {
            "principle": "lock-content-not-composition",
            "summary": "Lock content hierarchy, safe zones, and forbidden patterns, but allow controlled compositional freedom.",
            "must_lock": [
                "content order",
                "page hierarchy",
                "template boundaries",
                "safe zones",
                "forbidden patterns",
                "complexity target",
            ],
            "must_not_lock": [
                "single rigid box layout",
                "one fixed connector path",
                "one mandatory module geometry",
                "one mandatory board skeleton",
            ],
        },
        "render_title": slide.get("title", ""),
        "legacy_english_title": english_title_for_slide(index, role, slide),
        "source_title_zh": slide.get("title", ""),
        "core_claim": slide.get("takeaway") or (slide.get("bullets") or [""])[0],
        "content_blocks": blocks,
        "visual_blocks": visual_blocks(role),
        "layout_slots": layout,
        "layout_freedom": layout_freedom(role),
        "must_include_elements": must_include_elements(role),
        "complexity_target": complexity_target(role),
        "brand_rules": {
            "name_zh": "",
            "name_en": "",
            "logo_overlay": "none",
            "logo_zone_behavior": "keep-blank-for-native-overlay",
        },
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
            "Do not alter the title band, top-right quiet zone, or footer band.",
            "Do not replace the main page language with English unless the user explicitly asks for English output.",
            "No random arrows or unstructured connectors.",
            "No unsupported numeric charts or fabricated plots.",
            "Do not turn local figure references into a full-page collage.",
            "Do not show any school name, school logo, or placeholder university branding.",
            "Do not print coordinates, thresholds, x/y/w/h values, or JSON-like metadata.",
            "Do not print slot names, schema labels, component ids, or internal route-map tokens.",
            "Do not render dense Chinese microtext or blurred tiny body copy.",
        ],
        "figure_source_refs": figure_source_refs(role, slide, figure_ref_dir),
        "review_checks": review_checks(role),
        "word_budget_total": sum(block["max_words"] for block in blocks),
    }


def update_slide_spec(slide: dict[str, Any], recipe_file: Path, role: str) -> dict[str, Any]:
    updated = dict(slide)
    if slide.get("id") != "slide-01":
        updated["visual_route"] = "image2-page-raster"
        updated["page_role"] = role
        updated["recipe_file"] = str(recipe_file.resolve())
        updated["raster_asset"] = None
        updated["review_state"] = {"status": "pending", "attempts": 0}
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Build strict per-page raster recipes so image2 generates controllable academic review pages.")
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

    source_slides = compact_to_35_slides(spec.get("slides", []))

    for index, slide in enumerate(source_slides, start=1):
        role = infer_role(index, slide)
        slide_id = slide.get("id", f"slide-{index:02d}")
        if role == "cover":
            updated_slides.append(dict(slide))
            manifest.append(
                {
                    "slide_id": slide_id,
                    "slide_number": index,
                    "page_role": "cover",
                    "render_title": slide.get("title", ""),
                }
            )
            continue

        recipe = build_recipe(index, slide, profile, figure_ref_dir)
        recipe_file = recipes_dir / f"{slide_id}.json"
        write_json(recipe_file, recipe)
        updated_slides.append(update_slide_spec(slide, recipe_file, role))
        manifest.append(
            {
                "slide_id": recipe["slide_id"],
                "slide_number": index,
                "page_role": role,
                "render_title": recipe["render_title"],
                "recipe_file": str(recipe_file.resolve()),
                "template_reference_roles": recipe["template_reference_roles"],
            }
        )

    updated_spec = dict(spec)
    updated_spec["template"] = "cdutcm-defense"
    updated_spec["slides"] = updated_slides
    updated_spec["page_raster_v1"] = {
        "strategy": "strict-page-contracts",
        "primary_full_page_backend": "image2",
        "supplemental_visual_backends": ["gemini", "image2"],
        "locked_page_count": 35,
        "template_profile_file": str(Path(args.template_profile_file).resolve()),
        "manifest_file": str(Path(args.output_manifest_file).resolve()),
        "recipes_dir": str(recipes_dir),
        "allowed_page_roles": PAGE_ROLE_ORDER,
    }

    write_json(Path(args.output_manifest_file).resolve(), manifest)
    write_json(Path(args.output_spec_file).resolve(), updated_spec)


if __name__ == "__main__":
    main()
