# Evidence report

Append a compact block like this when the answer depends on specific packages, versions or
URLs. One line per claim. Drop it when nothing was checked.

## Checks

| Claim | Check | Result | Source | Date |
|---|---|---|---|---|
| `react@19.1.0` is published | `pkgcheck.py npm react --version 19.1.0` | exists, latest 19.1.0 | registry.npmjs.org | 2026-11-14 |
| `foo-bar-utils` exists | `pkgcheck.py npm foo-bar-utils` | 404 | registry.npmjs.org | 2026-11-14 |
| `requests` installed here | `pkgcheck.py installed python requests` | 2.32.3 | local interpreter | 2026-11-14 |
| spec URL reachable | `pkgcheck.py url https://agentskills.io/specification` | 200 | live | 2026-11-14 |

## Verdicts

- verified: <claim> - <one-line evidence>
- from docs: <claim> - <url> (fetched <date>, version selector <v>)
- inferred: <claim> - follows from <verified facts>
- unknown: <claim> - <what blocked the check>, <what would settle it>

## Notes

- Registry blocked or rate-limited: <which>, so <claims> stay unverified.
- Skipped checks: <list>, because <reason>.
