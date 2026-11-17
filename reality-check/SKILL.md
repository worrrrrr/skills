---
name: reality-check
description: >-
  Stops the agent from guessing and makes it verify package names, versions, APIs,
  CLI flags, config keys, file paths and URLs against real sources before answering.
  Use when the user asks to check that a library or dependency really exists, confirm
  a version is published or installed, validate a dependency before adding it, review
  an answer for hallucinated packages or made-up APIs, or when any answer would name a
  package, version, flag or path. Triggers include "reality-check", "verify this",
  "does this package exist", "check the version", "is it installed", "don't guess",
  "กันเดา", "อย่าเดา", "เช็กก่อนตอบ", "ตรวจแพ็กเกจ", "ตรวจเวอร์ชัน", "ของจริงไหม".
license: MIT
metadata:
  version: "1.0.0"
  tags: "verification, hallucination, packages, registry, dependencies"
  category: "verification"
  tier: "core"
allowed-tools: Read Write Edit Bash Glob Grep
---

# Reality Check

Every specific claim gets evidence you can show. Guessing is a defect, not a style.

## When to use

- Any answer would name a package, version, API, flag, config key or file path.
- The user asks to verify, fact-check, or confirm something exists.
- A dependency is about to be added, upgraded or recommended.
- You are about to say "deprecated", "does not exist" or "latest".

Triggers: "reality-check", "verify this", "does this package exist", "check the version",
"กันเดา", "อย่าเดา", "เช็กก่อนตอบ", "ตรวจแพ็กเกจ".

## Operating contract

1. **Specific means checkable.** Package names, versions, API signatures, CLI flags, config
   keys, file paths, URLs, prices, dates and numbers are claims. State one only after you
   looked it up or ran it in this session.
2. **Unknown is a valid answer.** "Not verified" beats a plausible invention, every time.
3. **Never invent a package to satisfy a request.** If the package does not exist, say so
   and offer verified alternatives - not a renamed guess.
4. **A 404 is evidence about one registry.** Say which registry you checked and when.
   "Not on npm" is not "does not exist".
5. **Do not cite what you did not open.** No documentation link, changelog line or quote
   that you have not fetched in this session.
6. **Unknown flag, option or subcommand? Run `--help`.** One command beats a paragraph of
   hedging. If the flag is not in `<tool> --help`, it does not exist - do not invent it.

The three checks agents skip most often: run `--help` before quoting a flag, read exit code 2
as *unverified* rather than *missing*, and read the installed version before writing code.
If you do only three things, do these.

## Phase 0 - Classify the claim

| Claim | Verify with | Cost |
|---|---|---|
| Package exists | `pkgcheck.py npm/pypi/crates/nuget/gem/go <name>` | one request |
| Version is published | add `--version <v>` | same call |
| Package is installed / usable here | `pkgcheck.py installed python/node <name>` | local |
| Repository is alive | `pkgcheck.py github <owner/repo>` | one request |
| URL works | `pkgcheck.py url <https://...>` | one request |
| API signature, flag, config key | installed source, `--help`, or the official docs page | read |
| Domain fact (price, law, date) | a primary source you fetched | read |

If the claim is not in this table, decide its evidence before writing the sentence.

## Phase 1 - Package and dependency checks

```bash
python scripts/pkgcheck.py npm react
python scripts/pkgcheck.py npm react --version 19.1.0
python scripts/pkgcheck.py pypi requests --version 2.32.3
python scripts/pkgcheck.py crates serde --json
python scripts/pkgcheck.py github vercel/next.js
python scripts/pkgcheck.py installed python requests
python scripts/pkgcheck.py installed node next --cwd .
python scripts/pkgcheck.py inspect node @sveltejs/kit --cwd .   # read what is installed
python scripts/pkgcheck.py project . --state                   # every dep + drift since last save
python scripts/pkgcheck.py url https://agentskills.io/specification
```

Read the exit code, not just the text:

| Code | Meaning | What you may say |
|---|---|---|
| 0 | exists, requested version published | "exists, latest X, published YYYY-MM-DD" |
| 1 | not found, version not published, or not installed | "not found on <registry> as of <date>" |
| 2 | network or registry error | "unverified: registry unreachable" - never "does not exist" |
| 3 | usage error | fix the command; do not report a verdict |

Before recommending a dependency, all three must hold:

