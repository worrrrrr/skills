# Atomicity: when to stop splitting

A task is **atomic** when one person can pick it up, finish it in one sitting, and prove
it is done without asking anyone "is this finished?".

## The six tests

| # | Test | Fail signal | Action |
|---|---|---|---|
| T1 | Size | PERT mean > 2 ideal days (12h) | split by sub-outcome |
| T2 | Single verb | title chains two verbs ("build X and deploy Y") | split at the verb boundary |
| T3 | One owner | needs backend + design + legal | split per role, add a handoff artifact |
| T4 | Verifiable | acceptance says "works well" / "is clean" | write a binary check or make it a spike |
| T5 | Independent value | cannot be merged/demoed alone | merge upward or re-cut vertically |
| T6 | Known how | you cannot list the steps | extract a timeboxed spike first |

T2 nuance: noun coordination is fine ("implement update and cancel" = one state machine).
Verb coordination is not ("implement auth and migrate the DB").

T5 nuance: a task may be non-demoable to users but still valuable if it produces a
**consumable artifact** (a contract, a fixture, a runbook). That counts.

## Sizing calibration (ideal hours, solo, no meetings)

| Size | Hours | Typical shape |
|---|---|---|
| XS | 0.5-1 | config flag, copy change, one test case |
| S | 1-3 | one function + tests, one endpoint against a known contract |
| M | 3-6 | one module, one migration with rollback, one dashboard |
| L | 6-12 | one vertical slice end-to-end - **upper bound of atomic** |
| XL | >12 | not a task; a container. Split. |

If everything you write is M or L, you are estimating clock hours, not ideal hours.
Ideal hours assume uninterrupted focus; convert with capacity, not by inflating tasks.

## Worked split

**Before:** "Migrate the orders service to v2" (estimate: 3 weeks, acceptance: "it works")

Fails T1, T2, T4, T6.

**Cut axis:** strangler-fig seam (risk-first, then read/write separation).

```text
S1  Spike: prove dual-write consistency        (timebox 1.5d, output: decision doc)
T1  Freeze the v2 contract                     (unblocks 3 parallel branches)
T2  Build parity replay harness                (QA, parallel with T3/T4)
T3  Implement read path                        (backend A)
T4  Implement create path                      (backend B)
T4b Implement update/cancel transitions        (backend B, after T4)
T5  Wire shadow-traffic diff                   (join point)
T6  Ramp 1% -> 100% with rollback rehearsal    (high risk, explicit mitigation)
T7  Retire v1 endpoints                        (cleanup, low risk)
M1  Declare complete                           (milestone, zero duration)
```

Why this is better: integration risk moved from week 3 to day 1 (S1); three branches run
in parallel after T1; every leaf has a pass/fail check.

## Splitting moves (pick one, do not mix axes mid-level)

1. **By workflow step** - draft -> review -> publish.
2. **By business rule** - happy path first, then each validation rule.
3. **By data variation** - one entity type, then the rest.
4. **By interface** - contract, producer, consumer, contract tests.
5. **By operation** - CRUD split; read path vs write path.
6. **By platform/tenant** - one region/tenant first, then fan out.
7. **By risk** - spike, then implementation, then hardening.
8. **By quality level** - make it work, make it right, make it fast (separate tasks!).

## Stop conditions

Stop splitting when all six tests pass **and** the overhead of tracking the task exceeds
the work (< ~30 min). Below that, fold into a checklist inside the parent task's
acceptance criteria rather than creating a node.

## Depth discipline

Level 1 = outcome streams (3-6 nodes). Level 2 = shippable slices. Level 3 = atomic tasks.
Level 4 = only for genuinely large programs. If you need level 5, your level-1 axis is wrong.