#!/usr/bin/env python3
"""Self-test for the skill-creator scripts.

Runs the linter against a good skill, a broken skill and a missing reference,
then scaffolds a skill with new.py and checks that it validates. Exits non-zero
if any expectation fails.

Usage:
    python scripts/selftest.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LINT = HERE / "lint.py"
NEW = HERE / "new.py"
GUARD = HERE / "guard.py"

GOOD = """---
name: demo-skill
description: >-
  Formats reports into the house template and checks the required sections.
  Use when the user asks to format, standardize or review a report.
license: MIT
metadata:
  version: "1.0"
---

# Demo Skill

## When to use

- The user asks to format or standardize a report.

## Workflow

1. Read the input.
2. Apply the template.
3. Verify every required section is present.
"""

BAD = """---
name: Demo--Skill
description: Helps.
---

# Bad
"""

BROKEN_REF = """---
name: broken-ref
description: >-
  Demonstrates a missing bundled file. Use when testing the linter's reference
  checks against a skill that points at nothing.
---

# Broken ref

## Workflow

1. Read `references/missing.md` before doing anything.
"""


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")


def lint_json(path: Path) -> tuple[int, dict]:
    result = run([sys.executable, str(LINT), str(path), "--json"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"errors": [], "warnings": [], "raw": result.stdout + result.stderr}
    return result.returncode, payload


def codes(payload: dict, severity: str) -> set[str]:
    return {item["code"] for item in payload.get(severity, [])}


def make_skill(root: Path, name: str, text: str, files: dict[str, str] | None = None) -> Path:
    skill = root / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(text, encoding="utf-8")
    for relative, content in (files or {}).items():
        target = skill / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return skill


def collection_skill(name: str, trigger: str, body: str = "",
                     desc: str | None = None) -> str:
    description = desc or (f"Demo skill {name} for the guard test. "
                           f'Triggers include "{trigger}".')
    return f"""---
name: {name}
description: >-
  {description}
license: MIT
metadata:
  version: "1.0"
  category: "meta"
  tier: "core"
---

# {name}

