from __future__ import annotations

import argparse
import base64
import copy
import json
import mimetypes
import subprocess
import sys
from pathlib import Path
from typing import Any

from common_io import ensure_parent, read_json, write_json, write_text


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def inline_part(path: Path) -> dict[str, Any]:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime_type, "data": payload}}


def profile_reference_map(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    mapping: dict[str, list[dict[str, Any]]] = {}
    for item in profile.get("selected_references", []):
        mapping.setdefault(item["role"], []).append(item)
    return mapping


def selected_reference_images(recipe: dict[str, Any], profile: dict[str, Any]) -> list[Path]:
    mapping = profile_reference_map(profile)
    results: list[Path] = []
    for role in recipe.get("template_reference_roles", []):
        for item in mapping.get(role, []):
            path = Path(item["image_file"])
            if path.exists():
                results.append(path)
                break
    return results[:3]


def figure_reference_images(recipe: dict[str, Any]) -> list[Path]:
    images: list[Path] = []
    for item in recipe.get("figure_source_refs", []):
        path = Path(item["file"])
        if path.exists():
            images.append(path)
    return images[:2]


def describe_safe_zones(safe: dict[str, Any]) -> list[str]:
    return [
        "Keep the title inside the top-left header strip only.",
        "Keep the top-right corner quiet, clean, and free of logos, school names, or dense content.",
        "Keep all main content inside the central body canvas with generous margins.",
        "Keep footer elements inside the bottom footer strip only.",
        f"Respect an outer page margin of about {safe.get('outer_margin', 0.04) * 100:.0f}% of the page width.",
    ]


def humanize_slot(slot: str) -> str:
    mapping = {
        "title_band": "title area",
        "left_anchor": "left anchor area",
        "outline_list": "outline list",
        "left_text": "primary text column",
        "right_visual": "supporting visual zone",
        "left_problem": "problem statement zone",
        "right_gap_box": "research gap emphasis zone",
        "top_summary": "top summary zone",
        "three_cards": "main card group",
        "two_cards": "main card pair",
        "summary_strip": "summary strip",
        "central_board": "central structured board",
        "left_rail": "left workstream area",
        "center_board": "central board area",
        "right_rail": "right workstream area",
        "output_band": "final synthesis band",
        "vertical_design_cards": "design card sequence",
        "main_findings": "main findings zone",
        "support_cards": "support evidence modules",
        "optional_figure_slot": "supporting figure zone",
        "two_claim_blocks": "two claim blocks",
        "center_hub": "central claim zone",
        "support_quadrants": "supporting evidence domains",
        "three_panel_flow": "main mechanism flow region",
        "bridge_callout": "bridge conclusion strip",
        "left_argument": "left discussion column",
        "right_implication": "right implication column",
        "main_claims": "main conclusion zone",
        "supportive_chips": "supporting highlight tags",
        "three_future_paths": "future directions group",
        "footer_band": "footer zone",
    }
    return mapping.get(slot, slot.replace("_", " "))


def humanize_visual_block(block_type: str) -> str:
    mapping = {
        "dense-route-board": "a high-density technical route map",
        "center-question-hub": "a clear central scientific question anchor",
        "four-workstream-panels": "four substantial workstream panels",
        "cross-connectors": "visible cross-links between workstreams",
        "side-pillars": "side support pillars or side evidence modules",
        "output-ribbon": "a final synthesis ribbon or output zone",
        "micro-evidence-tags": "small supporting evidence tags",
        "vertical-design-cards": "a disciplined design-card sequence",
        "number-rail": "a numbered progression rail",
        "clean-connectors": "clean and aligned connectors",
        "summary-strip": "a summary strip that frames the board",
        "evaluation-badges": "endpoint or evaluation badges",
        "radial-evidence-board": "an integrated evidence board",
        "central-claim": "a dominant central claim",
        "domain-rings": "surrounding evidence domains or rings",
        "peripheral-support-labels": "peripheral support labels",
        "aggregation-connectors": "aggregation connectors showing convergence",
        "trigger-layer": "a trigger or disease-entry layer",
        "autophagy-dysregulation-core": "a core dysregulation module",
        "inflammasome-axis": "an inflammatory signaling axis",
        "cell-injury-consequences": "consequence nodes showing injury outcomes",
        "intervention-rescue-layer": "an intervention or rescue layer",
        "supportive-callout-bubbles": "small supporting callouts",
        "feedback-arrows": "secondary feedback arrows or loops",
    }
    return mapping.get(block_type, block_type.replace("-", " "))


def role_specific_rules(recipe: dict[str, Any]) -> list[str]:
    role = recipe["page_role"]
    rules: list[str] = []
    if role == "agenda":
        rules.extend(
            [
                "- Build a four-item outline only.",
                "- Use badges 01, 02, 03, and 04 exactly once each.",
                "- Keep the body list clean and elegant, without diagonal decorations or slogan ribbons.",
            ]
        )
    if role == "study-design-board":
        rules.extend(
            [
                "- Preserve subject, grouping, intervention, and evaluation order clearly.",
                "- Prefer a refined stepped, laddered, tiered, or board-like clinical composition over a crude chain diagram.",
                "- Keep connectors disciplined and aligned; avoid loops unless they serve a real study logic.",
            ]
        )
    if role == "goal-innovation":
        rules.extend(
            [
                "- Match the number of innovation cards to the available content exactly.",
                "- Make the cards information-rich and committee-facing rather than slogan-like.",
            ]
        )
    if role == "route-board":
        rules.extend(
            [
                "- Make the reading flow directional and obvious within two seconds.",
                "- Avoid a simple cross or four-box layout; build a true thesis-level technical route board with hierarchy and orchestration.",
                "- Use layered connectors, grouped modules, and synthesis logic so the page feels closer to a polished route-map board than a generic flowchart.",
                "- Learn from the thesis route-map sample bank as a style family, not as a literal four-panel sheet.",
                "- Prefer a strong top headline, a visible central hub, surrounding workstream clusters, side support lanes, and a bottom synthesis zone.",
                "- Keep the page blue-white academic, high-density, and engineered in alignment, with restrained red accents only for emphasis.",
            ]
        )
    if role == "evidence-chain-board":
        rules.extend(
            [
                "- Avoid a simple circle with four blobs. Build a dense evidence board with a strong core and visible convergence logic.",
                "- Use multiple evidence domains, layered support modules, and explicit aggregation cues.",
                "- Borrow the same route-board grammar when useful: central anchor, surrounding domains, lower landing zone, and clear directional convergence.",
            ]
        )
    if role == "mechanism-board":
        rules.extend(
            [
                "- Avoid a flat three-panel strip. Build a dense graphical-summary page with nested mechanistic subcomponents.",
                "- Use trigger, dysregulation, injury, and rescue logic together, with secondary cues that make the page feel journal-grade.",
                "- Keep the board dense and modular rather than poster-like, and make the central mechanism read as the anchor of the page.",
            ]
        )
    return rules


def build_prompt(recipe: dict[str, Any], style_brief: str) -> str:
    content_lines = []
    for idx, block in enumerate(recipe.get("content_blocks", []), start=1):
        content_lines.append(f"Block {idx} purpose: {humanize_slot(block['slot'])}")
        content_lines.append(f"Block {idx} writing goal: {block['rewrite_instruction']}")
        content_lines.append(f"Block {idx} minimum words target: {block.get('min_words', block['max_words'])}")
        content_lines.append(f"Block {idx} maximum words target: {block['max_words']}")
        for point in block.get("source_points_zh", []):
            content_lines.append(f"Block {idx} source meaning (zh): {point}")

    visual_lines = [f"- {humanize_visual_block(item['type'])}" for item in recipe.get("visual_blocks", [])]
    freedom_lines = [f"- {item}" for item in recipe.get("layout_freedom", [])]
    must_have_lines = [f"- {item}" for item in recipe.get("must_include_elements", [])]
    forbidden_lines = [f"- {item}" for item in recipe.get("forbidden_patterns", [])]
    review_lines = [f"- {item}" for item in recipe.get("review_checks", [])]
    repair_lines = [f"- {item}" for item in recipe.get("repair_notes", [])]

    safe = recipe["safe_zone_rules"]
    safe_zone_lines = describe_safe_zones(safe)
    complexity = recipe.get("complexity_target", {})
    role_rules = role_specific_rules(recipe)

    return "\n".join(
        [
            "You are generating one final-review academic PPT page image.",
            "Use English only. No Chinese anywhere.",
            "Respect the provided template style and safe zones strictly.",
            "",
            "STYLE BRIEF",
            style_brief,
            "",
            "PAGE IDENTITY",
            f"Slide id: {recipe['slide_id']}",
            f"Page role: {recipe['page_role']}",
            f"English title: {recipe['english_title']}",
            f"Core claim from source thesis: {recipe['core_claim']}",
            f"Density policy: {recipe.get('density_policy', 'default')}",
            "",
            "HEADER / BRANDING RULES",
            "Do not render any school name, any school logo, any crest, any seal, or any placeholder university branding.",
            "Keep the top-right corner visually quiet and empty so a manual school mark can be added later outside the model workflow.",
            "",
            "SAFE ZONE RULES",
            *safe_zone_lines,
            "",
            "CONTENT DENSITY TARGET",
            "Write fuller English than a normal final slide draft because this review version is intentionally overbuilt for later Chinese compression.",
            "Do not output ultra-short labels unless the page really needs a short banner or node name.",
            "",
            "CONTENT CONTRACT",
            *content_lines,
            "",
            "MUST-HAVE CONTENT ELEMENTS",
            *(must_have_lines or ["- Preserve the declared content hierarchy and reading order."]),
            "",
            "VISUAL INTENT",
            *visual_lines,
            "",
            "COMPOSITION FREEDOM",
            "You must keep the content contract and reading order fixed, but you may choose a more advanced and elegant composition instead of rigidly following a crude box template.",
            *(freedom_lines or ["- Use a disciplined but flexible presentation-ready composition."]),
            "",
            "COMPLEXITY TARGET",
            f"Visual intensity target: {complexity.get('visual_intensity', 'high')}",
            f"Minimum structural groups: {complexity.get('min_structural_groups', 4)}",
            f"Minimum connectors: {complexity.get('min_connectors', 0)}",
            f"Minimum visual layers: {complexity.get('min_layers', 3)}",
            f"Complexity note: {complexity.get('notes', 'Keep the page visually rich and controlled.')}",
            "",
            "ROLE-SPECIFIC HARD RULES",
            *(role_rules or ["- Preserve hierarchy, readability, and presentation-grade order."]),
            "",
            "TEMPLATE COMPLIANCE RULES",
            f"Primary accent: #{recipe['template_constraints']['primary_accent']}",
            f"Secondary accents: {recipe['template_constraints']['secondary_accents']}",
            f"Fonts: {recipe['template_constraints']['fonts']}",
            "Keep a white-first blue academic tone.",
            "Make the page feel like a polished defense slide, not a research poster.",
            "",
            "FORBIDDEN LIST",
            *forbidden_lines,
            "- Do not render any coordinates, JSON, x/y/w/h values, prompt metadata, slot names, schema labels, or internal component names on the page.",
            "- Do not collapse a high-complexity board into a sparse infographic.",
            "- Do not print words such as center_hub, output_band, title_band, footer_band, left_rail, right_rail, route-board, evidence-chain-board, or mechanism-board.",
            "",
            "REPAIR NOTES",
            *(repair_lines or ["- None."]),
            "",
            "REVIEW CHECKLIST",
            *review_lines,
            "",
            "OUTPUT",
            "Produce one 16:9 slide image that already looks presentation-ready.",
        ]
    )


def build_generation_body(recipe: dict[str, Any], style_brief: str, profile: dict[str, Any]) -> dict[str, Any]:
    prompt = build_prompt(recipe, style_brief)
    parts: list[dict[str, Any]] = [{"text": prompt}]
    for image_path in selected_reference_images(recipe, profile):
        parts.append(inline_part(image_path))
    for image_path in figure_reference_images(recipe):
        parts.append(inline_part(image_path))
    return {
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        "generationConfig": {
            "responseModalities": ["Image"],
            "imageConfig": {"aspectRatio": "16:9"},
        },
    }


def build_review_body(recipe: dict[str, Any], candidate_image: Path, profile: dict[str, Any]) -> dict[str, Any]:
    review_prompt = "\n".join(
        [
            "Review this generated PPT page image against the page recipe and the academic-blue template references.",
            "Return strict JSON only.",
            "Schema:",
            '{"pass": true|false, "summary": "short", "issues": [{"type": "layout|overflow|safe-zone|arrow|density|style", "severity": "low|medium|high", "reason": "..." }], "recommended_repairs": ["..."]}',
            f"Page role: {recipe['page_role']}",
            f"English title should be: {recipe['english_title']}",
            f"Density policy: {recipe.get('density_policy', 'default')}",
            f"Complexity target: {recipe.get('complexity_target', {})}",
            f"Must-have content elements: {recipe.get('must_include_elements', [])}",
            "Check whether the page respects title band, top-right quiet zone, footer band, order, density, readability, and board complexity.",
            "If the page is too sparse, too simple, or collapses a complex board into a lightweight infographic, set pass=false.",
            "If the page contains any school branding, coordinate strings, x/y/w/h metadata, JSON fragments, internal schema labels, or prompt leakage, set pass=false.",
        ]
    )
    parts: list[dict[str, Any]] = [{"text": review_prompt}, inline_part(candidate_image)]
    for image_path in selected_reference_images(recipe, profile)[:2]:
        parts.append(inline_part(image_path))
    return {
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT"],
        },
    }


