---
name: paper-to-defense-ppt
description: Build defense-ready academic presentation workflows from thesis or project materials. Use when Codex needs to turn PDF or DOCX papers, graduation thesis drafts, research reports, abstracts, or defense requirements into a reviewable pipeline with extraction, analysis brief, deck outline, deck spec, fixed 35-page contracts, image2 full-page generation, and final PDF-only output for graduation defense or research talk scenarios.
---

# Overview

Use this skill to convert thesis materials into a structured, reviewable presentation workflow instead of jumping straight to slide generation. Treat Codex as the reasoning lead and the bundled scripts as deterministic helpers for extraction, file shaping, fixed page contracts, image-page generation, and PDF export.

## Locked Mainline

1. Prepare a `paper-pack` input directory.
2. Run extraction to create `extraction.json`.
3. Review and refine `analysis-brief.json` and `presentation-brief.json`.
4. Produce `deck-outline.md` and `deck-spec.json`.
5. Lock the final deck to `35` pages and build a strict `page_manifest.json` and `page_recipe/<slide-id>.json` contract for every generated page.
6. Generate ordered full-page review images with `image2`.
7. Export the ordered images into a single `PDF`.
8. Stop the production route at the `PDF`.
9. Use the validated external PDF-to-PPT toolchain only as a separate downstream step outside this skill when PPT conversion is needed.

## Supplemental Asset Route

- `Gemini API` is only a supplemental visual-asset backend.
- Use it only when the user explicitly asks for a missing image or figure on a page.
- In that case, generate candidates with both `Gemini` and `image2`, compare them, and insert only the stronger result.

## Input Convention

Use a directory-based input pack rather than a single loose file. The canonical layout is:

```text
paper-pack/
  manifest.json
  thesis.pdf
  thesis.docx
  abstract.txt
  defense-requirements.txt
```

Production runs should prefer `PDF` and `DOCX`. For local smoke development, plain text files are also accepted so the pipeline can be exercised without large binaries.

## Output Convention

Write all generated artifacts into a single work directory:

```text
runs/<run-name>/
  extraction.json
  analysis-brief.json
  presentation-brief.json
  deck-outline.md
  deck-spec.json
  page_manifest.json
  page_recipe/
  page_assets/
  slides/
  final-deck.pdf
```

## Script Entry Points

Use these scripts directly when you want deterministic file generation:

- `scripts/extract_paper_pack.py`
- `scripts/analyze_extraction.py`
- `scripts/rewrite_presentation_brief.py`
- `scripts/spec_outline.py`
- `scripts/build_template_profile.py`
- `scripts/build_page_raster_contracts_v1.py`
- `scripts/export_image_pages_to_pdf.py`
- `scripts/generate_third_party_image.py`
- `scripts/call_third_party_model.py`

## Reasoning Rules

- Preserve uncertainty.
- Prefer evidence-backed bullets over broad summaries.
- Use extracted headings, figure mentions, and section hints to anchor the narrative.
- Rebuild the storyline for a defense audience: problem, motivation, method, evidence, takeaway, limitations.
- Default the presentation language to Chinese unless the user explicitly asks for English output.
- Keep slide bullets short. Long prose belongs in notes, not slide bodies.

## Visual Backend Strategy

- The current production route is `image2-page-raster`.
- Every generated page must first have a strict contract before any model call happens.
- The canonical review artifact is a folder of ordered slide images plus a merged `PDF`.
- `PDF` is the only production export. Do not create PPT/PPTX from inside this skill.
- Do not use Python PPT libraries, Node PPT libraries, PowerPoint COM automation, Google Slides, draw.io, or archived renderers as production backends.
- Do not execute files under `archive/legacy-routes/` unless the user explicitly asks for a legacy experiment.
- For `route-board` pages, treat the user's thesis-roadmap sample images as a style family, not as a literal multi-panel layout to copy.
- For `route-board` pages, prefer the shared thesis-roadmap grammar: strong top headline, central hub, surrounding workstreams, side support rails, and a bottom synthesis zone.
- Generated pages are Chinese-first by default; do not route through an English intermediate draft unless the user explicitly asks for English output.
- Keep Chinese page content intentionally dense and complete so the final review deck still feels full and committee-ready.
- Preserve density through structure, modules, chips, connectors, and visual layers; do not rely on tiny blurred Chinese text to make a page feel full.
- When small Chinese labels are necessary, prefer a deterministic local Chinese text layer over asking the image model to paint microtext directly into the raster image.
- Do not keep optimizing around prompt-only Chinese text sharpening or Photoshop text-layer post-processing; those routes have been tested and are no longer part of the active effort.
- For `route-board`, `study-design-board`, `evidence-chain-board`, and `mechanism-board`, define a per-page complexity target and treat sparse layouts as failures.
- Keep generated raster pages free of all school branding and leave the top-right header corner visually quiet so branding can be added manually later.
- Fix the content contract and density, but allow controlled compositional freedom so the image model can produce more advanced board layouts.
- Lock content, hierarchy, template boundaries, and failure rules; do not lock every page into a single rigid composition.
- Keep the system strict about what must appear and what must never appear, but flexible about how a page can become elegant.
- Do not over-constrain box positions, connector geometry, or module shapes when the page can stay clearer and more beautiful with controlled freedom.
- Treat any rendered coordinate text, `x/y/w/h` values, JSON fragments, threshold strings, schema labels, or prompt metadata as a hard failure.
- Do not use Figma or Canva in the production route.
- Do not treat image-to-editable-PPT reconstruction as the primary strategy.

## Template Selection

Treat `cdutcm-defense` as the canonical deck template profile and do not fall back to the older Tongji variant.
The concrete PPTX template file is user-provided at run time rather than committed into this skill repository.
Generated page images must not include any school logo or school name; keep the top-right region quiet for manual branding after export.

## Connected Design Tools

- `Figma`
  Excluded from the current production route. Keep only as an optional experiment space if explicitly requested later.
- `Canva`
  Excluded from the current production route because stability and reproducibility are not strong enough for the locked workflow.
- `BioRender`
  Treat as a scientific illustration asset source when available manually. In the current Codex session it is not exposed as a callable MCP tool, so it should not be assumed to be automatable from inside this skill yet.

## References

- `references/workflow.md`
- `references/file-contracts.md`
- `references/narrative-rules.md`
- `references/image-backends.md`
- `references/page-raster-v1.md`
- `references/technical-route-board-style.md`
- `references/current-skill-package.md`
- `references/third-party-image-api.md`

## Archived Routes

Historical draw.io, Gemini hybrid, native-PPT diagram, and visual-QA route files are stored under the local archive area and are no longer part of the default workflow.
