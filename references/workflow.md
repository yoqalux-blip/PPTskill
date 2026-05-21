# Workflow

Use the locked production pipeline in seven checkpoints:

1. Extract source material into `extraction.json`.
2. Build `analysis-brief.json` and `presentation-brief.json`.
3. Shape `deck-outline.md` and `deck-spec.json`.
4. Lock the final deck to `35` pages and generate strict page contracts with `page_manifest.json` and `page_recipe/<slide-id>.json`.
5. Generate ordered full-page review images with `image2`.
6. Export the ordered slide images into a single `PDF`.
7. Stop the production route at the `PDF`. Use an external PDF-to-PPT toolchain only as a separate downstream/manual step.

Gemini is not part of the default full-page route. It is only used later as a supplemental visual-asset generator when a page is missing a figure and the user explicitly asks for one.

Do not generate PPT/PPTX inside the skill. Do not use Python, Node, PowerPoint COM, PptxGenJS, python-pptx, Google Slides, draw.io, or archived renderers to build a deck in the production route.
