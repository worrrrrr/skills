# Authoring workflow and design decisions

## Should this be a skill?

| Repeating shape | Better artifact |
|---|---|
| "Always be concise", "prefer TypeScript" | `AGENTS.md` / instructions file |
| One command you run yourself | a script, not a skill |
| Knowledge an agent needs only sometimes | a skill |
| A deterministic transformation | a script *inside* a skill |
| Product documentation the user reads | docs site |

Signals a skill is right: the task recurs, needs judgment, has a stable procedure, and
the agent currently re-derives the same steps every time.

## One skill, one job

Split when the description needs "and" between unrelated outcomes:

- "Formats reports **and** reconciles bank statements" -> two skills.
- "Formats reports **and** validates their required sections" -> one skill, one outcome.

Keep one skill when the steps share inputs, outputs or a quality bar.

## Budget table

| Content | Where | Why |
|---|---|---|
| Triggers, workflow, hard rules | `SKILL.md` | needed on every activation |
| Long tables, playbooks, edge cases | `references/*.md` | loaded rarely |
| Repeatable computation, parsing, validation | `scripts/*.py` | deterministic, saves tokens |
| Output skeletons, schemas, images | `assets/*` | copied, not reasoned about |

If `SKILL.md` grows past ~500 lines, promote a section to `references/` and leave a
one-line pointer with the condition for reading it.

## Instructions versus scripts

Write instructions when judgment is required and the path varies.
Write a script when the same transformation runs every time, the result must be exact,
or the model would otherwise hand-write fragile logic (parsing, arithmetic, graph checks).

Script rules:

- one job, named after the job; `--help` explains it
- standard library only unless the dependency is unavoidable and documented
- exit non-zero on failure with an actionable message
- print machine-readable output when another step consumes it (`--json`)

## Writing the body

- Imperative voice, short lines, tables over paragraphs.
- Make stop conditions explicit: when to ask, when to refuse, when to escalate.
- Define done in checkable terms; if it cannot be checked, it is not done.
- Avoid marketing language; the agent does not need persuasion.
- Put the highest-frequency path first, exceptions last.
- Never duplicate a rule in two files; duplicates drift.

## Versioning and maintenance

- `metadata.version` follows semver: bump on any behavioral change.
- Changing the description changes activation for every user; treat it as a breaking change.
- Keep a short "changelog" section only if the skill is shared widely.
- Re-run the linter and the activation prompts after every edit; both are cheap.

## Testing activation

Prepare 5 prompts: 3 that must load the skill, 2 that must not (near-misses). If the skill
fires on the near-misses, tighten the description; if it misses, add the missing nouns.

Then walk the workflow once with a real request and confirm every referenced file and
script command actually works.
