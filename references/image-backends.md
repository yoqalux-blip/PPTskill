# Image Backends

## Locked Positioning

- `image2` is the primary page-generation backend for the current production route.
- `Gemini API` is not a full-page production backend anymore.
- `Gemini API` is only a supplemental visual-asset backend.

## Current Production Route

1. Thesis content is converted into strict page contracts.
2. Full-page review images are generated with `image2`.
3. Ordered slide images are exported into a merged `PDF`.
4. Production stops at the merged `PDF`.
5. External tools handle any downstream `PDF -> PPT` conversion as a separate non-skill step when needed.

## Gemini Supplemental Asset Route

Use Gemini only when the user explicitly asks for a missing visual asset on a page, such as:

- one missing mechanism insert
- one missing biology illustration
- one missing supporting concept figure
- one missing decorative-but-academic visual reinforcement asset

In that workflow:

1. define the exact page slot and missing asset purpose
2. generate candidates with both `Gemini` and `image2`
3. compare the outputs
4. insert only the stronger one into the page

## Guardrails

- Do not use Gemini as the default full-page renderer.
- Do not generate native PPT/PPTX inside this skill.
- Do not use Python PPT libraries, Node PPT libraries, PowerPoint COM automation, Google Slides rendering, draw.io rendering, or archived render scripts as a production backend.
- Do not use image models to fabricate quantitative charts.
- Do not ask image models to print coordinates, schema labels, JSON fragments, or internal metadata.
- Do not embed school names, school logos, or template branding into generated page images.
- Prefer transparent-background outputs when a supplemental visual should float inside a page layout.
- Prefer a clean academic visual style over fantasy or commercial poster aesthetics.
- For dense Chinese pages, do not ask the image backend to solve clarity by printing tiny body copy. Prefer structural density and, when needed, a local deterministic Chinese text layer before PDF export.

## Review Questions

- Is the generated asset filling a specific page-level gap?
- Does the page still read clearly after the asset is inserted?
- Between Gemini and image2, which output is more consistent with the page hierarchy and the locked template?
- Is the result genuinely improving comprehension rather than just decorating the page?
