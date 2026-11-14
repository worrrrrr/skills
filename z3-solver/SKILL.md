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

## Requirements

Python 3.11+ and the `z3-solver` package:

```bash
python -m pip install z3-solver
```

`lint` runs without z3. `doctor`, `run`, `solve` and `sudoku.py` exit 2 and print the install
command until it is available. No other third-party package is used.

## When to use

- A puzzle or assignment with rules: sudoku, logic grid, seating, timetabling.
- Values must satisfy interacting conditions: scheduling, packing, budgets, configuration.
- Prove a property holds for every input, or produce a counterexample.
- Generate or solve a Sudoku (or any Latin-square / all-different grid).
- The problem arrives as data: a JSON list of variables and constraints, solved without a script.
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

## Dynamic specs: solve JSON instead of writing code

When the constraints arrive as data, do not generate a Python file - describe them:

```json
{
  "timeout_ms": 20000,
  "variables": {
    "a": { "type": "int", "min": 0, "max": 9 },
    "b": { "type": "int", "min": 0, "max": 9 }
  },
  "constraints": [
    "a + b == 10",
    "a > b",
    { "all_different": ["a", "b"] },
    { "sum_eq": ["a", "b", 10] }
  ],
  "enumerate": 3,
  "objective": { "maximize": "a" }
}
```

```bash
python scripts/z3tool.py solve assets/problem.json --json
```

- Types: `int`, `real`, `bool`, `bv` (`bits`), `string`, `array`. Add `min`/`max` to bound a
  variable - unbounded integers are the most common reason a solve never finishes.
- Constraint strings are evaluated with only the variables and `z3` in scope.
- Object constraints: `all_different`, `sum` (`eq`/`le`/`ge`), `sum_eq`/`sum_le`/`sum_ge`,
  `at_most`, `at_least`, `exactly`, `implies`.
- `enumerate: N` blocks each model and returns up to N; `objective` switches to `Optimize`.
- The result carries `verified`, so a model is only reported after a re-check.

## Sudoku

```bash
python scripts/sudoku.py --difficulty hard --seed 7          # generate, unique solution
python scripts/sudoku.py --solve "530070000600195000..."     # solve a puzzle
python scripts/sudoku.py --solve "..." --count 3             # count solutions (stops at 3)
python scripts/sudoku.py --size 4 --difficulty easy --json   # sizes 4, 6, 9, 16
```

Generation fills a grid by backtracking, then removes clues one at a time and keeps a removal
only if Z3 confirms the puzzle still has exactly one solution. `--json` returns `puzzle`,
`clues`, `unique` and timing. Exit code 1 means "not unique" or "no solution" - never report a
success from a non-zero exit.

## Pitfalls (verified on z3 5.4.1)

- `Solver(timeout=1000)` raises `TypeError`; call `s.set(timeout=1000)` instead.
- `s.timeout()` and `s.get_parameter()` do not exist; remember the value you passed.
- `/` between two `Int` values is integer division, and `%` is modulo; z3py exports no `Div`
  or `Mod` function in 5.4.1. Use `ToReal(x) / ToReal(y)` for real division.
- `**` makes the problem nonlinear: expect `unknown` more often, and keep the timeout.
- `Optimize.maximize` returns a handle; pass that handle to `upper`/`lower`, and expect `oo`
  when the objective is unbounded.
- Quantifiers without `patterns=` blow up the search; prefer finite domains.
- `push()` and `pop()` change the assertion stack; re-check after every `pop()`.
- A nullary datatype constructor is a value: `Tree.leaf`, not `Tree.leaf()`.
- `z3.With(tactic, 'timeout', 1000)` raises `unknown parameter 'timeout'`; set the timeout on
  `tactic.solver()` instead.

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

- `scripts/z3tool.py` - doctor, lint, bounded run, and `solve` for JSON specs.
- `scripts/sudoku.py` - generate, solve and count Sudoku (sizes 4, 6, 9, 16).
- `scripts/selftest.py` - offline tests for all three scripts.
- `references/z3-encodings.md` - worked encodings, unsat cores, debugging `unknown`.
- `references/z3-theories.md` - bit-vectors, strings, datatypes, arrays, FP, tactics.
- `assets/solver_template.py` - starter script with the verify step wired in.
- `assets/problem.json` - example JSON spec for `z3tool.py solve`.
