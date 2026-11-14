# Verification playbook

Match the claim to the cheapest evidence that can falsify it.

## Evidence hierarchy

1. **You ran it** - command output, test result, installed file read this session.
2. **Registry or API response** - npm/PyPI/crates/GitHub/ NuGet data you fetched.
3. **Official documentation you fetched** - version selector matching the project.
4. **Source code** - the implementation at the installed version.
5. **Secondary writing** - blog, forum, generated summary. Never sole evidence for a
   specific API or version.
6. **Memory** - not evidence. Convert it into one of the above before stating it.

## Claim recipes

| Claim | Recipe |
|---|---|
| Package exists | `pkgcheck.py npm <name>`; 404 means not on npm, not "never existed" |
| Version published | `--version <v>`; compare against `latest` and `versions_count` |
| Dependency safe to add | exists + version fits runtime + not deprecated/archived + license compatible |
| Package installed | `pkgcheck.py installed python <mod>` or `installed node <pkg>` |
| API changed between versions | `pkgcheck.py inspect node <pkg> --cwd .`: version gap, export map, symbols, changelog |
| Dependencies drifted or deprecated | `pkgcheck.py project . --state`: per-dep status + changes since last save |
| Which members exist | read the `.d.ts` that `inspect` names; symbols list is an index, not a signature |
| Function signature | read installed types/source, or docs for the pinned version |
| CLI flag | run `<cmd> --help`; do not trust a remembered flag list |
| Config key | read the schema or the code that loads it |
| Env var | `grep -R "ENV_NAME"` in the dependency, not in a chat memory |
| File path | `ls`/`Glob` the path; if it is in a repo, check the branch |
| URL | `pkgcheck.py url <url>`; 200 for the exact URL, not a redirect target you assumed |
| Repository health | `pkgcheck.py github <owner/repo>`: `archived`, `pushed_at`, license |
| Price, law, date | primary source fetched today; state the effective date |
| Benchmark number | the paper or repo with a version/commit, not a summary of it |

## Version ranges

`--version` accepts a plain version or a range prefix and strips `^ ~ >= > = v`:

```bash
pkgcheck.py npm react --version "^19.0.0"   # checks 19.0.0 is published
```

It does not solve the range against a resolution algorithm. For "does my lockfile satisfy
this range", read the lockfile and compare, or run the package manager's own resolver.

## When the registry is unreachable

Exit code 2 means **unverified**, not missing. Options:

1. Retry once with `--timeout 20`.
2. Check a local cache or lockfile: `npm ls`, `pip show`, `cargo tree`, `dotnet list package`.
3. Report the claim as unverified, name the blocked registry, and stop. Do not downgrade to
   a guess and do not upgrade to a denial.

## Wording that stays honest

| Situation | Write |
|---|---|
| Checked, exists | "`react@19.1.0` is published (npm, checked 2026-11-14)." |
| Checked, missing | "No package `foo-bar-utils` exists on npm (404, checked 2026-11-14)." |
| Could not check | "Unverified: registry unreachable; I could not confirm `foo` exists." |
| Docs only | "Per the v19 docs (<url>, fetched 2026-11-14), ..." |
| Logical conclusion | "Inferred from the two checks above: ..." |

## Timebox

Two attempts per claim, five lookups per answer. After that, answer with explicit gaps.

## Anti-patterns

- Checking `latest` and claiming a pinned version is fine.
- Citing a docs page whose version selector is `next`.
- Treating a search engine snippet as a fetched source.
- Listing five alternatives when the primary was never verified.
- Reporting exit code 2 as "does not exist".
