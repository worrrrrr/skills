#!/usr/bin/env python3
"""Self-tests for the AIWOR interview ledger (stdlib only).

Run: python scripts/selftest.py
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("interview", os.path.join(HERE, "interview.py"))
if _spec is None or _spec.loader is None:
    raise SystemExit("cannot load interview.py next to this selftest")
I = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(I)

fails = []


def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)


def doc(**kw):
    d = {"schema_version": "1.0", "topic": "export csv", "request": "add csv export",
         "round": 1, "max_rounds": 4, "questions": [], "decisions": [], "conflicts": []}
    d.update(kw)
    return d


def q(qid, status="open", **kw):
    d = {"id": qid, "round": 1, "ask": "which columns?", "why": "decides the schema",
         "owner": "repo", "status": status}
    d.update(kw)
    return d


def answered(qid, **kw):
    return q(qid, "answered", answer="all public columns", evidence=["src/export.ts:12"], **kw)


def assumed(qid, **kw):
    return q(qid, "assumed", assumption="land in /api/export",
             impact="route name changes with the UI", **kw)


def codes(d):
    return {i.code for i in I.validate(d)}


def run(argv):
    """Return (exit_code, stdout). SystemExit becomes its code."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            rc = I.main(argv)
        except SystemExit as exc:
            rc = exc.code
    return rc, buf.getvalue()


# ---------------------------------------------------------------- schema gates
check("engine imports", hasattr(I, "validate") and hasattr(I, "render_plan"))
check("clean converged ledger", I.validate(doc(questions=[answered("Q1")],
                                                decisions=[{"id": "D1", "text": "all public columns",
                                                            "question": "Q1"}])) == [])

check("open question blocks", "E_OPEN_Q" in codes(doc(questions=[q("Q1")])))
check("answered needs text", "E_ANSWER" in codes(doc(questions=[q("Q1", "answered", evidence=["a:1"])])))
check("answered needs evidence",
      "E_EVIDENCE" in codes(doc(questions=[q("Q1", "answered", answer="x")])))
check("assumed needs assumption", "E_ASSUMPTION" in codes(doc(questions=[q("Q1", "assumed", impact="x")])))
check("assumed needs impact", "E_IMPACT" in codes(doc(questions=[q("Q1", "assumed", assumption="x")])))
check("duplicate question id", "E_QID" in codes(doc(questions=[answered("Q1"), answered("Q1")])))
check("bad question id", "E_QID" in codes(doc(questions=[q("q1")])))
check("bad owner", "E_OWNER" in codes(doc(questions=[q("Q1", owner="nobody")])))
check("bad status", "E_QSTATUS" in codes(doc(questions=[q("Q1", "maybe")])))
check("why is required", "E_WHY" in codes(doc(questions=[answered("Q1", why="")])))

check("duplicate decision id", "E_DID" in codes(doc(
    decisions=[{"id": "D1", "text": "a"}, {"id": "D1", "text": "b"}])))
check("decision points at unknown question", "E_DECISION_SRC" in codes(doc(
    decisions=[{"id": "D1", "text": "a", "question": "Q9"}])))

check("conflict needs two ids", "E_CONFLICT_PAIR" in codes(doc(
    conflicts=[{"id": "C1", "between": ["D1"], "status": "resolved", "resolution": "x"}])))
check("conflict refs unknown decision", "E_CONFLICT_REF" in codes(doc(
    conflicts=[{"id": "C1", "between": ["D1", "D2"], "status": "open"}])))
check("open conflict blocks", "E_OPEN_CONFLICT" in codes(doc(
    decisions=[{"id": "D1", "text": "a"}, {"id": "D2", "text": "b"}],
    conflicts=[{"id": "C1", "between": ["D1", "D2"], "text": "a vs b", "status": "open"}])))
check("resolved needs text", "E_CONFLICT_RESOLUTION" in codes(doc(
    decisions=[{"id": "D1", "text": "a"}, {"id": "D2", "text": "b"}],
    conflicts=[{"id": "C1", "between": ["D1", "D2"], "text": "a vs b", "status": "resolved"}])))

