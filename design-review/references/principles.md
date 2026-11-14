# Design principles

Adapted from Anthropic's public `frontend-design` and `theme-factory` skills
(<https://github.com/anthropics/skills>), narrowed to rules this skill can check.

## The brief decides, not the defaults

Write one concrete sentence before choosing anything:

> A `<product>` for `<audience>` whose job is `<primary job>`.

If the brief already pins a direction, follow it. Where an axis is free, do not spend that
freedom on a default.

## Known AI defaults (the tells)

These are legitimate for some briefs, but they appear regardless of subject. Do not use one
unless the brief asks for it:

1. warm cream background (#F4F1EA-ish) + high-contrast serif + terracotta accent;
2. near-black background + one acid-green or vermilion accent;
3. broadsheet layout: hairline rules, zero radius, dense columns;
4. the SaaS-card kit: every block is the same rounded card with the same grey shadow, plus a
   gradient wash for decoration;
5. template chrome: tracked-out ALL-CAPS eyebrow above every heading, `A · B · C` meta strings,
   `WORD — fragment` labels, #0B0B0B "black", monospace micro-labels, `→` appended to links.

## Plan before building

Produce a compact plan, in prose, before any component:

| Axis | Minimum content |
|---|---|
| Colour | 4-6 named values: surface, raised, ink, muted, line, accent (+danger/ok if used) |
| Type | one or two families, their roles, a scale (xs → xl) and line-height |
| Layout | one sentence + an ASCII wireframe; alignment; max measure |
| Principles | 2-3 sentences on what makes this page this page |

Then review the plan against the brief: if any part would be identical for a different
product, revise it and say what changed. Only then write code.

## Structure carries information

Borders, rules, numbering and labels are only useful when they encode something real
(a sequence, a grouping, a state). Decoration that encodes nothing is noise.

## Restraint

Spend the boldness in one place. One memorable element; everything around it quiet.
Before finishing, remove one accessory: if nothing can be removed without loss, the design
is not finished being reduced.

## Motion

One orchestrated moment beats scattered effects. Motion that answers a user action
(open, expand, confirm) is welcome; motion that plays at every scroll is a tell.

## Tokens, then components

Every raw value lives in one token block. Components only reference tokens. If a component
needs a new value, add a token - do not inline it. This is what makes theme/shape/density
changes possible without touching components.
