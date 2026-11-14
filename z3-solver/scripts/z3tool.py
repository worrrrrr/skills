#!/usr/bin/env python3
"""z3tool - check the Z3 install, lint solver scripts, run them with a time limit.

Exit codes everywhere: 0 ok, 1 findings or a failed script, 2 cannot check, 3 usage.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_UNAVAILABLE = 2
EXIT_USAGE = 3

TAIL_CHARS = 4000


def _tail(text: str, limit: int = TAIL_CHARS) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else "…" + text[-limit:]


def doctor() -> tuple[dict, int]:
    info: dict = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        import z3  # noqa: PLC0415 - optional dependency, checked at runtime

        info.update(available=True, z3=z3.get_version_string())
        return info, EXIT_OK
    except Exception as exc:  # noqa: BLE001 - any import failure means unavailable
        info.update(available=False, error=f"{type(exc).__name__}: {exc}")
        return info, EXIT_UNAVAILABLE


def _strip_comment(line: str) -> str:
    return re.sub(r"#.*$", "", line)


def lint_source(text: str) -> list[dict]:
    lines = text.splitlines()
    code_lines = [_strip_comment(line) for line in lines]
    code = "\n".join(code_lines)
    findings: list[dict] = []

    def add(code_name: str, number: int, message: str) -> None:
        findings.append(
            {
                "code": code_name,
                "line": number,
                "message": message,
                "excerpt": lines[number - 1].strip()[:120] if 0 < number <= len(lines) else "",
            }
        )

    imports_z3 = re.search(r"^\s*(import z3|from z3)", code, re.M) is not None

    for number, line in enumerate(code_lines, 1):
        if re.search(r"\bif\s+[\w.]+\.check\(\)\s*:", line):
            add("Z3_TRUTHY", number, "if x.check(): is always true; compare with == z3.sat")
        if re.search(r"\b(Int|Real|Bool)\w*\(\s*timeout\s*=", line) or re.search(
            r"\bSolver\(\s*timeout\s*=", line
        ):
            add("Z3_CTOR_TIMEOUT", number, "Solver(timeout=...) raises TypeError; call s.set(timeout=ms)")
        if re.search(r"\.timeout\(\)|\.get_parameter\(", line):
            add("Z3_NO_GETTER", number, "no timeout getter exists; keep the value you passed to set()")
        if re.search(r"\b(ForAll|Exists)\(", line) and "patterns=" not in line:
            add("Z3_QUANTIFIER", number, "quantifier without patterns=; prefer a finite domain")
        if "**" in line:
            add("Z3_NONLINEAR", number, "** makes the problem nonlinear; expect unknown and keep a timeout")

    if imports_z3 and not re.search(
        r"\.set\(\s*timeout|set_param\(\s*['\"]timeout|set_option\(\s*['\"]timeout|\bSolverFor\(", code
    ):
        add("Z3_NO_TIMEOUT", 1, "no timeout configured; call s.set(timeout=ms) before check()")

    first_check = next((n for n, line in enumerate(code_lines, 1) if ".check()" in line), None)
    if first_check is not None and not re.search(
        r"==\s*(z3\.)?(sat|unsat|unknown)|\bis\s+(z3\.)?(sat|unsat|unknown)", code
    ):
        add("Z3_IGNORED_RESULT", first_check, "check() result is never compared with sat/unsat/unknown")

    first_model = next((n for n, line in enumerate(code_lines, 1) if ".model()" in line), None)
    if first_model is not None and first_check is None:
        add("Z3_MODEL_NO_CHECK", first_model, ".model() used without calling check() first")

    findings.sort(key=lambda item: (item["line"], item["code"]))
    return findings


def lint_file(path: Path) -> tuple[list[dict], int]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], EXIT_USAGE
    except OSError as exc:
        return [{"code": "IO", "line": 0, "message": str(exc), "excerpt": ""}], EXIT_UNAVAILABLE
    findings = lint_source(text)
    return findings, (EXIT_FINDINGS if findings else EXIT_OK)


def run_file(path: Path, timeout_ms: int) -> tuple[dict, int]:
    started = time.perf_counter()
    payload: dict = {"script": str(path), "timeout_ms": timeout_ms}
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_ms / 1000,
            cwd=str(path.parent),
        )
    except subprocess.TimeoutExpired:
        payload.update(
            status="timeout",
            exit_code=None,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            stdout="",
            stderr=f"stopped after {timeout_ms} ms",
        )
        return payload, EXIT_FINDINGS
    except OSError as exc:
        payload.update(status="error", exit_code=None, error=str(exc))
        return payload, EXIT_UNAVAILABLE

    payload.update(
        status="ok" if proc.returncode == 0 else "failed",
        exit_code=proc.returncode,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        stdout=_tail(proc.stdout),
        stderr=_tail(proc.stderr),
    )
    return payload, EXIT_OK if proc.returncode == 0 else EXIT_FINDINGS


def _print(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        if isinstance(value, (list, dict)):
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            print(f"{key}: {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="z3tool",
        description="Check the Z3 install, lint solver scripts, run them with a time limit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    doctor_parser = sub.add_parser("doctor", help="report whether z3 is importable, and its version")
    doctor_parser.add_argument("--json", action="store_true")

    lint_parser = sub.add_parser("lint", help="static checks on a solver script; never executes it")
    lint_parser.add_argument("script")
    lint_parser.add_argument("--json", action="store_true")

    run_parser = sub.add_parser("run", help="run a solver script with a wall-clock limit")
    run_parser.add_argument("script")
    run_parser.add_argument("--timeout", type=int, default=20_000, metavar="MS")
    run_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "doctor":
        payload, code = doctor()
        if args.json:
            _print(payload, True)
        elif payload.get("available"):
            print(f"z3 {payload['z3']} (python {payload['python']})")
        else:
            print(f"z3 not importable: {payload['error']}", file=sys.stderr)
            print("install it with: python -m pip install z3-solver", file=sys.stderr)
        return code

    path = Path(args.script)
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return EXIT_USAGE
    path = path.resolve()

    if args.command == "lint":
        findings, code = lint_file(path)
        if args.json:
            _print({"script": str(path), "findings": findings, "count": len(findings)}, True)
        else:
            for finding in findings:
                print(f"  {finding['line']:>4}  {finding['code']:<18} {finding['message']}")
                if finding["excerpt"]:
                    print(f"        {finding['excerpt']}")
            print(f"{len(findings)} finding(s)")
        return code

    payload, code = run_file(path, args.timeout)
    if args.json:
        _print(payload, True)
    else:
        print(f"status: {payload['status']}  exit: {payload.get('exit_code')}  {payload['elapsed_ms']} ms")
        if payload.get("stdout"):
            print("--- stdout ---")
            print(payload["stdout"])
        if payload.get("stderr"):
            print("--- stderr ---")
            print(payload["stderr"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
