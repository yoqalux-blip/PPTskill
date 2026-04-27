from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz
from docx import Document

from common_io import write_json

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
HEADING_RE = re.compile(r"^(\d+(\.\d+)*[\s\-、.]*)?[\w\u4e00-\u9fff][^\n]{0,78}$")
FIGURE_RE = re.compile(r"(图\s*\d+|Figure\s+\d+)", re.IGNORECASE)
TABLE_RE = re.compile(r"(表\s*\d+|Table\s+\d+)", re.IGNORECASE)
NOISE_LINE_RE = re.compile(
    r"^(Downloaded from www\.annualreviews\.org|On:\s|Guest \(guest\) IP:|https?://doi\.org/|Intensive Care Med\s*\(|Annual Review of Physiology$)",
    re.IGNORECASE,
)


def extract_pdf(path: Path) -> str:
    doc = fitz.open(path)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def extract_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".docx":
        return extract_docx(path)
    return path.read_text(encoding="utf-8")


def split_chunks(text: str) -> list[str]:
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()][:200]


def clean_text(text: str) -> str:
    cleaned_lines = []
    for raw_line in text.replace("\r\n", "\n").replace("\u3000", " ").splitlines():
        line = raw_line.strip()
        if not line:
            cleaned_lines.append("")
            continue
        if NOISE_LINE_RE.search(line):
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def clean_title(title: str | None) -> str | None:
    if not title:
        return None
    title = clean_text(title).strip()
    if len(title) < 8:
        return None
    if title.lower().startswith("downloaded from"):
        return None
    return title


def section_hint(chunk: str) -> str:
    first_line = chunk.splitlines()[0] if chunk.splitlines() else chunk
    first_line_lower = first_line.lower()
    lowered = chunk.lower()
    if any(key in first_line for key in ("方法", "模型", "系统设计")) or "method" in first_line_lower:
        return "method"
    if any(key in first_line for key in ("摘要", "背景", "研究背景")) or "background" in first_line_lower:
        return "background"
    if any(key in first_line for key in ("实验", "结果", "评估")) or any(key in first_line_lower for key in ("experiment", "result", "evaluation")):
        return "results"
    if any(key in first_line for key in ("结论", "展望", "不足")) or any(key in first_line_lower for key in ("conclusion", "limitation", "future work")):
        return "conclusion"
    if any(key in chunk for key in ("方法", "模型", "系统设计")) or "method" in lowered:
        return "method"
    if any(key in chunk for key in ("摘要", "背景", "研究背景")) or "background" in lowered:
        return "background"
    if any(key in chunk for key in ("实验", "结果", "评估")) or any(key in lowered for key in ("experiment", "result", "evaluation")):
        return "results"
    if any(key in chunk for key in ("结论", "展望", "不足")) or any(key in lowered for key in ("conclusion", "limitation", "future work")):
        return "conclusion"
    return "body"


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured text from a paper-pack directory.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--scene", default="graduation-defense")
    parser.add_argument("--language", default="auto")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    manifest_path = input_dir / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    files = sorted(path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)
    primary_source = manifest.get("primary_source")
    if primary_source:
        files.sort(key=lambda path: (0 if path.name == primary_source else 1, path.name))
    if not files:
        raise SystemExit(f"No supported files found in {input_dir}")

    source_files = []
    headings = []
    figure_mentions = []
    table_mentions = []
    chunks = []
    notes = []
    document_title = None

    for path in files:
        try:
            text = extract_text(path)
        except Exception as exc:
            notes.append({"level": "warning", "message": f"Failed to extract {path.name}: {exc}"})
            continue

        text = clean_text(text)
        if not text:
            notes.append({"level": "warning", "message": f"No text extracted from {path.name}"})
            continue

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title_guess = lines[0][:120] if lines else path.stem
        if path.suffix.lower() == ".pdf":
            with fitz.open(path) as doc:
                title_guess = clean_title(doc.metadata.get("title")) or title_guess
        document_title = document_title or title_guess
        paragraphs = split_chunks(text)

        source_files.append(
            {
                "path": str(path),
                "name": path.name,
                "suffix": path.suffix.lower(),
                "chars": len(text),
                "paragraphs": len(paragraphs),
                "title_guess": title_guess,
            }
        )

        for line in lines[:80]:
            if HEADING_RE.match(line):
                headings.append({"source": path.name, "text": line})

        for match in FIGURE_RE.finditer(text):
            figure_mentions.append({"source": path.name, "text": match.group(0)})
        for match in TABLE_RE.finditer(text):
            table_mentions.append({"source": path.name, "text": match.group(0)})

        for index, chunk in enumerate(paragraphs, start=1):
            chunks.append(
                {
                    "id": f"{path.stem}-{index:03d}",
                    "source": path.name,
                    "section_hint": section_hint(chunk),
                    "text": chunk[:1800],
                    "chars": len(chunk),
                }
            )

    payload = {
        "schema_version": "0.1",
        "scene": manifest.get("scene", args.scene),
        "language": manifest.get("language", args.language),
        "input_dir": str(input_dir),
        "manifest": manifest,
        "document_title": document_title or input_dir.name,
        "source_files": source_files,
        "headings": headings[:120],
        "figure_mentions": figure_mentions[:60],
        "table_mentions": table_mentions[:60],
        "chunks": chunks,
        "notes": notes,
    }
    write_json(Path(args.output_file), payload)


if __name__ == "__main__":
    from extract_paper_pack_refined import main as refined_main

    refined_main()
