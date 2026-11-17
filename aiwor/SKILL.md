---
name: aiwor
description: >-
  Turns a rough request into a plan by making two AI roles interrogate each other: an
  asker that finds every gap which would change the plan, and an answerer that settles
  each gap from evidence in the repo or records an explicit assumption, round after round,
  until nothing is open. Writes a question ledger, then a plan with decisions,
  assumptions, scope, steps and verify commands. Use when the user gives a vague, large
  or under-specified request and wants the questions resolved before any code is written,
  when they want the AI to clarify with itself instead of interviewing them for twenty
  turns, or when a plan keeps changing because the request was never pinned down.
  Triggers include "aiwor", "ask each other until it is clear", "clarify before you
  code", "เอไอถามเอไอ", "ถามกันให้เคลีย", "เคลียร์โจทย์ก่อน",
  "ยังไม่ชัด อย่าเพิ่งเขียน", "สรุปแผนก่อนลงมือ". Not for one-line edits whose scope is
  already obvious.
license: MIT
metadata:
  version: "1.0.0"
  tags: "requirements, clarification, multi-agent, planning, spec"
  category: "meta"
  tier: "core"
allowed-tools: Read Write Edit Bash Glob Grep Subagent
---

# AIWOR - ask, answer, repeat, then plan

The user says what they want once. An **asker** finds what is still missing, an
**answerer** settles it from the codebase, and the loop runs until no question is open.
Only then does a plan exist, and every line of it traces back to a decision or a stated
assumption.

Commands below run from the project root. `<skill>` is the folder holding this `SKILL.md`.

## When to use

- The request is vague, oversized, or missing the facts a plan needs.
- The user asks to clarify before coding, or to have the AI ask itself instead of them.
- A previous plan kept changing because the request was never pinned down.
- A handover needs the questions and their evidence written down.

## When not to use

- The edit is one line and its scope is already obvious - just do it.
- The user asked for a task graph - use `decompose` after this skill's plan exists.
- The user wants the project surveyed before planning - use `project-onboarding` first.

## Operating contract

1. **Two roles, never one pass.** The asker never answers. The answerer never decides what
   the user wants. If the client has no subagent tool, run the roles as separate numbered
   passes and label them; never let one pass both ask and answer the same question.
2. **Evidence beats opinion.** A question is answered only with a path, a command output or
   the user's own words. Otherwise it is `assumed`, with the impact if it is wrong.
3. **Clear is a file, not a feeling.** `interview.py validate` exits 0 before any plan. A
   plan written while a question is open is a defect.
4. **Ask the user once, at the end.** AI answers everything the AI can; the user gets one
   short batch of the decisions only they can make.
5. **Every assumption is visible** in the plan with its blast radius. Silent guesses are
   what this skill exists to delete.
6. **Stop at the plan.** No code, no file edits outside the ledger and plan, until approved.

Caps: 4 rounds (6 hard), 7 questions per round, 20 total, 2 subagent sessions. Hitting a
cap means escalate, not continue.

## The loop

| Phase | Who | Gate line before moving on |
|---|---|---|
| 0 Start | you | `round 0: ledger at <path>` |
| 1 Ask | asker | `round N: N questions` |
| 2 Answer | answerer | `round N: N answered, N assumed, N open` |
| 3 Record | you | `round N recorded: N decisions, N open, N conflicts` |
| 4 Repeat or stop | you | `converged: yes/no` |
| 5 Ask the user | you | `user round: N questions, N answers` |
| 6 Plan | you | `plan: <path>, waiting for approval` |

### Phase 0 - Start the ledger

```bash
python <skill>/scripts/interview.py init --topic "<short name>" \
  --request "<the user's words, verbatim>" --out interview.json
```

Copy the request, do not paraphrase it. A paraphrase at this step hides the ambiguity the
whole loop is meant to find.

### Phase 1 - Ask

Spawn the asker with the brief in `references/roles.md`, passing: the verbatim request, the
project root, and the settled decisions so far (Phase 2 output, or `none` on round 1).

- 3-7 questions, each `{id, ask, why, owner}`.
- Order by cost of being wrong, using the ladder in `references/question-ladder.md`.
- A question the repo can answer is not a question - it is a task for the answerer.

### Phase 2 - Answer

Spawn the answerer once, then continue **the same session** with `sessionID` on every later
round so evidence accumulates. Give it the JSON batch from:

```bash
python <skill>/scripts/interview.py next interview.json --json
```

It returns one result per question: `answered` (answer + `path:line` or the command it ran),
`assumed` (assumption + impact), or `open` with `owner: "user"` when only the user knows.
It must not answer this repo from memory; `reality-check` rules apply.

