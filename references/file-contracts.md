# File Contracts

## extraction.json
- `document_title`
- `source_files[]`
- `headings[]`
- `figure_mentions[]`
- `table_mentions[]`
- `chunks[]`

## analysis-brief.json
- `research_problem`
- `method_summary`
- `results_summary`
- `conclusion_summary`
- `contributions[]`
- `limitations[]`
- `narrative_arc[]`
- `evidence_map`
- `open_questions[]`
- `risk_flags[]`

## deck-spec.json
- `title`
- `template`
- `slides[]`
- per-slide `layout`, `title`, `bullets`, `notes`

The scaffold prioritizes reviewability over completeness. Missing evidence should remain explicit.
