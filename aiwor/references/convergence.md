# Convergence, conflicts and escalation

`validate` proves the ledger is complete. This file decides when the loop should stop
before the ledger is complete, and what to do with what is left.

## Stop earlier than the gate

Stop and escalate when any of these happens:

| Signal | Reading | Move |
|---|---|---|
| A round adds no decision | the asker is circling | end the loop, list what is still open |
| The same answer keeps being re-derived | the question is wrong, not unanswered | merge it into a decision and move on |
| Two rounds of questions about rung 5 | the real gap is a rung-1 contract | go back up the ladder with one question |
| The answerer says "depends on the user" for rung 1-4 facts | it has not looked | send it back once with the file to read; then assume |
| Questions exceed 20 | the request is an epic, not a task | propose the first slice, plan only that |
| Assumptions exceed 3 | the request is under-specified in a structural way | escalate them all in the user batch |

Rounds, question counts and session caps are in `SKILL.md`. This table is about stopping
sooner, not later.

## Conflicts

A conflict is recorded when two decisions cannot both hold: `D1 "reuse the JSON exporter"`
and `D2 "CSV has different columns"`. Resolution order, first match wins:

1. **User statement** - the user said it out loud in this session.
2. **Newer evidence** - a file at HEAD beats a remembered convention.
3. **Tests and schemas** beat prose docs, which beat comments.
4. **The stricter option** - the one that preserves behavior and can be relaxed later.

Write the winner and the reason into `conflicts[].resolution`, flip `status` to `resolved`,
and add a decision that states the outcome. Never silently delete the loser: a future reader
will propose it again.

If the order above cannot decide, the conflict is a real fork. That is one user question,
phrased as the choice between the two decisions, not as an open-ended "what do you think".

## What "clear" means per request type

The gate is generic; these are the facts that must exist before it opens. Use the column for
the request in front of you as the answerer's checklist.

| Request | Must be settled |
|---|---|
| Bug fix | repro command, expected vs actual, environment, surfaces that must not change, regression test location |
| Feature | user-visible outcome, input and output shape, failure behavior, out of scope, acceptance check |
| Refactor | behavior frozen, seams to cut at, rollback, safety net (tests or snapshot), performance budget |
| Migration / upgrade | target version, breaking changes list, data compatibility, rollback, order of cutover |
| Ops / infra | environment, access and credentials source, blast radius, rollback, monitoring signal |
| Docs / writing | audience, length, must-include, must-avoid, format and location |

A request that fits none of these gets its own five-line checklist: outcome, boundary,
failure, proof, non-goal.

## Escalating to the user

One batch, at the end, in the user's language.

- Ask only what evidence cannot settle: priority, budget, deadline, risk appetite, access,
  or a tie between two defensible designs.
- Every option must be executable as written, not "another approach".
- Never ask what the repo answered in phases 1-4. That is the failure this skill exists to
  prevent.
- After the answers: record each as `answered` with `evidence: ["user:<date>"]`, re-run
  `validate`, then write the plan.

## Assumption debt

Assumptions are allowed, hidden ones are not. Before the plan is presented:

- every assumed question appears in `PLAN.md` under **Assumptions in force** with its
  impact copied from the ledger;
- more than three assumptions means the plan is a guess with steps - escalate instead;
- an assumption that would change the file layout, the public API or the data model is not
  an assumption, it is a user question.
