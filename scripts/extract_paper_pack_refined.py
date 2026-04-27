from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import fitz
from docx import Document

from common_io import write_json

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
FIGURE_RE = re.compile(r"\bFigure\s+\d+|\bFig\.\s*\d+", re.IGNORECASE)
TABLE_RE = re.compile(r"\bTable\s+\d+", re.IGNORECASE)
PAGE_NUMBER_RE = re.compile(r"^(page\s+)?\d+$", re.IGNORECASE)
NOISE_LINE_RE = re.compile(
    r"^(downloaded from|guest \(guest\) ip:|on:\s|www\.annualreviews\.org|https?://doi\.org/|doi:|copyright|all rights reserved|annu\.\s+rev\.|intensive care med\b)",
    re.IGNORECASE,
)
ABSTRACT_LABEL_RE = re.compile(
    r"(?i)\b(purpose|background|objective|aims?|methods?|patients and methods|study design|results?|findings|conclusions?|interpretation|目的|背景|研究目的|研究背景|方法|研究方法|结果|研究结果|结论|研究结论)\s*[:：]"
)

SECTION_PATTERNS = {
    "abstract": [
        re.compile(r"^abstract$", re.IGNORECASE),
        re.compile(r"^summary$", re.IGNORECASE),
        re.compile(r"^摘要$"),
        re.compile(r"^中文摘要$"),
        re.compile(r"^英文摘要$"),
    ],
    "background": [
        re.compile(r"^introduction$", re.IGNORECASE),
        re.compile(r"^background$", re.IGNORECASE),
        re.compile(r"^overview$", re.IGNORECASE),
        re.compile(r"^引言$"),
        re.compile(r"^绪论$"),
        re.compile(r"^研究背景$"),
        re.compile(r"^前言$"),
    ],
    "method": [
        re.compile(r"^(materials and )?methods?$", re.IGNORECASE),
        re.compile(r"^patients and methods$", re.IGNORECASE),
        re.compile(r"^study design$", re.IGNORECASE),
        re.compile(r"^methodology$", re.IGNORECASE),
        re.compile(r"^方法$"),
        re.compile(r"^研究方法$"),
        re.compile(r"^实验方法$"),
        re.compile(r"^材料与方法$"),
        re.compile(r"^研究设计$"),
    ],
    "results": [
        re.compile(r"^results?$", re.IGNORECASE),
        re.compile(r"^findings$", re.IGNORECASE),
        re.compile(r"^outcomes?$", re.IGNORECASE),
        re.compile(r"^结果$"),
        re.compile(r"^研究结果$"),
        re.compile(r"^实验结果$"),
    ],
    "discussion": [
        re.compile(r"^discussion$", re.IGNORECASE),
        re.compile(r"^discussion and conclusions?$", re.IGNORECASE),
        re.compile(r"^讨论$"),
        re.compile(r"^讨论与结论$"),
    ],
    "conclusion": [
        re.compile(r"^conclusions?$", re.IGNORECASE),
        re.compile(r"^conclusion and perspectives?$", re.IGNORECASE),
        re.compile(r"^future work$", re.IGNORECASE),
        re.compile(r"^limitations?$", re.IGNORECASE),
        re.compile(r"^结论$"),
        re.compile(r"^结论与展望$"),
        re.compile(r"^研究结论$"),
        re.compile(r"^不足与展望$"),
        re.compile(r"^局限性$"),
    ],
    "references": [
        re.compile(r"^references$", re.IGNORECASE),
        re.compile(r"^bibliography$", re.IGNORECASE),
        re.compile(r"^参考文献$"),
    ],
}

