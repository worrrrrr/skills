# Observed patterns: ChatGPT, Gemini, DeepSeek

Measured in the user's logged-in Chrome (browse relay) on 2026-11-14. Layout metrics only -
no message content was read. These are observations at one point in time, not specifications.

Method: open the product, wait for the composer, then read `getBoundingClientRect` on the
composer container (walking up from the editable until it has padding or radius), plus button
counts and `aria-label` coverage.

## Logged-in measurements

| Site | Composer (w x h) | Editable font | Sidebar | Buttons | Icon-only | With `aria-label` | Placeholder |
|---|---|---|---|---|---|---|---|
| ChatGPT | 768 x 52 | 16 px | 340 px | 60 | 41 | 49 | none (contenteditable) |
| Gemini | 373 x 40 | 17 px | n/a | 11 | 0 | 9 | "ป้อนพรอมต์สำหรับ Gemini" |
| DeepSeek | 774 x 60 | 16 px | n/a | 0 native | 0 | 0 | "Message DeepSeek" |

Caveats:

- DeepSeek exposes **no native `<button>`** on the composer screen; controls are `div[role=button]`,
  so button counts undercount it. Do not read "0" as "no controls".
- Gemini's icon-only count is 0 because its controls carry text nodes inside custom elements;
  `aria-label` coverage (9/11) is the meaningful number.
- ChatGPT's placeholder is rendered by a sibling overlay, not an attribute on the editable.

## Patterns that held across all three

1. **Composer width is stable, not fluid.** 768-774 px on full layouts; Gemini's centred column
   is 373 px. None of them stretch the composer to the viewport.
2. **Composer height is compact.** 40-60 px, one or two lines, growing with content.
3. **Body size 16-17 px.** No 13-14 px interface text in the primary input.
4. **Short instruction as placeholder.** 2-3 words: "Message DeepSeek", "ป้อนพรอมต์สำหรับ Gemini".
5. **Chrome is icon-first and labelled.** ChatGPT: 41 icon-only buttons, 49 with `aria-label`.
   Visual text is dropped; the accessible name is not.
6. **No page title or description above the input.** Hierarchy comes from position and space.
7. **Sidebar is collapsible** and does not reserve width when closed (ChatGPT 340 px open).

## What we adopt

- Chat surface measure around **48rem (768 px)** - matches ChatGPT/DeepSeek containers.
- Input font >= 1rem; placeholder "…" only when the context is obvious, otherwise 2-3 words.
- `aria-label` on every icon control; use native `<button>` where possible so counts and
  keyboard behaviour are standard.
- No visible page description above the composer.

## What we do not copy

- 60 buttons of navigation density; it fits a mature product.
- Custom `div[role=button]` controls instead of native buttons.
- Login walls as a substitute for designing the empty state.

## Re-check

```js
document.querySelectorAll('button').length
[...document.querySelectorAll('button')].filter(b => b.getAttribute('aria-label')).length
// composer: walk up from textarea/[contenteditable] until padding or radius is non-zero
```

Record the date with the numbers; an undated measurement is a rumour.
