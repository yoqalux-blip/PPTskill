from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_MAINLINE_FILES = [
    "scripts/export_image_pages_to_ppt.mjs",
    "scripts/normalize_pptx.ps1",
    "scripts/render_local_deck.mjs",
    "scripts/render_google_deck.py",
    "scripts/build_drawio_backend.py",
]

FORBIDDEN_SCRIPT_PATTERNS = [
    "PresentationFile.exportPptx",
    "pptxgen",
    "python-pptx",
    "New-Object -ComObject PowerPoint",
    "render_local_deck",
    "render_google",
    "drawio_backend",
]

REQUIRED_TEXT = {
    "SKILL.md": [
        "final PDF-only output",
        "`PDF` is the only production export",
        "Do not create PPT/PPTX from inside this skill",
    ],
    "agents/openai.yaml": [
        "export ordered images to PDF only",
        "Do not generate PPTX inside the skill",
    ],
    "references/current-skill-package.md": [
        "`PDF` is the only production export",
        "Native PPT/PPTX generation",
    ],
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(message: str) -> None:
    print(f"ROUTE LOCK FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def audit_files_absent() -> None:
    for relative in FORBIDDEN_MAINLINE_FILES:
        path = ROOT / relative
        if path.exists():
            fail(f"forbidden mainline file exists: {relative}")


def audit_package() -> None:
    package = json.loads(read_text(ROOT / "package.json"))
    scripts = package.get("scripts", {})
    dependencies = {
        **package.get("dependencies", {}),
        **package.get("devDependencies", {}),
        **package.get("optionalDependencies", {}),
    }

    forbidden_scripts = {"export:ppt", "ppt:normalize", "render:local", "drawio:build"}
    present = sorted(forbidden_scripts.intersection(scripts))
    if present:
        fail(f"forbidden npm scripts present: {', '.join(present)}")

    forbidden_deps = {"pptxgenjs", "@oai/artifact-tool", "python-pptx", "@drawio/mcp"}
    present_deps = sorted(forbidden_deps.intersection(dependencies))
    if present_deps:
        fail(f"forbidden production dependencies present: {', '.join(present_deps)}")

    if "export:pdf" not in scripts:
        fail("missing required npm script: export:pdf")


def audit_script_patterns() -> None:
    for path in sorted((ROOT / "scripts").glob("**/*")):
        if not path.is_file():
            continue
        if path.name == "audit_route_lock.py":
            continue
        if "__pycache__" in path.parts or path.suffix.lower() not in {".py", ".js", ".mjs", ".ps1"}:
            continue
        text = read_text(path)
        for pattern in FORBIDDEN_SCRIPT_PATTERNS:
            if pattern in text:
                fail(f"forbidden production pattern {pattern!r} in {path.relative_to(ROOT)}")


def audit_required_text() -> None:
    for relative, snippets in REQUIRED_TEXT.items():
        text = read_text(ROOT / relative)
        for snippet in snippets:
            if snippet not in text:
                fail(f"required route-lock text missing from {relative}: {snippet}")


def main() -> None:
    audit_files_absent()
    audit_package()
    audit_script_patterns()
    audit_required_text()
    print("ROUTE LOCK PASS: production route is image2-page-raster -> PDF only")


if __name__ == "__main__":
    main()
