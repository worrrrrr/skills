# How invented facts look

Each pattern below is a guess that reads as knowledge. The tell is what to look for; the
check is what to run before repeating it.

| # | Pattern | Tell | Check |
|---|---|---|---|
| 1 | Phantom package | Name is a plausible compound of real ones (`react-use-hover-intent`) | `pkgcheck.py npm <name>` -> 404 |
| 2 | Version that never shipped | Clean number one patch above latest, or a jump that skips releases | `--version <v>`, compare `versions_count` |
| 3 | Renamed package treated as current | Advice cites the old name after a rename | registry record + repo redirect |
| 4 | Invented API method | Verb fits the domain (`client.streamQuery()`) but no signature is quoteable | read installed types/source |
| 5 | Invented option | `{ strict: true }` sounds reasonable, docs never mention it | grep the source for the key |
| 6 | Made-up CLI flag | `--no-cache` exists in a sibling tool, not this one | run `--help` |
| 7 | Config key from another ecosystem | `package.json` field that belongs in `tsconfig.json` | read the schema |
| 8 | Path that was never there | `src/lib/foo/utils.ts` matches the project's shape | `Glob`/`ls` it |
| 9 | Quote from a document | Paraphrase presented as a quote, no page number | fetch the document, quote exactly |
| 10 | Number without provenance | Star count, benchmark, price, "X% faster" | primary source, with a date |
| 11 | Deprecated-but-present | Exists and installs, marked deprecated or archived | `deprecated`, `archived`, last publish |
| 12 | Wrong registry | Package real on PyPI, cited for npm (or vice versa) | check the ecosystem the project uses |
| 13 | Stale version advice | Correct for v2, project is on v5 | read the lockfile, then the docs for that version |
| 14 | Works-on-my-machine assume | "Just run `pnpm dlx x`" without checking the runtime | run it, or state the assumption |
| 15 | Fabricated citation | DOI/URL looks structured | `pkgcheck.py url <url>` |

## Self-audit questions

1. Could I paste the command output that proves this sentence?
2. Did I read the page I am linking, in this session?
3. Is my version the one in the lockfile, or the one in my memory?
4. If the check failed, did I write "unverified" or did I quietly soften the claim?
5. Would a wrong answer here cost the user a broken build, a security issue or money?

Any "no" means the claim is not ready.

## Common causes

- Filling a gap because the user sounded certain.
- Extrapolating from a neighbouring library.
- Summarizing a search result instead of the source.
- Reusing a pattern from a different ecosystem.
- Trusting a docs page for `latest` while the project pins an older version.
