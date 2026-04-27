# Gemini Editable-Hybrid Implementation

## Scope

- This route is used only for high-risk complex figure pages.
- The first production targets are:
  - `slide-09` technical route board
  - `slide-12` study design board
  - `slide-31` evidence chain board
  - `slide-32` mechanism integration board
- Ordinary text-heavy slides stay on the existing native PPT path.

## Rendering Contract

- `Gemini` generates no-text visual plates or mechanism assets.
- `PPT` remains responsible for:
  - Chinese titles
  - editable labels
  - editable cards
  - editable arrows and connectors
  - takeaway boxes
- `draw.io` stays as the controlled fallback when Gemini hybrid pages still fail QA.

## Spec Additions

- Each hybrid page sets:
  - `visual_route: gemini-editable-hybrid`
- Each hybrid page writes:
  - `page_brief.json`
  - `layout_schema.json`
- The slide payload also keeps a `gemini_hybrid` block with:
  - `page_kind`
  - `page_brief_file`
  - `layout_schema_file`
  - inline `page_brief`
  - inline `layout_schema`
  - `generated_assets`
  - `qa_policy`
  - `qa_state`

## Layer Model

- Bottom layer:
  - Gemini-generated plate
  - Gemini-generated mechanism pieces
  - soft textures and atmosphere blocks
- Middle layer:
  - native PPT cards
  - rails
  - connectors
  - arrows
  - hub blocks
- Top layer:
  - Chinese headings
  - Chinese labels
  - summary text
  - takeaway text

## QA Loop

- Iteration 1:
  - schema repair only
- Iteration 2:
  - Gemini asset regeneration allowed
- Later iterations:
  - draw.io fallback can be triggered

The current QA loop checks:

- text overlap
- text-image overlap
- connector-text overlap
- edge risk
- clipping risk
- density risk

For hybrid pages, large Gemini plates are treated as background assets so they do not create false-positive text-image overlap findings.

## Current Scripts

- Builder:
  - `scripts/build_visual_package_v6_gemini_hybrid.py`
- Renderer:
  - `scripts/render_local_deck_v5.mjs`
- QA loop:
  - `scripts/run_visual_qa_loop.py`
- Repair pass:
  - `scripts/repair_from_visual_audit.py`
- Geometry audit:
  - `scripts/audit_rendered_deck_v2.py`

## Current Validation Status

- `deck-spec-v6.json` is present and populated.
- `visual-assets-plan-v6.json` is present.
- `final-deck-v6-gemini-hybrid-review.pptx` is generated successfully.
- `visual-qa-v6-loop` shows the expected control flow:
  - schema repair
  - asset regeneration
  - draw.io fallback

## Known Boundaries

- This route does not promise full-image-to-editable-PPT conversion.
- It does not OCR Chinese text back out of a generated image.
- It does not require Gemini to place Chinese text in the image itself.
- It optimizes for:
  - stronger aesthetics
  - editable key expression layers
  - safer fallback behavior
