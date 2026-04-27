# Visual System

## Goal

Use the visual system to turn a text-only academic deck into a figure-assisted defense presentation with stable layout logic, reusable diagram families, and an explicit aesthetic review pass.

## Workflow

1. Generate the textual deck spec.
2. Run a visual planning pass to assign `layout_hint`, `visual_type`, `figure`, `takeaway`, and image-backend routing.
3. Generate deterministic assets for logic-heavy pages, favoring native PPT geometry when the figure must match the page typography and spacing.
4. Generate Nano Banana assets for mechanism and high-aesthetic illustration pages, but keep those assets text-free and composable.
5. Run an aesthetic review pass against both page layouts and generated figures.
6. Render the final PPTX from the enriched spec.
7. For review drafts, export slides to images and run a geometry-plus-visual QA pass before accepting the deck.

## Rendering Layers

- `deterministic-vector`
  Use for route diagrams, study designs, evidence chains, and any page where exact node order matters more than painterly style.
- `native-ppt-diagram`
  Use when the figure should inherit the deck's fonts, stroke widths, spacing, and label system instead of behaving like an embedded poster.
- `gemini-editable-hybrid`
  Use when a complex route board, study-design page, evidence chain, or mechanism summary needs stronger visual composition than native PPT alone, while keeping editable text, labels, and arrows in PPT.
- `drawio-mcp-diagram-lab`
  Use when a route board or research structure is too complex for lightweight PPT geometry and benefits from an editable diagram workspace before export.
- `programmatic-chart`
  Use for statistics, trend charts, grouped comparisons, and other data-bearing figures.
- `nano-banana-raster`
  Use for mechanism panels, biological concept art, transparent-background cutouts, and other supporting visuals that need higher aesthetic quality.

## Figure Families

- `process-flow`
  Use for the overall technical route and multi-stage research pipelines.
- `study-design`
  Use for clinical, animal, or cell experiment design pages.
- `evidence-chain`
  Use for summary pages that connect clinical evidence, omics, animal validation, and cell validation.
- `mechanism-pathway`
  Use for mechanism slides that explain infection, pathway activation, injury, intervention, and reversal.
- `result-card`
  Reserve for later use when a statistics-heavy slide needs KPI cards or stylized result blocks.

## Backend Routing

- Route `process-flow` to native PPT cards and connectors unless a later D2 export is explicitly chosen.
- Route `study-design` to native PPT cards and connectors unless a later D2 export is explicitly chosen.
- Route `evidence-chain` to native PPT cards and connectors unless a later D2 export is explicitly chosen.
- Escalate `process-flow`, `study-design`, or `evidence-chain` to draw.io MCP only when the page needs a denser route board, richer stencil vocabulary, or manual post-editability.
- When visual QA keeps reporting overlap or crowding on these pages, generate draw.io XML and Mermaid drafts and treat them as editable remediation artifacts rather than continuing to only shrink PPT text.
- Route the highest-risk complex pages to `gemini-editable-hybrid` when the page needs a no-text visual plate, structured `layout_schema.json`, and editable overlay layers instead of a pure native card layout.
- Route `mechanism-pathway` to a hybrid path: first prepare a structured brief, then generate no-text image elements with Nano Banana, then assemble the final slide with native PPT labels and arrows.
- Route statistics visuals to local chart tooling rather than the image model.

## Layout Hints

- `figure-full`
  Use when the figure is the main object on the page and bullets should act as captions or reading guides.
- `figure-right`
  Use when a figure should sit to the right and text should remain on the left.
- `figure-left`
  Use when the figure should introduce the page and bullets should support it on the right.
- `section`
  Use as a module transition page with minimal text and strong chapter separation.

## Aesthetic Review Scope

Review both the PPT pages and the generated figures.

For PPT pages, check:
- visual balance
- text density
- whitespace usage
- hierarchy clarity
- whether the page feels empty or overcrowded
- whether text boxes overlap each other
- whether text intrudes into image regions
- whether dense route boards have local crowding hotspots

For figures, check:
- palette consistency
- label length
- node count
- arrow direction clarity
- whether the figure can be read in a defense setting from a distance
- whether raster assets and vector assets feel like they belong to the same deck

## Heuristics

- Prefer one dominant visual message per figure.
- Keep node labels short enough to scan in under 2 seconds.
- Use no more than one accent color plus one warning color inside a single figure family.
- Prefer horizontal causal flow for mechanism diagrams unless there is a strong reason to branch vertically.
- Let figures explain logic; let bullets explain interpretation.
- Avoid screenshots unless the source image itself is the evidence.
- Ask Nano Banana for transparent-background outputs when the asset should be layered into the PPT.
- Keep embedded text inside generated illustrations minimal so final labels can stay editable in PPT when needed.
- Prefer multiple smaller mechanism assets over one long generated image so arrows and bridge text can remain outside the art.
- When PowerPoint is available, export each slide as a PNG and use that review loop to drive repairs rather than relying on screenshot-based manual inspection alone.
- For `gemini-editable-hybrid` pages, keep `page_brief.json` and `layout_schema.json` as first-class artifacts so the QA loop can adjust layout without OCR or bitmap tracing.
- If draw.io MCP is used, keep `.drawio` or XML sources as intermediate assets so failed visual QA rounds can be traced back to the diagram source rather than only the exported bitmap.
- When a draw.io diagram is approved, export it back into the slide artifact directory as `exported.svg` or `exported.png` so the renderer can swap from native PPT geometry to the polished draw.io asset automatically.
- When PowerPoint is available, normalize the rendered PPTX through a local open-and-save pass before visual QA export; use the normalized file as the review artifact instead of the raw renderer output.
- Store per-slide draw.io work orders with `draft.xml`, `draft.mmd`, and `context.json` so the lab path stays reproducible across QA iterations.
- Let Gemini hybrid pages consume one schema-repair pass and one background-regeneration pass before they fall back to draw.io.

## V2 Priorities

- First add structure diagrams for route and design pages.
- Then add mechanism and evidence-chain diagrams for experimental sections.
- Only after the logic diagrams are stable, add refined charts and statistic visuals.
