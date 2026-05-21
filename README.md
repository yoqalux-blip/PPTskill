# paper-to-defense-ppt

`paper-to-defense-ppt` is a Codex skill for turning thesis or research materials into a defense-ready presentation workflow.

The current locked route is intentionally simple and stable:

1. Extract thesis content from a `paper-pack`.
2. Build reviewable analysis, outline, and deck spec artifacts.
3. Lock the final deck to `35` pages.
4. Generate strict page contracts before any image generation.
5. Use `image2` for Chinese-first full-page slide images.
6. Export ordered slide images to a canonical `PDF`.
7. Stop there for production. Any downstream PPT conversion happens outside this skill with an external PDF-to-PPT tool.

## Production Rules

- Default output language is Chinese.
- School names and school logos are not baked into generated pages.
- The top-right header region stays visually quiet for manual branding after export.
- Technical route boards use the supplied thesis-roadmap style family: dense blue-white academic hierarchy, central hub, workstream clusters, support rails, and bottom synthesis zones.
- Coordinates, schema words, JSON fragments, internal prompt metadata, and `x/y/w/h` strings inside rendered pages are treated as failures.
- Figma and Canva are excluded from the production route.
- Gemini is only a supplemental asset backend when the user explicitly asks for a missing visual asset.
- Native PPT/PPTX generation is excluded from the production route.
- Do not run PowerPoint automation, PptxGenJS, python-pptx, Google Slides rendering, draw.io rendering, or files under `archive/legacy-routes/` unless the user explicitly asks for a legacy experiment.

## Main Files

- `SKILL.md`
- `agents/openai.yaml`
- `references/current-skill-package.md`
- `references/page-raster-v1.md`
- `references/technical-route-board-style.md`
- `scripts/build_page_raster_contracts_v1.py`
- `scripts/export_image_pages_to_pdf.py`

## Local Commands

```powershell
npm install
npm run template:profile -- --template-pptx <template.pptx> --work-dir <run-dir>
npm run page-raster:contracts -- --spec-file <deck-spec.json> --template-profile-file <template_profile.json> --recipes-dir <page_recipe> --output-manifest-file <page_manifest.json> --output-spec-file <deck-spec.raster.json>
npm run export:pdf -- --slides-dir <slides> --output-pdf <final-deck.pdf>
npm run audit:route-lock
```

Run `npm run audit:route-lock` after pulling this skill on another computer. It fails if the production route drifts back toward PPTX rendering, PowerPoint automation, draw.io rendering, or other archived branches.

Generated runs, paper packs, node modules, local API config files, and binary decks are intentionally ignored by Git.
