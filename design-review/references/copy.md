# Interface copy

Words are design content. Every visible string does one job.

## Rules

1. **Name by user concept, not system concept.** "Notifications", not "webhook config".
2. **Active voice, imperative for actions.** "Save changes", not "Submit".
3. **Same verb through the flow.** A button that says "Publish" produces "Published".
4. **Sentence case.** Not ALL CAPS labels (a known AI tell).
5. **One job per element.** A heading headings; a label labels; a badge states one fact.
6. **No filler.** Delete "Please note that", "In order to", "Simply".
7. **Specific beats clever.** "Backup runs at 02:00 UTC" beats "Your data is safe".
8. **Errors explain the fix**, never apologise, never vague.
9. **Empty states invite action.** "Ask something to start", not "No data".
10. **Icon-only is allowed** when the meaning is universal (send, close, search), but the
    accessible name must exist (`aria-label`).

## Microcopy budget

| Element | Budget |
|---|---|
| Button | 1-3 words |
| Page title | 1-4 words |
| Field label | 1-3 words |
| Helper text | 1 line, only if the label is not enough |
| Error | 1 sentence: what + fix |
| Empty state | 1 line of direction |

If a string exceeds its budget, the layout is likely doing too much, not the copy.

## Checklist before shipping a screen

- [ ] Every button says what happens.
- [ ] No label is all caps.
- [ ] No two elements say the same thing.
- [ ] Error and empty states exist for every async surface.
- [ ] Icon-only controls have an accessible name.
- [ ] Nothing explains the UI to the UI ("Click here to...").
