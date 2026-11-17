# Question ladder

Ask in this order. A question from a lower rung is only allowed once every rung above it is
settled, because everything below is cheaper to change later.

| Rung | Question about | Example | Owner |
|---|---|---|---|
| 1 Contract | input, output, error behavior, compatibility | "Does a failed row abort the export or become a warning line?" | repo, else user |
| 2 Boundary | what is in, what must not break, what is out | "Must the CSV match the existing JSON exporter's column order?" | repo |
| 3 Constraint | runtime, deadline, offline, permissions, data volume | "Does this run in the 512 MB worker?" | repo, else user |
| 4 Convention | naming, file placement, existing pattern to copy | "Where do other exporters live and what do they export?" | repo |
| 5 Taste | priority, wording, UI choice, acceptable trade-off | "Ship filters later or block on them?" | user |

Rungs 1-4 are the answerer's job. Only rung 5, and rungs 1-3 when the evidence is silent,
reach the user.

## One decision per question

| Bad | Why | Rewrite |
|---|---|---|
| "How should export work?" | unbounded; answer is another essay | "Which columns ship in v1?" |
| "Should we use streaming and pagination?" | two decisions, one of them may be moot | "Is the largest export 10k rows or 10M?" |
| "Don't you think CSV is better than XLSX?" | leading; answer is in the wording | "Which format does the requester open, and with what tool?" |
| "What's the deadline, and is auth needed?" | unrelated facts | split into two questions with separate `why` |

## Kill list

Delete a question when any of these is true:

- a file, test, schema, migration or git log already answers it;
- it has no `why` - no plan decision changes either way;
- it repeats a settled decision, even reworded;
- it asks for an estimate of work instead of a fact about the request;
- it invites "it depends" and cannot be answered in one sentence;
- it is rung 5 while a rung 1 contract is still open.

## Coverage check before handing the batch over

The batch is complete when these can all be written as one sentence each. Missing ones are
the questions you failed to ask:

| Must be answerable | Looks like |
|---|---|
| Outcome | "After this, <actor> can <observable action>." |
| Trigger | "It happens when <event>." |
| Failure path | "When <bad input>, the result is <defined behavior>." |
| Non-goal | "This does not change <adjacent surface>." |
| Proof | "Done is proven by `<command>` returning <result>." |

If a rung-1 answer would invalidate most of the batch, send only that question this round.
Cheap rounds are better than wide ones that all get rewritten.
