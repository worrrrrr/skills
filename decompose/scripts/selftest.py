#!/usr/bin/env python3
"""Self-tests for the Decomposition Engine (stdlib only). Run: python scripts/selftest.py"""
import importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("decompose", os.path.join(HERE, "decompose.py"))
if _spec is None or _spec.loader is None:
    raise SystemExit("cannot load decompose.py next to this selftest")
_loader = _spec.loader
D = importlib.util.module_from_spec(_spec)
_loader.exec_module(D)

fails = []
def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)

def doc(tasks, unit="h"):
    return {"schema_version": "1.0",
            "project": {"name": "t", "outcome": "o", "definition_of_done": ["d"], "unit": unit},
            "assumptions": ["a"], "open_questions": [], "tasks": tasks}

def leaf(i, deps=(), o=1, m=2, p=3, parent=None, **kw):
    t = {"id": i, "title": "Do " + i, "parent": parent, "type": "task", "deps": list(deps),
         "estimate": {"o": o, "likely": m, "p": p}, "owner_role": "dev",
         "acceptance": ["ok"], "artifacts": [], "risk": "low", "notes": ""}
    t.update(kw); return t

def codes(d):
    return {i.code for i in D.validate(d)}

check("engine imports", hasattr(D, "Graph") and hasattr(D, "validate"))

d = doc([leaf("A"), leaf("B", ["A"]), leaf("C", ["A"]), leaf("D", ["B", "C"])])
g = D.Graph(d); s = g.schedule()
check("pert mean", abs(D.Graph.pert({"estimate": {"o": 1, "likely": 2, "p": 9}})[0] - 3.0) < 1e-9)
check("pert sigma", abs(D.Graph.pert({"estimate": {"o": 1, "likely": 2, "p": 9}})[1] - 8/6) < 1e-9)
check("span = 3 tasks not 4", abs(s["project"] - 3 * 2.0) < 1e-9)
check("critical path length 3", len(s["critical"]) == 3)
check("wave of D is 3", s["wave"]["D"] == 3)

d = doc([leaf("A", ["B"]), leaf("B", ["A"])])
check("cycle detected", "E_CYCLE" in codes(d))

d = doc([leaf("A", ["ZZ"]), leaf("B", acceptance=[])])
c = codes(d); check("dangling dep", "E_DEP" in c); check("missing acceptance", "E_ACCEPT" in c)
d = doc([leaf("A"), leaf("A")]); check("duplicate id", "E_DUP_ID" in codes(d))

d = doc([leaf("A", o=10, m=14, p=20)])
check("soft cap warn", "W_TOO_BIG" in codes(d))
d = doc([leaf("A", o=30, m=40, p=60)])
check("hard cap error", "E_HUGE" in codes(d))

d = doc([{"id": "G", "title": "Group", "parent": None, "type": "task", "deps": [],
          "acceptance": [], "risk": "low"},
         leaf("G1", parent="G"), leaf("G2", ["G1"], parent="G"), leaf("B", ["G"])])
g = D.Graph(d); s = g.schedule()
check("rollup dep -> full span", abs(s["project"] - 3 * 2.0) < 1e-9)
check("rollup excluded from CP", "G" not in s["critical"])
check("no negative slack", all(v >= 0 for v in s["slack"].values()))

d = doc([leaf("A"), leaf("M", ["A"], o=0, m=0, p=0, type="milestone")])
s = D.Graph(d).schedule(); check("milestone adds no time", abs(s["project"] - 2.0) < 1e-9)

d = doc([leaf("A"), leaf("B", ["A"]), leaf("C", ["A"])])
g = D.Graph(d); eff = g.effective_deps(); done = {"A"}
ready = [t for t in g.order if t not in done and not g.children.get(t)
         and all(x in done for x in eff[t])]
check("frontier after A", set(ready) == {"B", "C"})

d = doc([leaf("A"), leaf("B", ["A"])])
g = D.Graph(d); iss = D.validate(d); s = g.schedule()
for fn in (D.render_md, D.render_mermaid, D.render_csv, D.render_json):
    out = fn(d, g, s, iss)
    check(f"{fn.__name__} produces output", isinstance(out, str) and len(out) > 50)
check("P80 >= P50", s["p80"] >= s["p50"])

print("\n" + ("ALL TESTS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)