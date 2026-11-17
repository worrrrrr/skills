# Evidence ladder

Look in this order and stop at the first source that answers the challenge. Cheaper and more
local wins: a lockfile beats a blog post, and a command that runs beats a memory of a command.

| Order | Source | How to read it | Cite as |
|---|---|---|---|
| 1 | The user's own words | the frozen `ask` in the ledger | `ask: "<quote>"` |
| 2 | This repository | `glob`, `grep`, `read` - manifests, lockfiles, config, code | `src/app.ts:14` |
| 3 | Installed code | run the version, `--help` or a one-line import against the real environment | `cmd: python -c "import x; print(x.__version__)"` |
| 4 | Official docs and registries | the maintainer's site, the package registry, the RFC | `https://...` |
| 5 | Authoritative third party | a dated benchmark or a standards body, never a content farm | `https://...` |

## Rules

- One lookup per challenge; a second only when two sources disagree.
- Cite the narrowest thing that proves it: a line, an anchor, a command. Not a homepage.
- Volatile facts (prices, versions, limits) carry the date you checked: `checked 2026-11-18`.
- A search result is not evidence. Open the page and cite the page.
- If nothing answers it in two lookups, mark `assumed`, write the impact, and move on. Do not
  silently upgrade a guess into a fact.
- When sources conflict, prefer the one that runs on this machine, then the newer official
  one. Put the conflict in the final answer, one sentence.

## Tool mapping (OpenCode)

| Need | Tool |
|---|---|
| find a file fast | `glob` |
| find a symbol or string | `grep` |
| read the source of truth | `read` |
| run the thing | `bash` |
| fetch a doc page | `webfetch` |
| two independent lookups at once | `subagent` (parallel) |

## What "resolved" looks like

```jsonc
{"id": "C3", "status": "resolved",
 "answer": "Python 3.15 is current here, so the 3.13 wheel question is moot",
 "evidence": ["cmd: python --version -> 3.15.2"]}
```

If the evidence proves a different answer than the draft, change the answer - not the
evidence.