{body}
"""


def guard_json(root: Path, *extra: str) -> tuple[int, dict]:
    result = run([sys.executable, str(GUARD), str(root), "--json", "--no-selftest", *extra])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"issues": [], "raw": result.stdout + result.stderr}
    return result.returncode, payload


def guard_codes(payload: dict) -> set[str]:
    return {item["code"] for item in payload.get("issues", []) if item["level"] == "ERROR"}


def main() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        checks += 1
        good = make_skill(base, "demo-skill", GOOD)
        code, payload = lint_json(good)
        if code != 0 or not payload.get("ok"):
            failures.append(f"good skill should pass, got exit {code}: {payload.get('errors') or payload}")

        checks += 1
        bad = make_skill(base, "bad-skill", BAD)
        code, payload = lint_json(bad)
        found = codes(payload, "errors")
        if code == 0:
            failures.append("bad skill should fail")
        if "E004" not in found or "E005" not in found:
            failures.append(f"bad skill should report E004 and E005, got {sorted(found)}")

        checks += 1
        broken = make_skill(base, "broken-ref", BROKEN_REF)
        code, payload = lint_json(broken)
        if "E020" not in codes(payload, "errors"):
            failures.append(f"broken reference should report E020, got {sorted(codes(payload, 'errors'))}")

        checks += 1
        scaffold = run(
            [
                sys.executable,
                str(NEW),
                "scaffold-demo",
                "--dir",
                str(base),
                "--scripts",
                "--references",
                "--assets",
            ]
        )
        if scaffold.returncode != 0:
            failures.append(f"new.py failed ({scaffold.returncode}): {scaffold.stdout}{scaffold.stderr}")
        elif not (base / "scaffold-demo" / "SKILL.md").is_file():
            failures.append("new.py did not create SKILL.md")

        checks += 1
        code, payload = lint_json(base / "scaffold-demo")
        if code != 0:
            failures.append(f"scaffolded skill should pass, got {payload.get('errors')}")

        # --- collection guard -------------------------------------------------
        repo = base / "collection"
        repo.mkdir()
        make_skill(repo, "alpha", collection_skill(
            "alpha", "alpha run",
            desc='Formats quarterly reports into the house template and checks every section. '
                 'Use when a report needs formatting. Triggers include "alpha run".'))
        make_skill(repo, "beta", collection_skill(
            "beta", "beta run",
            desc='Schedules nightly batch jobs and pages the on-call channel when one fails. '
                 'Use when a cron entry needs a schedule. Triggers include "beta run".'))
        (repo / "README.md").write_text(
            "| Skill | What |\n|---|---|\n"
            "| [`alpha`](alpha/SKILL.md) | a |\n| [`beta`](beta/SKILL.md) | b |\n",
            encoding="utf-8",
        )

        checks += 1
        code, payload = guard_json(repo)
        if "E_CATALOG" not in guard_codes(payload):
            failures.append(f"a collection without catalog.json must report E_CATALOG, got {sorted(guard_codes(payload))}")

        (repo / "catalog.json").write_text(json.dumps(
            {"version": 1, "categories": [{"id": "meta", "label": "Meta", "order": 10}]}), encoding="utf-8")

        checks += 1
        code, payload = guard_json(repo, "--strict")
        if code != 0:
            failures.append(f"clean collection should pass --strict, got {sorted(guard_codes(payload))}")

        checks += 1
        (repo / "alpha" / "PLAN.md").write_text("stray\n", encoding="utf-8")
        code, payload = guard_json(repo)
        if "E_STRAY" not in guard_codes(payload):
            failures.append(f"a stray file at a skill root must report E_STRAY, got {sorted(guard_codes(payload))}")
        (repo / "alpha" / "PLAN.md").unlink()

        checks += 1
        (repo / "beta" / "scripts").mkdir()
        (repo / "beta" / "scripts" / "tool.py").write_text("print('x')\n", encoding="utf-8")
        (repo / "alpha" / "SKILL.md").write_text(
            collection_skill("alpha", "alpha run", "Run `tool.py` before reporting."), encoding="utf-8")
        code, payload = guard_json(repo)
        if "E_CROSS_REF" not in guard_codes(payload):
            failures.append(f"a bare foreign script reference must report E_CROSS_REF, got {sorted(guard_codes(payload))}")

        checks += 1
        (repo / "alpha" / "SKILL.md").write_text(
            collection_skill("alpha", "beta run"), encoding="utf-8")
        code, payload = guard_json(repo)
        if "E_TRIGGER" not in guard_codes(payload):
            failures.append(f"a shared trigger phrase must report E_TRIGGER, got {sorted(guard_codes(payload))}")

        checks += 1
        (repo / "alpha" / "SKILL.md").write_text(
            collection_skill("alpha", "alpha run",
                             body="```svelte\n<button on:click={go}>x</button>\n```"),
            encoding="utf-8")
        code, payload = guard_json(repo)
        if "E_DEPRECATED" not in guard_codes(payload):
            failures.append(f"deprecated API in a tagged code fence must report E_DEPRECATED, "
                            f"got {sorted(guard_codes(payload))}")

        checks += 1
        (repo / "alpha" / "SKILL.md").write_text(
            collection_skill("alpha", "alpha run",
                             body="```\nscan output: onclick={fn} not on:click\n```"),
            encoding="utf-8")
        code, payload = guard_json(repo)
        if "E_DEPRECATED" in guard_codes(payload):
            failures.append("an untagged fence is sample output and must not report E_DEPRECATED")

    for failure in failures:
        print(f"FAIL  {failure}")
    if failures:
        print(f"\n{len(failures)} of {checks} checks failed")
        return 1
    print(f"PASS  {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
