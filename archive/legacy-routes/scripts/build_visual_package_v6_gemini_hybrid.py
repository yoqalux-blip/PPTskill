from __future__ import annotations

import argparse
import copy
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance

from common_io import ensure_parent, read_json, write_json


TARGET_PAGE_KINDS = {
    "slide-09": "route-board",
    "slide-12": "study-board",
    "slide-31": "evidence-board",
    "slide-32": "mechanism-board",
}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def generate_image(
    config_file: Path,
    prompt: str,
    output_file: Path,
    request_dump: Path,
    response_dump: Path,
    transparent_background: bool = False,
) -> None:
    ensure_parent(output_file)
    cmd = [
        sys.executable,
        str(Path(__file__).with_name("generate_third_party_image.py")),
        "--config-file",
        str(config_file),
        "--prompt",
        prompt,
        "--output-file",
        str(output_file),
        "--request-dump-file",
        str(request_dump),
        "--response-dump-file",
        str(response_dump),
    ]
    if transparent_background:
        cmd.append("--transparent-background")
    run(cmd)


def soften_plate(input_file: Path, output_file: Path, white_mix: float = 0.8, saturation: float = 0.7, alpha: int = 140) -> None:
    image = Image.open(input_file).convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    softened = Image.blend(image, white, white_mix)
    softened = ImageEnhance.Color(softened).enhance(saturation)
    alpha_layer = Image.new("L", softened.size, alpha)
    softened.putalpha(alpha_layer)
    ensure_parent(output_file)
    softened.save(output_file)


def polish_panel(input_file: Path, output_file: Path, white_mix: float = 0.22, saturation: float = 0.9, alpha: int = 232) -> None:
    image = Image.open(input_file).convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    polished = Image.blend(image, white, white_mix)
    polished = ImageEnhance.Color(polished).enhance(saturation)
    alpha_layer = Image.new("L", polished.size, alpha)
    polished.putalpha(alpha_layer)
    ensure_parent(output_file)
    polished.save(output_file)


def failed_slide_ids(spec: dict[str, Any], audit: dict[str, Any] | None) -> set[str]:
    if not audit:
        return set()
    failed_numbers = {
        item["slide_number"]
        for item in audit.get("slides", [])
        if item.get("issues")
    }
    ids: set[str] = set()
    for idx, slide in enumerate(spec.get("slides", []), start=1):
        if idx in failed_numbers:
            ids.add(slide.get("id", f"slide-{idx:02d}"))
    return ids


def target_slide_ids(spec: dict[str, Any], audit: dict[str, Any] | None, only_failed: bool) -> set[str]:
    present = {slide.get("id") for slide in spec.get("slides", []) if slide.get("id") in TARGET_PAGE_KINDS}
    if only_failed:
        return present.intersection(failed_slide_ids(spec, audit))
    return present


def route_page_brief(slide: dict[str, Any]) -> dict[str, Any]:
    diagram = slide.get("diagram_v5", {})
    return {
        "slide_id": slide.get("id"),
        "page_kind": "route-board",
        "page_goal": "Show the thesis as a dense translational technical route board rather than a simple left-to-right flow.",
        "core_claim": diagram.get("center", {}).get("body", slide.get("takeaway", "")),
        "visual_style": [
            "dense academic roadmap board",
            "clean scientific poster hierarchy",
            "centered research question with multi-directional support",
            "soft ivory background with navy, blue, violet, copper, and green grouping accents",
        ],
        "must_show": [
            "one centered scientific question",
            "four upstream route modules",
            "three downstream output modules",
            "left and right support rails",
        ],
        "forbidden": [
            "no text",
            "no labels",
            "no numbers",
            "no arrows",
            "no screenshot-like UI",
        ],
    }


