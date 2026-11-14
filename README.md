# Skills

A collection of Agent Skills for coding assistants: portable `SKILL.md` packages that load only
when a task matches, then bring their own scripts, references and assets.

Six skills, each with a single job:

| Skill | What it does | Fires when you say |
|---|---|---|
| [`decompose`](decompose/SKILL.md) | Turns vague or oversized work into atomic, verifiable tasks with a dependency DAG, critical path, parallel waves and acceptance criteria. Outputs `tasks.json` + `PLAN.md`. | "break this down", "WBS", "plan this refactor", "แยกงาน", "แตกงาน" |
| [`design-review`](design-review/SKILL.md) | Chooses a token system (color, type, spacing, radius), builds composable layout classes and small components, supports runtime themes, and audits accessibility and copy. | "design this page", "design system", "check contrast", "ตรวจ UI", "ธีม" |
| [`divination-charts`](divination-charts/SKILL.md) | Computes Thai, Bazi, Vedic, Western and Human Design charts from one birth record, with a deterministic Python engine and a Markdown/JSON report. | "ดูดวง", "Bazi", "ลัคนา", "Human Design", "อ่านดวง" |
| [`reality-check`](reality-check/SKILL.md) | Stops guessing and verifies packages, versions, APIs, flags, config keys and URLs against registries or installed code before answering. | "does this package exist", "check the version", "verify this", "อย่าเดา", "เช็กก่อนตอบ" |
| [`skill-creator`](skill-creator/SKILL.md) | Creates, scaffolds, lints and repairs Agent Skills against the open Agent Skills spec, including name/description rules and budget checks. | "create a skill", "validate skill", "lint skill", "สร้างสกิล", "ตรวจสกิล" |
| [`thai-name-numerology`](thai-name-numerology/SKILL.md) | Maps a Thai name and surname to the traditional digit table, sums first name, surname and combined total, reduces the total and reads the meaning. | "วิเคราะห์ชื่อ", "เลขศาสตร์ชื่อ", "ตั้งชื่อ", "ตรวจชื่อ", "ชื่อมงคล" |

## Install

OpenCode discovers skills from these locations:

```
~/.config/opencode/skills
~/.claude/skills
~/.agents/skills
.opencode/skills            (project)
```

Point OpenCode at this repository instead of copying folders, in `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": ["C:/Users/worrr/skills"]
}
```

Use an absolute path, or `~/skills`. Other agents that read `.agents/skills` or
`.claude/skills` can link this directory there. After adding the config, run `/reload` if the
skills do not appear; a session started before the change will not see them.

## Validate

```bash
python skill-creator/scripts/cli.py doctor .          # every skill: errors + warnings
python skill-creator/scripts/lint.py design-review    # one skill
python skill-creator/scripts/cli.py lint --strict .   # warnings fail
```

Expected output today: `6/6 skills pass`.

## Repository conventions

```
<skill>/
├── SKILL.md            required: frontmatter (name, description) + instructions
├── references/         long tables, playbooks, domain rules (loaded on demand)
├── scripts/            deterministic work: parsing, checks, generation
└── assets/             copy-ready skeletons, tokens, split mocks
```

- One skill, one job. If the description needs "and" between unrelated outcomes, split it.
- Everything in `references/`, `scripts/` and `assets/` sits one level below `SKILL.md`.
- Keep `SKILL.md` under ~500 lines; move detail into `references/`.
- Scripts take `--help`, print machine-readable `--json`, and exit non-zero on failure.

## Requirements

- Python 3.11+ for the skill scripts (stdlib only, no installs).
- Node 18+ only for `reality-check/scripts/docs.mjs`, which fetches published docs.
- No package manager, build step or dependencies for the skills themselves.

## License

MIT, as declared in each `SKILL.md`.
