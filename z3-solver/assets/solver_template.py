"""Starter Z3 script: edit build(), keep verify().

Run it through the wrapper so the time budget is explicit:
    python scripts/z3tool.py run assets/solver_template.py --timeout 20000
"""

from __future__ import annotations

import z3

TIMEOUT_MS = 20_000


def build():
    """Return (solver, variables, constraints). Replace with the real problem."""
    x, y = z3.Ints("x y")
    constraints = [x + y == 10, x > y, y >= 0]
    solver = z3.Solver()
    solver.set(timeout=TIMEOUT_MS)
    solver.add(constraints)
    return solver, [x, y], constraints


def verify(constraints, variables, model) -> bool:
    """Re-check the candidate model against every original constraint."""
    check = z3.Solver()
    check.set(timeout=5_000)
    check.add(constraints)
    check.add([v == model.eval(v, model_completion=True) for v in variables])
    return check.check() == z3.sat


def main() -> int:
    solver, variables, constraints = build()
    result = solver.check()

    if result == z3.unknown:
        print(f"unknown: {solver.reason_unknown()}")
        return 1
    if result == z3.unsat:
        print("unsat")
        return 0

    model = solver.model()
    values = {str(v): model.eval(v, model_completion=True) for v in variables}
    if not verify(constraints, variables, model):
        print(f"model failed verification: {values}")
        return 1

    print(f"sat: {values}")
    print(f"verified against {len(constraints)} constraint(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