def revise_recipe(recipe: dict[str, Any], attempt: int, review: dict[str, Any] | None = None) -> dict[str, Any]:
    updated = copy.deepcopy(recipe)
    updated.setdefault("repair_notes", [])
    if review:
        for item in review.get("recommended_repairs", []):
            if isinstance(item, dict):
                reason = item.get("reason") or item.get("type")
                if reason:
                    updated["repair_notes"].append(str(reason))
            elif item:
                updated["repair_notes"].append(str(item))
    if attempt == 1:
        for block in updated.get("content_blocks", []):
            block["min_words"] = max(12, int(block.get("min_words", block["max_words"]) * 0.9))
            block["max_words"] = max(block["min_words"] + 8, int(block["max_words"] * 0.9))
        updated["repair_notes"].append("Slightly reduce text pressure while preserving a rich committee-level board composition.")
        if updated["page_role"] == "agenda":
            updated["layout_slots"]["variant"] = "agenda-list-strict"
            updated["repair_notes"].append("Use exactly four agenda rows numbered 01, 02, 03, and 04 once each.")
            updated["repair_notes"].append("Keep every agenda row to a single concise line and remove decorative ribbon text.")
        if updated["page_role"] == "study-design-board":
            updated["repair_notes"].append("Use a clearer stepped or laddered structure with better spacing, but keep a refined clinical-board sophistication.")
        if updated["page_role"] in {"route-board", "evidence-chain-board", "mechanism-board"}:
            updated["repair_notes"].append("Keep complexity high while improving spacing, rhythm, and connector discipline.")
    elif attempt == 2:
        updated["template_reference_roles"] = updated.get("template_reference_roles", [])[:1]
        updated["figure_source_refs"] = []
        updated["repair_notes"].append("Use fewer visual references and keep only the cleanest template cue.")
        if updated["page_role"] == "study-design-board":
            updated["template_reference_roles"] = ["background-text"]
            updated["repair_notes"].append("Fallback to a cleaner split-text reference while retaining an advanced clinical-board composition.")
    return updated