- it exists on the registry the project uses;
- a published version fits the project's runtime;
- it is not archived or deprecated - `pkgcheck.py` reports both flags.

## Phase 1b - Project drift

`pkgcheck.py project . --state` reads `package.json`, resolves what is installed in
`node_modules`, compares every dependency with the registry, and classifies it:

| Status | Meaning | Action |
|---|---|---|
| `CURRENT` | installed equals latest | none |
| `PATCH` / `OUTDATED` | same major, newer release | upgrade when convenient |
| `MAJOR` | newer major exists | breaking changes likely - read the changelog first |
| `DEPRECATED` | registry marks the package deprecated | replace it now (`lucide-svelte` -> `@lucide/svelte`) |
| `MISSING` | not on npm | wrong name or private registry |
| `NOT INSTALLED` / `SKIPPED` | not installed here / workspace or file link | install, or ignore deliberately |

- `--state` writes `.reality-check.json` next to `package.json`.
- Later runs print `changed since last save` with status transitions and new `latest` versions.
- Commit the state file when the team should share a baseline; otherwise add it to `.gitignore`.
- Exit codes: `0` clean, `1` any MAJOR/DEPRECATED/MISSING, `2` registry unreachable, `3` usage.
- Run it after every install, and before answering "is this dependency current?".

## Phase 1c - Match the installed style

A project on the newest majors must be written in the newest style. Copying an old snippet
is the same defect as inventing an API.

```bash
python scripts/pkgcheck.py project . --rules
python scripts/pkgcheck.py scan .          # old-style code already in the repo
```

It prints one line per detected major, for example:

```
write in this style (from installed versions):
  * svelte 5: runes only ($state, $derived, $effect, $props, $bindable); onclick={fn} not on:click; ...
  * tailwind 4: @import "tailwindcss" not @tailwind base/...; shadow-sm->shadow-xs ...
```

Rules of engagement:

1. Read the installed major before writing a component; never assume it from training data.
2. When the file you are editing already uses legacy syntax in a new-major project, say so
   and write the new form - do not imitate the stale code around you.
3. Do not mix: one component must not use both `on:click` and `onclick`.
4. Full old-vs-new tables: `references/framework-rules.md`.

`scan` walks `.svelte`, `.ts`, `.js` and `.css` files (skipping `node_modules`, `.svelte-kit`,
`build`, `dist`) and reports every legacy pattern with file and line: Svelte 5 event
attributes, `export let`, `$:`, `<slot>`, `new App()`, `$app/stores`, `@tailwind` directives,
and the AI SDK 4 call shapes (`maxTokens`, `convertToCoreMessages`, `Chat({` without `new`,
`initialMessages`, `append`, `addToolResult`, `maxSteps`). Exit code 1 means the repo still
contains old-style code.

## Phase 1d - Verify the change before claiming success

Reading docs prevents bad claims; running the project's own checks prevents bad code.

```bash
python scripts/verify.py .          # auto-detects check / typecheck / lint / test / build
python scripts/verify.py ../app --list
python scripts/verify.py ../app --only check
```

It picks the package manager from the lockfile, runs the scripts that exist, and exits
non-zero if any fails. Run it after every edit, and paste the failing output before saying
the work is done. A command that was not run is not evidence.

Rules:

- If the project has a check script, it owns the truth - not your reading of the code.
- Re-run after each fix; a fix can break the next script in the chain.
- Report the exact failing script and the first real error line, not a summary.

## Phase 2 - API, CLI and config claims

Before writing code against a function, print its shipped signature and copy that shape:

```bash
python scripts/pkgcheck.py docs ai --symbol convertToModelMessages --cwd ../app
python scripts/pkgcheck.py docs ai --symbol toUIMessageStreamResponse --cwd ../app
python scripts/pkgcheck.py docs ai-sdk-ollama --readme "Reasoning Support" --cwd ../app
```

The output is the `.d.ts` declaration plus its JSDoc, marked `deprecated` when the source says
so. Implement against that text, not against what you remember: if the return type is
`Promise<...>`, the call is awaited; if the JSDoc says `@deprecated`, do not use it.

When the package is not installed, read the published docs instead of guessing:

```bash
node scripts/docs.mjs zod                       # version + llms.txt / README / page, trimmed
node scripts/docs.mjs react --grep "useEffect"  # only matching lines
node scripts/docs.mjs https://example.com/api   # one page, HTML reduced to text
```

