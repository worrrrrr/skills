# Pre-publish checklist

Work top to bottom. Every ERROR must be fixed; every WARN must be fixed or justified in the
final message.

## Structure

- [ ] Directory name equals `name` in frontmatter (E005).
- [ ] `name` is lowercase, hyphenated, 64 chars or fewer, no `--` (E004, E010).
- [ ] `SKILL.md` is at the skill root, with frontmatter fenced by `---` (E001, E002).
- [ ] Body is not a stub (E009).
- [ ] Only spec fields in frontmatter, or the extra key is deliberate (W012).

## Description

- [ ] States what the skill does and when to use it (W002).
- [ ] 150 characters or more, hard cap 1024 (W001, E007).
- [ ] Contains the nouns a user would type, in every language they use.
- [ ] Has a boundary: what it should not activate for.

## Body

- [ ] Under 500 lines and about 5000 tokens (W003, W004).
- [ ] Headings follow one flow: when to use, workflow, rules, resources (W011).
- [ ] Every step has a checkable outcome.
- [ ] Stop conditions are explicit: ask, refuse, escalate.
- [ ] No duplicated rules across files.

## Resources

- [ ] Every referenced path exists (E020) and stays inside the skill.
- [ ] References are one level deep (W010).
- [ ] Nothing is bundled without a pointer from `SKILL.md` (W006).
- [ ] Reference files are focused; split anything above ~12k chars (W009).
- [ ] Python scripts compile (E011) and were run once for real.
- [ ] Scripts print actionable errors and exit non-zero on failure.

## Metadata

- [ ] `metadata.version` is quoted and bumped for behavior changes (W007).
- [ ] `license` is present if the skill is shared (W014).
- [ ] `compatibility` only when the environment really matters (E008, E013).

## Activation

- [ ] Three realistic prompts load the skill.
- [ ] Two near-miss prompts do not.
- [ ] The workflow was dry-run end to end with a real request.

## Commands

```bash
python scripts/lint.py ../my-skill            # human report
python scripts/lint.py ../my-skill --strict   # warnings block the build
python scripts/lint.py ../my-skill --json     # machine-readable
python scripts/selftest.py                    # verify the tooling itself
```
