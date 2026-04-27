# Design Tool Boundaries

## Figma

- Best use:
  - editable slide exploration
  - FigJam-style diagrams
  - layout experiments
  - visual reference extraction
- Good fit for this skill:
  - draft slide concepts
  - diagram prototypes
  - editable route-board experiments before they are translated into the local PPT pipeline
- Not the right source of truth for:
  - thesis reasoning
  - extracted paper structure
  - deterministic final rendering

## Canva

- Best use:
  - rapid visual directions
  - template search
  - on-brand asset generation
  - quick social, poster, flyer, or presentation draft alternatives
- Good fit for this skill:
  - exploring alternate visual directions quickly
  - testing branded layouts or presentation shells
  - converting flat images into editable Canva drafts for manual refinement
- Not the right tool for:
  - precise scientific route-board logic
  - complex mechanistic figure reasoning
  - strict thesis-slide contract control

## BioRender

- Best use:
  - biological diagrams
  - pathway illustrations
  - cell, tissue, and mechanism assets
- Good fit for this skill:
  - supplying manual scientific illustration assets for mechanism pages
  - replacing or enriching biology-heavy figures after the slide structure is fixed
- Current limitation:
  - in this Codex session, BioRender is not exposed as a callable MCP tool
  - treat it as a manual external asset source rather than an automated step in the skill

## Recommended Division Of Labor

- Thesis understanding, deck structure, contracts, and rendering:
  - local skill scripts
- Editable slide or diagram exploration:
  - Figma
- quick design alternatives and brand-template experiments:
  - Canva
- biology-specific illustration assets:
  - BioRender, when used manually
