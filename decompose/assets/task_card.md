# Task card: <T-id> - <verb + object>

| Field | Value |
|---|---|
| Id | `T<n>` |
| Parent | `<T-id or null>` |
| Type | `task` / `spike` / `milestone` |
| Owner role | `<role>` |
| Estimate | `o=<h> likely=<h> p=<h>` |
| Risk | `low` / `medium` / `high` |
| Depends on | `<artifact or task id>` |

## Why it exists

<one sentence: which outcome this unblocks>

## Acceptance (binary, checkable)

- [ ] <statement that is provably true or false>
- [ ] <command or artifact that proves it>

## Artifacts

- `<path or deliverable>`

## Notes

<constraints, links, assumptions - never requirements that were invented>

---

## Spike variant

For `type: spike`, replace Acceptance with:

- [ ] Written decision: `<option chosen>` because `<evidence>`
- [ ] Timebox respected: `<hours>`
- [ ] Follow-up tasks created from the answer
