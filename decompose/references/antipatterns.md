# Anti-patterns and fixes

| Anti-pattern | Symptom | Fix |
|---|---|---|
| **Horizontal layers** | "all models", then "all APIs", then "all UI" | re-cut vertically; integrate on day 1 |
| **Big-bang cutover** | one giant "go live" node | ramp steps + rehearsed rollback per step |
| **Vague acceptance** | "works correctly", "clean code" | binary check: command, metric, or artifact |
| **Hidden research** | 3-week task with unknown approach | timeboxed spike with a written decision |
| **Phantom dependencies** | "needs backend" | depend on a named artifact (contract, schema, fixture) |
| **Serial chain of everything** | parallelism ~1.0x | contract-first split; find false dependencies |
| **Padding everywhere** | every task 2x, still late | remove padding, add one explicit project buffer |
| **QA at the end** | one testing phase after all dev | acceptance per task + parity/regression harness early |
| **Micro-tasks** | 60 nodes of 15 minutes | fold into acceptance checklists of a parent |
| **Mixed axes** | siblings overlap in scope | one axis per level; move odd nodes to another parent |
| **Owner-less tasks** | nobody picks them up | `owner_role` required; single-role CP flagged as bus factor 1 |
| **Plan as prophecy** | dates quoted without assumptions | print start date, capacity, P50/P80, open questions |
| **Silent scope growth** | new tasks appear mid-flight | new work enters via re-validation, with a delta note |
| **Milestone inflation** | 10 zero-duration "checkpoints" | milestones only where an external commitment exists |

## Recovery moves when a plan is already stuck

1. **Find the blocked frontier**: `next --done ...` returns nothing -> the DAG has a false
   dependency or an unfinished spike. Inspect the highest fan-in node.
2. **Unblock by mock**: replace a real dependency with a contract + stub task; schedule the
   real integration as a later join.
3. **Shrink the critical path**: split the longest CP node and check whether part of it can
   move off-path (often validation/docs can).
4. **Buy information**: if CP variance is dominated by one node, spike it now even if it
   costs a day - it usually removes several days of `p`.