def route_layout_schema() -> dict[str, Any]:
    return {
        "page_kind": "route-board",
        "density_mode": "default",
        "connector_style": "outer",
        "canvas_regions": {
            "board": {"x": 0.82, "y": 1.2, "w": 11.72, "h": 5.02},
            "summary": {"x": 1.08, "y": 1.64, "w": 10.82, "h": 0.28, "font_size": 10.0},
            "left_rail": {"x": 1.04, "y": 2.1, "w": 0.72, "h": 3.62},
            "right_rail": {"x": 11.1, "y": 2.1, "w": 0.72, "h": 3.62},
            "center_hub": {"x": 4.56, "y": 2.68, "w": 3.96, "h": 1.84},
            "bottom_band": {"x": 2.0, "y": 5.08, "w": 9.2, "h": 0.92},
        },
        "background_asset_slots": [
            {"id": "route-plate", "x": 1.02, "y": 2.02, "w": 10.96, "h": 3.76, "fit": "contain"}
        ],
        "cards": [
            {"id": "card-01", "x": 1.9, "y": 2.26, "w": 2.18, "h": 1.0, "style": "blue", "header_fill": "E9F1FA", "stroke": "5A86C4"},
            {"id": "card-02", "x": 4.36, "y": 2.26, "w": 2.18, "h": 1.0, "style": "violet", "header_fill": "EFE8F7", "stroke": "8872B9"},
            {"id": "card-03", "x": 6.82, "y": 2.26, "w": 2.18, "h": 1.0, "style": "rose", "header_fill": "F7E9F0", "stroke": "C2658D"},
            {"id": "card-04", "x": 9.28, "y": 2.26, "w": 2.18, "h": 1.0, "style": "amber", "header_fill": "FFF0DF", "stroke": "D68C30"},
            {"id": "output-01", "x": 2.02, "y": 5.18, "w": 2.52, "h": 0.86, "style": "green", "header_fill": "EEF7EC", "stroke": "6DA56E"},
            {"id": "output-02", "x": 5.1, "y": 5.18, "w": 2.52, "h": 0.86, "style": "violet", "header_fill": "F2EBFA", "stroke": "8B69B8"},
            {"id": "output-03", "x": 8.18, "y": 5.18, "w": 2.52, "h": 0.86, "style": "rose", "header_fill": "F7E9F0", "stroke": "C2658D"},
        ],
        "connectors": [
            {"from": "card-01", "to": "center_hub", "color": "6D8FC6"},
            {"from": "card-02", "to": "center_hub", "color": "8572BB"},
            {"from": "card-03", "to": "center_hub", "color": "C2658D"},
            {"from": "card-04", "to": "center_hub", "color": "D68C30"},
            {"from": "center_hub", "to": "output-01", "color": "6DA56E"},
            {"from": "center_hub", "to": "output-02", "color": "8B69B8"},
            {"from": "center_hub", "to": "output-03", "color": "C2658D"},
        ],
        "text_slots": {
            "takeaway": {"x": 6.2, "y": 6.28, "w": 6.0, "h": 0.72},
        },
        "layer_order": ["frame", "background_assets", "rails", "cards", "connectors", "hub", "text"],
    }


def study_page_brief(slide: dict[str, Any]) -> dict[str, Any]:
    return {
        "slide_id": slide.get("id"),
        "page_kind": "study-board",
        "page_goal": "Turn the study design page into a polished clinical design board with an editable numbered rail and stacked cards.",
        "core_claim": slide.get("takeaway", ""),
        "visual_style": [
            "clinical design board",
            "editorial but restrained medical slide",
            "soft right-hand board with clean spacing",
        ],
        "must_show": [
            "one numbered vertical rail",
            "four stacked cards",
            "clean right-side board background",
        ],
        "forbidden": ["no text", "no labels", "no numbers", "no arrows"],
    }


def study_layout_schema() -> dict[str, Any]:
    return {
        "page_kind": "study-board",
        "density_mode": "default",
        "canvas_regions": {
            "left_text": {"x": 0.86, "y": 1.38, "w": 5.08, "h": 4.96, "font_size": 14.0},
            "board": {"x": 6.26, "y": 1.24, "w": 6.02, "h": 5.08},
            "summary": {"x": 6.72, "y": 1.94, "w": 4.84, "h": 0.34, "font_size": 9.8},
            "rail": {"x": 6.76, "y": 2.34, "w": 0.32, "h": 3.06},
        },
        "background_asset_slots": [
            {"id": "study-plate", "x": 6.58, "y": 2.12, "w": 5.24, "h": 3.62, "fit": "contain"}
        ],
        "cards": [
            {"id": "card-01", "x": 7.28, "y": 2.3, "w": 4.44, "h": 0.72, "header_fill": "EAF0FA", "stroke": "5A86C4"},
            {"id": "card-02", "x": 7.28, "y": 3.1, "w": 4.44, "h": 0.72, "header_fill": "F2EBFA", "stroke": "8B69B8"},
            {"id": "card-03", "x": 7.28, "y": 3.9, "w": 4.44, "h": 0.72, "header_fill": "F7E9F0", "stroke": "C2658D"},
            {"id": "card-04", "x": 7.28, "y": 4.7, "w": 4.44, "h": 0.72, "header_fill": "FFF0DF", "stroke": "D68C30"},
        ],
        "connectors": [
            {"from": "card-01", "to": "card-02", "color": "BBA88F"},
            {"from": "card-02", "to": "card-03", "color": "BBA88F"},
            {"from": "card-03", "to": "card-04", "color": "BBA88F"},
        ],
        "text_slots": {
            "takeaway": {"x": 6.34, "y": 6.18, "w": 6.0, "h": 0.72},
        },
        "background_tags": ["soft timeline motifs", "light clinical geometry"],
        "layer_order": ["frame", "background_assets", "rail", "cards", "connectors", "text"],
    }


