# Page Raster V1

- This route is the current production route.
- The final deck is locked to `35` pages.
- The current locked template profile is `cdutcm-defense`; the concrete PPTX template is user-provided at run time and is not committed into the skill repository.
- The current production export is `PDF` only.

## Core Principle

- Never send raw slide bullets directly to the model as a free prompt.
- Always build a strict `page_recipe` first.
- `image2` is the primary full-page generation backend.
- Generate the page in Chinese by default; do not force an English intermediate draft unless the user explicitly asks for English.
- Keep Chinese page content intentionally dense so the page still feels full and committee-ready.
- Do not preserve density by shrinking Chinese text until it becomes fuzzy. Density should come from structure, modules, labels, connectors, evidence bands, and visual layering.
- If small Chinese labels are required, the preferred next production candidate is a deterministic local text layer over the image2 visual board before PDF export.
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

## Current Scripts

- `scripts/build_template_profile.py`
- `scripts/build_page_raster_contracts_v1.py`
- `scripts/build_chinese_legibility_abtest.py`
- `scripts/export_image_pages_to_pdf.py`

Do not generate PPT/PPTX in this route. Legacy PPT packaging scripts are archived and must not be used unless the user explicitly asks for a legacy experiment.

## Chinese Legibility Experiment

Run `npm run abtest:legibility` to create a local image/PDF-only comparison under `runs/chinese-text-legibility-abtest/`.
It compares:

- `prompt-only`: simulated raster Chinese text painted into the page image
- `postprocess`: the same raster text with sharpening and contrast enhancement
- `deterministic-text-layer`: the same dense board style with local Chinese fonts drawn at export resolution

This experiment does not change the production route by itself. If the deterministic text layer clearly wins, promote it in a later revision while keeping the final artifact as PDF only.

## Supplemental Asset Route

- `Gemini API` is reserved for explicit page-level supplement requests only.
- If a page is missing one figure, one mechanism insert, or one support asset:
  - generate candidates with both `Gemini` and `image2`
  - compare them
  - insert only the stronger result
