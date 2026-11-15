---
name: skill-creator
description: >-
  Creates, scaffolds, audits and repairs Agent Skills (SKILL.md packages) that follow the
  open Agent Skills specification. Use when the user wants to create a new skill, turn a
  repeated workflow into a reusable skill, validate or lint an existing skill, fix broken
  frontmatter, naming or description rules, decide how to split content across SKILL.md,
  references, scripts and assets, or prepare a skill for publishing. Triggers include
  "create a skill", "new skill", "scaffold skill", "skill-creator", "validate skill",
  "lint skill", "agentskills", "สร้างสกิล", "ทำสกิลใหม่", "ตรวจสกิล", "แก้สกิล".
license: MIT
metadata:
  version: "1.0.0"
  tags: "skills, authoring, meta, agentskills"
allowed-tools: Read Write Edit Bash Glob Grep
---

# Skill Creator

Turn a repeatable workflow into a portable Agent Skill that loads only when it is needed,
then prove it complies with the spec before it ships.

## When to use

- The user wants to create, scaffold or repair an Agent Skill.
- A repeated workflow should become reusable, checkable and version controlled.
- A skill must be audited against the Agent Skills spec (naming, description, references).
- A skill passes review but fails to activate, or activates for the wrong requests.

Triggers: "create a skill", "new skill", "validate skill", "lint skill", "สร้างสกิล", "ตรวจสกิล".

## Operating contract

1. **One skill, one job.** If the description needs "and" between unrelated outcomes, split it.
2. **The description is the product.** It is the only text an agent sees before activation;
   spend effort there before writing the body.
3. **Progressive disclosure is a budget, not a style.** Metadata ~100 tokens, `SKILL.md`
   under ~5000 tokens and 500 lines, everything else on demand.
4. **Never ship unvalidated.** Run `scripts/lint.py`; fix every ERROR, and fix or justify
   every WARN in the final message.
5. **Do not scaffold what a paragraph can do.** A one-line rule belongs in `AGENTS.md`, not
   in a skill.

## Phase 0 - Is a skill the right artifact?

| Need | Use |
|---|---|
| Always-on preference or house style | `AGENTS.md` / instructions file |
| One deterministic command | a script, called directly |
| Recurring task that needs judgment and a stable procedure | **a skill** |
| Rare background detail | `references/` inside an existing skill |

Proceed only if the task recurs, needs judgment, and the agent currently re-derives it.

## Phase 1 - Choose the shape

- Name the single outcome: `<verb> <object>` that the agent could not do before.
- Decide the split with `references/authoring-workflow.md` (instructions vs scripts vs assets).
- Estimate size: if the body would exceed ~200 lines, plan a reference file up front.
- Collect the trigger phrases the user actually types, in every language they use.

## Phase 2 - Write the description first

Formula: **what it does** + **use when** + **triggers**.

```yaml
description: >-
  <Concrete verbs and nouns>. Use when <task shape>, <task shape>, or the user says
  <signal>. Triggers include "<phrase>", "<phrase>", "<Thai phrase>".
```

Hard limits: 1-1024 characters, non-empty, no instructions that belong in the body.
Full guidance and worked examples: `references/descriptions.md`.

## Phase 3 - Scaffold

```bash
python scripts/new.py my-skill                        # minimal skill
python scripts/cli.py new my-skill --scripts --references   # same, one entry point
python scripts/new.py pdf-tools --scripts --references # with resources
python scripts/new.py report-format --dir .. --title "Report Format" \
  --description "Formats reports to the house template. Use when the user asks to format or review a report." \
  --license MIT --allowed-tools "Read Write Bash"
```

`new.py` enforces the name rules, creates the directory named after the skill, fills
`assets/skill-template.md`, adds starter files from `assets/reference-template.md`,
`assets/script-template.py` and `assets/asset-template.md` when asked, then runs the linter.

Options: `--summary`, `--compatibility`, `--force`, `--no-lint`, `--dry-run`.

## Phase 4 - Write the body

Recommended flow (drop sections that do not apply):

1. One-paragraph outcome.
2. **When to use** / **When not to use** - concrete request shapes.
3. **Workflow** - numbered steps, each with a checkable result.
4. **Rules** - hard constraints, stop conditions, escalation.
5. **Progressive disclosure** - one line per bundled file with the condition to read it.

