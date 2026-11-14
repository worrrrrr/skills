---
name: design-review
description: >-
  Designs and audits UI for SvelteKit and web apps: chooses a token system (colour, type,
  spacing, radius), builds composable layout classes and small components (Box, Card, Chip,
  Input, Button), supports runtime themes, and checks accessibility and copy. Use when the
  user asks to design a page or layout, build a design system, add themes or variants, make
  the UI compact or icon-first, review contrast or focus states, or audit an existing screen
  for UX problems. Triggers include "design this page", "design system", "ui review",
  "check contrast", "accessibility", "theme", "variant", "ออกแบบหน้า", "ออกแบบ UI",
  "ตรวจ UI", "ธีม", "contrast".
license: MIT
metadata:
  version: "1.0.0"
  tags: "design, ui, ux, sveltekit, tailwind, tokens, a11y"
allowed-tools: Read Write Edit Bash Glob Grep
---

# Design Review

Make deliberate visual choices, express them as tokens, compose them into small components,
then prove the result with measurements instead of opinion.

## When to use

- A new page, layout or component needs to be designed, not just coded.
- The project needs a token layer, runtime themes, or more component variants.
- The UI feels templated, text-heavy, or too large and needs tightening.
- Someone asks whether contrast, focus, labels or copy are acceptable.

Triggers: "design this page", "design system", "ui review", "check contrast", "theme",
"variant", "ออกแบบหน้า", "ออกแบบ UI", "ตรวจ UI", "ธีม".

## Operating contract

1. **Brief first.** One sentence: product, audience, primary job. If it is missing, propose
   one and say it is an assumption.
2. **Tokens before components.** Every raw value lives in one token block; components only
   reference `var(--…)`. If a component needs a value, add a token.
3. **Small and composable.** Prefer `Box`/`Card`/`Chip`/`Input`/`Button` with variant props
   over new one-off CSS.
4. **Measure, do not assert.** Contrast is a number, focus is inspectable, labels are
   present or absent. Run the scripts.
5. **Remove one accessory.** Before calling it done, delete the least useful element.

## Phase 0 - Brief

Write the one sentence, the audience, and the screen's single job. List hard constraints
(framework, brand colours, existing tokens, density). Anything unknown becomes an assumption
in one line.

## Phase 1 - Plan the system

| Axis | Decide |
|---|---|
| Colour | 4-6 values: surface, raised, ink, muted, line, accent (+danger/ok if used) |
| Type | one or two families, roles, scale xs→xl, line-height |
| Space | one scale (1-6) plus a page padding that is fluid |
| Radius | sm/md/lg/pill, one value each |
| Layout | max measure, page shell, vertical rhythm, alignment |

Review the plan against the brief: if it would be identical for a different product, change
it. `references/principles.md` lists the known AI defaults to avoid.

## Phase 2 - Build the layers

1. **Tokens**: `assets/tokens.css` is a starting point. Keep raw values only here.
2. **Layout classes** in the same file: `.shell` (frame, max measure, fluid padding),
   `.stack` (vertical rhythm via `--stack-gap`), `.cluster` (wrapping group),
   `.card`, `.bubble`, `.composer`.
3. **Components** in `src/lib/components/ui/`: `Box`, `Card`, `Chip`, `Input`, `Button`.
   Variants are props that only change tokens or classes:

   ```svelte
   <Button variant="ghost" size="icon" label="Send"><Send class="h-4 w-4" /></Button>
   <Chip tone="ok" size="sm">saved</Chip>
   <Card variant="flat" pad="sm">...</Card>
   ```

4. **Themes**: put `data-theme`, `data-accent`, `data-shape`, `data-density`, `data-font`
   on `<html>` and override tokens under those selectors. Components never learn about a
   theme. Persist the choice and apply it before first paint (inline script in `app.html`).

## Phase 3 - Compose the screen

- Starting from a harness mock? Read `references/harness-patterns.md` first, then open only the
  one part you are building, such as `assets/orbit-composer.html` (1-4k tokens per part).
- One shell per route; the route supplies content, the shell supplies frame and header.
- Text is a last resort for meaning: use an icon with `aria-label`/`title` when the meaning
  is universal, and keep labels to 1-3 words.
- Reuse the same primitive in every route so changes propagate.

## Phase 4 - Verify

```bash
python scripts/contrast.py "oklch(0.24 0.02 260)" "#ffffff"     # text on surface
python scripts/contrast.py --pairs pairs.txt                    # whole palette
python scripts/audit.py src --tokens src/layout.css             # labels, alt, tokens, focus
python scripts/selftest.py                                      # the tools themselves
```

Then the project's own checks: `verify.py` (svelte-check/build) after any component change.
Numbers to report: contrast ratios, audit codes fixed, and what was removed.

## Phase 5 - Copy

Follow `references/copy.md`: user language, active voice, one job per element, errors that
explain the fix, empty states that invite action. Keep a microcopy budget per element.

## Hard bans

| Do not | Why |
|---|---|
| Hex/rgb values inside a component | breaks theming and drifts from tokens |
| `outline: none` without a visible replacement | keyboard users lose the cursor |
| Icon-only button without `aria-label` | screen readers announce "button" |
| ALL CAPS labels, eyebrow above every heading | reads as generated template |
| A new one-off class per screen | duplicates instead of composing |
| Declaring a design "accessible" without running contrast | it is a measurable claim |

## Files

- `scripts/contrast.py` - WCAG ratio for hex/rgb/oklch values.
- `scripts/audit.py` - static UI audit (tokens, alt, labels, focus).
- `scripts/selftest.py` - offline tests for both scripts.
- `references/principles.md` - brief, AI defaults, restraint, plan format.
- `references/a11y.md` - checkable accessibility rules.
- `references/copy.md` - interface writing rules and budgets.
- `references/observed-patterns.md` - live measurements from ChatGPT, Gemini, DeepSeek (dated).
- `references/current-practice.md` - what shadcn/ui and Carbon do today: tokens, density, data tables.
- `references/harness-patterns.md` - measured type, density, radius and layout of the two mocks.
- `assets/tokens.css` - starter token block with theme/shape/density variants.
- `assets/harness.css` - tokens, motion and the custom utilities the parts need; load after Tailwind.
- `assets/orbit-sidebar.html`, `assets/orbit-composer.html`, `assets/deepseek-chat.html` - split harness mocks; full parts list in `references/harness-patterns.md`.
