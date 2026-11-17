# Refresh audit, no bias

Step 3 wrote `BOOK.md` while reading: it filled gaps, trusted headings, and kept what
looked useful. Step 4 reads the same file as a stranger with no memory of writing it.

## Rules of the pass

1. Read `BOOK.md` from disk, top to bottom, once. Do not page back through the conversation.
2. Judge each line by one test: can I paste the evidence for it right now?
3. Apply exactly one action per line: keep, fix, remove, move to `## Unknowns`.
4. Do not rewrite style, add sections, or start new research. If a line needs more than a
   minute to settle, it becomes an unknown.
5. The pass is done when every line has an action and a source.

## False-fact tells

| Tell | Why it is not a fact | Fix |
|---|---|---|
| Vague verb: "supports", "handles", "is set up for" | describes intent, not code | quote the file and line, or remove |
| Row with no source | remembered, not read | add the path or drop it |
| "latest", "current", "modern" | moves with time | exact version string from a command |
| Command nobody ran | could be conventional | mark `Verified: no` or remove |
| README adjective: "fast", "simple", "production-ready" | marketing, not behaviour | delete |
| Version without an install path | declared range mistaken for installed | `not installed` or the resolved version |
| A section that restates the README heading | costs context, adds nothing | one line with the path |
| Confidence words: "clearly", "obviously", "should" | covers a missing check | the evidence or an unknown |

## Freshness check

Re-run `python <skill>/scripts/scan.py .` and compare:

- `commit` against the `commit:` line in `BOOK.md` - different means every file-derived line
  is suspect; re-check the changed areas.
- `tools` against `## Versions` - any drift means at least one line is stale.
- dependency counts against `## Dependencies` - a new package or section invalidates the table.

## Report shape

```
Step 4 done: 18 kept, 3 fixed, 2 removed, 2 moved to unknowns
risk: <the unknown most likely to change the plan>
```

The three riskiest unknowns are the ones the plan consumes. Keep them at the top of
`## Unknowns` so step 5 can turn them into questions.
