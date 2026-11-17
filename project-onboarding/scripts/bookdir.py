#!/usr/bin/env python3
"""Resolve where project-onboarding writes BOOK.md and PLAN.md.

Precedence: --dir, PROJECT_ONBOARDING_DIR, the config file, then the project root.
Default layout puts each project in its own folder so one notes directory can hold many
projects: <dir>/<project>/BOOK.md. Use --flat to write BOOK.md directly in <dir>.

Exit codes: 0 ok, 2 path problem, 3 usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

CONFIG_NAME = "config.json"
ENV = "PROJECT_ONBOARDING_DIR"


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "project-onboarding" / CONFIG_NAME


def read_config(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def slugify(name: str) -> str:
    cleaned = re.sub(r"[^\w.-]+", "-", name, flags=re.UNICODE).strip("-._")
    return cleaned or "project"


def resolve(project: Path, override: str | None, flat: bool, name: str | None) -> dict:
    cfg_path = config_path()
    cfg = read_config(cfg_path)

    if override:
        base, source = override, "--dir"
    elif os.environ.get(ENV):
        base, source = os.environ[ENV], f"env:{ENV}"
    elif cfg.get("dir"):
        base, source = str(cfg["dir"]), "config"
    else:
        base, source = str(project), "project root"

    try:
        base_path = Path(base).expanduser()
        if not base_path.is_absolute():
            base_path = project / base_path
        base_path = base_path.resolve()
    except OSError:
        base_path = Path(base)

    target = base_path if flat or source == "project root" else base_path / slugify(name or project.name)
    return {
        "config": str(cfg_path),
        "configured": cfg.get("dir"),
        "source": source,
        "dir": str(target),
        "book": str(target / "BOOK.md"),
        "plan": str(target / "PLAN.md"),
    }


def show_config(path: Path) -> int:
    cfg = read_config(path)
    state = cfg.get("dir") or "not set"
    print(f"config  {path}")
    print(f"dir     {state}")
    if path.exists() and not cfg:
        print("note    config exists but is not valid JSON")
    return 0


def set_config(value: str) -> int:
    target = Path(value).expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"dir": str(target)}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"config  {path}")
    print(f"dir     {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bookdir.py",
        description="Show or set where BOOK.md and PLAN.md are written.",
    )
    parser.add_argument("project", nargs="?", default=".", help="project root (default: current directory)")
    parser.add_argument("--dir", help="one-off output directory for this run")
    parser.add_argument("--name", help="folder name to use instead of the project directory name")
    parser.add_argument("--flat", action="store_true", help="write BOOK.md directly in the directory")
    parser.add_argument("--set", metavar="PATH", help="save PATH as the default output directory")
    parser.add_argument("--show", action="store_true", help="print the saved configuration")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.show:
        if args.json:
            path = config_path()
            print(json.dumps({"config": str(path), "dir": read_config(path).get("dir")}, indent=2, ensure_ascii=False))
            return 0
        return show_config(config_path())

    if args.set:
        code = set_config(args.set)
        if code == 0 and not args.json:
            print("saved. bookdir.py with no --dir now uses this directory.")
        return code

    project = Path(args.project).expanduser()
    if not project.is_dir():
        print(f"bookdir.py: not a directory: {project}", file=sys.stderr)
        return 2
    info = resolve(project.resolve(), args.dir, args.flat, args.name)

    if args.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0
    print(f"config  {info['config']} ({'set' if info['configured'] else 'not set'})")
    print(f"source  {info['source']}")
    print(f"book    {info['book']}")
    print(f"plan    {info['plan']}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
