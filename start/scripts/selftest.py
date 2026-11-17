#!/usr/bin/env python3
"""Regression tests for scripts/check_routes.py.

    python scripts/selftest.py

Exit 0 when every check passes, 1 when one fails. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE / "check_routes.py"
failures: list[str] = []
checks = 0


def expect(condition: bool, label: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(label)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECK), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def fixture(root: Path, body: str) -> Path:
    skill_md = root / "SKILL.md"
    skill_md.write_text(body, encoding="utf-8")
    return skill_md


def make_skill(root: Path, skill_id: str) -> None:
    target = root / skill_id / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("---\nname: x\n---\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run check_routes.py regression tests.")
    parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # the real skill must pass against the real repository
        real = run()
        expect(real.returncode == 0, f"real route table should pass:\n{real.stdout}{real.stderr}")

        make_skill(root, "alpha")
        make_skill(root, "beta")
        good = fixture(
            root,
            "# t\n\n## Route table\n\n"
            "| Request shape | First | Then |\n|---|---|---|\n"
            "| one | alpha | beta |\n| two | beta | - |\n\n## Next\n",
        )
        result = run("--root", str(root), "--skill-md", str(good))
        expect(result.returncode == 0, f"valid fixture should pass:\n{result.stdout}")

        payload = run("--root", str(root), "--skill-md", str(good), "--json")
        try:
            data = json.loads(payload.stdout)
            expect(payload.returncode == 0 and data["ok"] is True, "json output should say ok")
            expect(data["rows"] == 2, "json output should report the row count")
        except json.JSONDecodeError:
            expect(False, "json output should be valid JSON")

        missing = fixture(
            root,
            "## Route table\n| Request shape | First | Then |\n|---|---|---|\n| one | alpha | ghost |\n",
        )
        result = run("--root", str(root), "--skill-md", str(missing))
        expect(
            result.returncode == 1 and "ghost" in result.stdout and "no SKILL.md" in result.stdout,
            "unknown id should fail and name the id",
        )

        loop = fixture(
            root,
            "## Route table\n| Request shape | First | Then |\n|---|---|---|\n| one | start | - |\n",
        )
        result = run("--root", str(root), "--skill-md", str(loop))
        expect(result.returncode == 1 and "router" in result.stdout, "self route should fail")

        bad_id = fixture(
            root,
            "## Route table\n| Request shape | First | Then |\n|---|---|---|\n| one | Alpha | - |\n",
        )
        result = run("--root", str(root), "--skill-md", str(bad_id))
        expect(result.returncode == 1 and "kebab" in result.stdout, "non-kebab id should fail")

        no_table = fixture(root, "# t\n\n## Other\n| a | b | c |\n")
        result = run("--root", str(root), "--skill-md", str(no_table))
        expect(result.returncode == 2, "missing table should exit 2")

        short_row = fixture(
            root,
            "## Route table\n| Request shape | First | Then |\n|---|---|---|\n| one | alpha |\n",
        )
        result = run("--root", str(root), "--skill-md", str(short_row))
        expect(result.returncode == 2, "malformed row should exit 2")

    if failures:
        print(f"selftest: {len(failures)} of {checks} checks failed", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"selftest: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
