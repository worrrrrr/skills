# DSH right-sidebar delivery (optional)

The skill's main delivery is a chat reading from `scripts/chart.py`. A DeepSeek Harness
plugin can show the same values on a page in the right sidebar, but that is a second artifact
with its own lifecycle. This note records the contract so the wrapper is not re-derived.

## What a right-sidebar page is

A tab type is **two registrations sharing one `id`**:

1. `ctx.sidebarRightTabs.register({ id, kind, title, guide })` — static: the tab kind, the
   chip title, and optional guide entries.
2. `ctx.slots.inject('sidebar.right.pane.tab', () => ctx.slots.register({ name:
   'sidebar.right.pane.tab', key: id, locale }, Body))` — the React body keyed by the same id.

The guide entry is the entry point: when a user opens the guide, picks the entry, the sidebar
opens the tab of that kind. `title(address)` is captured when the tab opens, so a language
switch needs the optional `sidebar.right.pane.tab.title` seat.

## Bundle shape

```
divination-plugin/
├── package.json          dsh.bundle.patch + dsh.client { platform: web, inject: [...] }
├── cordis.patch.yml      - insert: [{ id, name: '@local/...' }]
├── index.js              export function apply() {}   (Host half)
├── client.js             generated: window.__ModuleLoader__.load({ id, factory })
├── locale/{en,th}.json   meta.title, meta.description, meta.detail
├── docs/DETAIL.md        one image line, optional
└── icon.svg
```

`client.js` is a browser module: it gets React from the host module table
(`const React = require('react')`), must not import `@deepseek-ai/dsh-client-ui-primitives`,
and must register styles/components inside `apply`. For a source layout with a pure engine and
an app module, a small build step concatenates both into that wrapper; the wrapper is the only
file the loader reads.

## Engine choice

`scripts/engine.py` is the reference implementation. A DSH **client** page runs JavaScript, so
either:

- port `engine.py` to a pure JS module and ship it in `client.js` (what the original plugin
  does), or
- keep Python on the Host and expose one tool/endpoint that the client calls (slower, but one
  implementation).

Do not import Python from the browser. If both surfaces must agree, keep one tested engine
and port with a fixed test vector file.

## Pitfalls learned from the reference build

- Register the tab type inside `ctx.effect`; the registry adds an effect to its own fiber.
- Register the locale dictionary **before** the body; the body's `t` seat reads it.
- Use theme tokens (`--dsw-alias-*`), not literal colours; light mode collapses layer tokens.
- The right pane is narrow: single-column form below ~340 px, no fixed-width tables.
- Client changes need a page refresh unless the deployment's dev watcher is running.
- Without browser control, verify only: JS syntax, installed slot occupant, and the guide
  registration. Do not claim a visual pass.

## Verification checklist

- [ ] `node --check client.js`
- [ ] `install_bundle` returns `application: applied`
- [ ] `sidebar.right.pane.tab` lists the plugin id as an active occupant
- [ ] guide entry title/description/icon appear in the guide (inspect or screenshot)
- [ ] tab opens with a session selected and the body renders without a slot crash
- [ ] light and dark, 320 and 460 px, keyboard focus
