---
name: grill-ai
description: >-
  Grills the agent's own answer before the user sees it: freezes the request, drafts the
  claim set, raises five to seven challenges ordered by cost of being wrong, settles each
  from repository or official-document evidence, then attacks the surviving answer with the
  strongest counter-argument. Reports the answer with computed confidence, visible
  assumptions and the evidence that would change it, without interviewing the user. Use when
  the user is tired of answering questions ("don't ask me, figure it out"), asks for a
  researched recommendation or decision, or wants an answer stress-tested before acting on
  it. Triggers include "grill-ai", "grill the AI", "answer without asking me", "think it
  through yourself", "research it and answer", "หาข้อมูลแล้วตอบเอง", "ขี้เกียจตอบ",
  "ถามเองตอบเอง", "กริลเอง". Not for turning a vague coding request into a plan (use
  aiwor), not for checking one package, version, API or flag (use reality-check), and not
  for asking the user about their own preferences - ask them directly.
license: MIT
metadata:
  version: "1.0.0"
  tags: "reasoning, self-review, research, decisions, no-questions"
  category: "meta"
  tier: "core"
allowed-tools: Read Write Edit Glob Grep Bash
---

# Grill AI - interrogate the answer, not the user

The user gives one request and does not want to be interviewed. The agent drafts an answer,
finds every claim that could be wrong, settles each claim with evidence, then tries to break
its own conclusion. The user receives the surviving answer plus the challenges it survived.

## When to use

- The user says "don't ask me, figure it out", or is visibly bored of questions.
- The request needs research or a recommendation, not just code.
- A decision is expensive to reverse and should be stress-tested first.
- An earlier answer felt confident but turned out to be a guess.

## When not to use

- Turning a vague coding request into a plan with tasks -> `aiwor`.
- Verifying one package, version, API, flag or URL -> `reality-check`.
- Interviewing the user about their own preferences -> ask them directly, once.
- The answer is a single fact you can paste from a file you already read.

## Operating contract

1. **No questions to the user.** A question costs a turn the user refused to spend. Ask only
   when the request is unsafe or impossible without a secret: credentials, payment, or a
   destructive irreversible action. Then ask exactly one.
2. **Draft first, grill second.** A challenge needs a target. Write the answer you would
   send, then attack it.
3. **Evidence or assumption.** Every challenge ends `resolved` with a `path:line`, a URL or
   a command, or `assumed` with the impact if wrong. "I think" is not a status.
4. **Attack the survivor.** After the fixes, state the strongest argument against the final
   answer and say whether it survived or what changed.
5. **Confidence is computed.** The script derives it from assumptions, not from tone.
6. **Stop at the answer.** This skill delivers a researched answer, not a task graph and not
   code.

Caps: 7 challenges per round, 2 rounds (3 hard), 12 total. Hitting a cap means deliver with
lower confidence and name what is unresolved.

## Workflow

| Phase | You do | Gate line before moving on |
|---|---|---|
| 0 Freeze | copy the request verbatim | `ask: <n> words, deliverable: answer` |
| 1 Draft | write the answer you would send | `draft: <n> claims` |
| 2 Challenge | 5-7 attacks, cost-ordered | `round 1: <n> challenges` |
| 3 Settle | evidence or assumption per challenge | `settled: <n> resolved, <n> assumed, 0 open` |
| 4 Attack | strongest counter, revise or survive | `counter: survived/revised` |
| 5 Report | check, then render | `check: PASS, confidence: <level>` |
| 6 Deliver | answer in the user's language | `delivered: <n> words` |

### Phase 0 - Freeze

```bash
python <skill>/scripts/grill.py init --ask "<verbatim request>" --deliverable answer --out grill.json
```

Verbatim, not a summary. The wording contains the constraint you would otherwise drop.

### Phase 1 - Draft

Write `draft` in the ledger: the direct answer, two to five sentences. Then list the claims
it makes. A claim is anything that would change the answer if it were false: a version, a
price, an API shape, a limit, a dependency, a legal rule.

### Phase 2 - Challenge