def evidence_page_brief(slide: dict[str, Any]) -> dict[str, Any]:
    diagram = slide.get("diagram_v5", {})
    return {
        "slide_id": slide.get("id"),
        "page_kind": "evidence-board",
        "page_goal": "Present the evidence chain as a centered thesis conclusion with four supporting layers arranged around it.",
        "core_claim": diagram.get("center", {}).get("body", slide.get("takeaway", "")),
        "visual_style": [
            "radial scientific evidence board",
            "soft concentric structure",
            "clear thesis-centered hierarchy",
        ],
        "must_show": [
            "one centered conclusion",
            "four surrounding evidence modules",
            "soft radial background",
        ],
        "forbidden": ["no text", "no labels", "no numbers", "no arrows"],
    }


def evidence_layout_schema() -> dict[str, Any]:
    return {
        "page_kind": "evidence-board",
        "density_mode": "default",
        "canvas_regions": {
            "board": {"x": 0.84, "y": 1.22, "w": 11.7, "h": 4.72},
            "summary": {"x": 1.02, "y": 1.82, "w": 10.88, "h": 0.3, "font_size": 10.0},
            "center_hub": {"x": 4.98, "y": 3.08, "w": 2.42, "h": 0.94},
            "bullet_strip": {"x": 1.02, "y": 5.88, "w": 10.86, "h": 0.42, "font_size": 11.0},
        },
        "background_asset_slots": [
            {"id": "evidence-plate", "x": 1.02, "y": 2.12, "w": 10.98, "h": 3.28, "fit": "contain"}
        ],
        "cards": [
            {"id": "card-01", "x": 1.14, "y": 2.34, "w": 3.1, "h": 1.1, "header_fill": "EAF0FA", "stroke": "5A86C4"},
            {"id": "card-02", "x": 8.08, "y": 2.34, "w": 3.1, "h": 1.1, "header_fill": "F2EBFA", "stroke": "8B69B8"},
            {"id": "card-03", "x": 1.14, "y": 4.1, "w": 3.1, "h": 1.1, "header_fill": "EEF7EC", "stroke": "6DA56E"},
            {"id": "card-04", "x": 8.08, "y": 4.1, "w": 3.1, "h": 1.1, "header_fill": "FFF0DF", "stroke": "D68C30"},
        ],
        "connectors": [
            {"from": "card-01", "to": "center_hub", "color": "5A86C4"},
            {"from": "card-02", "to": "center_hub", "color": "8B69B8"},
            {"from": "card-03", "to": "center_hub", "color": "6DA56E"},
            {"from": "card-04", "to": "center_hub", "color": "D68C30"},
        ],
        "text_slots": {
            "takeaway": {"x": 6.14, "y": 6.08, "w": 6.0, "h": 0.72},
        },
        "layer_order": ["frame", "background_assets", "cards", "connectors", "hub", "text"],
    }


def mechanism_page_brief(slide: dict[str, Any]) -> dict[str, Any]:
    return {
        "slide_id": slide.get("id"),
        "page_kind": "mechanism-board",
        "page_goal": "Show a polished no-text mechanism page with a left-to-right biological rescue narrative and editable Chinese labels outside the art.",
        "core_claim": slide.get("takeaway", ""),
        "visual_style": [
            "journal-style biological triptych",
            "left infection, middle pathway stress, right therapeutic rescue",
            "clean light background suitable for editable overlays",
        ],
        "must_show": [
            "alveolar infection state",
            "autophagy and inflammation dysregulation",
            "therapeutic rescue",
        ],
        "forbidden": ["no text", "no labels", "no numbers"],
    }