check("round cap enforced", "E_ROUND_OVER" in codes(doc(round=5, max_rounds=4)))
check("bad max_rounds", "E_MAX_ROUNDS" in codes(doc(max_rounds=99)))
check("non-object is one error", codes(["not a ledger"]) == {"E_DOC"})

# --------------------------------------------------------------------- stats
s = I.stats(doc(round=2, questions=[answered("Q1"), assumed("Q2"), q("Q3", owner="user")],
                decisions=[{"id": "D1", "text": "x", "question": "Q1"}]))
check("stats counts", s["questions"] == 3 and s["answered"] == 1 and s["assumed"] == 1
      and s["open"] == 1 and s["user_open"] == 1 and s["decisions"] == 1)
check("stats not converged", s["converged"] is False)
check("stats converged", I.stats(doc(questions=[answered("Q1")]))["converged"] is True)

# -------------------------------------------------------------------- render
clear = doc(questions=[answered("Q1"), assumed("Q2")],
            decisions=[{"id": "D1", "text": "export all public columns", "question": "Q1",
                        "evidence": ["src/export.ts:12"]}])
interview_md = I.render_interview(clear)
check("interview shows question", "Q1" in interview_md and "src/export.ts:12" in interview_md)
check("interview shows assumption", "land in /api/export" in interview_md)
check("plan prefilled with decision", "export all public columns" in I.render_plan(clear))
check("plan lists assumption", "If wrong" in I.render_plan(clear))
check("plan asks for verification", "verify:" in I.render_plan(clear))

# --------------------------------------------------------------- CLI + exits
with tempfile.TemporaryDirectory() as tmp:
    ledger = os.path.join(tmp, "interview.json")
    rc, _ = run(["init", "--topic", "t", "--request", "r", "--out", ledger])
    check("init exit 0", rc == 0 and os.path.exists(ledger))
    check("init refuses overwrite", run(["init", "--topic", "t", "--request", "r", "--out", ledger])[0] == 3)

    with open(ledger, "r", encoding="utf-8") as fh:
        on_disk = json.load(fh)
    check("init writes schema", on_disk["schema_version"] == "1.0" and on_disk["questions"] == [])

    rc, _ = run(["validate", ledger])
    check("empty ledger is not converged", rc == 1)
    rc, out = run(["status", ledger])
    check("empty ledger status not converged", rc == 1 and "NOT CONVERGED" in out)
    check("empty ledger has nothing to ask", run(["next", ledger])[0] == 1)

    on_disk["questions"] = [answered("Q1")]
    on_disk["decisions"] = [{"id": "D1", "text": "all public columns", "question": "Q1",
                             "evidence": ["src/export.ts:12"]}]
    with open(ledger, "w", encoding="utf-8") as fh:
        json.dump(on_disk, fh)

    plan_path = os.path.join(tmp, "PLAN.md")
    rc, out = run(["validate", ledger])
    check("settled ledger validates", rc == 0)
    rc, out = run(["status", ledger])
    check("settled ledger converged", rc == 0 and "CONVERGED" in out)
    rc, _ = run(["plan", ledger, "--out", plan_path])
    check("plan writes when clear", rc == 0 and os.path.exists(plan_path))
    with open(plan_path, "r", encoding="utf-8") as fh:
        check("plan file has decision", "all public columns" in fh.read())

    on_disk["questions"].append(q("Q2"))
    with open(ledger, "w", encoding="utf-8") as fh:
        json.dump(on_disk, fh)
    rc, _ = run(["plan", ledger, "--out", plan_path])
    check("plan refuses while unclear", rc == 1)
    rc, out = run(["next", ledger, "--json"])
    check("next prints open batch", rc == 0 and json.loads(out)[0]["id"] == "Q2")
    rc, _ = run(["validate", ledger, "--strict"])
    check("strict fails on error", rc == 1)

    missing = os.path.join(tmp, "nope.json")
    rc, _ = run(["validate", missing])
    check("missing file exits 2", rc == 2)
    rc, _ = run(["init", "--topic", "t"])
    check("bad usage exits 3", rc == 3)

print()
print(f"{len(fails)} failure(s)" if fails else "all checks passed")
sys.exit(1 if fails else 0)
