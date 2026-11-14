# Z3 encodings

Worked shapes for the problems that come up most. Every snippet is complete enough to run.

## Base pattern

```python
import z3

TIMEOUT_MS = 20_000

s = z3.Solver()
s.set(timeout=TIMEOUT_MS)
x, y = z3.Ints("x y")
s.add(x + y == 10, x > y)

result = s.check()
if result == z3.sat:
    m = s.model()
    print({str(v): m.eval(v, model_completion=True) for v in (x, y)})
elif result == z3.unsat:
    print("unsat")
else:
    print("unknown:", s.reason_unknown())
```

## Verify the model

A model is only a candidate until the constraints are re-checked against it.

```python
def verify(constraints, variables, model) -> bool:
    check = z3.Solver()
    check.set(timeout=5_000)
    check.add(constraints)
    check.add([v == model.eval(v, model_completion=True) for v in variables])
    return check.check() == z3.sat
```

## Scheduling: one slot per task, no overlap

```python
tasks = {"build": 3, "test": 2, "deploy": 1}
horizon = sum(tasks.values())
start = {t: z3.Int(f"start_{t}") for t in tasks}

s = z3.Solver()
s.set(timeout=20_000)
for t, d in tasks.items():
    s.add(start[t] >= 0, start[t] + d <= horizon)

for a in tasks:
    for b in tasks:
        if a < b:
            s.add(z3.Or(start[a] + tasks[a] <= start[b],
                        start[b] + tasks[b] <= start[a]))
```

Add a makespan variable and minimise it:

```python
makespan = z3.Int("makespan")
s.add([start[t] + d <= makespan for t, d in tasks.items()])
opt = z3.Optimize()
opt.set(timeout=20_000)
opt.add(s.assertions())
obj = opt.maximize(makespan)     # keep the handle
if opt.check() == z3.sat:
    print(opt.lower(obj))        # 'oo' means unbounded
```

## All-different grid (sudoku)

```python
grid = [[z3.Int(f"c{r}{c}") for c in range(9)] for r in range(9)]
s = z3.Solver()
s.set(timeout=30_000)
for row in grid:
    s.add(z3.Distinct(row))
for c in range(9):
    s.add(z3.Distinct([grid[r][c] for r in range(9)]))
for br in range(3):
    for bc in range(3):
        s.add(z3.Distinct([grid[br*3+i][bc*3+j] for i in range(3) for j in range(3)]))
s.add([z3.And(v >= 1, v <= 9) for row in grid for v in row])
```

## Cardinality without arithmetic

```python
picked = [z3.Bool(f"p{i}") for i in range(6)]
s.add(z3.PbEq([(p, 1) for p in picked], 3))      # exactly 3
s.add(z3.AtMost(*picked, 4))                      # at most 4
```

`Sum([If(p, 1, 0) for p in picked]) == 3` also works and is easier to read.

## Why is it unsat

```python
s = z3.Solver()
s.set(unsat_core=True)                 # required before unsat_core()
s.assert_and_track(x > 3, "x_gt_3")
s.assert_and_track(x < 0, "x_lt_0")
if s.check() == z3.unsat:
    print(s.unsat_core())              # [x_gt_3, x_lt_0]
```

## Debugging `unknown`

1. Read `s.reason_unknown()`: `timeout`, `canceled`, `incomplete`, `memout`.
2. `timeout`: raise the budget once, or shrink the problem (smaller domain, symmetry breaking).
3. `incomplete`: the theory is outside the solver's fragment. Replace quantifiers with finite
   conjunctions, or switch to `SolverFor('QF_LIA')`, `QF_LRA`, `QF_BV`.
4. Nonlinear terms (`**`, `*` of two variables): try `z3.Real` instead of `Int`, or bound the
   variables.
5. Print `s.statistics()` to see where time went (conflicts, decisions, propagations).

## Symmetry breaking

Without it, symmetric solutions multiply the search. Add one canonical choice:

```python
s.add(start["build"] <= start["test"])     # identical tasks: fix their order
```

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Always enters the `if` | `if s.check():` - all three results are truthy | compare with `== z3.sat` |
| `TypeError: unexpected keyword` | `Solver(timeout=...)` | `s.set(timeout=ms)` |
| `unknown` immediately | 1 ms timeout, or nonlinear arithmetic | raise the budget, linearise |
| `oo` from `upper`/`lower` | objective unbounded | add a bound or a domain |
| Wrong model | constraint encoded with the wrong operator | substitute the model back and re-check |