def update_slide_record(slide: dict[str, Any], asset_path: Path, review: dict[str, Any], attempts: int) -> dict[str, Any]:
    updated = dict(slide)
    updated["raster_asset"] = {
        "path": str(asset_path.resolve()),
        "format": asset_path.suffix.lstrip(".").lower(),
    }
    updated["review_state"] = {
        "status": "pass" if review.get("pass") else "needs-review",
        "attempts": attempts,
        "summary": review.get("summary", ""),
        "issues": review.get("issues", []),
    }
    return updated


def update_slide_failure(slide: dict[str, Any], review: dict[str, Any], attempts: int) -> dict[str, Any]:
    updated = dict(slide)
    updated["raster_asset"] = None
    updated["review_state"] = {
        "status": "needs-review",
        "attempts": attempts,
        "summary": review.get("summary", ""),
        "issues": review.get("issues", []),
    }
    return updated


def generation_command(config_file: Path, body_file: Path, output_file: Path, request_dump: Path, response_dump: Path) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).with_name("generate_third_party_image.py")),
        "--config-file",
        str(config_file.resolve()),
        "--raw-body-file",
        str(body_file.resolve()),
        "--output-file",
        str(output_file.resolve()),
        "--request-dump-file",
        str(request_dump.resolve()),
        "--response-dump-file",
        str(response_dump.resolve()),
    ]


