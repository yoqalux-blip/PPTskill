# Page Raster V1

- This route is the current production route.
- The final deck is locked to `35` pages.
- The current locked template profile is `cdutcm-defense`; the concrete PPTX template is user-provided at run time and is not committed into the skill repository.
- The current production export is `PDF` first, with optional image-based `PPTX` packaging.

## Core Principle

- Never send raw slide bullets directly to the model as a free prompt.
- Always build a strict `page_recipe` first.
- `image2` is the primary full-page generation backend.
- Generate the page in Chinese by default; do not force an English intermediate draft unless the user explicitly asks for English.
- Keep Chinese page content intentionally dense so the page still feels full and committee-ready.
- For `route-board`, `study-design-board`, `evidence-chain-board`, and `mechanism-board`, store an explicit complexity target instead of accepting lightweight infographic layouts.
- Keep the top-right corner visually quiet and free of all school branding.
- Fix the content contract and density, but allow controlled compositional freedom so the page can look advanced rather than template-stiff.
- The production principle is: lock content and forbidden zones, but do not lock a single mechanical layout.
- A page should be deterministic in meaning and boundary control, yet still free to choose the most elegant composition within the approved style family.
- Treat coordinate leakage (`x/y/w/h`), JSON snippets, thresholds, metadata strings, and schema words as hard rendering failures.

## Required Artifacts

- `template_profile.json`
- `template_style_brief.md`
- `template_reference_pack/`
- `page_manifest.json`
- `page_recipe/<slide-id>.json`
- `page_assets/<slide-id>/attempt-*/`
- ordered `slides/`
- final `PDF`
- optional local `PPTX`

## Current Scripts

- `scripts/build_template_profile.py`
- `scripts/build_page_raster_contracts_v1.py`
- `scripts/export_image_pages_to_pdf.py`
- `scripts/export_image_pages_to_ppt.mjs`
- `scripts/normalize_pptx.ps1`

## Supplemental Asset Route

- `Gemini API` is reserved for explicit page-level supplement requests only.
- If a page is missing one figure, one mechanism insert, or one support asset:
  - generate candidates with both `Gemini` and `image2`
  - compare them
  - insert only the stronger result
