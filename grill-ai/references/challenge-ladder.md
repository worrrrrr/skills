# Challenge ladder

Six classes, ordered by **cost of being wrong**, not by ease of checking. Start at the top;
stop adding challenges when the next one cannot change the answer.

| # | Kind | The question it asks | Evidence that settles it |
|---|---|---|---|
| 1 | `fact` | Is the number, version, price, limit or API shape true? | `path:line`, lockfile, official docs, registry |
| 2 | `feasibility` | Can this actually run here - runtime, platform, permissions, quota? | installed version, OS, config, a one-line run |
| 3 | `cost` | What does it cost in money, tokens, latency or maintenance? | pricing page, benchmark, current usage |
| 4 | `risk` | What breaks, leaks or gets deleted if this is wrong? | threat model, permissions, failure path |
| 5 | `fit` | Does it match the user's constraint or existing stack? | the user's words, existing code, conventions |
| 6 | `reversibility` | How expensive is undoing it? | migration path, data, lock-in |

## Writing one challenge

```
claim:       what the draft asserts, as a sentence
challenge:   the specific way it could be false
kind:        one of the six above
```

Good: `claim: "z3-solver 4.13 supports Python 3.13" / challenge: "the wheels may stop at 3.12,
so pip would build from source and need a C toolchain"`.

Bad: `challenge: "is this really the best approach?"` - no claim, no test, no evidence.

## What never to challenge

- A preference the user already stated. Record it as a constraint, not a question.
- Wording, formatting or tone.
- A decision already made in this conversation.
- Anything whose outcome would not change the answer.
- The user's goal itself. Grill the path to it.

## Round discipline

- Round 1: facts, feasibility, cost. These invalidate whole answers.
- Round 2: only the survivors plus anything round 1 exposed. Risk, fit, reversibility.
- No round 3 unless a settled fact changed the shape of the answer; then say why in one line.
- Cap: 7 per round, 12 total. Past that, the request is too big - answer the narrowest useful
  version and name the rest as a risk.

## Smells

| Smell | What it means | Fix |
|---|---|---|
| All challenges are `fact` | you are only checking citations | add feasibility and cost |
| Every challenge resolves instantly | they were rhetorical | pick claims a reviewer would attack |
| Challenges restate the draft | no opposition | phrase each as "this is false if..." |
| A challenge needs the user to answer | it is a preference | assume it, state the impact |
| Ten challenges, same claim | duplication | merge them into one |
