from __future__ import annotations

import argparse
from pathlib import Path

from common_io import read_json, write_json


def find_first_chunk(chunks: list[dict], hint: str, preferred_source: str | None = None) -> str:
    if preferred_source:
        for chunk in chunks:
            if chunk.get("source") == preferred_source and chunk.get("section_hint") == hint:
                return chunk.get("text", "")[:400]
    for chunk in chunks:
        if chunk.get("section_hint") == hint:
            return chunk.get("text", "")[:400]
    return ""


def gather_evidence(chunks: list[dict], hint: str, preferred_source: str | None = None) -> list[str]:
    preferred = []
    if preferred_source:
        preferred = [chunk["id"] for chunk in chunks if chunk.get("source") == preferred_source and chunk.get("section_hint") == hint][:4]
    if len(preferred) >= 4:
        return preferred
    fallback = [chunk["id"] for chunk in chunks if chunk.get("source") != preferred_source and chunk.get("section_hint") == hint][: max(0, 4 - len(preferred))]
    return preferred + fallback


def build_limitations(chunks: list[dict], preferred_source: str | None = None) -> list[str]:
    matches = []
    prioritized = chunks
    if preferred_source:
        prioritized = sorted(chunks, key=lambda chunk: 0 if chunk.get("source") == preferred_source else 1)
    for chunk in prioritized:
        text = chunk.get("text", "")
        if any(key in text for key in ("不足", "局限", "future work", "limitation", "展望")):
            matches.append(text[:180])
    return matches[:3] or ["Source does not clearly state limitations; Codex review required."]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a provisional analysis brief from extraction output.")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    extraction = read_json(Path(args.input_file))
    chunks = extraction.get("chunks", [])
    preferred_source = extraction.get("manifest", {}).get("primary_source")

    analysis = {
        "schema_version": "0.1",
        "title": extraction.get("document_title", "Untitled thesis"),
        "scene": extraction.get("scene", "graduation-defense"),
        "language": extraction.get("language", "auto"),
        "provisional": True,
        "review_required": True,
        "primary_source": preferred_source,
        "research_problem": find_first_chunk(chunks, "background", preferred_source) or "Research problem needs Codex review against the extracted source text.",
        "method_summary": find_first_chunk(chunks, "method", preferred_source) or "Method summary needs Codex review.",
        "results_summary": find_first_chunk(chunks, "results", preferred_source) or "Result evidence is incomplete in the current extraction; keep claims conservative.",
        "conclusion_summary": find_first_chunk(chunks, "conclusion", preferred_source) or "Conclusion section needs Codex review.",
        "contributions": [
            "Restate the core contribution with evidence from the thesis before finalizing the deck.",
            "Prefer concrete method/result claims over generic novelty language."
        ],
        "limitations": build_limitations(chunks, preferred_source),
        "narrative_arc": [
            "Why this problem matters",
            "What gap remains unresolved",
            "What the thesis proposes",
            "What evidence supports the proposal",
            "What the committee should remember"
        ],
        "evidence_map": {
            "background": gather_evidence(chunks, "background", preferred_source),
            "method": gather_evidence(chunks, "method", preferred_source),
            "results": gather_evidence(chunks, "results", preferred_source),
            "conclusion": gather_evidence(chunks, "conclusion", preferred_source)
        },
        "open_questions": [
            "Which single-sentence contribution should be emphasized on slide 2?",
            "Which experiment or figure is the strongest evidence for the core deck?",
            "Which limitation should be stated explicitly during the defense?"
        ],
        "risk_flags": [
            "Do not infer experimental superiority when extraction does not show comparative evidence.",
            "Do not claim novelty beyond what the thesis text supports."
        ]
    }
    write_json(Path(args.output_file), analysis)


if __name__ == "__main__":
    from analyze_extraction_refined import main as refined_main

    refined_main()
