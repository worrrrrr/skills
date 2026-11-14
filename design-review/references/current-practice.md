# What UI systems use now (checked 2026-11-14)

Two sources read today: shadcn/ui docs (theming + AI Elements) and IBM Carbon
(data table usage, updated 2026-09-30). Numbers below are quoted from those pages.

## 1. Theming: semantic token pairs, not raw colours

shadcn/ui defines paired background/foreground tokens and maps them into Tailwind:

| Token | Controls | Used by |
|---|---|---|
| `background` / `foreground` | app surface + default text | page shell |
| `card` / `card-foreground` | elevated surfaces | cards, panels |
| `popover` / `popover-foreground` | floating surfaces | menus, popovers |
| `primary` / `primary-foreground` | high-emphasis actions | default button, active states |
| `secondary` / `secondary-foreground` | lower-emphasis filled actions | secondary buttons |
| `muted` / `muted-foreground` | subtle surfaces, subdued text | placeholders, helper text |
| `accent` / `accent-foreground` | hover/focus/selected surfaces | ghost buttons, hovered rows |
| `destructive` | errors and destructive actions | invalid states |
| `border`, `input`, `ring` | separators, control borders, focus rings | all controls |
| `chart-1..5` | chart palette | charts |
| `sidebar`, `sidebar-*` | sidebar surface, accent, border, ring | sidebar component |

Notes worth copying:

- Values are **oklch** and live in `:root` + `.dark`; components only use `bg-*`/`text-*`.
- **One radius token** (`--radius`) derives the whole scale:
  `radius-sm = 0.6x`, `md = 0.8x`, `lg = 1x`, `xl = 1.4x`, `2xl = 1.8x`.
- Adding a token = define in `:root` and `.dark`, expose with `@theme inline`, then use it.
- Base palettes offered: neutral, stone, zinc, mauve, olive, mist, taupe.

What this means for us: our `--color-*` set is close but we lack paired `*-foreground`
tokens and a derived radius scale. Adopt both before adding more components.

## 2. Component distribution is a registry, not a package

shadcn/ui ships components as **open code** pulled by CLI from a registry
(`registry.json`), so the app owns and edits the code. The docs list ~60 base
components including `Sidebar`, `Data Table`, `Empty`, `Field`, `Item`, `Kbd`.

Practical takeaway: treat our `src/lib/components/ui` the same way - one file per
primitive, variants as props, no wrappers around a third-party package.

## 3. AI interfaces have their own primitives

shadcn/ui ships **AI Elements**: chain-of-thought, reasoning, message, prompt
input, tool, sources, inline citation, confirmation, task/subagent, terminal,
test results, model selector, queue, plan.

That is the current vocabulary for chat UIs. Our sidebar/tool badges map to:
`tool`, `reasoning`, `message`, `prompt input`, `sources`.

## 4. Data tables: density is a decision, sizes must line up

Carbon defines five row/header heights and requires everything else to match:

| Size | Height | Use |
|---|---|---|
| xs | 24 px | very dense layouts |
| sm | 32 px | compact interfaces |
| md | 40 px | default |
| lg | 48 px | spacious |
| xl | 64 px | two-line rows |

Rules quoted from the page:

- Header row must use the **same size** as body rows (never mix).
- Toolbar height should match the row height; the batch action bar too.
- Pagination height should match the row height (xl pairs with lg).
- Row hover must always be enabled, even for non-interactive rows, to help scanning.
- Column titles: 1-2 words, sentence case; wrap to two lines then truncate with a tooltip.
- Sorting: icon only on the sorted column; unsorted icons appear on hover.
- Loading uses **skeletons**, not spinners.
- Overflow menus: persistent by default, optional `overflowMenuOnHover` to reduce clutter
  (touch devices persist them anyway).
- Fewer than three row actions -> keep them inline as icon buttons.
- Don't nest tables or squeeze them into containers that force truncation.

## 5. What we should adopt next

1. Paired `*-foreground` tokens + one `--radius` driving the scale.
2. Row-height scale (24/32/40/48) as tokens, applied to sidebar rows and tables.
3. Hover state on every row (already true) and skeletons for async content.
4. For chat: name parts like AI Elements - `tool`, `reasoning`, `sources` - so the
   component map stays recognisable to anyone who has used shadcn.

Sources:
- <https://ui.shadcn.com/docs/theming>
- <https://ui.shadcn.com/docs> (AI Elements index)
- <https://carbondesignsystem.com/components/data-table/usage/> (updated 2026-09-30)