It prints the registry version first, then the best source it found (`llms.txt` -> GitHub
README -> homepage). Cite the version and the source URL it reports; never the package name
alone. Requires Node 18+.

- **Installed code wins.** Run `pkgcheck.py inspect node <pkg> --cwd .` (or `inspect python
  <module>`). It reports the version actually on disk, where it lives, its export map, the
  public symbols parsed from the shipped `.d.ts`, the changelog versions it carries and, when
  the registry is reachable, how far behind `latest` the installed copy is. A major gap means
  the API may have changed: read the changelog before reusing a remembered signature.
- **Read the shipped types.** Open the file `inspect` names and confirm the exact member -
  `pkgcheck.py` lists symbols, it does not resolve overloads or generics.
- **Run `--help`.** For a command you are about to tell the user to run, run `<tool> --help`
  first - not the manual, not memory. On Windows PowerShell use `npx.cmd` (the `npx.ps1` shim
  is blocked by ExecutionPolicy); `bunx <pkg> --help` works unchanged. Quote the flags it
  actually lists, and treat anything absent from that output as non-existent.
- **Quote the docs.** When the claim comes from documentation, fetch the page, confirm the
  version selector matches the project's version, and keep the URL and the exact line.
- **Never trust a remembered signature.** If you cannot read it, mark it unverified and say
  what would settle it.

## Phase 3 - Write the answer

Label every non-obvious claim with one of:

| Label | Meaning |
|---|---|
| **verified** | you ran a check or read the source in this session |
| **from docs** | official documentation you fetched, with URL |
| **inferred** | follows logically from verified facts; say what it follows from |
| **unknown** | not checked; say why and what would check it |

Use `assets/evidence-report.md` as the shape for the evidence block. Keep it short: one line
per claim, source, date, verdict. Do not pad the answer with checks that did not change it.

## Phase 4 - Self-audit before sending

- [ ] Every package name, version, flag, key and path in the answer appears in a command
      output, a file you read, or a page you fetched.
- [ ] No "should work", "probably", "I believe" presented as fact.
- [ ] Alternatives were verified the same way as the primary suggestion.
- [ ] Anything unchecked is labelled *unknown* with the reason.
- [ ] Dates state the day the check ran.

**STOP.** If you cannot paste the evidence for a sentence - a command output, a file line, or
a fetched URL - delete that sentence before sending.

## Hard bans

| Banned | Say instead |
|---|---|
| "The package `foo-bar-utils` provides..." | run `pkgcheck.py`, then quote the result |
| "Use `npm install x@4.2.1`" without a check | confirm 4.2.1 is published first |
| "This API accepts `options.strict`" (from memory) | read the installed types or docs |
| "It doesn't exist" after one 404 | "not found on <registry> as of <date>" |
| "Latest version is 3.x" | the exact version from the registry response |
| Citation without a URL you opened | remove it or fetch it |

## Failure modes this prevents

- **Phantom packages.** Names that pattern-match the ecosystem but were never published. The
  registry returns 404; the honest answer is "does not exist", not a similar-sounding name.
- **Version drift.** A real package, an invented version. `--version` catches it.
- **Stale advice.** Correct for v2, wrong for v5. Check the installed version, not the blog.
- **Archived dependencies.** Exists, installs, but unmaintained. The `archived` flag matters.
- **Wrong registry.** The package is on PyPI, not npm. Check the ecosystem the project uses.

## Cost control

Batch related checks in one script call, cap it at about five lookups per answer, and skip
checks that cannot change the answer. If the task needs more, say which checks you skipped
and why. Never let verification turn into a research project the user did not ask for.

## Files

- `scripts/pkgcheck.py` - registry, repository, URL and installed-package checks.
- `scripts/verify.py` - run the project's own check/typecheck/lint/test scripts.
- `scripts/docs.mjs` - published docs + latest version for a package or URL (Node 18+).
- `scripts/selftest.py` - offline regression tests; `--network` adds live smoke tests.
- `references/verification-playbook.md` - claim-by-claim recipes and evidence hierarchy.
- `references/registries.md` - endpoints, fields and gotchas per ecosystem.
- `references/framework-rules.md` - Svelte 4 vs 5, Kit 2 vs 3, Tailwind 3 vs 4, AI SDK pairing.
- `references/hallucination-patterns.md` - how invented facts look, and the tell for each.
- `assets/evidence-report.md` - evidence block template for answers.
