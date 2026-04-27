# Workflow

Use the locked production pipeline in eight checkpoints:

1. Extract source material into `extraction.json`.
2. Build `analysis-brief.json` and `presentation-brief.json`.
3. Shape `deck-outline.md` and `deck-spec.json`.
4. Lock the final deck to `35` pages and generate strict page contracts with `page_manifest.json` and `page_recipe/<slide-id>.json`.
5. Generate ordered full-page review images with `image2`.
6. Export the ordered slide images into a single `PDF`.
7. Optionally package the same ordered images into an image-based `PPTX`.
8. Use the external PDF-to-PPT toolchain when a downstream PPT version is needed.

Gemini is not part of the default full-page route. It is only used later as a supplemental visual-asset generator when a page is missing a figure and the user explicitly asks for one.
