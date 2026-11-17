#!/usr/bin/env python3
"""Check that every skill id in the Start route table exists.

The router is only useful while its table points at real skills. Rename or delete a skill and
the table silently sends work to a missing id; this script turns that into a non-zero exit.

Usage:
    python scripts/check_routes.py
    python scripts/check_routes.py --root .. --json

Exit codes: 0 all ids resolve, 1 at least one problem, 2 the table cannot be parsed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_MD = HERE.parent / "SKILL.md"
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SELF_ID = "start"


class TableError(Exception):
    """The route table is missing or malformed."""


def table_rows(markdown: str) -> list[list[str]]:
    try:
        section = markdown.split("## Route table", 1)[1].split("\n## ", 1)[0]
    except IndexError as exc:
        raise TableError("SKILL.md has no '## Route table' section") from exc

    rows: list[list[str]] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 3:
            raise TableError(f"row needs exactly 3 cells: {line}")
        if cells[0].lower() == "request shape" or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(cells)
    if not rows:
        raise TableError("the route table has no rows")
    return rows


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Verify Start route-table ids against skill directories.")
    parser.add_argument("--root", default=str(HERE.parent.parent), help="repository root (default: the skill's parent)")
    parser.add_argument("--skill-md", default=str(SKILL_MD), help="SKILL.md to read (default: this skill's)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    problems: list[str] = []
    ids: set[str] = set()

    try:
        rows = table_rows(Path(args.skill_md).read_text(encoding="utf-8"))
    except (OSError, TableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for shape, first, then in rows:
        for role, value in (("first", first), ("then", then)):
            if value in ("-", ""):
                if role == "first":
                    problems.append(f"{shape!r}: first hop is empty")
                continue
            if not ID_RE.match(value):
                problems.append(f"{shape!r}: {value!r} is not a kebab-case skill id")
                continue
            ids.add(value)
            if value == SELF_ID:
                problems.append(f"{shape!r}: route points back at the router")
            if not (root / value / "SKILL.md").is_file():
                problems.append(f"{shape!r}: {value!r} has no SKILL.md under {root}")

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not problems,
                    "root": str(root),
                    "rows": len(rows),
                    "ids": sorted(ids),
                    "problems": problems,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"routes: {len(rows)} rows, {len(ids)} ids, {len(problems)} problem(s)")
        for problem in problems:
            print(f"  ERROR {problem}")
        print("PASS" if not problems else "FAIL")

    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
