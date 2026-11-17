# Skills

Agent Skills for coding assistants: portable `SKILL.md` packages that load only when a task
matches, then bring their own scripts, references and assets.

One entry point. Type `@start <what you want>` and it picks the first skill that fits, follows
it, then decides the next hop from what that step produced. You can still call any skill by id
when you already know which one you need.

## Quickstart

Add the repository to your OpenCode config instead of copying folders:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": ["~/skills"]
}
```

Save the file; OpenCode reloads skills without a restart. If a skill is missing, run
`/reload` once. Then:

```
@start ย้ายโปรเจกต์นี้ไป SvelteKit แล้วทำหน้า dashboard ให้ด้วย
```

The router prints its path, for example `route: start -> project-onboarding -> aiwor`, and
stops when there is something you can act on.

Other agents that read `.agents/skills` or `.claude/skills` can use the same directory. The
global `~/.config/opencode/skills` folder is not needed once this path is configured.

## The single entry

- **`start` routes by request shape, not by topic.** It loads one skill, reads the artifact
  that came out, and only then chooses the next.
- **Four hops maximum.** The chain stops when an artifact exists or two hops add nothing.
- **Explicit beats inferred.** `@aiwor`, `@grill-ai`, `@z3-solver` skip the router.
- **The other skills stay visible.** Hiding them behind the router would also disable normal
  auto-activation; `start` is a habit, not a gate.

Chains that are known to pay off:

| Start with | Then | Gate |
|---|---|---|
| `project-onboarding` | `aiwor` | the repo is mapped but the request is still vague |
| `aiwor` | `decompose` | the plan has more than three steps |
| `grill-ai` | `reality-check` | a load-bearing version or API claim is unverified |
| `skill-creator` | `grill-ai` | the new skill makes a factual claim |

## Skills

Eleven skills, each with one job:

| Skill | Category | Job | Say |
|---|---|---|---|
| [`start`](start/SKILL.md) | meta | Routes one request to the first skill that fits, chains up to four hops, prints the route. | "@start", "เริ่มจากไหน", "ไปไหนต่อ" |
| [`aiwor`](aiwor/SKILL.md) | meta | Interrogates a vague request with two AI roles, then writes a plan with decisions, assumptions and verify commands. | "aiwor", "เอไอถามเอไอ" |
| [`grill-ai`](grill-ai/SKILL.md) | meta | Drafts an answer, grills it with evidence, attacks the survivor, reports computed confidence. | "grill-ai", "ไม่ต้องถาม" |
| [`skill-creator`](skill-creator/SKILL.md) | meta | Creates, scaffolds, lints and repairs skills against the Agent Skills spec. | "สร้างสกิล", "lint skill" |
| [`decompose`](decompose/SKILL.md) | workflow | Turns oversized work into a dependency DAG of verifiable tasks with acceptance criteria. | "แยกงาน", "WBS" |
| [`project-onboarding`](project-onboarding/SKILL.md) | workflow | Surveys an unfamiliar repo into `BOOK.md`, audits it, then plans before any code changes. | "เริ่มงาน", "onboard me" |
| [`reality-check`](reality-check/SKILL.md) | verification | Verifies packages, versions, APIs, flags and paths against real sources instead of guessing. | "อย่าเดา", "check the version" |
| [`z3-solver`](z3-solver/SKILL.md) | formal | Encodes constraint and scheduling problems as SMT, solves them, re-checks the model. | "z3", "จัดตาราง" |
| [`design-review`](design-review/SKILL.md) | ui | Chooses a token system, builds composable components, audits accessibility and copy. | "ตรวจ UI", "design system" |
| [`divination-charts`](divination-charts/SKILL.md) | divination | Computes Thai, Bazi, Vedic, Western and Human Design charts from one birth record. | "ดูดวง", "Bazi" |
| [`thai-name-numerology`](thai-name-numerology/SKILL.md) | divination | Scores a Thai or English name with the traditional digit table and reads the result. | "วิเคราะห์ชื่อ", "ตั้งชื่อ" |

Skills are addressed by **id**, which is the directory name, case-sensitive. The `name` in
frontmatter is a display label only.

## Structure

The collection is flat on disk - one directory per skill - because `doctor` and most clients
scan exactly one level. Grouping lives in data, not folders:

```
<skill>/
├── SKILL.md            required: frontmatter + instructions
├── references/         long tables, playbooks, edge cases (loaded on demand)
├── scripts/            deterministic work: parsing, checks, generation
└── assets/             copy-ready skeletons, schemas, templates
```

- `catalog.json` holds category ids, labels and order. It never lists skill names.
- Every `SKILL.md` declares `metadata.category` (from the catalog) and `metadata.tier`
  (`core`, `specialist`, `product` or `domain`).
- Adding a skill means a directory, one row above, and an existing category; `guard.py`
  fails if any of those is missing.
- Long-form material lives in a separate knowledge base; skills copy an excerpt into
  `assets/` with a `source:` line when they need it.

## Validate

```bash
python skill-creator/scripts/cli.py doctor .          # every skill: errors + warnings
python skill-creator/scripts/guard.py .              # layout, catalog, README, triggers, selftests
python skill-creator/scripts/lint.py design-review    # one skill while iterating
python start/scripts/check_routes.py                 # route table ids resolve
python skill-creator/scripts/guard.py . --strict      # warnings fail
```

Expected today: `11/11 skills pass` from `doctor`, `0 error(s), 0 warning(s)` from `guard.py`,
and `PASS` from `check_routes.py`. Run the route check after any rename or deletion.

## Execution evidence

Every skill must provide evidence from a real execution, not just documentation or a lint
result. The GitHub Actions workflow runs each bundled `scripts/selftest.py`, records raw
stdout/stderr and machine-readable results, captures a report screenshot, and uploads the
evidence as a workflow artifact. See
[`skill-creator/references/evidence-standard.md`](skill-creator/references/evidence-standard.md).

The current runner verifies bundled script tests only. Live agent-host discovery, activation,
and behavior require separate host-specific integration tests; they must not be marked verified
until those tests have actually run.

## Requirements

- Python 3.11+ for every skill script.
- [`z3-solver`](https://pypi.org/project/z3-solver/) for the `z3-solver` skill:
  `python -m pip install z3-solver`. Its `lint` runs without it; `doctor`, `run`, `solve` and
  `sudoku.py` exit 2 until it is installed.
- Node 18+ only for `reality-check/scripts/docs.mjs`, which fetches published docs.
- No package manager or build step; everything else is Python standard library.

## License

MIT, as declared in each `SKILL.md`.