### Phase 3 - Record

Append the results to `interview.json` (schema below), promote settled answers to
`decisions[]`, and record contradictions in `conflicts[]`. Then:

```bash
python <skill>/scripts/interview.py validate interview.json
python <skill>/scripts/interview.py status interview.json
```

A conflict is two decisions that cannot both hold. Record it; do not delete the loser.

### Phase 4 - Repeat or stop

Open a new round only for questions still `open`, plus any conflict. Stop when:

- `status` reports `CONVERGED`, or
- the asker produces no question that changes a decision, or
- a cap is hit - then escalate what remains instead of looping.

Full stop rules and per-request-type clarity checklists: `references/convergence.md`.

### Phase 5 - Ask the user, once

Only `owner: "user"` questions and unresolved scope/priority forks belong here. Ask them in
one batched multi-select call (max 4 questions, recommended option first, every option
executable as written). Record each answer as an `answered` question with evidence
`user:<date>`, then re-run `validate`. If nothing is genuinely user-owned, skip this phase
and say why.

### Phase 6 - Plan

```bash
python <skill>/scripts/interview.py validate interview.json   # must exit 0
python <skill>/scripts/interview.py plan interview.json --out PLAN.md
python <skill>/scripts/interview.py render interview.json --out INTERVIEW.md
```

Fill every `<...>` in `PLAN.md`: out-of-scope, numbered steps, a verify command per step,
binary done criteria. `plan` refuses to write while anything is open - that refusal is the
feature, not an obstacle.

Present in the user's language, under ~400 words: outcome, the decisions that shaped it,
the assumptions and their blast radius, the steps, the biggest risk. Then stop and wait for
approval.

## Ledger schema (v1)

```jsonc
{
  "schema_version": "1.0",
  "topic": "short name",
  "request": "the user's words, verbatim",
  "round": 1,
  "max_rounds": 4,
  "questions": [{
    "id": "Q1",
    "round": 1,
    "ask": "one decision, one sentence",
    "why": "the decision this unblocks",
    "owner": "repo",              // repo | user | external
    "status": "answered",         // open | answered | assumed
    "answer": "what was found",
    "evidence": ["src/app.ts:14"]
    // assumed instead: "assumption": "...", "impact": "what breaks if wrong"
  }],
  "decisions": [{ "id": "D1", "text": "settled choice", "question": "Q1",
                  "evidence": ["src/app.ts:14"] }],
  "conflicts": [{ "id": "C1", "between": ["D1", "D2"], "text": "why they clash",
                  "status": "resolved", "resolution": "which one wins and why" }]
}
```

`answered` without evidence is an error, and so is `assumed` without an impact. That is the
point: it is impossible to record a guess as a fact.

## Convergence gate

| Condition | Code | Meaning |
|---|---|---|
| no questions recorded | `E_EMPTY` | the loop never ran - run the asker |
| any `open` question | `E_OPEN_Q` | not clear yet, answer or assume it |
| any `open` conflict | `E_OPEN_CONFLICT` | two decisions clash, pick one |
| `round > max_rounds` | `E_ROUND_OVER` | stop and escalate |
| `answered` without evidence | `E_EVIDENCE` | a claim with no source |
| `assumed` without impact | `E_IMPACT` | a hidden risk |

Warnings (`W_ASSUMED`, `W_NO_DECISIONS`, `W_MANY_QUESTIONS`) do not block the plan but must
appear in it or be justified in the final message.

## Cost control

- One asker call and one answerer call per round; reuse the answerer session.
- No re-reading a file the answerer already cited; cite the same line.
- Stop reading once `status` says `CONVERGED`.
- If the loop reaches 20 questions, the request is too big - propose a first slice instead.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Endless rounds, no new decisions | asker asks what it can check itself | enforce the ladder; drop questions with no `why` |
| Plan keeps changing | assumptions never written down | `assumed` questions must carry an `impact` |
| Answerer invents an API or path | answered from memory | demand `path:line` or a command; otherwise `open` |
| User annoyed by questions | repo facts escalated as user questions | user-owned means taste, money, deadline, risk, priority |
| Plan reads like a wish list | no verify command per step | fill every `<verify:>` before presenting |
| Two agents agree on everything | answerer also asking | keep roles in separate sessions |

## Files

- `scripts/interview.py` - ledger init, convergence gate, interview render, plan scaffold.
- `scripts/selftest.py` - regression tests for the ledger; run after editing the script.
- `references/roles.md` - the asker and answerer briefs to pass verbatim.
- `references/question-ladder.md` - what to ask, in what order, and what to never ask.
- `references/convergence.md` - stop rules, conflict order, per-request-type clarity checks.
