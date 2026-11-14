# Plan - demo

**Outcome:** Observable end state

**Definition of Done**
- ...

## Schedule
- Total ideal effort: **6.5h**
- Critical-path length (P50): **6.5h**
- With uncertainty (P80): **7.4h** (sigma 1.12)
- Theoretical parallelism: **1.00x** (effort / span)
- Critical path: S1 -> T1

## Waves (parallel batches)
| Wave | Tasks | Effort | Can run concurrently |
|---|---|---|---|
| 1 | S1 | 4.3h | 1 |
| 2 | T1 | 2.2h | 1 |

## Tasks
| ID | Title | Type | Owner | Deps | PERT | Slack | Risk | CP |
|---|---|---|---|---|---|---|---|---|
| S1 | Spike: prove the risky integration works | spike | backend | - | 4.3h | 0.0h | high | YES |
| T1 | Define the interface contract | task | backend | S1 | 2.2h | 0.0h | low | YES |

## Acceptance criteria
**S1 - Spike: prove the risky integration works**
- [ ] Written go/no-go decision with evidence
  - artifacts: docs/spike-s1.md

**T1 - Define the interface contract**
- [ ] Contract reviewed and merged
  - artifacts: api/schema.json

## Top risks
- **S1** Spike: prove the risky integration works - Timebox 1 day.

## Assumptions
- Team of 2 engineers, 6 ideal hours/day each

## Open questions
- Which system owns the source of truth?

## Validator warnings (justify or fix)
- `W_RISK_LOAD` 67% of effort is high-risk; front-load spikes