def mechanism_layout_schema() -> dict[str, Any]:
    return {
        "page_kind": "mechanism-board",
        "density_mode": "default",
        "canvas_regions": {
            "board": {"x": 0.84, "y": 1.24, "w": 11.7, "h": 4.5},
            "summary": {"x": 1.02, "y": 1.44, "w": 10.9, "h": 0.3, "font_size": 10.0},
            "art": {"x": 1.02, "y": 1.9, "w": 10.96, "h": 3.16},
            "bridge": {"x": 4.32, "y": 4.84, "w": 4.34, "h": 0.38},
            "bullet_strip": {"x": 1.02, "y": 5.22, "w": 10.8, "h": 0.5, "font_size": 11.3},
        },
        "background_asset_slots": [
            {"id": "mechanism-plate", "x": 1.02, "y": 1.98, "w": 10.96, "h": 3.02, "fit": "cover"}
        ],
        "text_slots": {
            "takeaway": {"x": 6.12, "y": 6.0, "w": 6.0, "h": 0.72},
        },
        "overlay_labels": [
            {"text": "感染触发", "x": 1.36, "y": 1.72, "w": 1.72, "h": 0.28},
            {"text": "通路失衡", "x": 5.04, "y": 1.72, "w": 1.72, "h": 0.28},
            {"text": "干预逆转", "x": 8.76, "y": 1.72, "w": 1.72, "h": 0.28},
        ],
        "connectors": [
            {"type": "line", "x1": 3.76, "y1": 3.42, "x2": 4.76, "y2": 3.42, "color": "8A5A44"},
            {"type": "line", "x1": 7.38, "y1": 3.42, "x2": 8.38, "y2": 3.42, "color": "8A5A44"},
        ],
        "layer_order": ["frame", "background_assets", "overlay_labels", "connectors", "text"],
    }


def build_prompt(page_brief: dict[str, Any]) -> str:
    style = ", ".join(page_brief["visual_style"])
    must_show = "; ".join(page_brief["must_show"])
    forbidden = ", ".join(page_brief["forbidden"])
    return (
        f"Create a 16:9 academic slide artwork for a PhD defense. "
        f"Page goal: {page_brief['page_goal']} "
        f"Core claim: {page_brief['core_claim']} "
        f"Visual style: {style}. "
        f"Must visually suggest: {must_show}. "
        f"Important constraints: {forbidden}. "
        "Use a premium scientific graphical abstract style with clean hierarchy, soft ivory background, "
        "controlled palette, and generous space for editable overlays."
    )