Style: imperative, short lines, tables over prose, no marketing. Keep the highest-frequency
path first. Never duplicate a rule in two files.

## Phase 5 - Add resources

| Folder | Put here | Rules |
|---|---|---|
| `references/` | long tables, playbooks, edge cases, domain rules | one level deep, focused, named from `SKILL.md` with the condition to load |
| `scripts/` | parsing, validation, computation, anything exact | one job, `--help`, stdlib preferred, non-zero exit on failure, actionable errors |
| `assets/` | output skeletons, schemas, lookup tables, images | copy-ready, small |

If a script can prove something (a graph is acyclic, a file parses), prefer the script over
instructions - it is cheaper and reproducible.

## Phase 6 - Lint and fix

```bash
python scripts/lint.py .            # report for the current skill
python scripts/cli.py lint ..       # same, through the one CLI
python scripts/cli.py fix ..        # create missing referenced files, then lint
python scripts/cli.py doctor ..     # audit every skill under a folder
python scripts/lint.py ../my-skill --strict   # warnings fail the build
python scripts/lint.py ../my-skill --json     # machine-readable
python scripts/lint.py --list-codes           # every diagnostic explained
```

Exit `0` means no errors; `1` means at least one error; `2` means the path is not a skill.
The linter checks name/directory agreement, description length and trigger phrasing,
frontmatter types, line and token budgets, broken or orphaned references, nested
references, Python compilation and YAML validity.

After any edit, re-run it. A skill that has not been linted is not finished. The full
pre-publish list is `references/checklist.md`.

## Phase 7 - Prove activation

Write 5 prompts: 3 that must load the skill, 2 near-misses that must not. If it fires on a
near-miss, tighten the description; if it misses, add the missing nouns. Then dry-run the
workflow once with a real request, including every script command.

Verify the tooling itself with `python scripts/selftest.py` after changing either script.

## Phase 8 - Attach execution evidence

Before calling a skill tested or verified, follow `references/evidence-standard.md`.
Use the repository workflow to execute bundled self-tests and capture the generated report.
Distinguish static checks, script tests, live host activation, and behavior verification.
Never treat a lint pass or a generated screenshot as proof of live agent behavior.

## Naming rules

| Rule | Invalid | Valid |
|---|---|---|
| lowercase letters, digits, single hyphens | `PDF-Tools` | `pdf-tools` |
| no leading or trailing hyphen | `-pdf` | `pdf` |
| no consecutive hyphens | `pdf--tools` | `pdf-tools` |
| 1-64 characters | 65+ chars | `data-analysis` |
| equals the directory name | folder `x`, name `y` | both `y` |

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| Skill never activates | description lacks user nouns | add artifacts, request shapes, Thai/English triggers |
| Skill activates too often | description too generic | add a boundary and remove generic words |
| Body truncated or ignored | body over ~5000 tokens | move sections to `references/` |
| Agent reads a missing file | reference typo or deleted file | linter E020, recreate or re-point |
| Same rule drifts in two places | duplication | keep it in `SKILL.md`, delete the copy |
| Script output unusable | script printed prose | add `--json`, exit codes, stderr errors |

## Files

- `scripts/lint.py` - spec, reference and script validator.
- `scripts/cli.py` - one entry point: `new`, `lint`, `fix` (resume a half-finished skill), `doctor`.
- `scripts/new.py` - scaffold a compliant skill directory.
- `scripts/selftest.py` - regression test for both scripts.
- `assets/skill-template.md`, `assets/reference-template.md`, `assets/script-template.py`,
  `assets/asset-template.md` - what `new.py` fills in.
- `references/spec-rules.md` - condensed spec: fields, limits, budgets.
- `references/descriptions.md` - writing descriptions that trigger, with examples.
- `references/authoring-workflow.md` - deciding, splitting, scripts vs instructions.
- `references/checklist.md` - pre-publish checklist mapped to linter codes.
- `references/evidence-standard.md` - evidence levels, capture requirements and release claims.
- `references/landscape.md` - what skills exist publicly today and which archetypes win.