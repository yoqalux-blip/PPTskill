# Current Skill Package

This file is the fixed operating view of `paper-to-defense-ppt`.

## Locked Mainline

The current production route is:

1. Thesis materials -> `extraction.json`
2. `analysis-brief.json` and `presentation-brief.json`
3. `deck-outline.md` and `deck-spec.json`
4. A fixed `35-page` contract set is built for the final deck
5. `image2` generates the ordered full-page review images
6. Ordered slide images export to `PDF` as the canonical delivery artifact
7. The production route stops at `PDF`; external tools convert the `PDF` into downstream PPT only outside the skill when needed

## What Is Fixed

- The deck is locked to `35` pages as the golden page count.
- Template source is the Chengdu University of Traditional Chinese Medicine defense deck.
- Template style constraints are fixed through:
  - `scripts/build_template_profile.py`
  - `SKILL.md`
  - `references/page-raster-v1.md`
- School branding is not baked into generated page images.
- `route-board` pages learn from the user's thesis-roadmap sample bank as a style family, not as a fixed four-panel collage.
- Technical route-board style grammar is fixed through:
  - `references/technical-route-board-style.md`
  - `scripts/build_page_raster_contracts_v1.py`
  - page-level `complexity_target`, `layout_freedom`, and `template_reference_roles`
- Generated review pages are now Chinese-first; the old English intermediate route is no longer the default.
- Chinese page content should stay intentionally dense so the final deck still feels full and committee-ready.
- The composition policy is fixed as: `lock content and forbidden zones, but do not lock one rigid layout`.
- The system should be stable in hierarchy and boundaries, but still leave enough design freedom to avoid mechanical slides.
- Coordinate leakage, schema leakage, JSON fragments, and internal layout metadata on rendered pages are hard failures.
- `PDF` is the only production export for the image-page route.
- Image-based `PPTX` generation is not part of the production route.
- `Gemini API` is reserved for explicit supplemental visual-asset requests only.
- Native PPT/PPTX generation through Python, Node, PowerPoint COM, Google Slides, draw.io, or archived renderers is forbidden in the production route.

## What Is No Longer Mainline

- Figma is excluded from the primary production chain.
- Canva is excluded from the primary production chain.
- BioRender is not assumed to be automatable in this session.
- Gemini full-page generation is excluded from the primary production chain.
- Image-to-editable-PPT reconstruction is not the primary route.
- Image-based PPTX packaging is archived and excluded from the primary production chain.
- draw.io, Gemini hybrid, native-PPT diagram routes, and visual-QA repair routes are archived capabilities.

## Core Deliverables

For a full production run, expect:

- `extraction.json`
- `analysis-brief.json`
- `presentation-brief.json`
- `deck-outline.md`
- `deck-spec.json`
- `page_manifest.json`
- `page_recipe/<slide-id>.json`
- `page_assets/<slide-id>/attempt-*/`
- ordered `slides/`
- `*.pdf`

## Core Scripts

- `scripts/extract_paper_pack.py`
- `scripts/analyze_extraction.py`
- `scripts/rewrite_presentation_brief.py`
- `scripts/spec_outline.py`
- `scripts/build_template_profile.py`
- `scripts/build_page_raster_contracts_v1.py`
- `scripts/export_image_pages_to_pdf.py`
- `scripts/generate_third_party_image.py`
- `scripts/call_third_party_model.py`

## Review Surface

The review surface is the pair:

- structured content contracts
- ordered generated slide images

That pair keeps the process stable. Any final PDF-to-PPT step must be performed by an external tool outside the skill.
