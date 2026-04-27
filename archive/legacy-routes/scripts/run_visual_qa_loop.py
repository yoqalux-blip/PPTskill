from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from common_io import read_json, write_json


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


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
    except subprocess.CalledProcessError:
        if input_file != output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            if output_file.exists():
                output_file.unlink()
            input_file.replace(output_file)


def render_and_normalize(renderer_file: str, spec_file: Path, template_file: Path, output_file: Path, cwd: Path) -> None:
    raw_output = output_file.with_name(f"{output_file.stem}.raw{output_file.suffix}")
    run(
        [
            "node",
            str((cwd / "scripts" / renderer_file).resolve()),
            "--spec-file",
            str(spec_file.resolve()),
            "--template-file",
            str(template_file.resolve()),
            "--output-file",
            str(raw_output.resolve()),
        ],
        cwd,
    )
    normalize_pptx(raw_output, output_file, cwd)


def failed_gemini_slides(spec_file: Path, audit: dict[str, object]) -> list[dict[str, object]]:
    failed_numbers = {
        item["slide_number"]
        for item in audit.get("slides", [])
        if item.get("issues")
    }
    spec = read_json(spec_file)
    slides: list[dict[str, object]] = []
    for idx, slide in enumerate(spec.get("slides", []), start=1):
        if idx in failed_numbers and slide.get("visual_route") == "gemini-editable-hybrid":
            slides.append(slide)
    return slides


def main() -> None:
    parser = argparse.ArgumentParser(description="Render, export, audit, repair, and rerender a deck until issues settle.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--template-file", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--renderer-file", default="render_local_deck_v5.mjs")
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--export-width", type=int, default=2560)
    parser.add_argument("--drawio-on-fail", action="store_true")
    parser.add_argument("--drawio-output-dir", help="Optional directory for draw.io escalation artifacts.")
    parser.add_argument("--gemini-image-config-file", help="Optional image config used to regenerate failed Gemini hybrid assets.")
    parser.add_argument("--gemini-builder-file", default="build_visual_package_v6_gemini_hybrid.py")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    current_spec = Path(args.spec_file).resolve()
    history: list[dict[str, object]] = []

    for iteration in range(1, args.iterations + 1):
        pptx_file = work_dir / f"iteration-{iteration}.pptx"
        slides_dir = work_dir / f"iteration-{iteration}-slides"
        audit_json = work_dir / f"iteration-{iteration}-audit.json"
        audit_md = work_dir / f"iteration-{iteration}-audit.md"

        render_and_normalize(
            args.renderer_file,
            Path(current_spec),
            Path(args.template_file).resolve(),
            pptx_file.resolve(),
            root,
        )
        run(
            [
                "powershell",
                "-ExecutionPolicy",
                "ByPass",
                "-File",
                str((root / "scripts" / "export_ppt_slides.ps1").resolve()),
                "-PptPath",
                str(pptx_file.resolve()),
                "-OutputDir",
                str(slides_dir.resolve()),
                "-Width",
                str(args.export_width),
            ],
            root,
        )
        run(
            [
                sys.executable,
                str((root / "scripts" / "audit_rendered_deck_v2.py").resolve()),
                "--pptx-file",
                str(pptx_file.resolve()),
                "--output-json",
                str(audit_json.resolve()),
                "--output-md",
                str(audit_md.resolve()),
                "--spec-file",
                str(current_spec),
            ],
            root,
        )

        audit = read_json(audit_json)
        history.append(
            {
                "iteration": iteration,
                "spec_file": str(current_spec),
                "pptx_file": str(pptx_file),
                "audit_file": str(audit_json),
                "summary": audit["summary"],
            }
        )

        gemini_failed = failed_gemini_slides(Path(current_spec), audit)

        if audit["summary"]["fail"] == 0:
            break

        if iteration < args.iterations and gemini_failed:
            next_spec = work_dir / f"iteration-{iteration + 1}-spec.json"
            needs_schema_repair = any(
                int(slide.get("gemini_hybrid", {}).get("qa_state", {}).get("schema_repair_count", 0)) < 1
                for slide in gemini_failed
            )
            needs_asset_regen = bool(args.gemini_image_config_file) and any(
                int(slide.get("gemini_hybrid", {}).get("qa_state", {}).get("asset_regeneration_count", 0)) < 1
                for slide in gemini_failed
            )

            if needs_schema_repair:
                run(
                    [
                        sys.executable,
                        str((root / "scripts" / "repair_from_visual_audit.py").resolve()),
                        "--spec-file",
                        str(current_spec),
                        "--audit-file",
                        str(audit_json.resolve()),
                        "--output-file",
                        str(next_spec.resolve()),
                    ],
                    root,
                )
                history[-1]["gemini_action"] = "schema-repair"
                current_spec = next_spec.resolve()
                continue

            if needs_asset_regen:
                gemini_plan = work_dir / f"iteration-{iteration + 1}-gemini-plan.json"
                gemini_assets = work_dir / f"iteration-{iteration + 1}-gemini-assets"
                run(
                    [
                        sys.executable,
                        str((root / "scripts" / args.gemini_builder_file).resolve()),
                        "--spec-file",
                        str(current_spec),
                        "--output-spec-file",
                        str(next_spec.resolve()),
                        "--assets-dir",
                        str(gemini_assets.resolve()),
                        "--plan-file",
                        str(gemini_plan.resolve()),
                        "--image-config-file",
                        str(Path(args.gemini_image_config_file).resolve()),
                        "--audit-file",
                        str(audit_json.resolve()),
                        "--only-failed",
                        "--regenerate-assets",
                    ],
                    root,
                )
                history[-1]["gemini_action"] = "asset-regeneration"
                history[-1]["gemini_plan"] = str(gemini_plan.resolve())
                current_spec = next_spec.resolve()
                continue

        if args.drawio_on_fail and audit["summary"]["fail"] > 0:
            drawio_dir = Path(args.drawio_output_dir).resolve() if args.drawio_output_dir else (work_dir / "drawio")
            iteration_drawio_dir = drawio_dir / f"iteration-{iteration}"
            drawio_spec = iteration_drawio_dir / "drawio-spec.json"
            run(
                [
                    sys.executable,
                    str((root / "scripts" / "build_drawio_backend.py").resolve()),
                    "--spec-file",
                    str(current_spec),
                    "--audit-file",
                    str(audit_json.resolve()),
                    "--output-dir",
                    str(iteration_drawio_dir.resolve()),
                    "--only-failed",
                    "--output-spec-file",
                    str(drawio_spec.resolve()),
                ],
                root,
            )
            history[-1]["drawio_manifest"] = str((iteration_drawio_dir / "drawio-manifest.json").resolve())
            history[-1]["drawio_spec"] = str(drawio_spec.resolve())

        if iteration < args.iterations:
            next_spec = work_dir / f"iteration-{iteration + 1}-spec.json"
            repair_source = Path(history[-1]["drawio_spec"]).resolve() if history[-1].get("drawio_spec") else current_spec
            run(
                [
                    sys.executable,
                    str((root / "scripts" / "repair_from_visual_audit.py").resolve()),
                    "--spec-file",
                    str(repair_source),
                    "--audit-file",
                    str(audit_json.resolve()),
                    "--output-file",
                    str(next_spec.resolve()),
                ],
                root,
            )
            current_spec = next_spec.resolve()

    write_json(work_dir / "visual-qa-loop-summary.json", {"history": history, "final_spec": str(current_spec)})


if __name__ == "__main__":
    main()
