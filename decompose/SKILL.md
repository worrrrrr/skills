---
name: decompose
description: >-
  Decomposes complex, vague, or oversized work into atomic, verifiable tasks with an
  explicit dependency DAG, critical path, parallel waves, risk spikes and acceptance
  criteria. Use when the user asks to break down / split up a project, plan a refactor
  or migration, scope an epic, build a WBS, roadmap, backlog or sprint plan, estimate
  effort, find what can run in parallel, or says a task is too big, blocked, unclear or
  stuck. Triggers include "decompose", "break this down", "task breakdown", "WBS",
  "plan this refactor", "แยกงาน", "แตกงาน", "ย่อยงาน", "วางแผนงาน".
license: MIT
metadata:
  version: "1.0.0"
  tags: "planning, decomposition, wbs, dag, estimation, project-management"
  category: "workflow"
  tier: "core"
allowed-tools: Read Write Edit Bash Glob Grep
---

# Decomposition Engine

Turn one fuzzy blob of work into a **dependency graph of tasks that each fit in one sitting
and can be proven done**. Output is machine-readable (`tasks.json`) plus human views
(`PLAN.md`, Mermaid graph, CSV).

## When to use

- The work is too big, vague, blocked or already slipping.
- The user asks for a breakdown, WBS, roadmap, sprint plan, dependency order or estimate.
- A refactor, migration or epic needs slices that can ship independently.

Triggers: "decompose", "break this down", "WBS", "แยกงาน", "แตกงาน", "วางแผนงาน".

## Operating contract

1. **Never invent requirements.** Missing facts become `assumptions[]` or `open_questions[]`,
   never silent guesses inside a task.
2. **Every leaf task is verifiable.** If you cannot write a pass/fail check, the task is not
   decomposed yet - split it or turn it into a spike.
3. **The engine validates; you author.** You write `tasks.json`; `scripts/decompose.py`
   proves the graph is legal and computes the schedule. Do not hand-compute critical paths.
4. **Report uncertainty as ranges**, never single-point dates.

## Workflow

### Phase 0 - Frame (do not skip)
Capture in <=6 lines: **Outcome** (observable end state), **Definition of Done**, **hard
constraints** (deadline, budget, stack, freeze windows), **non-goals**, **unknowns**.
If Outcome or DoD is missing and cannot be inferred -> ask *one* consolidated question, then
proceed with stated assumptions. Never block on a question round-trip.

### Phase 1 - Choose the cut axis
Pick the axis that produces independently shippable slices. Details: `references/patterns.md`.

| Axis | Use when | Slice looks like |
|---|---|---|
| Vertical slice / user journey | Product features | thin end-to-end path, UI->DB |
| Data flow / pipeline stage | ETL, ML, compilers | ingest -> normalize -> train -> serve |
| Strangler-fig seam | Legacy refactor/migration | route X% traffic to new impl |
| Component / interface boundary | Systems, services | contract first, then each side |
| Risk-first (spike) | Unknown feasibility | timeboxed experiment -> decision |
| Lifecycle | Ops, infra | provision -> configure -> verify -> cutover |

Rule: **cut by value/risk, not by layer.** "All models, then all APIs, then all UI" defers
integration risk to the end - it is an anti-pattern.

### Phase 2 - Recurse until atomic
Split while **any** test fails (details: `references/atomicity.md`):

- **T1 Size:** PERT mean > 2 ideal days (12h); hard cap 5 days.
- **T2 Single verb:** title chains two verbs -> split at the verb boundary.
- **T3 One owner:** more than one role required -> split, add a handoff artifact.
- **T4 Verifiable:** no binary acceptance check -> split or spike.
- **T5 Independent value:** cannot be merged/demoed alone -> merge upward or re-cut.
- **T6 Uncertainty:** unknown *how*, not just how long -> extract a timeboxed **spike**
  whose deliverable is a written decision, not code.

Depth cap **4 levels**. Deeper means the wrong axis was chosen - return to Phase 1.
Stop splitting below ~30 min of work; fold those into acceptance checklists.

### Phase 3 - Wire the graph
- Dependencies point at **real artifacts** ("needs api/v2/openapi.yaml"), not vibes.
- Prefer contract nodes so downstream work can start against mocks (max parallelism).
- Fan-out >= 3 is a schedule hotspot -> do it early. No cycles; the validator rejects them.

### Phase 4 - Estimate
Three-point per leaf: `o`, `likely`, `p` in ideal hours (or days if `unit: "d"`).
PERT mean `(o + 4*likely + p)/6`, sigma `(p - o)/6`. The engine rolls variance along the
critical path and reports P50/P80. Buffer goes at the end, never as padding inside tasks.
See `references/estimation.md`.

### Phase 5 - Validate & emit
```bash
python scripts/decompose.py init --name my-project --out tasks.json
python scripts/decompose.py validate tasks.json
python scripts/decompose.py plan tasks.json --format md --out PLAN.md
python scripts/decompose.py plan tasks.json --format mermaid
python scripts/decompose.py next tasks.json --done T1,T2
python scripts/decompose.py stats tasks.json
```
`validate` must exit 0 before presenting a plan. Fix every ERROR; fix or explicitly justify
every WARN (the renderer appends them to PLAN.md automatically).

### Phase 6 - Present
Lead with: outcome -> wave table (what runs in parallel) -> critical path -> P50/P80 ->
top 3 risks -> open questions. Attach `PLAN.md`. Keep prose under ~400 words; the artifact
carries the detail. Match the user's language.

## Task schema (v1)

```jsonc
{
  "schema_version": "1.0",
  "project": { "name": "...", "outcome": "...", "definition_of_done": ["..."],
               "unit": "h", "constraints": [], "non_goals": [] },
  "assumptions": [], "open_questions": [],
  "tasks": [{
    "id": "T1",
    "title": "verb + object",
    "parent": null,
    "type": "task",
    "deps": ["T0"],
    "estimate": {"o": 2, "likely": 4, "p": 8},
    "owner_role": "backend",
    "acceptance": ["binary, checkable statement"],
    "artifacts": ["path/or/deliverable"],
    "risk": "low",
    "notes": ""
  }]
}
```
Rollup parents carry no estimate (computed from children). Milestones have zero duration.

## Hard rules

- Leaf without `acceptance` -> ERROR. Cycle / dangling dep / duplicate id -> ERROR.
- Leaf over the 5-day hard cap -> ERROR; over the 2-day soft cap -> WARN.
- Fan-out >= 3, >30% high-risk effort, single-role critical path -> WARN.
- Never print a calendar date without stating the assumed start date and capacity.
- Re-run `validate` after any edit; a plan that has not been validated is not a plan.

## Progressive disclosure

Load only what the current phase needs:
- `references/atomicity.md` - six tests, sizing calibration, worked split, stop conditions.
- `references/patterns.md` - 8 cut axes + playbooks (refactor, ML, data, incident, writing, infra).
- `references/estimation.md` - PERT, buffers, capacity, Monte Carlo upgrade.
- `references/antipatterns.md` - failure modes and recovery moves for stuck plans.
- `assets/plan_template.md`, `assets/task_card.md` - output skeletons.
- `scripts/decompose.py` - validator and scheduler (run `--help` for all commands).
- `scripts/selftest.py` - regression check for the engine; run after editing `decompose.py`.
