from __future__ import annotations

import argparse
import copy
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance

from common_io import ensure_parent, read_json, write_json


def generate_image(
    config_file: Path,
    prompt: str,
    output_file: Path,
    request_dump: Path,
    response_dump: Path,
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
    subprocess.run(cmd, check=True)


def soften_background(input_file: Path, output_file: Path, white_mix: float = 0.72, saturation: float = 0.75) -> None:
    image = Image.open(input_file).convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    softened = Image.blend(image, white, white_mix)
    softened = ImageEnhance.Color(softened).enhance(saturation)
    alpha = Image.new("L", softened.size, 208)
    softened.putalpha(alpha)
    ensure_parent(output_file)
    softened.save(output_file)


def polish_hero(input_file: Path, output_file: Path, white_mix: float = 0.18, saturation: float = 0.92) -> None:
    image = Image.open(input_file).convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    polished = Image.blend(image, white, white_mix)
    polished = ImageEnhance.Color(polished).enhance(saturation)
    ensure_parent(output_file)
    polished.save(output_file)


def stage_chip(text: str, x: float, y: float, w: float = 2.2) -> dict[str, Any]:
    return {
        "type": "label",
        "style": "chip",
        "text": text,
        "x": x,
        "y": y,
        "w": w,
        "h": 0.42,
    }


def line_arrow(x: float, y: float, w: float) -> dict[str, Any]:
    return {
        "type": "line",
        "x": x,
        "y": y,
        "w": w,
        "h": 0.0,
        "color": "8A5A44",
        "pt": 1.8,
        "endArrowType": "triangle",
    }


def hero_card(text: str, x: float, y: float, w: float) -> dict[str, Any]:
    return {
        "type": "label",
        "style": "hero-card",
        "text": text,
        "x": x,
        "y": y,
        "w": w,
        "h": 0.62,
    }


def image_plan(spec: dict[str, Any]) -> list[dict[str, Any]]:
    title = spec.get("title", "doctoral-thesis")
    return [
        {
            "asset_id": "slide-09-route-plate",
            "slide_id": "slide-09",
            "kind": "background-plate",
            "prompt": (
                "Elegant scientific editorial background for a PhD defense slide, "
                "suggesting a translational research route from clinic to omics to animal to cell, "
                "warm ivory base, deep navy and muted copper accents, abstract scientific collage, "
                "soft layered panels, premium journal style, no text, no letters, no numbers, no arrows, "
                "wide 16:9 composition with calm negative space."
            ),
        },
        {
            "asset_id": "slide-31-evidence-plate",
            "slide_id": "slide-31",
            "kind": "background-plate",
            "prompt": (
                "Minimal scientific editorial background for an evidence-chain slide, "
                "subtle network motifs linking clinical evidence, omics, animal validation, and cell validation, "
                "warm ivory canvas, deep navy, muted copper, premium graphical-abstract feel, "
                "no text, no letters, no numbers, no arrows, wide 16:9 composition, quiet and refined."
            ),
        },
        {
            "asset_id": "slide-32-mechanism-triptych",
            "slide_id": "slide-32",
            "kind": "mechanism-hero",
            "prompt": (
                f"Scientific graphical abstract for the thesis '{title}'. "
                "Create a clean left-to-right triptych with no text: "
                "left panel shows severe bacterial lung infection and inflamed alveoli, "
                "middle panel shows intracellular pathway dysregulation with autophagy vesicles, mitochondria stress, "
                "and inflammasome-like cues, "
                "right panel shows therapeutic rescue with calmer alveoli and reduced inflammatory damage. "
                "Premium journal illustration style, realistic but stylized, very clean composition, "
                "no letters, no numbers, no labels, light background, suitable for overlaying editable Chinese labels in PPT."
            ),
        },
    ]


def update_v3_slides(spec: dict[str, Any], assets: dict[str, Path]) -> dict[str, Any]:
    refined = copy.deepcopy(spec)
    for slide in refined.get("slides", []):
        if slide.get("id") == "slide-09":
            slide["background_image"] = {
                "path": str(assets["slide-09-route-plate"]),
                "transparency": 0,
            }
            slide["v3_upgrade"] = {
                "focus": "structured-diagram-with-editorial-plate",
            }
        elif slide.get("id") == "slide-31":
            slide["background_image"] = {
                "path": str(assets["slide-31-evidence-plate"]),
                "transparency": 0,
            }
            slide["v3_upgrade"] = {
                "focus": "evidence-page-with-editorial-plate",
            }
        elif slide.get("id") == "slide-32":
            slide["layout_hint"] = "figure-full"
            slide["visual_type"] = "hybrid-mechanism"
            slide["figure"] = {
                "path": str(assets["slide-32-mechanism-triptych"]),
                "caption": "V3 混合机制图：无字审美底图 + PPT 可编辑标签与箭头。",
                "placement": "full",
                "overlays": [
                    stage_chip("感染触发", 1.25, 1.55, 2.15),
                    stage_chip("通路失衡", 5.15, 1.55, 2.15),
                    stage_chip("干预逆转", 9.05, 1.55, 2.15),
                    line_arrow(3.55, 3.22, 1.05),
                    line_arrow(7.45, 3.22, 1.05),
                    hero_card("HQQD 介入后，自噬与炎症调控趋于恢复", 4.45, 4.4, 4.45),
                ],
            }
            slide["takeaway"] = "这一页开始采用“无字机制底图 + 中文可编辑标签”的 V3 混合图路线。"
            slide["v3_upgrade"] = {
                "focus": "hybrid-mechanism-page",
            }
    refined["schema_version"] = "0.6"
    refined["visual_pass"] = {
        "stage": "v3",
        "strategy": "hybrid-raster-plus-editable-overlays",
    }
    return refined


def main() -> None:
    parser = argparse.ArgumentParser(description="Build V3 visual assets and slide overrides for selected review pages.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--output-spec-file", required=True)
    parser.add_argument("--assets-dir", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--image-config-file", required=True)
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    assets_dir = Path(args.assets_dir)
    config_file = Path(args.image_config_file)
    assets_dir.mkdir(parents=True, exist_ok=True)

    plan_items = image_plan(spec)
    resolved_assets: dict[str, Path] = {}
    emitted_plan: list[dict[str, Any]] = []

    for item in plan_items:
        raw_path = assets_dir / f"{item['asset_id']}-raw.png"
        final_path = assets_dir / f"{item['asset_id']}.png"
        request_dump = assets_dir / f"{item['asset_id']}-request.json"
        response_dump = assets_dir / f"{item['asset_id']}-response.json"

        generate_image(config_file, item["prompt"], raw_path, request_dump, response_dump)

        if item["kind"] == "background-plate":
            soften_background(raw_path, final_path)
        else:
            polish_hero(raw_path, final_path)

        resolved_assets[item["asset_id"]] = final_path.resolve()
        emitted_plan.append(
            {
                "asset_id": item["asset_id"],
                "slide_id": item["slide_id"],
                "kind": item["kind"],
                "final_path": str(final_path.resolve()),
                "request_dump": str(request_dump.resolve()),
                "response_dump": str(response_dump.resolve()),
            }
        )

    refined = update_v3_slides(spec, resolved_assets)
    write_json(Path(args.output_spec_file), refined)
    write_json(
        Path(args.plan_file),
        {
            "schema_version": "0.1",
            "stage": "v3",
            "assets": emitted_plan,
        },
    )


if __name__ == "__main__":
    main()
