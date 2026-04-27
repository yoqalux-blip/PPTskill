from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


def run_optional(command: list[str], cwd: Path) -> None:
    try:
        run(command, cwd)
    except subprocess.CalledProcessError as exc:
        print(f"[warn] Optional step failed and was skipped: {exc}", file=sys.stderr)


def normalize_pptx(input_file: Path, output_file: Path, cwd: Path) -> None:
    if os.name != "nt":
        if input_file != output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            input_file.replace(output_file)
        return

    try:
        run(
            [
                "powershell",
                "-ExecutionPolicy",
                "ByPass",
                "-File",
                str((cwd / "scripts" / "normalize_pptx.ps1").resolve()),
                "-InputPpt",
                str(input_file.resolve()),
                "-OutputPpt",
                str(output_file.resolve()),
            ],
            cwd,
        )
        if input_file.exists() and input_file != output_file:
            input_file.unlink(missing_ok=True)
    except subprocess.CalledProcessError as exc:
        print(f"[warn] PPT normalization failed and raw output was kept: {exc}", file=sys.stderr)
        if input_file != output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            if output_file.exists():
                output_file.unlink()
            input_file.replace(output_file)


def render_local_deck(renderer: str, spec_file: Path, template_file: Path, output_file: Path, cwd: Path, optional: bool = False) -> None:
    raw_output = output_file.with_name(f"{output_file.stem}.raw{output_file.suffix}")
    command = [
        "node",
        str((cwd / "scripts" / renderer).resolve()),
        "--spec-file",
        str(spec_file.resolve()),
        "--template-file",
        str(template_file.resolve()),
        "--output-file",
        str(raw_output.resolve()),
    ]
    if optional:
        run_optional(command, cwd)
        if not raw_output.exists():
            return
    else:
        run(command, cwd)
    normalize_pptx(raw_output, output_file, cwd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the scaffold smoke pipeline.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--template", default="academic-elegance")
    parser.add_argument("--mode", default="local", choices=["local", "google"])
    parser.add_argument("--image-config-file", help="Optional local config for the V3/V4/V5 image backend stages.")
    parser.add_argument("--with-drawio-drafts", action="store_true", help="Generate draw.io drafts for route/design/evidence pages.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    extraction = work_dir / "extraction.json"
    analysis = work_dir / "analysis-brief.json"
    presentation = work_dir / "presentation-brief.json"
    outline = work_dir / "deck-outline.md"
    spec = work_dir / "deck-spec.json"
    outline_v1 = work_dir / "deck-outline-v1.md"
    spec_v1 = work_dir / "deck-spec-v1.json"
    review_v1 = work_dir / "deck-review-v1.md"
    spec_v2 = work_dir / "deck-spec-v2.json"
    visual_plan_v2 = work_dir / "visual-assets-plan-v2.json"
    visual_review_v2 = work_dir / "visual-review-v2.md"
    figures_v2 = work_dir / "figures-v2"
    spec_v3 = work_dir / "deck-spec-v3.json"
    visual_plan_v3 = work_dir / "visual-assets-plan-v3.json"
    figures_v3 = work_dir / "figures-v3"
    spec_v4 = work_dir / "deck-spec-v4.json"
    visual_plan_v4 = work_dir / "visual-assets-plan-v4.json"
    figures_v4 = work_dir / "figures-v4"
    spec_v5 = work_dir / "deck-spec-v5.json"
    visual_plan_v5 = work_dir / "visual-assets-plan-v5.json"
    spec_v6 = work_dir / "deck-spec-v6.json"
    visual_plan_v6 = work_dir / "visual-assets-plan-v6.json"
    figures_v6 = work_dir / "figures-v6"
    drawio_dir = work_dir / "drawio-drafts"
    drawio_spec = work_dir / "deck-spec-drawio.json"
    notes = work_dir / "speaker-notes.md"
    qa = work_dir / "defense-qa.md"
    template_file = (root / "assets" / "templates" / args.template / "template.json").resolve()

    run([sys.executable, str(root / "scripts" / "extract_paper_pack.py"), "--input-dir", str(Path(args.input_dir).resolve()), "--output-file", str(extraction.resolve())], root)
    run([sys.executable, str(root / "scripts" / "analyze_extraction.py"), "--input-file", str(extraction.resolve()), "--output-file", str(analysis.resolve())], root)
    run([
        sys.executable,
        str(root / "scripts" / "rewrite_presentation_brief.py"),
        "--analysis-file", str(analysis.resolve()),
        "--extraction-file", str(extraction.resolve()),
        "--output-file", str(presentation.resolve()),
        "--presentation-language", "zh-CN"
    ], root)
    run([
        sys.executable,
        str(root / "scripts" / "spec_outline.py"),
        "--analysis-file", str(presentation.resolve()),
        "--extraction-file", str(extraction.resolve()),
        "--outline-file", str(outline.resolve()),
        "--spec-file", str(spec.resolve()),
        "--notes-file", str(notes.resolve()),
        "--qa-file", str(qa.resolve()),
        "--template", args.template
    ], root)
    run([
        sys.executable,
        str(root / "scripts" / "refine_deck_spec.py"),
        "--spec-file", str(spec.resolve()),
        "--brief-file", str(presentation.resolve()),
        "--extraction-file", str(extraction.resolve()),
        "--output-file", str(spec_v1.resolve()),
        "--report-file", str(review_v1.resolve()),
        "--outline-file", str(outline_v1.resolve())
    ], root)
    run([
        sys.executable,
        str(root / "scripts" / "build_visual_package.py"),
        "--spec-file", str(spec_v1.resolve()),
        "--brief-file", str(presentation.resolve()),
        "--template-file", str((root / "assets" / "templates" / args.template / "template.json").resolve()),
        "--output-spec-file", str(spec_v2.resolve()),
        "--assets-dir", str(figures_v2.resolve()),
        "--plan-file", str(visual_plan_v2.resolve())
    ], root)
    run([
        sys.executable,
        str(root / "scripts" / "review_visual_system.py"),
        "--spec-file", str(spec_v2.resolve()),
        "--plan-file", str(visual_plan_v2.resolve()),
        "--output-file", str(visual_review_v2.resolve())
    ], root)

    if args.image_config_file:
        run([
            sys.executable,
            str(root / "scripts" / "build_visual_package_v3.py"),
            "--spec-file", str(spec_v2.resolve()),
            "--output-spec-file", str(spec_v3.resolve()),
            "--assets-dir", str(figures_v3.resolve()),
            "--plan-file", str(visual_plan_v3.resolve()),
            "--image-config-file", str(Path(args.image_config_file).resolve())
        ], root)
        run([
            sys.executable,
            str(root / "scripts" / "build_visual_package_v4.py"),
            "--spec-file", str(spec_v2.resolve()),
            "--output-spec-file", str(spec_v4.resolve()),
            "--assets-dir", str(figures_v4.resolve()),
            "--plan-file", str(visual_plan_v4.resolve()),
            "--image-config-file", str(Path(args.image_config_file).resolve())
        ], root)
        run([
            sys.executable,
            str(root / "scripts" / "build_visual_package_v5_dense.py"),
            "--spec-file", str(spec_v4.resolve()),
            "--output-spec-file", str(spec_v5.resolve()),
            "--plan-file", str(visual_plan_v5.resolve())
        ], root)

    if args.with_drawio_drafts:
        drawio_source = spec_v5 if spec_v5.exists() else spec_v2
        drawio_spec = work_dir / "deck-spec-drawio.json"
        run([
            sys.executable,
            str(root / "scripts" / "build_drawio_backend.py"),
            "--spec-file", str(drawio_source.resolve()),
            "--output-dir", str(drawio_dir.resolve()),
            "--output-spec-file", str(drawio_spec.resolve())
        ], root)

    if args.mode == "local":
        render_local_deck("render_local_deck.mjs", spec.resolve(), template_file, (work_dir / "final-deck.pptx").resolve(), root, optional=True)
        render_local_deck("render_local_deck.mjs", spec_v1.resolve(), template_file, (work_dir / "final-deck-v1.pptx").resolve(), root, optional=True)
        render_local_deck("render_local_deck_v2.mjs", spec_v2.resolve(), template_file, (work_dir / "final-deck-v2.pptx").resolve(), root)
        if args.image_config_file:
            render_local_deck("render_local_deck_v3.mjs", spec_v3.resolve(), template_file, (work_dir / "final-deck-v3-review.pptx").resolve(), root)
            render_local_deck("render_local_deck_v4.mjs", spec_v4.resolve(), template_file, (work_dir / "final-deck-v4-review.pptx").resolve(), root)
            v5_render_spec = drawio_spec if drawio_spec.exists() else spec_v5
            render_local_deck("render_local_deck_v5.mjs", v5_render_spec.resolve(), template_file, (work_dir / "final-deck-v5-review.pptx").resolve(), root)
            gemini_source = v5_render_spec if v5_render_spec.exists() else spec_v5
            run([
                sys.executable,
                str(root / "scripts" / "build_visual_package_v6_gemini_hybrid.py"),
                "--spec-file", str(gemini_source.resolve()),
                "--output-spec-file", str(spec_v6.resolve()),
                "--assets-dir", str(figures_v6.resolve()),
                "--plan-file", str(visual_plan_v6.resolve()),
                "--image-config-file", str(Path(args.image_config_file).resolve())
            ], root)
            render_local_deck("render_local_deck_v5.mjs", spec_v6.resolve(), template_file, (work_dir / "final-deck-v6-hybrid-review.pptx").resolve(), root)
    else:
        run([
            sys.executable,
            str(root / "scripts" / "render_google_deck.py"),
            "--spec-file", str(spec_v2.resolve()),
            "--template", args.template,
            "--output-file", str((work_dir / "google-render-plan.json").resolve())
        ], root)


if __name__ == "__main__":
    main()
