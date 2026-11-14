# Theories beyond linear arithmetic

Verified on z3 5.4.1 with the snippets below. Load this file only for the theory you need.

## Enumeration: all models

```python
s = z3.Solver(); s.set(timeout=20_000)
s.add(constraints)
seen = []
while s.check() == z3.sat and len(seen) < LIMIT:
    m = s.model()
    seen.append({str(v): m.eval(v, model_completion=True) for v in variables})
    s.add(z3.Or([v != m.eval(v, model_completion=True) for v in variables]))
```

`z3tool.py solve spec.json` does this with `"enumerate": N`.

## Incremental solving

```python
s = z3.Solver(); s.set(timeout=5_000)
x = z3.Int('x')
s.add(x > 3)
s.push(); s.add(x < 0); s.check()    # unsat, the base assertions stay
s.pop()
s.check(x < 100)                      # check() takes assumptions, no push needed
```

Balance every `push()` with a `pop()`; `z3tool.py lint` flags an imbalance. Use assumptions
instead of push/pop when the extra facts are per-call only.

## Bit-vectors

```python
a, b = z3.BitVecs('a b', 8)
s = z3.Solver(); s.set(timeout=5_000)
s.add(z3.BVAddNoOverflow(a, b, True), a == 200, b == 100)   # sat: 300 overflows 8 bits
s.check()
```

- `bvadd`, `bvsub`, `bvmul` wrap silently; guard with `BVAddNoOverflow`, `BVSubNoUnderflow`,
  `BVMulNoOverflow`.
- Signed division is `a / b`; unsigned is `z3.UDiv(a, b)`; remainder `z3.SRem` (signed),
  `z3.URem` (unsigned), `z3.SMod`.
- Convert with `z3.Int2BV`, `z3.BV2Int(bv, is_signed)`.

## Arrays and lambda

```python
A = z3.Array('A', z3.IntSort(), z3.IntSort())
s.add(z3.Select(A, 0) == 7, z3.Select(z3.Store(A, 1), 0) == 7)
const = z3.K(z3.IntSort(), z3.IntVal(0))     # constant array
f = z3.Lambda([z3.Int('i')], z3.Int('i') + 1)
```

Array equality is extensional: `A == B` means equal at every index.

## Strings and regex

```python
x = z3.String('x')
s = z3.Solver(); s.set(timeout=5_000)
s.add(z3.Length(x) == 3, z3.PrefixOf(z3.StringVal('ab'), x),
      z3.SuffixOf(z3.StringVal('9'), x))          # x = "ab9"
s.check()
s.add(z3.InRe(x, z3.Re('ab*')))                   # regex membership
```

- `z3.StrToInt` returns -1 on failure, so add `IntToStr` round-trips if the value matters.
- Long string problems are slow: bound `Length` first.

## Datatypes

```python
Tree = z3.Datatype('Tree')
Tree.declare('leaf')
Tree.declare('node', ('left', Tree), ('right', Tree))
Tree = Tree.create()
h = z3.Const('h', Tree)
s.add(h == Tree.node(Tree.leaf, Tree.leaf))       # leaf is a value, NOT leaf()
```

- A nullary constructor is a constant: `Tree.leaf`, never `Tree.leaf()`.
- Recursive functions: `z3.RecFunction`, then `z3.RecAddDefinition`.

## Floating point

```python
f = z3.FP('f', z3.Float32())
s.add(f > z3.FPVal(1.0, z3.Float32()))
```

Z3 models IEEE-754 exactly, including rounding modes (`z3.RNE`, `z3.RTZ`, …). Use `Real` when
the question is arithmetic, not bits.

## Fixedpoint (Datalog)

```python
fp = z3.Fixedpoint()
edge = z3.Function('edge', z3.IntSort(), z3.IntSort(), z3.BoolSort())
reach = z3.Function('reach', z3.IntSort(), z3.BoolSort())
i, j = z3.Ints('i j')
fp.rule(reach(i), [edge(i, j)])
```

Good for reachability and simple inference; it does not accept arbitrary arithmetic goals.

## Tactics and performance

```python
tac = z3.Then('simplify', 'solve-eqs', 'smt')      # works
s = tac.solver()
s.set(timeout=10_000)                              # timeout on the solver
```

- `z3.With(tac, 'timeout', 1000)` raises `Z3Exception: unknown parameter 'timeout'` on this
  tactic. Set the timeout on the solver instead.
- `s.statistics()` after `check()` shows `conflicts`, `decisions`, `propagations`, `memory`.
- `z3.SolverFor('QF_LIA')` (or `QF_BV`, `QF_LRA`, `AUFLIA`) picks a theory solver directly.

## Not available in this build

`z3.proof()` and `z3.Div` / `z3.Mod` do not exist in z3py 5.4.1; integer division is `/`, modulo
is `%`, and proofs need a custom build.
