#!/usr/bin/env python3
"""Scaffold a spec-compliant Agent Skill directory.

Usage:
    python scripts/new.py my-skill
    python scripts/new.py pdf-tools --dir .. --title "PDF Tools" --scripts --references
    python scripts/new.py report-format --description "..." --license MIT

The generated directory is named after the skill, because the spec requires
`name` to match the directory name. Lint runs automatically when it is done.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
ASSETS = SKILL_ROOT / "assets"

FALLBACK_TEMPLATE = """---
name: {{name}}
description: >-
  {{description}}
{{license_line}}{{compatibility_line}}{{allowed_tools_line}}metadata:
  version: "0.1.0"
---

# {{title}}

{{summary}}

## When to use

- Replace with the concrete situations that should activate this skill.
- Include the words a user would actually type.

## When not to use

- Replace with near-misses that should stay manual.

## Workflow

1. First step.
2. Second step.
3. Verify the result against the definition of done.

## Rules

- Never invent inputs the user did not provide; ask once, then state assumptions.
- Stop and report if a required file or command is missing.

## Progressive disclosure

{{resources}}
"""

FALLBACK_REFERENCE = """# {{title}} reference

Loaded only when `SKILL.md` says so. Keep this file focused on one topic.

- Replace this with the detail that would make `SKILL.md` too long.
- Prefer tables and short rules over narrative.
"""

FALLBACK_SCRIPT = '''#!/usr/bin/env python3
"""Helper for the {{name}} skill.

Keep scripts self-contained: standard library only, clear error messages,
non-zero exit codes on failure. Read arguments, do one job, print the result.
"""

from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TODO: describe the job of this script")
    parser.add_argument("input", nargs="?", help="TODO")
    args = parser.parse_args(argv)
    if not args.input:
        print("error: missing input", file=sys.stderr)
        return 2
    print(f"TODO: process {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

FALLBACK_ASSET = """# {{title}} asset

Templates and static resources live here: document skeletons, schemas,
lookup tables, diagrams. Reference them from SKILL.md by relative path.
"""


def template(name: str, fallback: str) -> str:
    path = ASSETS / name
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return fallback


def fill(text: str, values: dict) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def validate_name(name: str) -> str:
    if len(name) > 64:
        raise SystemExit("error: name must be 64 characters or fewer")
    if not NAME_RE.match(name):
        raise SystemExit(
            "error: name must be lowercase letters, digits and single hyphens "
            "(no leading/trailing hyphen, no '--')"
        )
    return name


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Scaffold a new Agent Skill directory.")
    parser.add_argument("name", help="skill name, also the directory name (kebab-case)")
    parser.add_argument("--dir", default=".", help="parent directory for the new skill (default: .)")
    parser.add_argument("--title", help="human title (default: derived from name)")
    parser.add_argument("--description", help="frontmatter description: what it does and when to use it")
    parser.add_argument("--summary", help="one paragraph under the title")
    parser.add_argument("--license", help="license name, for example MIT")
    parser.add_argument("--compatibility", help="environment requirements, 500 characters max")
    parser.add_argument("--allowed-tools", help='space-separated tools, for example "Read Write Bash"')
    parser.add_argument("--scripts", action="store_true", help="add scripts/<name>.py")
    parser.add_argument("--references", action="store_true", help="add references/<name>-notes.md")
    parser.add_argument("--assets", action="store_true", help="add assets/<name>-template.md")
    parser.add_argument("--force", action="store_true", help="write into an existing directory")
    parser.add_argument("--no-lint", action="store_true", help="skip the validation step")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without writing")
    args = parser.parse_args(argv)

    name = validate_name(args.name)
    parent = Path(args.dir).resolve()
    root = parent / name
    title = args.title or name.replace("-", " ").title()
    description = " ".join(
        (
            args.description
            or f"{title} helper. Use when the user asks for {title.lower()} work; "
            "replace this with the concrete triggers and keywords."
        ).split()
    )
    if len(description) > 1024:
        raise SystemExit(f"error: description is {len(description)} characters (max 1024)")

    summary = args.summary or (
        f"Describe the outcome this skill produces for {title}, in one or two sentences. "
        "State what the agent can do after loading it that it could not do before."
    )

    if root.exists() and any(root.iterdir()) and not args.force:
        raise SystemExit(f"error: {root} already exists and is not empty (use --force to overwrite)")

    plan: list[tuple[Path, str]] = []

    skill_md = template("skill-template.md", FALLBACK_TEMPLATE)
    resources: list[str] = []
    docs: list[tuple[Path, str]] = []

    if args.references:
        resources.append(
            f"- `references/{name}-notes.md` - background detail loaded only when the task needs it."
        )
        docs.append(
            (
                root / "references" / f"{name}-notes.md",
                fill(template("reference-template.md", FALLBACK_REFERENCE), {"name": name, "title": title}),
            )
        )
    if args.scripts:
        resources.append(f"- `scripts/{name}.py` - executable helper; run it instead of doing the work by hand.")
        docs.append(
            (
                root / "scripts" / f"{name}.py",
                fill(template("script-template.py", FALLBACK_SCRIPT), {"name": name, "title": title}),
            )
        )
    if args.assets:
        resources.append(f"- `assets/{name}-template.md` - output skeleton the agent fills in.")
        docs.append(
            (
                root / "assets" / f"{name}-template.md",
                fill(template("asset-template.md", FALLBACK_ASSET), {"name": name, "title": title}),
            )
        )
    if not resources:
        resources.append("- (none yet) - add references or scripts only when SKILL.md cannot stay focused.")

    values = {
        "name": name,
        "title": title,
        "description": description,
        "summary": summary,
        "license_line": f"license: {args.license}\n" if args.license else "",
        "compatibility_line": f"compatibility: {args.compatibility}\n" if args.compatibility else "",
        "allowed_tools_line": f"allowed-tools: {args.allowed_tools}\n" if args.allowed_tools else "",
        "resources": "\n".join(resources),
    }
    plan.append((root / "SKILL.md", fill(skill_md, values)))
    plan.extend(docs)

    if args.dry_run:
        print(f"would create {root}")
        for path, _ in plan:
            print(f"  {path.relative_to(root).as_posix()}")
        return 0

    for path, content in plan:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8", newline="\n")

    print(f"created {root}")
    for path, _ in plan:
        print(f"  {path.relative_to(root).as_posix()}")

    if args.no_lint:
        return 0

    lint = HERE / "lint.py"
    if not lint.is_file():
        print("warning: lint.py not found; validation skipped", file=sys.stderr)
        return 0

    print()
    result = subprocess.run([sys.executable, str(lint), str(root)])
    if result.returncode != 0:
        print(
            "\nNext: fix every ERROR, then run lint again. See references/checklist.md.",
            file=sys.stderr,
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
