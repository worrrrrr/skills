# AGENTS.md

Instructions for agents working **in this repository**. They are not part of any skill.

## What this repository is

A skills-only repository. Every top-level directory except `.git` is one Agent Skill, and one
skill is one directory containing `SKILL.md`. Do not add applications, scratch projects, build
output or node_modules here. Scratch work belongs outside the repo.

## Before you change anything

1. Read the target skill's `SKILL.md` and only the references it points to. Do not read a whole
   skill to answer a question about one section.
2. Keep one skill = one job. If a change adds a second unrelated outcome, propose a new skill
   instead.
3. Never delete or rewrite a skill's scripts, references or assets without reading them first.

## After you change anything

```bash
python skill-creator/scripts/cli.py doctor .         # all skills, must stay 4/4 pass
python skill-creator/scripts/lint.py <skill>         # one skill while iterating
```

Fix every error. Fix or justify every warning. A skill that has not been linted is not finished.

## Layout rules

- Only these folders go inside a skill: `references/`, `scripts/`, `assets/`.
- Nothing nests deeper than one level below `SKILL.md`; `assets/templates/x.html` triggers
  warning W010, so flatten to `assets/x.html` or prefix filenames.
- Paths written in `SKILL.md` are relative to the skill directory. The agent's shell runs in the
  project, so tell it to prefix the skill path when the cwd differs.
- Do not write globs inside backticks in `SKILL.md` (`assets/harness-*.html` is read as a
  literal path and fails lint with E020). Name real files or name none.

## Writing rules

- Frontmatter: `name`, `description`, optional `license`, `metadata`. The description is the
  product: what it does + when to use it + real trigger phrases in the user's languages.
- Imperative voice, one rule per line, tables over prose, fewer than 7 items per list.
- Do not duplicate a rule in two files. If two copies drift, delete one.
- Mark the checks that cost the most if skipped; do not mark everything as critical.

## Script rules

- Python 3.11+, standard library only, no installs.
- Every script supports `--help`, prints `--json` when useful, and exits non-zero on failure
  (0 ok, 1 negative result, 2 could not check, 3 usage).
- Keep `scripts/selftest.py` passing whenever you touch a script.

## Never commit

`__pycache__/`, `*.pyc`, `node_modules/`, `.app-locked/`, OS metadata. `.gitignore` covers these;
do not force-add them.
