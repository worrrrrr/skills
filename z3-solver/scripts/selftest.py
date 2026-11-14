#!/usr/bin/env python3
"""Offline regression tests for z3tool. Z3 itself is optional: its checks skip when missing."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "z3tool.py"

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


def tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
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
if s.check():
    print(s.model())
"""

CLEAN = """\
import z3

s = z3.Solver()
s.set(timeout=5_000)
x = z3.Int('x')
s.add(x > 3)
result = s.check()
if result == z3.sat:
    print(s.model())
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
    bad.write_text(BAD, encoding="utf-8")
    clean.write_text(CLEAN, encoding="utf-8")
    ok.write_text("print('ok')\n", encoding="utf-8")
    slow.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    broken.write_text("raise SystemExit(1)\n", encoding="utf-8")

    result = tool("lint", str(bad), "--json")
    check("lint exits 1 on a bad script", result.returncode == 1)
    payload = json.loads(result.stdout)
    codes = {finding["code"] for finding in payload["findings"]}
    for expected in ("Z3_TRUTHY", "Z3_CTOR_TIMEOUT", "Z3_QUANTIFIER", "Z3_NONLINEAR", "Z3_IGNORED_RESULT"):
        check(f"lint reports {expected}", expected in codes)
    check("lint reports a timeout rule", "Z3_NO_TIMEOUT" in codes)

    clean_result = tool("lint", str(clean), "--json")
    clean_payload = json.loads(clean_result.stdout)
    check("lint exits 0 on a clean script", clean_result.returncode == 0)
    check("clean script has no findings", clean_payload["findings"] == [])

    missing = tool("lint", str(tmpdir / "nope.py"))
    check("lint exits 3 on a missing file", missing.returncode == 3)

    doctor = tool("doctor", "--json")
    doctor_payload = json.loads(doctor.stdout)
    check("doctor reports the python version", "python" in doctor_payload)
    check("doctor exit code matches availability", doctor.returncode == (0 if doctor_payload["available"] else 2))
    if doctor_payload["available"]:
        check("doctor reports a z3 version", bool(doctor_payload.get("z3")))

    ok_run = tool("run", str(ok), "--timeout", "10000", "--json")
    ok_payload = json.loads(ok_run.stdout)
    check("run exits 0 on a working script", ok_run.returncode == 0)
    check("run captures stdout", "ok" in ok_payload["stdout"])

    slow_run = tool("run", str(slow), "--timeout", "300", "--json")
    slow_payload = json.loads(slow_run.stdout)
    check("run stops a slow script", slow_payload["status"] == "timeout")
    check("timeout exits non-zero", slow_run.returncode == 1)

    broken_run = tool("run", str(broken), "--timeout", "10000", "--json")
    check("run reports a failing script", broken_run.returncode == 1)

print(f"\n{passed} passed, {failed} failed")
raise SystemExit(0 if failed == 0 else 1)
