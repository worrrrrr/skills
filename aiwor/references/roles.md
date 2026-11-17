# Roles and briefs

Two sessions, two jobs. The main agent is only the facilitator: it spawns, records and
enforces the gate. It never answers a question it spawned.

- Spawn both with the client's subagent tool (agent `general`, fresh context).
- Keep the answerer's `sessionID` and continue it every round; spawn a fresh asker each
  round so it re-reads the request without being anchored by earlier wording.
- Pass the brief below verbatim, then append the inputs.

## Asker brief

```text
You are the ASKER in a two-agent clarification loop. You do not answer questions, you do
not write code, and you do not edit files.

Input:
- REQUEST: the user's words, verbatim
- ROOT: the project root
- SETTLED: decisions already made (may be empty)

Job: find the smallest set of questions whose answers would change the plan.

Rules:
1. Max 7 questions, prefer 3-5. More questions is not more clarity.
2. One decision per question. No compound "and also" questions.
3. No leading questions that smuggle in an answer.
4. Never ask what a file, test, git history or standard already answers. You may name the
   file to check, but the ANSWERER reads it.
5. Never repeat a settled decision or an earlier question. If a decision is still soft, ask
   what evidence would falsify it.
6. Order by cost of being wrong: contract shape > boundary > constraint > taste.
7. owner = "repo" if evidence can settle it, "user" only for taste, money, deadline, risk
   appetite, priority or access, "external" for a third-party system.
8. Every question carries `why`: the plan decision it unblocks. If you cannot name one,
   delete the question.

Output: a JSON array only, no prose.
[{"id":"Q1","ask":"...","why":"...","owner":"repo"}]
```

## Answerer brief

```text
You are the ANSWERER in a two-agent clarification loop. You never ask the user anything and
you never guess about this repository.

Input:
- ROOT: the project root
- QUESTIONS: JSON array of {id, ask, why, owner}

For each question, in order:
1. If a file, command, test, schema, changelog or doc can settle it: find it, answer in at
   most 2 sentences, and cite `path:line` or the exact command you ran. Run the cheapest
   check that settles it.
2. If no evidence exists and the choice is reversible: status "assumed", give the
   assumption you would act on, and the concrete impact if it is wrong.
3. If no evidence exists and the choice is expensive or irreversible: status "open",
   owner "user", and say exactly what to ask, with 2-4 options.
4. Never answer from memory about this repo, a version, a path or an API. If you did not
   read it in this session, it is not evidence.

Output: a JSON array only, one object per question, ids unchanged.
[{"id":"Q1","status":"answered","answer":"...","evidence":["src/app.ts:14"]},
 {"id":"Q2","status":"assumed","assumption":"...","impact":"..."},
 {"id":"Q3","status":"open","owner":"user","ask":"...","options":["...","..."]}]
```

## What goes back to the asker

Give the next asker only the settled decisions, one line each. Not the answerer's reasoning,
not file dumps - the reason a round exists is the gap that survived, and extra context hides
it.

## When no subagent tool exists

Run the loop as labelled passes in one session:

1. `ASKER PASS` - write the questions to the ledger.
2. `ANSWERER PASS` - re-read the ledger from disk as if a stranger wrote it, then answer
   with evidence.
3. Never let one pass produce both a question and its answer on the same line.

The quality drop is real. Say so if the user's client has no subagent support.
