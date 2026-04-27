# Technical Route Board Style

- Use this style for `route-board` pages and for standalone thesis roadmap figures.
- Treat the user's supplied thesis roadmap images as a sample bank, not as a fixed multi-panel page template.

## Core Look

- White-first academic canvas with strong blue structure, restrained red emphasis, and light gray support containers.
- Large Chinese headline at the top, similar to the user's thesis roadmap reference sheets.
- Dense but orderly hierarchy that still reads cleanly in a defense setting.
- No university logo, school name, watermark, page number, schema word, or internal metadata inside the generated figure.

## What To Learn From The Sample Bank

- The reference sheets contain multiple examples on one image, but the final generated figure does not need to copy that sheet layout.
- Learn the shared visual grammar instead:
  - strong top headline
  - central hub, ring-core, or anchor module
  - multiple surrounding workstreams
  - side pillars or framed support lanes
  - lower landing zone or synthesis/output zone
  - deliberate connector arrows that show convergence and feedback
  - engineered alignment rather than poster-like improvisation

## Required Traits For Route Boards

- One dominant title area at the top.
- A visible central framework, question, or mechanism anchor.
- Multiple substantial workstream clusters, not a sparse four-box infographic.
- A lower synthesis or output zone that explains the final integration value.
- Rich secondary components such as ribbons, badges, support cards, ring structures, side labels, or landing modules.

## Do Not Do

- Do not flatten the page into a simple left-to-right flowchart.
- Do not force a `2 x 2` or four-subfigure layout unless the content truly requires it.
- Do not leave large empty areas.
- Do not generate randomly floating arrows or weakly aligned blocks.
- Do not emit coordinates, JSON fragments, slot names, schema labels, or prompt leakage.
- Do not render placeholder English when the figure is meant to be Chinese.

## Prompting Guidance

- Lock the content contract and density first, then allow composition freedom inside this style family.
- Do not freeze every route-board into one rigid skeleton. Learn the style grammar, then let the board choose the clearest high-density composition.
- The goal is disciplined beauty, not mechanical repetition.
- Ask for:
  - high density
  - central hub
  - layered structure
  - modular hierarchy
  - bottom landing zone
  - blue-white academic style
  - restrained red emphasis
- For thesis route pages, prefer these lanes when relevant:
  - clinical evidence lane
  - omics or biomarker lane
  - animal validation lane
  - cell or pathway validation lane
  - final integration or conclusion output area
