#!/usr/bin/env python3
"""z3tool - check Z3, lint solver scripts, run them, and solve JSON problem specs.

Exit codes everywhere: 0 ok, 1 findings / failed / unsat, 2 cannot check, 3 usage.
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
        import z3

        info.update(available=True, z3=z3.get_version_string())
        return info, EXIT_OK
    except Exception as exc:
        info.update(available=False, error=f"{type(exc).__name__}: {exc}")
        return info, EXIT_UNAVAILABLE


# --------------------------------------------------------------------------- lint

def _strip_comment(line: str) -> str:
    return re.sub(r"#.*$", "", line)


def lint_source(text: str) -> list[dict]:
    lines = text.splitlines()
    code_lines = [_strip_comment(line) for line in lines]
    code = "\n".join(code_lines)
    findings: list[dict] = []

    def add(name: str, number: int, message: str) -> None:
        findings.append(
            {
                "code": name,
                "line": number,
                "message": message,
                "excerpt": lines[number - 1].strip()[:120] if 0 < number <= len(lines) else "",
            }
        )

    imports_z3 = re.search(r"^\s*(import z3|from z3)", code, re.M) is not None
    uses_int = re.search(r"\bz3\.(Int|Ints)\(", code) is not None

    for number, line in enumerate(code_lines, 1):
        if re.search(r"\bif\s+[\w.]+\.check\(\)\s*:", line):
            add("Z3_TRUTHY", number, "if x.check(): is always true; compare with == z3.sat")
        if re.search(r"\bSolver\(\s*timeout\s*=", line) or re.search(
            r"\b(Int|Real|Bool)\w*\(\s*timeout\s*=", line
        ):
            add("Z3_CTOR_TIMEOUT", number, "Solver(timeout=...) raises TypeError; call s.set(timeout=ms)")
        if re.search(r"\.timeout\(\)|\.get_parameter\(", line):
            add("Z3_NO_GETTER", number, "no timeout getter exists; keep the value you passed to set()")
        if re.search(r"\b(ForAll|Exists)\(", line) and "patterns=" not in line:
            add("Z3_QUANTIFIER", number, "quantifier without patterns=; prefer a finite domain")
        if "**" in line:
            add("Z3_NONLINEAR", number, "** makes the problem nonlinear; expect unknown and keep a timeout")
        if uses_int and re.search(r"[^/=!<>]\s/\s", line) and "ToReal(" not in line:
            add("Z3_INT_DIV", number, "/ on Int is integer division; wrap in ToReal() for reals")
        if re.search(r"\.eval\([^)]*\)", line) and "model_completion" not in line:
            add("Z3_PARTIAL_MODEL", number, "eval() without model_completion=True can return an expression")

    if imports_z3 and not re.search(
        r"\.set\(\s*timeout|set_param\(\s*['\"]timeout|set_option\(\s*['\"]timeout|\bSolverFor\(", code
    ):
        add("Z3_NO_TIMEOUT", 1, "no timeout configured; call s.set(timeout=ms) before check()")

    pushes = len(re.findall(r"\.push\(", code))
    pops = len(re.findall(r"\.pop\(", code))
    if pushes != pops:
        add("Z3_PUSH_POP", 1, f"{pushes} push() but {pops} pop(); the assertion stack must balance")

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


# --------------------------------------------------------------------------- run

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


# --------------------------------------------------------------------------- solve

def _decl(z3, name: str, spec) -> object:
    """Build a variable from a type name or a spec object."""
    if isinstance(spec, str):
        kind, options = spec, {}
    elif isinstance(spec, dict):
        kind, options = spec.get("type", "int"), spec
    else:
        raise ValueError(f"{name}: variable spec must be a type name or an object")

    if kind == "int":
        var = z3.Int(name)
    elif kind == "real":
        var = z3.Real(name)
    elif kind == "bool":
        var = z3.Bool(name)
    elif kind == "bv":
        var = z3.BitVec(name, int(options.get("bits", 8)))
    elif kind == "string":
        var = z3.String(name)
    elif kind == "array":
        var = z3.Array(name, z3.IntSort(), z3.IntSort())
    else:
        raise ValueError(f"{name}: unknown type {kind!r} (int, real, bool, bv, string, array)")
    return var, kind, options


def _structural(z3, item: dict, env: dict) -> list:
    out = []
    if "all_different" in item:
        out.append(z3.Distinct([env[n] for n in item["all_different"]]))
    for key, op in (("sum_eq", "=="), ("sum_le", "<="), ("sum_ge", ">=")):
        if key in item:
            block = item[key]
            names = block["vars"] if isinstance(block, dict) else block[:-1]
            value = block["value"] if isinstance(block, dict) else block[-1]
            total = z3.Sum([env[n] for n in names])
            out.append(total == value if op == "==" else total <= value if op == "<=" else total >= value)
    if "sum" in item:
        block = item["sum"]
        total = z3.Sum([env[n] for n in block["vars"]])
        if "eq" in block:
            out.append(total == block["eq"])
        if "le" in block:
            out.append(total <= block["le"])
        if "ge" in block:
            out.append(total >= block["ge"])
    for key, fn in (("at_most", z3.AtMost), ("at_least", z3.AtLeast)):
        if key in item:
            block = item[key]
            names = block["vars"] if isinstance(block, dict) else block[:-1]
            value = block["value"] if isinstance(block, dict) else block[-1]
            out.append(fn(*[env[n] for n in names], value))
    if "exactly" in item:
        block = item["exactly"]
        out.append(z3.PbEq([(env[n], 1) for n in block["vars"]], block["value"]))
    if "implies" in item:
        left, right = item["implies"]
        out.append(z3.Implies(_expr(z3, left, env), _expr(z3, right, env)))
    if "distinct_cells" in item:
        out.append(z3.Distinct([env[n] for n in item["distinct_cells"]]))
    if not out:
        raise ValueError(f"unknown constraint object: {sorted(item)}")
    return out


def _expr(z3, text: str, env: dict):
    """Evaluate one constraint expression against the variables and z3."""
    scope = {"__builtins__": {}, "z3": z3, **env}
    try:
        return eval(text, scope)  # noqa: S307 - local spec file, same trust as running a script
    except Exception as exc:
        raise ValueError(f"cannot evaluate {text!r}: {type(exc).__name__}: {exc}") from exc


def solve_spec(spec: dict, timeout_override: int | None = None) -> tuple[dict, int]:
    import z3

    timeout_ms = int(timeout_override or spec.get("timeout_ms", 20_000))
    limits: dict = {}
    variables: dict = {}
    kinds: dict = {}
    for name, raw in (spec.get("variables") or {}).items():
        var, kind, options = _decl(z3, name, raw)
        variables[name] = var
        kinds[name] = kind
        if "min" in options:
            limits[name] = (options["min"], options["max"])
        elif "max" in options:
            limits[name] = (None, options["max"])

    constraints: list = []
    for name, (low, high) in limits.items():
        if low is not None:
            constraints.append(variables[name] >= low)
        if high is not None:
            constraints.append(variables[name] <= high)
    for item in spec.get("constraints") or []:
        constraints.extend(_structural(z3, item, variables) if isinstance(item, dict) else [_expr(z3, item, variables)])

    objective = spec.get("objective")
    if objective:
        opt = z3.Optimize()
        opt.set(timeout=timeout_ms)
        opt.add(constraints)
        handle_name = "minimize" if "minimize" in objective else "maximize"
        handle = getattr(opt, handle_name)(_expr(z3, objective[handle_name], variables))
        result = opt.check()
        if result == z3.unknown:
            return {"status": "unknown", "reason": opt.reason_unknown(), "timeout_ms": timeout_ms}, EXIT_FINDINGS
        if result == z3.unsat:
            return {"status": "unsat", "timeout_ms": timeout_ms}, EXIT_FINDINGS
        model = opt.model()
        value = opt.lower(handle) if handle_name == "minimize" else opt.upper(handle)
        return {
            "status": "sat",
            "objective": {"kind": handle_name, "value": str(value)},
            "model": {n: str(model.eval(v, model_completion=True)) for n, v in variables.items()},
            "verified": _verify(z3, constraints, variables, model, timeout_ms),
            "timeout_ms": timeout_ms,
        }, EXIT_OK

    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    solver.add(constraints)
    result = solver.check()
    if result == z3.unknown:
        return {"status": "unknown", "reason": solver.reason_unknown(), "timeout_ms": timeout_ms}, EXIT_FINDINGS
    if result == z3.unsat:
        return {"status": "unsat", "timeout_ms": timeout_ms}, EXIT_FINDINGS

    model = solver.model()
    payload = {
        "status": "sat",
        "model": {n: str(model.eval(v, model_completion=True)) for n, v in variables.items()},
        "verified": _verify(z3, constraints, variables, model, timeout_ms),
        "timeout_ms": timeout_ms,
    }

    limit = int(spec.get("enumerate", 0) or 0)
    if limit:
        models = [payload["model"]]
        probe = z3.Solver()
        probe.set(timeout=timeout_ms)
        probe.add(constraints)
        while len(models) < limit:
            probe.add(z3.Or([variables[n] != model.eval(variables[n], model_completion=True) for n in variables]))
            if probe.check() != z3.sat:
                break
            model = probe.model()
            models.append({n: str(model.eval(v, model_completion=True)) for n, v in variables.items()})
        payload["models"] = models
        payload["enumerated"] = len(models)
    return payload, EXIT_OK


def _verify(z3, constraints, variables, model, timeout_ms: int) -> bool:
    check = z3.Solver()
    check.set(timeout=timeout_ms)
    check.add(constraints)
    check.add([v == model.eval(v, model_completion=True) for v in variables.values()])
    return check.check() == z3.sat


# --------------------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="z3tool",
        description="Check Z3, lint solver scripts, run them, and solve JSON problem specs.",
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

    solve_parser = sub.add_parser("solve", help="solve a JSON problem spec (the dynamic path)")
    solve_parser.add_argument("spec")
    solve_parser.add_argument("--timeout", type=int, default=None, metavar="MS")
    solve_parser.add_argument("--json", action="store_true")
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

    path = Path(args.script if args.command != "solve" else args.spec)
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

    if args.command == "run":
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

    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read spec: {exc}", file=sys.stderr)
        return EXIT_USAGE

    started = time.perf_counter()
    try:
        payload, code = solve_spec(spec, args.timeout)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except ImportError:
        print("error: z3 is not importable; run `z3tool doctor`", file=sys.stderr)
        return EXIT_UNAVAILABLE
    payload["elapsed_ms"] = int((time.perf_counter() - started) * 1000)

    if args.json:
        _print(payload, True)
    else:
        print(f"status: {payload['status']}  {payload['elapsed_ms']} ms  timeout: {payload['timeout_ms']} ms")
        if payload.get("reason"):
            print(f"reason: {payload['reason']}")
        if payload.get("model"):
            print("model:", json.dumps(payload["model"], ensure_ascii=False))
        if "verified" in payload:
            print(f"verified: {payload['verified']}")
        if payload.get("objective"):
            print(f"objective: {payload['objective']['kind']} = {payload['objective']['value']}")
        if payload.get("models"):
            print(f"enumerated: {payload['enumerated']}")
            for item in payload["models"]:
                print("  ", json.dumps(item, ensure_ascii=False))
    return code


def _print(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        if isinstance(value, (list, dict)):
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
