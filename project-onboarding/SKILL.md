---
name: project-onboarding
description: >-
  Onboards a session into a project before any code is written: scans the workspace,
  collects the project's real commands, reads AGENTS.md and README, records dependency
  and runtime versions in a configurable BOOK.md one item at a time, audits that book
  without bias, then proposes a plan and asks multi-select questions about what is still
  ambiguous.
  Use when work starts in an unfamiliar repository, when the user asks to inspect the
  workspace first or wants a plan before coding, or says "onboard me", "read the project
  before you start", "start from the repo", "เริ่มงาน", "สำรวจโปรเจกต์",
  "ทำความรู้จักโปรเจกต์", "อ่านโปรเจกต์ก่อน", "วางแผนก่อนลงมือ", "BOOK.md".
  Not for a one-line question in a repo whose BOOK.md is already fresh.
license: MIT
metadata:
  version: "1.0.0"
  tags: "onboarding, workspace, book, planning, dependencies, versions"
  category: "workflow"
  tier: "core"
allowed-tools: Read Write Edit Bash Glob Grep
---

# Project Onboarding

Open a project the same way every time: scan it, read what governs it, prove the versions,
write `BOOK.md`, audit it without bias, ask what is still unclear, then write `PLAN.md`.
Steps run in order 1 to 6. Skipping a step invalidates the ones after it.

Commands below run from the project root. `<skill>` is this skill's directory, the folder
holding this `SKILL.md`.

## When to use

- A session starts in a repository you have not worked in yet.
- The user asks to survey the workspace, learn the project, or plan before touching code.
- The user asks for `BOOK.md`, an onboarding brief, or "what is this project".
- Existing `BOOK.md` is stale: its `commit:` differs from the current HEAD.

## When not to use

- One quick question in a repo whose `BOOK.md` commit still matches HEAD - answer directly.
- A repo where `AGENTS.md` already lists every command and the user wants a single edit.
- Deep verification of packages or registry freshness - use the `reality-check` skill.
- Breaking a large task into a task graph - use the `decompose` skill after step 6.

## Where BOOK.md lives

Resolve once in step 1 and reuse the same paths for the whole session:

```bash
python <skill>/scripts/bookdir.py .
```

| Setting | Beats | Scope |
|---|---|---|
| a path the user names in this session | everything | one run |
| `--dir <path>` | env, config | one run |
| `PROJECT_ONBOARDING_DIR` | config | shell or CI |
| config file `~/.config/project-onboarding/config.json` | project root | every run |
| project root | - | default |

Set the default once, then every project writes there:

```bash
python <skill>/scripts/bookdir.py --set "D:/notes/projects"
```

Default layout is `<dir>/<project>/BOOK.md`, so one notes folder holds many projects;
`--flat` drops the project folder. Every `BOOK.md` and `PLAN.md` mentioned below means the
resolved path, not the project root.

## Operating contract

1. **One step per turn.** End the turn with that step's gate line. Two steps in one turn
   is a defect, not speed.
2. **One item at a time inside step 3.** Read a file, append it to `BOOK.md`, then read the
   next. Never batch-read documents.
3. **Every line has a source.** A fact in `BOOK.md` carries a file path, a command, or the
   word `unknown`. Memory is not a source.
4. **Never invent a command.** Only commands printed by `scan.py` exist until one is run.
5. **Minimum tokens.** One scan per step, one file per read, one line per fact, no restating.
6. **Stop at the plan.** Do not execute `PLAN.md` steps until the user approves them.

## Step 1 - Workspace

```bash
python <skill>/scripts/scan.py .
python <skill>/scripts/bookdir.py .
```

Read these lines: `workspace`, `git`, `top`, `docs`, `manifests`, `lockfiles`, `ci` from the
scan, and `book` plus `plan` from the bookdir call. Do not open any project file yet, and do
not recurse into directories by hand.

If the book already exists, compare its `commit:` with the `git` line first. Same commit
and no changed files means steps 1-3 are done: jump to step 4.

Gate: `Step 1 done: <root>, book: <path>, manifests: <list or none>, docs: <list>`.

## Step 2 - Commands

Use the `commands` block from step 1. It is the only command source until something is run.

Append to `BOOK.md` under `## Commands`:

| Intention | Command | Source | Verified |
---|---|---|---|
| run the app | `pnpm dev` | package.json scripts.dev | no |
| test | `pnpm test` | `.github/workflows/ci.yml` | yes |

Rules:

