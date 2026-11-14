# Harness UI patterns

Measured 2026-11-14 from two Tailwind mocks, then split into component-sized parts under
`assets/`. Read this file first: it is ~700 tokens, while a single part is 1-4k tokens and the
full mocks (with app JS) are 28-32k. Full-fidelity originals live outside the repo in
`~/design-refs/`.

## Parts, mapped to Svelte components

Orbit Harness - workspace mock, Thai + English copy (374 classes, 330 `dark:` utilities):

| Part | Component | Size |
|---|---|---|
| `assets/orbit-topbar.html` | `TopBar.svelte` | 3.8 KB |
| `assets/orbit-sidebar.html` | `Sidebar.svelte` | 6.2 KB |
| `assets/orbit-hero.html` | `EmptyHero.svelte` (prompt card + suggestions) | 12.3 KB |
| `assets/orbit-composer.html` | `Composer.svelte` | 1.2 KB |
| `assets/orbit-panel-context.html` | `ContextPanel.svelte` | 4.7 KB |
| `assets/orbit-panel-orbit.html` | `OrbitPanel.svelte` | 6.6 KB |
| `assets/orbit-panels-tools.html` | `ToolPanels.svelte` (files/sandbox/terminal/logs) | 1.4 KB |
| `assets/orbit-customize.html` | `CustomizeDialog.svelte` | 4.9 KB |
| `assets/orbit-palette.html` | `CommandPalette.svelte` | 1.1 KB |

DeepSeek Harness clone - plugins, automation, settings (312 classes, 364 `dark:` utilities):

| Part | Component | Size |
|---|---|---|
| `assets/deepseek-topbar.html` | `TopBar.svelte` | 3.6 KB |
| `assets/deepseek-sidebar.html` | `Sidebar.svelte` | 6.6 KB |
| `assets/deepseek-chat.html` | `ChatView.svelte` (messages + composer) | 8.2 KB |
| `assets/deepseek-plugins.html` | `PluginsView.svelte` | 7.0 KB |
| `assets/deepseek-automations.html` | `AutomationsView.svelte` | 2.7 KB |
| `assets/deepseek-workspace-panel.html` | `WorkspacePanel.svelte` | 5.8 KB |
| `assets/deepseek-settings.html` | `SettingsDialog.svelte` | 3.1 KB |
| `assets/deepseek-automation-modal.html` | `AutomationDialog.svelte` | 2.1 KB |

Each part is static markup: no app JS, SVG icons reduced to their wrapper, comments removed.
They are copy references, not working demos.

## What the two share

- **Single-file mocks**: Tailwind from `cdn.tailwindcss.com`, no build step. Fine for a
  reference, wrong for production.
- **Density**: `text-xs` and `text-[11px]` everywhere (57 uses of `text-xs` in one file), rows
  at `py-1`/`py-1.5`, `px-3`. Compact, not airy.
- **Radius**: pill (`rounded-full`, 9999px) plus `rounded-lg` (8px) and `rounded-xl` (12px).
- **Shape**: two `<aside>` panels (navigation + context), one `<nav>`, flex rows with
  `items-center` + `justify-between`; only 3-4 `grid-cols` and 7-8 arbitrary `w-[...]`.
- **No tables, no dialogs** - lists, cards and split panels instead of `<table>` or `<dialog>`.
- **Accessibility gap**: one `aria-` attribute across both files. Do not copy that; add
  `aria-label` from `references/a11y.md`.

## Patterns worth copying

- One accent hue, five stops: `--brand-50 #eef2ff`, `-100 #e0e7ff`, `-500 #6366f1`,
  `-600 #4f46e5`, `-700 #4338ca`, over a neutral slate scale.
- Dark variants on every surface (`bg-white` -> `dark:bg-slate-800`), never a second palette.
- Sidebar-first layout: navigation is persistent, content scrolls inside one shell.
- Settings and plugins as ordinary pages, not modals.

## Patterns to avoid

- 11px body text; it fails the density rules in `references/current-practice.md`.
- 330+ `dark:` utilities per file with no token layer - every new surface needs two edits.
- CDN Tailwind in shipped code.
- `aria-` omissions above.

## How to use a part without burning context

1. Read this file for shape, density and palette.
2. Open only the part you are building, for example `assets/orbit-composer.html`.
3. Re-express colors and spacing through `assets/tokens.css` instead of hardcoding Tailwind
   literals, and add the props the component actually needs.

Parts use Tailwind utilities plus `assets/harness.css` (brand/dsh colors, shadows, pane
transitions). Load that CSS **after** Tailwind, or those colors render as nothing.