def make_page_artifacts(slide: dict[str, Any], slide_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    slide_id = slide["id"]
    if slide_id == "slide-09":
        return route_page_brief(slide), route_layout_schema()
    if slide_id == "slide-12":
        return study_page_brief(slide), study_layout_schema()
    if slide_id == "slide-31":
        return evidence_page_brief(slide), evidence_layout_schema()
    if slide_id == "slide-32":
        return mechanism_page_brief(slide), mechanism_layout_schema()
    raise ValueError(f"Unsupported Gemini hybrid slide: {slide_id}")


def asset_output_path(slide_dir: Path, page_kind: str, regenerate: bool, regen_count: int) -> tuple[Path, Path, Path]:
    suffix = f"-regen-{regen_count}" if regenerate and regen_count > 0 else ""
    raw = slide_dir / f"{page_kind}{suffix}-raw.png"
    final = slide_dir / f"{page_kind}{suffix}.png"
    request_dump = slide_dir / f"{page_kind}{suffix}-request.json"
    response_dump = slide_dir / f"{page_kind}{suffix}-response.json"
    return raw, final, request_dump, response_dump


def existing_qa_state(slide: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(slide.get("gemini_hybrid", {}).get("qa_state", {}))


def ensure_slide_artifacts(
    slide: dict[str, Any],
    slide_dir: Path,
    config_file: Path,
    regenerate: bool,
) -> dict[str, Any]:
    page_brief, layout_schema = make_page_artifacts(slide, slide_dir)
    qa_state = existing_qa_state(slide)
    regen_count = int(qa_state.get("asset_regeneration_count", 0)) + (1 if regenerate else 0)
    page_kind = page_brief["page_kind"]
    raw_file, final_file, request_dump, response_dump = asset_output_path(slide_dir, page_kind, regenerate, regen_count)

    generate_image(
        config_file=config_file,
        prompt=build_prompt(page_brief),
        output_file=raw_file,
        request_dump=request_dump,
        response_dump=response_dump,
        transparent_background=(page_kind == "mechanism-board"),
    )

    if page_kind == "mechanism-board":
        polish_panel(raw_file, final_file)
    else:
        soften_plate(raw_file, final_file)

    page_brief_file = slide_dir / "page_brief.json"
    layout_schema_file = slide_dir / "layout_schema.json"
    write_json(page_brief_file, page_brief)
    write_json(layout_schema_file, layout_schema)

    qa_state["asset_regeneration_count"] = regen_count
    qa_state.setdefault("schema_repair_count", 0)
    qa_state["request_regenerate_asset"] = False

    return {
        "page_brief_file": str(page_brief_file.resolve()),
        "layout_schema_file": str(layout_schema_file.resolve()),
        "page_brief": page_brief,
        "layout_schema": layout_schema,
        "generated_assets": [
            {
                "slot_id": layout_schema["background_asset_slots"][0]["id"],
                "path": str(final_file.resolve()),
                "role": "page-plate",
                "kind": page_kind,
                "request_dump": str(request_dump.resolve()),
                "response_dump": str(response_dump.resolve()),
            }
        ],
        "qa_state": qa_state,
    }


def enrich_slide(slide: dict[str, Any], artifact: dict[str, Any]) -> None:
    slide["visual_route"] = "gemini-editable-hybrid"
    slide["gemini_hybrid"] = {
        "page_kind": artifact["page_brief"]["page_kind"],
        "page_brief_file": artifact["page_brief_file"],
        "layout_schema_file": artifact["layout_schema_file"],
        "page_brief": artifact["page_brief"],
        "layout_schema": artifact["layout_schema"],
        "generated_assets": artifact["generated_assets"],
        "allow_english_terms": False,
        "qa_policy": {
            "max_schema_repairs": 1,
            "max_asset_regenerations": 1,
            "fallback_backend": "drawio-mcp-diagram-lab",
            "step_1": "adjust-layout-schema",
            "step_2": "regenerate-background-assets",
        },
        "qa_state": artifact["qa_state"],
    }


def update_spec(
    spec: dict[str, Any],
    config_file: Path,
    assets_dir: Path,
    target_ids: set[str],
    regenerate: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    refined = copy.deepcopy(spec)
    plan_items: list[dict[str, Any]] = []
    for slide in refined.get("slides", []):
        slide_id = slide.get("id")
        if slide_id not in TARGET_PAGE_KINDS:
            continue
        if slide_id in target_ids:
            slide_dir = assets_dir / slide_id
            slide_dir.mkdir(parents=True, exist_ok=True)
            artifact = ensure_slide_artifacts(slide, slide_dir, config_file, regenerate=regenerate)
            enrich_slide(slide, artifact)
            plan_items.append(
                {
                    "slide_id": slide_id,
                    "page_kind": artifact["page_brief"]["page_kind"],
                    "page_brief_file": artifact["page_brief_file"],
                    "layout_schema_file": artifact["layout_schema_file"],
                    "generated_assets": artifact["generated_assets"],
                    "qa_state": artifact["qa_state"],
                }
            )
        elif slide.get("gemini_hybrid"):
            plan_items.append(
                {
                    "slide_id": slide_id,
                    "page_kind": slide["gemini_hybrid"].get("page_kind"),
                    "page_brief_file": slide["gemini_hybrid"].get("page_brief_file"),
                    "layout_schema_file": slide["gemini_hybrid"].get("layout_schema_file"),
                    "generated_assets": slide["gemini_hybrid"].get("generated_assets", []),
                    "qa_state": slide["gemini_hybrid"].get("qa_state", {}),
                }
            )

    refined["schema_version"] = "1.0"
    refined["visual_pass"] = {
        "stage": "v6",
        "strategy": "gemini-editable-hybrid-complex-pages",
    }
    return refined, plan_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Gemini editable hybrid assets and layout schemas for complex pages.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--output-spec-file", required=True)
    parser.add_argument("--assets-dir", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--image-config-file", required=True)
    parser.add_argument("--audit-file")
    parser.add_argument("--only-failed", action="store_true")
    parser.add_argument("--regenerate-assets", action="store_true")
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    audit = read_json(Path(args.audit_file)) if args.audit_file else None
    assets_dir = Path(args.assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    target_ids = target_slide_ids(spec, audit, args.only_failed)
    refined, plan_items = update_spec(
        spec=spec,
        config_file=Path(args.image_config_file),
        assets_dir=assets_dir,
        target_ids=target_ids,
        regenerate=args.regenerate_assets,
    )
    write_json(Path(args.output_spec_file), refined)
    write_json(
        Path(args.plan_file),
        {
            "schema_version": "0.1",
            "stage": "v6",
            "strategy": "gemini-editable-hybrid",
            "target_slide_ids": sorted(target_ids),
            "regenerate_assets": bool(args.regenerate_assets),
            "assets": plan_items,
        },
    )


if __name__ == "__main__":
    main()