IGNORE_HEADING_PATTERNS = [
    re.compile(r"^acknowledg?ments?$", re.IGNORECASE),
    re.compile(r"^funding$", re.IGNORECASE),
    re.compile(r"^author contributions?$", re.IGNORECASE),
    re.compile(r"^data availability$", re.IGNORECASE),
    re.compile(r"^declarations?$", re.IGNORECASE),
    re.compile(r"^conflicts? of interest$", re.IGNORECASE),
    re.compile(r"^statement on ethics approval$", re.IGNORECASE),
    re.compile(r"^consent for publication$", re.IGNORECASE),
    re.compile(r"^publisher'?s note$", re.IGNORECASE),
    re.compile(r"^supplementary information$", re.IGNORECASE),
    re.compile(r"^keywords$", re.IGNORECASE),
    re.compile(r"^致谢$"),
    re.compile(r"^基金项目$"),
    re.compile(r"^作者贡献$"),
    re.compile(r"^数据可得性$"),
    re.compile(r"^利益冲突$"),
    re.compile(r"^伦理声明$"),
    re.compile(r"^关键词$"),
]

ABSTRACT_LABEL_TO_HINT = {
    "purpose": "background",
    "background": "background",
    "objective": "background",
    "aim": "background",
    "aims": "background",
    "methods": "method",
    "method": "method",
    "patients and methods": "method",
    "study design": "method",
    "results": "results",
    "result": "results",
    "findings": "results",
    "conclusions": "conclusion",
    "conclusion": "conclusion",
    "interpretation": "conclusion",
    "目的": "background",
    "背景": "background",
    "研究目的": "background",
    "研究背景": "background",
    "方法": "method",
    "研究方法": "method",
    "结果": "results",
    "研究结果": "results",
    "结论": "conclusion",
    "研究结论": "conclusion",
}


