# {{project}} - Plan

> Generated from `tasks.json`. Do not hand-edit task data here; edit the JSON and re-render.

## Outcome

<observable end state>

## Definition of Done

- <binary, checkable statement>

## Constraints and non-goals

| Constraints | Non-goals |
|---|---|
| <deadline, budget, stack, freeze window> | <what this plan deliberately ignores> |

## Waves (what can run in parallel)

| Wave | Tasks | Parallelism |
|---|---|---|
| 1 | T1, T2 | 2 |
| 2 | T3 (needs T1), T4 (needs T2) | 2 |

## Critical path

`T1 -> T3 -> T7` - <duration range>

## Estimate

| Metric | Value |
|---|---|
| P50 | <range> |
| P80 | <range> |
| Buffer | <where it sits and why> |

## Top risks

| Risk | Impact | Mitigation | Owner |
|---|---|---|---|
| <risk> | <effect> | <spike or contingency> | <role> |

## Open questions

- <question> - blocks <task id>; assumed default: <assumption>

## Validation

```
python scripts/decompose.py validate tasks.json
```