def review_command(config_file: Path, body_file: Path, output_file: Path, response_dump: Path) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).with_name("call_third_party_model.py")),
        "--config-file",
        str(config_file.resolve()),
        "--raw-body-file",
        str(body_file.resolve()),
        "--expect-json",
        "--output-json",
        str(output_file.resolve()),
        "--response-dump-file",
        str(response_dump.resolve()),
    ]


def slide_filter(slides: list[dict[str, Any]], requested_ids: set[str] | None) -> list[dict[str, Any]]:
    if not requested_ids:
        return [slide for slide in slides if slide.get("visual_route") == "gemini-page-raster"]
    return [slide for slide in slides if slide.get("id") in requested_ids]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate strict full-page academic raster slides from page recipes and review them with Gemini.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--template-profile-file", required=True)
    parser.add_argument("--template-style-brief-file", required=True)
    parser.add_argument("--config-file", required=True)
    parser.add_argument("--assets-dir", required=True)
    parser.add_argument("--output-spec-file", required=True)
    parser.add_argument("--output-review-file", required=True)
    parser.add_argument("--output-manual-review-file", required=True)
    parser.add_argument("--slide-ids", nargs="*")
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    profile = read_json(Path(args.template_profile_file))
    style_brief = Path(args.template_style_brief_file).read_text(encoding="utf-8")
    assets_dir = Path(args.assets_dir).resolve()
    config_file = Path(args.config_file).resolve()
    requested_ids = set(args.slide_ids or [])

    reviews: list[dict[str, Any]] = []
    manual_items: list[dict[str, Any]] = []
    updated_slides = []

    targets = {slide.get("id"): slide for slide in slide_filter(spec.get("slides", []), requested_ids)}

    for slide in spec.get("slides", []):
        slide_id = slide.get("id")
        if slide_id not in targets:
            updated_slides.append(dict(slide))
            continue

        recipe_file = Path(slide["recipe_file"])
        original_recipe = read_json(recipe_file)
        working_recipe = copy.deepcopy(original_recipe)
        slide_dir = assets_dir / slide_id
        best_asset: Path | None = None
        best_review: dict[str, Any] = {"pass": False, "summary": "No review completed.", "issues": [{"type": "generation", "severity": "high", "reason": "Generation did not complete."}]}
        attempts_used = 0

        for attempt in range(1, args.max_attempts + 1):
            attempts_used = attempt
            attempt_dir = slide_dir / f"attempt-{attempt}"
            ensure_parent(attempt_dir / "placeholder")
            recipe_snapshot = attempt_dir / "page_recipe.json"
            render_request = attempt_dir / "page_render_request.json"
            raw_image = attempt_dir / f"{slide_id}.png"
            request_dump = attempt_dir / "image-request.json"
            response_dump = attempt_dir / "image-response.json"
            review_body = attempt_dir / "review-request.json"
            review_result = attempt_dir / "review-result.json"
            review_response = attempt_dir / "review-response.json"

            write_json(recipe_snapshot, working_recipe)
            write_json(render_request, build_generation_body(working_recipe, style_brief, profile))

            try:
                run(generation_command(config_file, render_request, raw_image, request_dump, response_dump))
            except subprocess.CalledProcessError as exc:
                best_review = {
                    "pass": False,
                    "summary": "Image generation failed.",
                    "issues": [{"type": "generation", "severity": "high", "reason": exc.stderr or exc.stdout or "Unknown error"}],
                }
                break

            if raw_image.exists():
                best_asset = raw_image

            write_json(review_body, build_review_body(working_recipe, raw_image, profile))
            try:
                run(review_command(config_file, review_body, review_result, review_response))
                review_payload = read_json(review_result)
                current_review = review_payload.get("result", review_payload)
            except Exception as exc:  # noqa: BLE001
                current_review = {
                    "pass": False,
                    "summary": "Visual review failed to return structured JSON.",
                    "issues": [{"type": "review", "severity": "high", "reason": str(exc)}],
                    "recommended_repairs": [],
                }

            if isinstance(current_review, str):
                current_review = {
                    "pass": False,
                    "summary": "Visual review returned unstructured text.",
                    "issues": [{"type": "review", "severity": "high", "reason": current_review}],
                    "recommended_repairs": [],
                }

            best_review = current_review
            reviews.append(
                {
                    "slide_id": slide_id,
                    "attempt": attempt,
                    "asset_file": str(raw_image.resolve()),
                    "review": current_review,
                }
            )
            if current_review.get("pass"):
                break
            if attempt < args.max_attempts:
                working_recipe = revise_recipe(working_recipe, attempt)

        if not best_review.get("pass"):
            manual_items.append(
                {
                    "slide_id": slide_id,
                    "recipe_file": str(recipe_file.resolve()),
                    "best_asset": str(best_asset.resolve()) if best_asset else None,
                    "review": best_review,
                }
            )

        if best_asset:
            updated_slides.append(update_slide_record(slide, best_asset, best_review, attempts_used))
        else:
            updated_slides.append(update_slide_failure(slide, best_review, attempts_used))

    updated_spec = dict(spec)
    updated_spec["slides"] = updated_slides
    updated_spec["page_raster_v1_review"] = {
        "strategy": "gemini-page-raster-review-loop",
        "assets_dir": str(assets_dir),
        "manual_review_file": str(Path(args.output_manual_review_file).resolve()),
    }

    write_json(Path(args.output_spec_file).resolve(), updated_spec)
    write_json(Path(args.output_review_file).resolve(), reviews)
    write_json(Path(args.output_manual_review_file).resolve(), manual_items)


if __name__ == "__main__":
    main()
