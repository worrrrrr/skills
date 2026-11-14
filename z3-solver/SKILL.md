---
name: z3-solver
description: >-
  Encodes constraint, scheduling, configuration and verification problems as SMT formulas,
  solves them with Z3, and checks the answer against a model instead of guessing. Use when the
  user asks to solve a logic puzzle, pick values that satisfy constraints, check whether a
  schedule or configuration is possible, prove or refute a property, or debug a Z3 script that
  returns unknown, times out, or gives a wrong model. Triggers include "z3", "z3-solver",
  "SMT", "satisfiable", "unsat", "constraint solver", "แก้เงื่อนไข", "จัดตาราง", "ตรวจสอบสมการ".
license: MIT
metadata:
  version: "1.0.0"
  tags: "smt, z3, constraints, verification, scheduling, optimization"
allowed-tools: Read Write Edit Bash Glob Grep
---

# Z3 Solver

Turn a question about constraints into an SMT formula, let Z3 answer it, and prove the answer
before you report it.

## When to use

- A puzzle or assignment with rules: sudoku, logic grid, seating, timetabling.
- Values must satisfy interacting conditions: scheduling, packing, budgets, configuration.
- Prove a property holds for every input, or produce a counterexample.
- Optimise under constraints: maximise or minimise with `Optimize`.
- A Z3 script returns `unknown`, times out, or returns a model that violates the rules.

## When not to use

- Plain arithmetic or a small search space - a loop is clearer and faster.
- The answer needs floating-point reasoning Z3 models poorly; use a numeric method.
- `z3-solver` cannot be installed and the user needs a solver anyway: say that first.

## Operating contract

1. **Check the install first.** `python scripts/z3tool.py doctor` reports the version or exits 2.
2. **Bound every solve.** `s.set(timeout=<ms>)`. An unbounded solve can hang the user's machine.
3. **Never treat a check as a boolean.** `if s.check():` is always true - `sat`, `unsat` and
   `unknown` are all truthy (verified on z3 5.4.1). Compare with `== sat`.
4. **A model is a candidate.** Substitute the values back into the original constraints.
5. **`unknown` is an answer.** Report it with `s.reason_unknown()`; never call it unsat.
6. **Quote what you ran.** Give the script, the timeout and the exact solver result.

## Workflow

1. **Restate** the problem as variables, domains and constraints in the user's words.
2. **Encode** with the constructs below; name variables after the user's nouns.
3. **Run** `python scripts/z3tool.py run solver.py --timeout 20000` so the budget is explicit.
4. **Read** the result: `sat`, `unsat`, `unknown`, or `timeout` from the wrapper.
5. **Verify** the model against every original constraint before reporting it.
6. **Report** result, model, timeout, and what you verified.

## Encoding map

| Need | Use |
|---|---|
| Integer, real, boolean | `Int`, `Real`, `Bool` |
| Fixed-width machine integers | `BitVec('x', 32)` |
| Maps and memory | `Array('a', IntSort(), IntSort())` with `Select` / `Store` |
| Set membership | one `Bool` per element, or `SetSort` |
| All values differ | `Distinct(a, b, c)` |
| Counting | `Sum([If(p, 1, 0) for p in ps]) == k` |
| Implication | `Implies(a, b)` |
| At most one | `AtMost(*xs, 1)`, `PbEq`, `PbLe` |
| Optimisation | `Optimize()`; keep the handle from `maximize` |
| Why unsat | `assert_and_track(..., 'name')` then `unsat_core()` |
| Faster solving | `SolverFor('QF_LIA')`, `Then('simplify', 'solve-eqs', 'smt')` |

## Pitfalls (verified on z3 5.4.1)

- `Solver(timeout=1000)` raises `TypeError`; call `s.set(timeout=1000)` instead.
- `s.timeout()` and `s.get_parameter()` do not exist; remember the value you passed.
- `/` between two `Int` values is integer division; use `ToReal` or `Div` deliberately.
- `**` makes the problem nonlinear: expect `unknown` more often, and keep the timeout.
- `Optimize.maximize` returns a handle; pass that handle to `upper`/`lower`, and expect `oo`
  when the objective is unbounded.
- Quantifiers without `patterns=` blow up the search; prefer finite domains.
- `push()` and `pop()` change the assertion stack; re-check after every `pop()`.

## Scripts

```bash
python scripts/z3tool.py doctor
python scripts/z3tool.py lint solver.py
python scripts/z3tool.py run solver.py --timeout 20000
```

`lint` is static: it flags the truthiness bug, a missing timeout, reading a model without
`check`, quantifiers without patterns and nonlinear terms. It never executes the script.
`run` executes with a wall-clock limit and reports exit code, elapsed time and output tails.
Both accept `--json`.

## Files

- `scripts/z3tool.py` - doctor, lint, bounded run.
- `scripts/selftest.py` - offline tests for the tool.
- `references/z3-encodings.md` - worked encodings, unsat cores, debugging `unknown`.
- `assets/solver_template.py` - starter script with the verify step wired in.
