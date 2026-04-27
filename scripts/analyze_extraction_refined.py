from __future__ import annotations

import argparse
import re
from pathlib import Path

from common_io import read_json, write_json

PRIMARY_ONLY_SECTIONS = {"method", "results", "conclusion", "limitations"}
SECTION_HINTS = {
    "background": {"background", "body"},
    "method": {"method"},
    "results": {"results"},
    "conclusion": {"conclusion"},
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clip(text: str, limit: int = 420) -> str:
    text = normalize_whitespace(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def looks_like_reference(text: str) -> bool:
    lowered = text.lower()
    if re.match(r"^\d+\.\s+[A-Z][A-Za-z\-']+", text):
        return True
    if " et al" in lowered and len(re.findall(r"\b(19|20)\d{2}\b", text)) >= 2:
        return True
    if len(re.findall(r"\[[0-9,\-\s]+\]", text)) >= 3:
        return True
    return False


def score_chunk(chunk: dict, target: str, primary_source: str | None) -> int:
    text = normalize_whitespace(chunk.get("text", ""))
    section_hint = chunk.get("section_hint", "")
    section_label = chunk.get("section_label", "")
    source = chunk.get("source")
    source_role = chunk.get("source_role")
    kind = chunk.get("kind")
    abstract_label = (chunk.get("abstract_label") or "").lower()

    if not text or looks_like_reference(text):
        return -10_000

    score = 0
    if primary_source and source == primary_source:
        score += 80
    elif source_role == "primary":
        score += 60
    else:
        score += 5

    if target in PRIMARY_ONLY_SECTIONS and primary_source and source != primary_source:
        score -= 70

    if section_hint == target:
        score += 50
    elif section_hint in SECTION_HINTS.get(target, set()):
        score += 20

    if kind == "abstract_label":
        score += 25
    if abstract_label:
        if target == "background" and abstract_label in {"purpose", "background", "objective", "aim", "aims"}:
            score += 25
        if target == "method" and abstract_label in {"method", "methods", "patients and methods", "study design"}:
            score += 25
        if target == "results" and abstract_label in {"result", "results", "findings"}:
            score += 25
        if target == "conclusion" and abstract_label in {"conclusion", "conclusions", "interpretation"}:
            score += 25

    lowered = text.lower()
    if target == "background" and any(token in lowered for token in ("however", "despite", "burden", "critical", "immunosuppression")):
        score += 10
    if target == "method" and any(token in lowered for token in ("cohort", "flow cytometry", "measuring", "we conducted", "we included")):
        score += 12
    if target == "results" and any(token in lowered for token in ("associated", "significant", "mortality", "infection", "auc", "cluster")):
        score += 12
    if target == "conclusion" and any(token in lowered for token in ("this study confirms", "suggests", "collectively", "identifying", "robust enrichment biomarker")):
        score += 12

    if section_label == "abstract":
        score += 8
    if len(text) < 80:
        score -= 15
    if len(text) > 900:
        score -= 8

    return score


def select_best_chunk(chunks: list[dict], target: str, primary_source: str | None, allow_supporting: bool = False) -> dict | None:
    best_chunk = None
    best_score = -10_000
    for chunk in chunks:
        if not allow_supporting and target in PRIMARY_ONLY_SECTIONS and primary_source and chunk.get("source") != primary_source:
            continue
        score = score_chunk(chunk, target, primary_source)
        if score > best_score:
            best_score = score
            best_chunk = chunk
    if best_score < 20:
        return None
    return best_chunk


def gather_evidence(chunks: list[dict], target: str, primary_source: str | None, allow_supporting: bool = False, limit: int = 4) -> list[str]:
    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        if not allow_supporting and target in PRIMARY_ONLY_SECTIONS and primary_source and chunk.get("source") != primary_source:
            continue
        score = score_chunk(chunk, target, primary_source)
        if score >= 20:
            scored.append((score, chunk["id"]))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk_id for _, chunk_id in scored[:limit]]


def build_limitations(chunks: list[dict], primary_source: str | None) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for chunk in chunks:
        if primary_source and chunk.get("source") != primary_source:
            continue
        text = normalize_whitespace(chunk.get("text", ""))
        lowered = text.lower()
        score = 0
        if any(token in lowered for token in ("limitation", "future work", "further studies", "further investigation")):
            score += 40
        if "observational" in lowered and any(token in lowered for token in ("association", "causal", "cannot")):
            score += 28
        if any(token in lowered for token in ("single-center", "single centre")):
            score += 24
        if any(token in lowered for token in ("not captured", "does not fully overlap", "warrant further", "cannot")):
            score += 22
        if chunk.get("section_hint") == "conclusion":
            score += 10
        if score >= 25:
            candidates.append((score, clip(text, 220)))
    if not candidates:
        return ["Primary paper does not state limitations clearly in extraction; present the study as observational and avoid causal overclaiming."]
    candidates.sort(key=lambda item: -item[0])
    deduped = list(dict.fromkeys(text for _, text in candidates))
    return deduped[:3]


def supporting_context(extraction: dict, chunks: list[dict], primary_source: str | None) -> list[str]:
    source_files = extraction.get("source_files", [])
    contexts: list[str] = []
    for source in source_files:
        if source.get("name") == primary_source:
            continue
        title = source.get("title_guess") or source.get("metadata_title") or source.get("name")
        contexts.append(f"Supporting source: {title}")
    supporting_background = [
        chunk["id"]
        for chunk in sorted(
            (chunk for chunk in chunks if chunk.get("source") != primary_source),
            key=lambda item: score_chunk(item, "background", None),
            reverse=True,
        )
        if score_chunk(chunk, "background", None) >= 20
    ][:2]
    if supporting_background:
        contexts.append(f"Supporting evidence chunks: {', '.join(supporting_background)}")
    return contexts[:3]


def build_summary(chunks: list[dict], target: str, primary_source: str | None, fallback: str, allow_supporting: bool = False) -> str:
    chunk = select_best_chunk(chunks, target, primary_source, allow_supporting=allow_supporting)
    if not chunk:
        return fallback
    return clip(chunk.get("text", ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a provisional analysis brief from extraction output.")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    extraction = read_json(Path(args.input_file))
    chunks = extraction.get("chunks", [])
    manifest = extraction.get("manifest", {})
    primary_source = manifest.get("primary_source")

    research_problem = build_summary(
        chunks,
        "background",
        primary_source,
        "Research problem needs Codex review against the primary source.",
        allow_supporting=True,
    )
    method_summary = build_summary(
        chunks,
        "method",
        primary_source,
        "Method summary needs Codex review from the primary source.",
    )
    results_summary = build_summary(
        chunks,
        "results",
        primary_source,
        "Result evidence is incomplete in the current extraction; keep claims conservative.",
    )
    conclusion_summary = build_summary(
        chunks,
        "conclusion",
        primary_source,
        "Conclusion summary needs Codex review from the primary source.",
    )

    evidence_map = {
        "background": gather_evidence(chunks, "background", primary_source, allow_supporting=True),
        "method": gather_evidence(chunks, "method", primary_source),
        "results": gather_evidence(chunks, "results", primary_source),
        "conclusion": gather_evidence(chunks, "conclusion", primary_source),
    }

    contributions = [
        "Keep the main claim anchored to the primary paper rather than the review article.",
        "Prefer cohort-derived evidence and outcome associations over broad immunology generalizations.",
    ]
    if "1023" in method_summary or "20-year" in method_summary:
        contributions[0] = "Frame the main contribution as a 20-year, 1023-patient real-world cohort analysis of mHLA-DR in septic shock."
    if "mortality" in results_summary.lower() or "infection" in results_summary.lower():
        contributions[1] = "Highlight the association between low mHLA-DR and adverse outcomes, especially mortality and ICU-acquired infection."

    analysis = {
        "schema_version": "0.2",
        "title": extraction.get("document_title", "Untitled thesis"),
        "scene": extraction.get("scene", "graduation-defense"),
        "language": extraction.get("language", "auto"),
        "provisional": True,
        "review_required": True,
        "primary_source": primary_source,
        "supporting_context": supporting_context(extraction, chunks, primary_source),
        "research_problem": research_problem,
        "method_summary": method_summary,
        "results_summary": results_summary,
        "conclusion_summary": conclusion_summary,
        "contributions": contributions,
        "limitations": build_limitations(chunks, primary_source),
        "narrative_arc": [
            "Why this clinical stratification problem matters",
            "What gap remains in identifying delayed sepsis immunosuppression",
            "How the primary study measures and analyzes mHLA-DR",
            "What outcome evidence is strongest in the cohort",
            "What limitation and take-home message the audience should retain",
        ],
        "evidence_map": evidence_map,
        "open_questions": [
            "Which single cohort figure best shows the prognostic value of low mHLA-DR?",
            "How much review context should stay in the deck versus the appendix?",
            "Which study limitation should be stated explicitly during the talk?",
        ],
        "risk_flags": [
            "Do not let supporting review material replace the primary paper's conclusion.",
            "Do not infer causality or treatment efficacy from observational association data alone.",
        ],
    }
    write_json(Path(args.output_file), analysis)


if __name__ == "__main__":
    main()