- Copy the command from the manifest; do not rewrite it.
- `Verified: no` until you actually ran it or found it in CI. Never mark it yes from logic.
- No `commands` block means write `none declared` and stop inventing. Conventional commands
  like `make test` do not exist until a file says so.

Gate: `Step 2 done: N commands, N verified`.

## Step 3 - Learn, then check versions

Fixed order. Do not reorder, do not skip an item, do not read ahead.

| # | Item | Read | Append to `BOOK.md` |
|---|---|---|---|
| 3a | `AGENTS.md` | whole file | `## Rules`: commands, layout, forbidden actions, validation gates |
| 3b | `README.md` | whole file, or first 80 lines plus headings above 400 lines | `## Overview`: purpose, entry points, doc links, run instructions |
| 3c | docs linked from 3a/3b | max 3 files, one at a time | merge into `## Rules` or `## Overview`, with the path |
| 3d | dependencies | `scan.py` output only - never open a lockfile | `## Dependencies`: package, range, installed, source |
| 3e | versions | `scan.py` `tools` and `pins` lines | `## Versions`: tool, exact version string, source |

Rules for 3d and 3e:

- Installed beats declared, declared beats claimed. If `scan.py` says `not installed`,
  write that - do not fill the gap from memory.
- Copy version strings exactly, including the `v` and the build suffix.
- Freshness ("latest is 5.x") is not a version check - it belongs to `reality-check`.
- Missing manifest, README or lockfile is a fact: write `none captured` and the consequence.

Gate per item: `BOOK.md += <item> (source: <path or command>)`.
Gate for the step: `Step 3 done: N sections, N deps, N tools`.

Start from `assets/book-template.md`; keep `BOOK.md` under 120 lines. If it grows past that,
keep one line per fact and delete facts the plan does not need - do not add a second file.

## Step 4 - Refresh audit, no bias

Read `BOOK.md` from disk as if a stranger wrote it. The writer in step 3 filled gaps and
believed the README; this pass exists to catch both. Protocol:
`references/refresh-audit.md`.

Minimum pass:

1. Re-run `python <skill>/scripts/scan.py .` and diff `commit`, `tools`, dependency counts.
2. For each line, ask one question: can I paste the evidence? If not, it is not a fact.
3. Apply exactly one action per line: keep, fix, remove, or move to `## Unknowns` with the
   check that would settle it.
4. Do not polish wording. Do not add new sections. Do not research new topics.

Gate: `Step 4 done: N kept, N fixed, N removed, N moved to unknowns`.

## Step 5 - Plan and questions

Draft 3-6 steps in this shape: action, file or command it touches, verify command. Then ask
only the decisions the files cannot answer.

Ask with the client's question tool in multi-select mode (`multiple: true`):

- 2-5 questions maximum, each with 2-4 concrete options plus the free-text option.
- Recommended option first, labelled `(Recommended)`.
- Every option must be executable as written - no "other approach" placeholders.
- Never ask about stack, commands, structure or versions: steps 1-3 answered those. Ask
  about scope, priority, acceptable breakage, data or environment access, and definition of done.
- No real ambiguity means zero questions and one line stating why.

Typical forks: scope cut for the first pass, behaviour to preserve, test depth, whether to
touch generated files, target environment.

Gate: `Step 5 done: plan v1, N questions, N answers`.

## Step 6 - Write the plan

Fill `assets/plan-template.md` at the resolved `plan` path from step 1. Each step needs a
verify command a stranger could run. Close with the decided answers, the out-of-scope list,
and the done criteria. Then stop and wait for approval.

Gate: `Step 6 done: PLAN.md written, waiting for approval`.

## Token discipline

- One `scan.py` call answers layout, commands, pins and versions. Do not re-scan per question.
- Read a file once, whole, if it is under 400 lines; otherwise headings plus the relevant
  section. Never read a lockfile, generated file, or dependency source.
- One fact per line, no prose summaries, no quotes from the README longer than 10 words.
- Stop reading the moment the gate condition is met. Extra context is a cost, not a bonus.

## Files

- `scripts/scan.py` - workspace, docs, commands, pins, toolchain and dependency facts; `--json`, `--no-versions`.
- `scripts/bookdir.py` - resolve or save where `BOOK.md` and `PLAN.md` are written; `--dir`, `--set`, `--show`, `--flat`.
- `assets/book-template.md` - `BOOK.md` skeleton with a source column on every table.
- `assets/plan-template.md` - `PLAN.md` skeleton with verify and done criteria.
- `references/refresh-audit.md` - bias-free audit protocol with the tells that mark a fake fact.
