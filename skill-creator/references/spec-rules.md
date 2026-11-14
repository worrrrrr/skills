# Agent Skills spec, condensed

Source: <https://agentskills.io/specification>. This file exists so the agent does not
need to re-fetch the spec while creating a skill.

## Directory

```
skill-name/
├── SKILL.md          # required
├── scripts/          # optional: executable code
├── references/       # optional: documentation loaded on demand
├── assets/           # optional: templates, images, data
└── ...               # any extra files are allowed
```

The directory name **must** equal the frontmatter `name`.

## Frontmatter fields

| Field | Required | Constraints |
|---|---|---|
| `name` | yes | 1-64 chars, `a-z0-9-` only, no leading/trailing hyphen, no `--`, must equal the directory name |
| `description` | yes | 1-1024 chars, non-empty, says *what* it does and *when* to use it |
| `license` | no | short string, e.g. `MIT`, or `Proprietary. LICENSE.txt has complete terms` |
| `compatibility` | no | 1-500 chars, only for real environment requirements |
| `metadata` | no | map of string keys to string values |
| `allowed-tools` | no | space-separated string, experimental across clients |

Unknown top-level keys are not part of the spec; clients may ignore or reject them.

## Progressive disclosure

| Stage | Loaded | Budget |
|---|---|---|
| Discovery | `name` + `description` of every installed skill | ~100 tokens per skill |
| Activation | the whole `SKILL.md` body | aim < 5000 tokens, < 500 lines |
| Execution | `scripts/`, `references/`, `assets/` on demand | no fixed limit; keep files focused |

Rules that follow from this:

- Anything the agent needs *every time* goes in `SKILL.md`.
- Anything needed *sometimes* goes in `references/` and is named in `SKILL.md`.
- Anything deterministic goes in `scripts/` so the model does not re-derive it.
- Reference files sit one level deep; avoid chains (A -> B -> C).

## File references

Use paths relative to the skill root, and keep them discoverable:

```markdown
See [the rules](references/spec-rules.md).
Run `python scripts/lint.py .`
```

## Validation

The reference implementation is `skills-ref validate ./my-skill`. `scripts/lint.py` in this
skill covers the same rules offline plus reference and script checks.

## Compatibility notes

- Frontmatter is YAML; quote values that look like numbers or booleans (`version: "1.0"`).
- Wrap long descriptions in folded scalars (`>-`) to keep the line readable.
- `allowed-tools` varies by client: some read a comma-separated list, the spec says spaces.
  Write spaces and let the client adapt, or accept the linter warning deliberately.
