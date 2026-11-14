#!/usr/bin/env python3
"""Run the project's own verification commands and report pass/fail.

Auto-detects the package manager and the useful scripts, then runs them in order.
A change is not done until this exits 0.

Usage:
    python scripts/verify.py                 # verify the project in the current directory
    python scripts/verify.py ../app          # or another directory
    python scripts/verify.py --list          # show what would run
    python scripts/verify.py --only check    # run a single script
    python scripts/verify.py --json

Exit codes:
    0  every command passed
    1  at least one command failed
    2  nothing to verify (no recognised project or scripts)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

# Ordered by how early they catch real breakage.
SCRIPT_ORDER = [
    "check",
    "typecheck",
    "type-check",
    "lint",
    "test",
    "build",
]

MANAGERS = [
    ("bun.lockb", "bun"),
    ("bun.lock", "bun"),
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("package-lock.json", "npm"),
]


def read_json(path: str):
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def detect_node(root: str):
    manifest = read_json(os.path.join(root, "package.json"))
    if not isinstance(manifest, dict):
        return None

    scripts = manifest.get("scripts")
    if not isinstance(scripts, dict):
        scripts = {}

    manager = "npm"
    for marker, name in MANAGERS:
        if os.path.isfile(os.path.join(root, marker)):
            manager = name
            break
    if manager == "npm" and not shutil.which("npm"):
        manager = "bun" if shutil.which("bun") else "npm"

    runnable = [script for script in SCRIPT_ORDER if isinstance(scripts.get(script), str)]
    commands = []
    for script in runnable:
        if manager == "npm":
            commands.append((script, ["npm", "run", script]))
        elif manager == "yarn":
            commands.append((script, ["yarn", script]))
        else:
            commands.append((script, [manager, "run", script]))
    return manager, commands


def detect_python(root: str):
    commands = []
    if os.path.isfile(os.path.join(root, "pyproject.toml")) or os.path.isfile(
        os.path.join(root, "setup.py")
    ):
        if shutil.which("pytest") or os.path.isdir(os.path.join(root, "tests")):
            commands.append(("pytest", [sys.executable, "-m", "pytest", "-q"]))
    return commands


def collect(root: str):
    node = detect_node(root)
    python = detect_python(root)
    if node:
        return node[0], node[1] + python
    if python:
        return "python", python
    return None, []


def run(command: list[str], cwd: str, timeout: int):
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=(os.name == "nt"),
        )
        code = completed.returncode
        output = (completed.stdout or "") + (completed.stderr or "")
    except subprocess.TimeoutExpired:
        code = 124
        output = f"timed out after {timeout}s"
    except FileNotFoundError:
        code = 127
        output = f"command not found: {command[0]}"
    return code, output, round(time.time() - started, 1)


def tail(output: str, lines: int = 40) -> str:
    trimmed = [line.rstrip() for line in output.strip().splitlines() if line.strip()]
    return "\n".join(trimmed[-lines:])


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Run the project's own checks and report pass/fail.")
    parser.add_argument("path", nargs="?", default=".", help="project directory (default: .)")
    parser.add_argument("--list", action="store_true", help="print the commands without running")
    parser.add_argument("--only", action="append", default=[], help="run only this script name")
    parser.add_argument("--timeout", type=int, default=600, help="per-command timeout in seconds")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--tail", type=int, default=40, help="output lines to show per failure")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.path)
    manager, commands = collect(root)
    if not commands:
        print(f"nothing to verify in {root} (no package.json scripts or python tests)")
        return 2

    if args.only:
        wanted = {name.lower() for name in args.only}
        commands = [item for item in commands if item[0].lower() in wanted]
        if not commands:
            print(f"no matching scripts: {', '.join(sorted(wanted))}")
            return 2

    if args.list:
        print(f"{root}  (manager: {manager})")
        for name, command in commands:
            print(f"  {name:<10} {' '.join(command)}")
        return 0

    results = []
    for name, command in commands:
        code, output, seconds = run(command, root, args.timeout)
        results.append({"script": name, "command": " ".join(command), "code": code,
                        "seconds": seconds, "output": tail(output, args.tail)})
        status = "PASS" if code == 0 else "FAIL"
        print(f"{status}  {name:<10} {seconds:>5.1f}s")
        if code != 0:
            print(tail(output, args.tail))

    failed = [item for item in results if item["code"] != 0]
    if args.json:
        print(json.dumps({"ok": not failed, "results": results}, ensure_ascii=False, indent=2))
    else:
        print()
        print(("PASS" if not failed else "FAIL") + f": {len(results) - len(failed)}/{len(results)} scripts")
        if failed:
            print("failed: " + ", ".join(item["script"] for item in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