def normalize_line(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "\u2009": " ",
        "\u202f": " ",
        "\u3000": " ",
        "\u200b": "",
        "\u00ad": "",
        "\ufeff": "",
        "聽": " ",
        "–": "-",
        "—": "-",
        "−": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    text = re.sub(r"(?<=\w)-\s*\n(?=\w)", "", text.replace("\r\n", "\n"))
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        if PAGE_NUMBER_RE.match(line):
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
    title = normalize_whitespace(clean_text(title))
    if len(title) < 8:
        return None
    if NOISE_LINE_RE.search(title):
        return None
    return title


def match_section_heading(text: str) -> str | None:
    candidate = normalize_whitespace(text).rstrip(":")
    if not candidate or len(candidate) > 80:
        return None
    if len(candidate.split()) > 8:
        return None
    if candidate.endswith("."):
        return None
    for label, patterns in SECTION_PATTERNS.items():
        if any(pattern.match(candidate) for pattern in patterns):
            if label == "discussion":
                return "conclusion"
            return label
    return None


def infer_keyword_section(text: str) -> str:
    lowered = normalize_whitespace(text).lower()
    if any(
        token in lowered
        for token in (
            "we conducted",
            "we enrolled",
            "we included",
            "flow cytometry",
            "cohort study",
            "statistical analysis",
            "patients were",
            "研究对象",
            "纳入",
            "方法",
            "研究方法",
            "流式细胞术",
        )
    ):
        return "method"
    if any(
        token in lowered
        for token in (
            "significantly associated",
            "mortality",
            "icu-acquired infection",
            "kaplan",
            "auc",
            "trajectory cluster",
            "odds ratio",
            "hazard ratio",
            "显著相关",
            "差异有统计学意义",
            "死亡率",
            "感染",
            "实验结果",
        )
    ):
        return "results"
    if any(
        token in lowered
        for token in (
            "this study confirms",
            "collectively",
            "in conclusion",
            "these findings suggest",
            "taken together",
            "future investigation",
            "limitation",
            "本研究表明",
            "提示",
            "结论",
            "局限性",
            "展望",
        )
    ):
        return "conclusion"
    if any(
        token in lowered
        for token in (
            "sepsis",
            "burden",
            "however",
            "despite",
            "background",
            "immunosuppression",
            "clinical practice",
            "研究背景",
            "脓毒症",
            "免疫抑制",
            "临床问题",
        )
    ):
        return "background"
    return "body"


def looks_like_reference_block(text: str) -> bool:
    lowered = text.lower()
    if re.match(r"^\d+\.\s+[A-Z][A-Za-z\-']+", text):
        return True
    if re.match(r"^\[[0-9]+\]", text):
        return True
    if " et al" in lowered and len(re.findall(r"\b(19|20)\d{2}\b", text)) >= 2:
        return True
    if " doi" in lowered and len(re.findall(r"\b(19|20)\d{2}\b", text)) >= 1:
        return True
    if len(re.findall(r"\[[0-9,\-\s]+\]", text)) >= 3:
        return True
    return False


def looks_like_front_matter(text: str) -> bool:
    lowered = normalize_whitespace(text).lower()
    if any(token in lowered for token in ("email:", "full author information", "the author(s)", "department of", "university", "hospital")):
        return True
    if lowered.startswith("dear editor"):
        return False
    if lowered.count(",") >= 4 and re.search(r"\d", lowered):
        return True
    return False


def looks_like_back_matter(text: str) -> bool:
    candidate = normalize_whitespace(text).rstrip(":")
    if any(pattern.match(candidate) for pattern in IGNORE_HEADING_PATTERNS):
        return True
    lowered = candidate.lower()
    return any(
        lowered.startswith(prefix)
        for prefix in (
            "funding ",
            "acknowledg",
            "author contributions ",
            "data availability ",
            "conflicts of interest ",
            "statement on ethics approval ",
            "consent for publication ",
            "publisher",
            "supplementary information ",
            "received:",
            "基金项目",
            "作者贡献",
            "数据可得性",
            "利益冲突",
            "伦理声明",
            "致谢",
        )
    )


def looks_like_table_row(text: str) -> bool:
    normalized = normalize_whitespace(text)
    lowered = normalized.lower()
    if lowered.startswith(("table ", "fig.", "figure ", "(see figure", "publisher", "acknowledg", "表", "图", "致谢")):
        return True
    if lowered.startswith(("p value:", "a proportion ", "b source control ", "注：", "说明：")):
        return True
    digit_count = sum(character.isdigit() for character in normalized)
    has_stat_tokens = any(token in normalized.lower() for token in ("p value", "median", "q1", "q3", "n =", "(%)"))
    if digit_count >= 6 and has_stat_tokens:
        return True
    if digit_count >= 8 and len(normalized.split()) <= 24:
        return True
    return False


def split_into_paragraphs(text: str) -> list[str]:
    if "\n\n" in text:
        parts = [clean_text(part) for part in re.split(r"\n\s*\n", text)]
        return [part for part in parts if part]

    paragraphs: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            if current:
                paragraphs.append(clean_text("\n".join(current)))
                current = []
            continue
        if match_section_heading(line):
            if current:
                paragraphs.append(clean_text("\n".join(current)))
                current = []
            paragraphs.append(line)
            continue
        current.append(line)
    if current:
        paragraphs.append(clean_text("\n".join(current)))
    return [paragraph for paragraph in paragraphs if paragraph]


def infer_title_from_objective(paragraphs: list[str]) -> str | None:
    for paragraph in paragraphs[:40]:
        text = normalize_whitespace(paragraph)
        if not text:
            continue
        if "本研究旨在" in text or "本研究目的" in text:
            match = re.search(r"(系统评价|评估)(.+?)的(临床疗效|疗效与用药安全性|疗效及机制)", text)
            if match:
                subject = match.group(2).strip(" ，,。；;")
                if subject:
                    return clean_title(f"{subject}的临床与机制研究")
    return None


def infer_title_from_paragraphs(paragraphs: list[str], fallback: str) -> str:
    derived_title = infer_title_from_objective(paragraphs)
    if derived_title:
        return derived_title

    candidates: list[str] = []
    for paragraph in paragraphs[:5]:
        before_abstract = re.split(r"(?i)\babstract\b|摘要", paragraph, maxsplit=1)[0]
        for raw_line in before_abstract.splitlines():
            line = normalize_line(raw_line).rstrip(":")
            lowered = line.lower()
            if not line or PAGE_NUMBER_RE.match(line):
                continue
            if NOISE_LINE_RE.search(line):
                continue
            if lowered in {"original", "scientific letter", "abstract", "keywords", "摘要", "关键词"}:
                continue
            if match_section_heading(line):
                if candidates:
                    return clean_title(" ".join(candidates)) or fallback
                continue
            if looks_like_front_matter(line):
                if candidates:
                    return clean_title(" ".join(candidates)) or fallback
                continue
            if len(line) < 8 or len(line) > 150:
                continue
            candidates.append(line)
            if len(" ".join(candidates)) >= 90 or len(candidates) >= 3:
                return clean_title(" ".join(candidates)) or fallback
    return clean_title(" ".join(candidates)) or fallback


def collect_margin_noise(doc: fitz.Document) -> set[str]:
    margin_counter: Counter[str] = Counter()
    for page in doc:
        blocks = page.get_text("blocks", sort=True)
        if not blocks:
            continue
        margin_blocks = blocks[:2] + blocks[-2:]
        for _, _, _, _, text, *_ in margin_blocks:
            for raw_line in text.splitlines():
                line = normalize_line(raw_line)
                if line and len(line) <= 120:
                    margin_counter[line.lower()] += 1
    return {line for line, count in margin_counter.items() if count >= 2}


def extract_pdf(path: Path) -> dict:
    with fitz.open(path) as doc:
        repeated_margin_lines = collect_margin_noise(doc)
        paragraphs: list[str] = []
        for page_index, page in enumerate(doc):
            blocks = page.get_text("blocks", sort=True)
            page_height = page.rect.height or 1
            for _, y0, _, y1, text, *_ in blocks:
                kept_lines: list[str] = []
                for raw_line in text.splitlines():
                    line = normalize_line(raw_line)
                    if not line:
                        continue
                    if page_index > 0 and line.lower() in repeated_margin_lines and (y0 < page_height * 0.12 or y1 > page_height * 0.88):
                        continue
                    kept_lines.append(line)
                if not kept_lines:
                    continue
                cleaned = clean_text("\n".join(kept_lines))
                if cleaned:
                    paragraphs.append(cleaned)
        joined_text = "\n\n".join(paragraphs)
        return {
            "text": joined_text,
            "paragraphs": paragraphs,
            "metadata_title": clean_title(doc.metadata.get("title")),
            "page_count": len(doc),
        }


def extract_docx(path: Path) -> dict:
    doc = Document(path)
    paragraphs = [clean_text(paragraph.text) for paragraph in doc.paragraphs]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    return {
        "text": "\n\n".join(paragraphs),
        "paragraphs": paragraphs,
        "metadata_title": None,
        "page_count": None,
    }


def extract_text(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".docx":
        return extract_docx(path)
    raw_text = path.read_text(encoding="utf-8")
    paragraphs = split_into_paragraphs(raw_text)
    return {
        "text": "\n\n".join(paragraphs),
        "paragraphs": paragraphs,
        "metadata_title": None,
        "page_count": None,
    }


def build_abstract_label_chunks(paragraphs: list[str], source_name: str, source_role: str, offset: int = 0) -> tuple[list[dict], set[int]]:
    chunks: list[dict] = []
    consumed_indexes: set[int] = set()
    next_index = offset + 1

    for paragraph_index, paragraph in enumerate(paragraphs[:6]):
        normalized = normalize_whitespace(paragraph)
        matches = list(ABSTRACT_LABEL_RE.finditer(normalized))
        if len(matches) < 2:
            continue
        consumed_indexes.add(paragraph_index)
        for match_index, match in enumerate(matches):
            label = match.group(1).lower()
            start = match.end()
            end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(normalized)
            body = normalize_whitespace(normalized[start:end])
            body = re.split(r"(?i)\bkeywords\s*[:：]|关键词\s*[:：]", body, maxsplit=1)[0].strip()
            if not body:
                continue
            section_hint = ABSTRACT_LABEL_TO_HINT.get(label, "body")
            chunks.append(
                {
                    "id": f"{Path(source_name).stem}-{next_index:03d}",
                    "source": source_name,
                    "source_role": source_role,
                    "kind": "abstract_label",
                    "section_label": "abstract",
                    "section_hint": section_hint,
                    "abstract_label": label,
                    "text": body[:2400],
                    "chars": len(body),
                }
            )
            next_index += 1
        break

    return chunks, consumed_indexes


def build_chunks(paragraphs: list[str], source_name: str, source_role: str) -> tuple[list[dict], list[str], list[str]]:
    chunks, consumed_indexes = build_abstract_label_chunks(paragraphs, source_name, source_role)
    headings: list[str] = []
    sections_found: list[str] = []
    next_index = len(chunks) + 1
    current_section: str | None = None
    in_references = False

    for paragraph_index, paragraph in enumerate(paragraphs):
        cleaned = clean_text(paragraph)
        if not cleaned or paragraph_index in consumed_indexes:
            continue

        if looks_like_back_matter(cleaned):
            current_section = None
            continue

        heading = match_section_heading(cleaned)
        if heading:
            headings.append(cleaned)
            sections_found.append(heading)
            current_section = heading
            if heading == "references":
                in_references = True
            continue

        if in_references or looks_like_reference_block(cleaned) or looks_like_front_matter(cleaned) or looks_like_back_matter(cleaned):
            continue

        section_hint = current_section if current_section and current_section != "abstract" else infer_keyword_section(cleaned)
        if section_hint == "references":
            continue

        normalized_text = normalize_whitespace(cleaned)
        if looks_like_table_row(normalized_text):
            continue
        if len(normalized_text) < 60 and section_hint not in {"results", "conclusion"}:
            continue

        chunks.append(
            {
                "id": f"{Path(source_name).stem}-{next_index:03d}",
                "source": source_name,
                "source_role": source_role,
                "kind": "body",
                "section_label": current_section or "",
                "section_hint": section_hint,
                "abstract_label": None,
                "text": normalized_text[:2400],
                "chars": len(normalized_text),
            }
        )
        next_index += 1

    deduped_sections = list(dict.fromkeys(section for section in sections_found if section))
    deduped_headings = list(dict.fromkeys(headings))
    return chunks, deduped_sections, deduped_headings


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
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))

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
        source_role = "primary" if path.name == primary_source or (not primary_source and not source_files) else "supporting"
        try:
            extracted = extract_text(path)
        except Exception as exc:
            notes.append({"level": "warning", "message": f"Failed to extract {path.name}: {exc}"})
            continue

        text = extracted["text"]
        paragraphs = extracted["paragraphs"]
        if not text or not paragraphs:
            notes.append({"level": "warning", "message": f"No text extracted from {path.name}"})
            continue

        title_guess = extracted.get("metadata_title") or infer_title_from_paragraphs(paragraphs, path.stem)
        if source_role == "primary":
            document_title = title_guess
        elif not document_title:
            document_title = title_guess

        source_chunks, sections_found, source_headings = build_chunks(paragraphs, path.name, source_role)
        chunks.extend(source_chunks)
        headings.extend({"source": path.name, "text": heading} for heading in source_headings[:20])

        for match in FIGURE_RE.finditer(text):
            figure_mentions.append({"source": path.name, "text": match.group(0)})
        for match in TABLE_RE.finditer(text):
            table_mentions.append({"source": path.name, "text": match.group(0)})

        source_files.append(
            {
                "path": str(path),
                "name": path.name,
                "role": source_role,
                "suffix": path.suffix.lower(),
                "chars": len(text),
                "paragraphs": len(paragraphs),
                "page_count": extracted.get("page_count"),
                "metadata_title": extracted.get("metadata_title"),
                "title_guess": title_guess,
                "sections_found": sections_found,
            }
        )

    payload = {
        "schema_version": "0.2",
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
    main()