Raise 5-7 challenges against those claims, ordered by cost of being wrong. Use the classes
and order in `references/challenge-ladder.md`.

```jsonc
{"id": "C1", "round": 1, "kind": "fact",
 "claim": "the draft says X", "challenge": "X may be false because Y",
 "status": "open"}
```

Do not challenge taste, wording, or anything the user already decided. Five real challenges
beat fifteen decorative ones.

### Phase 3 - Settle

Work the evidence ladder in `references/evidence-ladder.md`: the repository, then installed
code and lockfiles, then official docs or registries, then the user's own words. Stop at the
first source that answers the question; cite it exactly.

```jsonc
{"id": "C1", "status": "resolved", "answer": "X is 2.1",
 "evidence": ["package.json:14", "https://example.com/docs#x"]}
{"id": "C2", "status": "assumed", "answer": "assume the free tier",
 "impact": "if paid, the cost estimate triples and a budget step is needed"}
```

If two sources disagree, prefer the one that runs on this machine and record the conflict in
the answer.

### Phase 4 - Attack

Write `counter`: the single strongest objection a smart reviewer would raise against the
answer you now believe. Then either revise the answer or mark `survives`. An answer that
never changed after this step was not really attacked.

### Phase 5 - Report

```bash
python <skill>/scripts/grill.py check grill.json        # must exit 0
python <skill>/scripts/grill.py report grill.json --out GRILL.md
```

`check` refuses an open challenge, a claim without evidence, an assumption without impact,
and a confidence higher than the evidence supports. That refusal is the product.

### Phase 6 - Deliver

Answer in the user's language, under ~300 words unless they asked for depth, in four parts:

1. The answer first, in one or two sentences.
2. Why it holds - the two or three challenges that mattered, with their sources.
3. Assumptions and what breaks if they are wrong.
4. The one thing that would change the answer.

Link `GRILL.md`; do not paste the whole table. End with no questions. If something is still
unresolved, name it as a risk with the cheapest next check.

Skeleton: `assets/answer-template.md`.

## Confidence

| Computed | When | What you may claim |
|---|---|---|
| high | every challenge resolved with evidence, 0 assumed | "this is the answer" |
| medium | 1-2 assumed, rest evidenced | "this is the answer if <assumption>" |
| low | 3+ assumed or a scope-level assumption | "best answer available; confirm <X> first" |

Declaring `high` with assumptions is an error, not optimism.

## Ledger schema (v1)

```jsonc
{
  "schema_version": "1.0",
  "ask": "verbatim request",
  "deliverable": "answer",
  "round": 1, "max_rounds": 2,
  "draft": "the first answer",
  "challenges": [{ "id": "C1", "round": 1, "kind": "fact|feasibility|cost|risk|fit|reversibility",
                   "claim": "...", "challenge": "...",
                   "status": "resolved|assumed|open",
                   "answer": "...", "evidence": ["path:line"],
                   "impact": "required only when assumed" }],
  "counter": { "text": "strongest objection", "verdict": "survives|revised",
               "change": "what changed" },
  "verdict": { "answer": "...", "confidence": "high|medium|low",
               "would_change": "the evidence that flips it" }
}
```

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Answer reads like the first draft | challenges were rhetorical | challenge numbers, limits and failure paths |
| Confident and wrong | popularity or memory used as evidence | cite `path:line`, URL or command output |
| User gets a question anyway | repository facts escalated to the user | answer from the repo; assume and label |
| Endless grilling | challenges outside the claim set | drop anything that cannot change the answer |
| Report longer than the answer | pasted table | link `GRILL.md`, keep the message under 300 words |
| Same output as aiwor | wrote a plan | this skill stops at an answer; no task graph |

## Files

- `scripts/grill.py` - ledger init, gate check, markdown report.
- `scripts/selftest.py` - regression tests; run after editing the script.
- `references/challenge-ladder.md` - six challenge classes, order, and what never to challenge.
- `references/evidence-ladder.md` - where to look, in what order, how to cite, how to record conflict.
- `assets/answer-template.md` - the four-part delivery skeleton.
