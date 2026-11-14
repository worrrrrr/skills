#!/usr/bin/env python3
"""Offline regression tests for z3tool and sudoku. Z3 checks skip when it is missing."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "z3tool.py"
SUDOKU = HERE / "sudoku.py"
PROBLEM = HERE.parent / "assets" / "problem.json"

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS  {name}")
    else:
        failed += 1
        print(f"FAIL  {name}")


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


BAD = """\
import z3

s = z3.Solver(timeout=1000)
x = z3.Int('x')
s.add(z3.ForAll([x], x ** 2 >= 0))
s.add(x > 3)
total = x / 2
s.push()
if s.check():
    m = s.model()
    print(m.eval(x))
"""

CLEAN = """\
import z3

s = z3.Solver()
s.set(timeout=5_000)
x = z3.Int('x')
s.push()
s.add(x > 3)
s.pop()
s.add(x > 3)
result = s.check()
if result == z3.sat:
    m = s.model()
    print(m.eval(x, model_completion=True))
elif result == z3.unsat:
    print('unsat')
else:
    print('unknown', s.reason_unknown())
"""


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    bad = tmpdir / "bad.py"
    clean = tmpdir / "clean.py"
    ok = tmpdir / "ok.py"
    slow = tmpdir / "slow.py"
    broken = tmpdir / "broken.py"
    unsat_spec = tmpdir / "unsat.json"
    bad.write_text(BAD, encoding="utf-8")
    clean.write_text(CLEAN, encoding="utf-8")
    ok.write_text("print('ok')\n", encoding="utf-8")
    slow.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    broken.write_text("raise SystemExit(1)\n", encoding="utf-8")
    unsat_spec.write_text(
        json.dumps(
            {
                "variables": {"a": {"type": "int", "min": 0, "max": 3}},
                "constraints": ["a > 5"],
            }
        ),
        encoding="utf-8",
    )

    result = run(TOOL, "lint", str(bad), "--json")
    check("lint exits 1 on a bad script", result.returncode == 1)
    codes = {finding["code"] for finding in json.loads(result.stdout)["findings"]}
    for expected in (
        "Z3_TRUTHY",
        "Z3_CTOR_TIMEOUT",
        "Z3_QUANTIFIER",
        "Z3_NONLINEAR",
        "Z3_IGNORED_RESULT",
        "Z3_INT_DIV",
        "Z3_PUSH_POP",
        "Z3_PARTIAL_MODEL",
    ):
        check(f"lint reports {expected}", expected in codes)

    clean_result = run(TOOL, "lint", str(clean), "--json")
    check("lint exits 0 on a clean script", clean_result.returncode == 0)
    check("clean script has no findings", json.loads(clean_result.stdout)["findings"] == [])

    check("lint exits 3 on a missing file", run(TOOL, "lint", str(tmpdir / "nope.py")).returncode == 3)

    doctor = run(TOOL, "doctor", "--json")
    doctor_payload = json.loads(doctor.stdout)
    check("doctor reports the python version", "python" in doctor_payload)
    check("doctor exit code matches availability", doctor.returncode == (0 if doctor_payload["available"] else 2))
    if doctor_payload["available"]:
        check("doctor reports a z3 version", bool(doctor_payload.get("z3")))

    ok_run = run(TOOL, "run", str(ok), "--timeout", "10000", "--json")
    check("run exits 0 on a working script", ok_run.returncode == 0)
    check("run captures stdout", "ok" in json.loads(ok_run.stdout)["stdout"])

    slow_run = run(TOOL, "run", str(slow), "--timeout", "300", "--json")
    check("run stops a slow script", json.loads(slow_run.stdout)["status"] == "timeout")
    check("timeout exits non-zero", slow_run.returncode == 1)
    check("run reports a failing script", run(TOOL, "run", str(broken), "--timeout", "10000", "--json").returncode == 1)

    if doctor_payload["available"]:
        solved = run(TOOL, "solve", str(PROBLEM), "--json")
        payload = json.loads(solved.stdout)
        check("solve returns sat", payload["status"] == "sat" and solved.returncode == 0)
        check("solve verifies the model", payload["verified"] is True)
        check("solve enumerates N models", payload["enumerated"] == 3 and len(payload["models"]) == 3)

        unsat = run(TOOL, "solve", str(unsat_spec), "--json")
        check("solve reports unsat with exit 1", json.loads(unsat.stdout)["status"] == "unsat" and unsat.returncode == 1)

        puzzle = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
        sudoku = run(SUDOKU, "--solve", puzzle, "--json")
        grid = json.loads(sudoku.stdout)["solved"]
        check("sudoku solves a known puzzle", sudoku.returncode == 0 and grid[0][:3] == [5, 3, 4])
        check("sudoku row is a permutation", sorted(grid[0]) == list(range(1, 10)))

        count = run(SUDOKU, "--solve", puzzle, "--count", "3", "--json")
        check("sudoku counts one solution", json.loads(count.stdout)["solutions"] == 1)

        generated = run(SUDOKU, "--size", "4", "--difficulty", "easy", "--seed", "1", "--json")
        gen = json.loads(generated.stdout)
        check("sudoku generates a unique 4x4", generated.returncode == 0 and gen["unique"] is True)
        check("sudoku keeps the requested size", len(gen["puzzle"]) == 4 and len(gen["puzzle"][0]) == 4)

print(f"\n{passed} passed, {failed} failed")
raise SystemExit(0 if failed == 0 else 1)
