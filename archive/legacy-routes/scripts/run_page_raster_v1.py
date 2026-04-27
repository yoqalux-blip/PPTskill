from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_TEMPLATE_PPTX = Path(r"C:\Users\joaqu\Desktop\文献汇报论文答辩（成都中医药大学）.pptx")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def normalize_pptx(input_file: Path, output_file: Path, root: Path) -> None:
    run(
        [
            "powershell",
            "-ExecutionPolicy",
            "ByPass",
            "-File",
            str((root / "scripts" / "normalize_pptx.ps1").resolve()),
            "-InputPpt",
            str(input_file.resolve()),
            "-OutputPpt",
            str(output_file.resolve()),
        ]
    )


def render_local(spec_file: Path, template_file: Path, output_file: Path, root: Path) -> None:
    raw_output = output_file.with_suffix(".raw.pptx")
    run(
        [
            "node",
            str((root / "scripts" / "render_local_deck_v5.mjs").resolve()),
            "--spec-file",
            str(spec_file.resolve()),
            "--template-file",
            str(template_file.resolve()),
            "--output-file",
            str(raw_output.resolve()),
        ]
    )
    normalize_pptx(raw_output, output_file, root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the V1 strict CDUTCM page-raster pipeline end to end.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--template-pptx", default=str(DEFAULT_TEMPLATE_PPTX))
    parser.add_argument("--image-config-file", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--slide-ids", nargs="*")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    work_dir = Path(args.work_dir).resolve()
    template_dir = work_dir / "template-profile"
    recipes_dir = work_dir / "page_recipe"
    assets_dir = work_dir / "page_assets"

    template_profile = template_dir / "template_profile.json"
    template_brief = template_dir / "template_style_brief.md"
    manifest_file = work_dir / "page_manifest.json"
    contract_spec = work_dir / "deck-spec-page-raster-contract.json"
    output_spec = work_dir / "deck-spec-page-raster-v1.json"
    review_file = work_dir / "page_raster_review.json"
    manual_file = work_dir / "manual-review-report.json"
    output_pptx = work_dir / "final-deck-page-raster-v1.pptx"
    template_file = root / "assets" / "templates" / "cdutcm-defense" / "template.json"

    run(
        [
            sys.executable,
            str((root / "scripts" / "build_template_profile.py").resolve()),
            "--template-pptx",
            str(Path(args.template_pptx).resolve()),
            "--work-dir",
            str(template_dir.resolve()),
            "--output-profile-file",
            str(template_profile.resolve()),
            "--output-brief-file",
            str(template_brief.resolve()),
        ]
    )

    contract_command = [
        sys.executable,
            str((root / "scripts" / "build_page_raster_contracts_v1.py").resolve()),
        "--spec-file",
        str(Path(args.spec_file).resolve()),
        "--template-profile-file",
        str(template_profile.resolve()),
        "--recipes-dir",
        str(recipes_dir.resolve()),
        "--output-manifest-file",
        str(manifest_file.resolve()),
        "--output-spec-file",
        str(contract_spec.resolve()),
    ]
    run(contract_command)

    asset_command = [
        sys.executable,
        str((root / "scripts" / "build_page_raster_assets_v1.py").resolve()),
        "--spec-file",
        str(contract_spec.resolve()),
        "--template-profile-file",
        str(template_profile.resolve()),
        "--template-style-brief-file",
        str(template_brief.resolve()),
        "--config-file",
        str(Path(args.image_config_file).resolve()),
        "--assets-dir",
        str(assets_dir.resolve()),
        "--output-spec-file",
        str(output_spec.resolve()),
        "--output-review-file",
        str(review_file.resolve()),
        "--output-manual-review-file",
        str(manual_file.resolve()),
    ]
    if args.slide_ids:
        asset_command.extend(["--slide-ids", *args.slide_ids])
    run(asset_command)

    render_local(output_spec, template_file, output_pptx, root)


if __name__ == "__main__":
    main()
