#!/usr/bin/env python3
"""Decomposition Engine - validate a task DAG and compute its schedule.

Stdlib only. Python 3.8+.

Commands
    init      scaffold a tasks.json
    validate  structural + quality gate (exit 1 on ERROR)
    plan      render md | mermaid | csv | json
    next      list currently unblocked tasks given completed ids
    stats     effort / risk / parallelism summary

Model
    duration = PERT mean (o + 4*likely + p) / 6 ; sigma = (p - o) / 6
    Rollup parents (nodes with children) contribute zero own duration; their
    subtree effort is reported separately. Dependencies are finish-to-start and
    may point at any node; a dependency on a rollup means "all its leaves".
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
from collections import defaultdict, deque
from typing import TypedDict

SCHEMA_VERSION = "1.0"
ID_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")
TYPES = {"task", "spike", "milestone", "decision"}
RISKS = {"low", "med", "high"}
IDEAL_HOURS_PER_DAY = 6.0    # focused hours in a working day, not clock hours
SOFT_CAP_DAYS = 2.0          # T1: split a leaf above this
HARD_CAP_DAYS = 5.0          # never allow a leaf above this
Z80 = 0.8416                 # normal quantile for P80
SECOND_VERB_RE = re.compile(
    r"^(implement|build|add|write|create|deploy|migrate|test|design|refactor|fix|set up|setup)\b")


class Schedule(TypedDict):
    """Result of Graph.schedule(): concrete values, not a mixed bag of types."""

    order: list[str]
    dur: dict[str, float]
    sigma: dict[str, float]
    es: dict[str, float]
    ef: dict[str, float]
    ls: dict[str, float]
    lf: dict[str, float]
    slack: dict[str, float]
    project: float
    critical: list[str]
    p50: float
    p80: float
    cp_sigma: float
    wave: dict[str, int]


def size_caps(unit):
    """(soft, hard) leaf-size caps expressed in the document's own unit."""
    scale = IDEAL_HOURS_PER_DAY if unit == "h" else 1.0
    return SOFT_CAP_DAYS * scale, HARD_CAP_DAYS * scale


# --------------------------------------------------------------------------- io
def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def emit(text, out=None):
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


class Issue:
    def __init__(self, level, code, msg, tid=None):
        self.level, self.code, self.msg, self.tid = level, code, msg, tid

    def __str__(self):
        loc = f"[{self.tid}] " if self.tid else ""
        return f"{self.level:5s} {self.code:22s} {loc}{self.msg}"


# ------------------------------------------------------------------- graph core
class Graph:
    def __init__(self, doc):
        self.doc = doc
        self.tasks = {}
        self.order = []
        for t in doc.get("tasks", []):
            tid = t.get("id")
            if tid in self.tasks:
                continue  # duplicate reported by validator
            self.tasks[tid] = t
            self.order.append(tid)
        self.children = defaultdict(list)
        for tid in self.order:
            par = self.tasks[tid].get("parent")
            if par in self.tasks:
                self.children[par].append(tid)
        self.deps = {tid: [d for d in self.tasks[tid].get("deps", []) if d in self.tasks]
                     for tid in self.order}
        self.succ = defaultdict(list)
        for tid, ds in self.deps.items():
            for d in ds:
                self.succ[d].append(tid)

    def descendants(self, tid):
        out, stack = set(), list(self.children.get(tid, []))
        while stack:
            n = stack.pop()
            if n in out:
                continue
            out.add(n)
            stack.extend(self.children.get(n, []))
        return out

    def leaf_set(self, tid):
        d = self.descendants(tid)
        return {n for n in d if not self.children.get(n)} or ({tid} if not d else set())

    def effective_deps(self):
        """Deps expanded so that pointing at a rollup means all its leaves."""
        eff = {}
        for tid in self.order:
            acc = set()
            for d in self.deps[tid]:
                acc |= self.leaf_set(d) if self.children.get(d) else {d}
            own = self.leaf_set(tid) if self.children.get(tid) else {tid}
            eff[tid] = sorted(acc - own)
        return eff

    @staticmethod
    def pert(t):
        if t.get("type") == "milestone":
            return 0.0, 0.0
        e = t.get("estimate") or {}
        o, m, p = (float(e.get(k, 0) or 0) for k in ("o", "likely", "p"))
        return (o + 4 * m + p) / 6.0, max(0.0, (p - o) / 6.0)

    def duration(self, tid):
        if self.children.get(tid):
            return 0.0, 0.0  # rollup: no own work
        return self.pert(self.tasks[tid])

    def topo(self):
        indeg = {t: len(self.deps[t]) for t in self.order}
        q = deque(sorted([t for t, d in indeg.items() if d == 0]))
        out = []
        while q:
            n = q.popleft()
            out.append(n)
            for s in sorted(self.succ[n]):
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)
        return out, len(out) == len(self.order)

    def schedule(self) -> "Schedule | None":
        """Forward/backward pass over real work items (rollups are containers)."""
        order, ok = self.topo()
        if not ok:
            return None
        dur = {t: self.duration(t)[0] for t in self.order}
        sig = {t: self.duration(t)[1] for t in self.order}

        # expand deps: pointing at a rollup means "after all of its leaves"
        eff = self.effective_deps()
        leaves = [t for t in order if not self.children.get(t)]
        preds = {t: [d for d in eff[t] if d in dur and not self.children.get(d)] for t in leaves}
        succ = defaultdict(list)
        for t in leaves:
            for d in preds[t]:
                succ[d].append(t)

        indeg = {t: len(preds[t]) for t in leaves}
        q = deque(sorted([t for t in leaves if indeg[t] == 0]))
        lorder = []
        while q:
            n = q.popleft()
            lorder.append(n)
            for s in sorted(succ[n]):
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)
        if len(lorder) != len(leaves):
            return None  # cycle introduced by expansion

        es, ef = {}, {}
        for t in lorder:
            es[t] = max((ef[d] for d in preds[t]), default=0.0)
            ef[t] = es[t] + dur[t]
        project = max(ef.values(), default=0.0)
        lf, ls = {}, {}
        for t in reversed(lorder):
            lf[t] = min((ls[s] for s in succ[t]), default=project)
            ls[t] = lf[t] - dur[t]

        # rollup nodes inherit the envelope of their subtree
        for t in order:
            if self.children.get(t):
                kids = [k for k in self.leaf_set(t) if k in es]
                es[t] = min((es[k] for k in kids), default=0.0)
                ef[t] = max((ef[k] for k in kids), default=0.0)
                ls[t] = min((ls[k] for k in kids), default=project)
                lf[t] = max((lf[k] for k in kids), default=project)

        slack = {t: max(0.0, round(ls[t] - es[t], 6)) for t in self.order}
        ends = [t for t in leaves if abs(ef[t] - project) < 1e-9]
        chain, cur, seen = [], (max(ends, key=lambda t: ef[t]) if ends else None), set()
        while cur and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            cur = max(preds[cur], key=lambda d: ef[d]) if preds[cur] else None
        chain.reverse()
        var = sum(sig[t] ** 2 for t in chain)

        wave = {}
        for t in lorder:
            wave[t] = 1 + max((wave[d] for d in preds[t]), default=0)
        for t in order:
            wave.setdefault(t, 0)  # rollup marker

        return Schedule(order=order, dur=dur, sigma=sig, es=es, ef=ef, ls=ls, lf=lf,
                        slack=slack, project=project, critical=chain,
                        p50=project, p80=project + Z80 * math.sqrt(var),
                        cp_sigma=math.sqrt(var), wave=wave)

    def subtree_span(self, tid):
        leaves = self.leaf_set(tid) if self.children.get(tid) else {tid}
        return sum(self.pert(self.tasks[l])[0] for l in leaves)


# -------------------------------------------------------------------- validate
def validate(doc):
    issues = []
    add = lambda lvl, code, msg, tid=None: issues.append(Issue(lvl, code, msg, tid))

    if not isinstance(doc, dict):
        return [Issue("ERROR", "E_ROOT", "document must be a JSON object")]
    if str(doc.get("schema_version", "")) != SCHEMA_VERSION:
        add("WARN", "W_SCHEMA", f"schema_version != {SCHEMA_VERSION}")
    proj = doc.get("project") or {}
    unit = proj.get("unit", "h")
    if unit not in ("h", "d"):
        add("ERROR", "E_UNIT", "project.unit must be 'h' or 'd'")
        unit = "h"
    if not proj.get("outcome"):
        add("ERROR", "E_OUTCOME", "project.outcome is required (Phase 0)")
    if not proj.get("definition_of_done"):
        add("WARN", "W_DOD", "project.definition_of_done is empty")

    raw = doc.get("tasks") or []
    if not raw:
        add("ERROR", "E_EMPTY", "no tasks")
        return issues

    seen = set()
    for t in raw:
        tid = t.get("id")
        if not tid or not ID_RE.match(str(tid)):
            add("ERROR", "E_ID", f"invalid id {tid!r}", tid)
            continue
        if tid in seen:
            add("ERROR", "E_DUP_ID", "duplicate id", tid)
        seen.add(tid)

    g = Graph(doc)
    soft_cap, hard_cap = size_caps(unit)

    for tid in g.order:
        t = g.tasks[tid]
        typ = t.get("type", "task")
        if typ not in TYPES:
            add("ERROR", "E_TYPE", f"unknown type {typ!r}", tid)
        if not t.get("title"):
            add("ERROR", "E_TITLE", "title required", tid)
        if t.get("risk", "low") not in RISKS:
            add("ERROR", "E_RISK", "risk must be low|med|high", tid)
        par = t.get("parent")
        if par is not None and par not in g.tasks:
            add("ERROR", "E_PARENT", f"unknown parent {par!r}", tid)
        for d in t.get("deps", []):
            if d not in g.tasks:
                add("ERROR", "E_DEP", f"unknown dependency {d!r}", tid)
            if d == tid:
                add("ERROR", "E_SELF_DEP", "depends on itself", tid)

        is_leaf = not g.children.get(tid)
        est = t.get("estimate") or {}
        if is_leaf and typ != "milestone":
            missing = [k for k in ("o", "likely", "p") if k not in est]
            if missing:
                add("ERROR", "E_EST", f"missing estimate keys {missing}", tid)
            else:
                o, m, p = (float(est[k]) for k in ("o", "likely", "p"))
                if min(o, m, p) < 0:
                    add("ERROR", "E_EST_NEG", "negative estimate", tid)
                if not (o <= m <= p):
                    add("ERROR", "E_EST_ORDER", "require o <= likely <= p", tid)
                mean, _ = g.pert(t)
                if mean > soft_cap:
                    add("WARN", "W_TOO_BIG",
                        f"PERT {mean:.1f}{unit} > soft cap {soft_cap:g}{unit} "
                        f"({SOFT_CAP_DAYS:g} days); split (T1)", tid)
                if mean > hard_cap:
                    add("ERROR", "E_HUGE",
                        f"PERT {mean:.1f}{unit} exceeds hard cap {hard_cap:g}{unit} "
                        f"({HARD_CAP_DAYS:g} days)", tid)
                if p == o and typ == "spike":
                    add("WARN", "W_SPIKE_RANGE", "spike should carry a pessimistic bound", tid)
            if not t.get("acceptance"):
                add("ERROR", "E_ACCEPT", "leaf has no acceptance criteria (T4)", tid)
            if typ == "spike" and not t.get("artifacts"):
                add("WARN", "W_SPIKE_OUT", "spike deliverable should be a written decision", tid)
            if not t.get("owner_role"):
                add("WARN", "W_OWNER", "no owner_role (T3)", tid)
            title_l = (t.get("title") or "").lower()
            if " and " in title_l:
                tail = title_l.split(" and ", 1)[1]
                if SECOND_VERB_RE.match(tail):
                    add("WARN", "W_AND", "title chains two verbs - likely two outcomes (T2)", tid)
        elif not is_leaf and est:
            add("WARN", "W_ROLLUP_EST", "rollup carries an estimate; it is ignored", tid)

    _, ok = g.topo()
    if not ok:
        add("ERROR", "E_CYCLE", "dependency cycle detected")
    for tid in g.order:
        chain, cur = set(), tid
        while cur is not None:
            if cur in chain:
                add("ERROR", "E_PARENT_CYCLE", "parent cycle", tid)
                break
            chain.add(cur)
            cur = g.tasks.get(cur, {}).get("parent")
    for tid in g.order:
        depth, cur = 1, g.tasks[tid].get("parent")
        while cur in g.tasks:
            depth += 1
            cur = g.tasks[cur].get("parent")
        if depth > 4:
            add("WARN", "W_DEPTH", f"hierarchy depth {depth} > 4; re-cut the axis", tid)

    sch = g.schedule()
    if sch:
        for tid in g.order:
            if len(g.succ[tid]) >= 3:
                add("WARN", "W_FANOUT", f"fan-out {len(g.succ[tid])} - schedule early", tid)
        total = sum(sch["dur"].values())
        hi = sum(sch["dur"][t] for t in g.order if g.tasks[t].get("risk") == "high")
        if total and hi / total > 0.30:
            add("WARN", "W_RISK_LOAD", f"{hi/total:.0%} of effort is high-risk; front-load spikes")
        roles = {g.tasks[t].get("owner_role") for t in sch["critical"] if g.tasks[t].get("owner_role")}
        if len(roles) == 1 and len(sch["critical"]) > 3:
            add("WARN", "W_SINGLE_ROLE", "critical path owned by one role - bus factor 1")
        if not doc.get("assumptions") and not doc.get("open_questions"):
            add("WARN", "W_UNKNOWNS", "no assumptions/open_questions recorded")
    return issues


# --------------------------------------------------------------------- renders
def fmt(x, unit):
    return f"{x:.1f}{unit}"


def render_md(doc, g, sch, issues=()):
    proj = doc.get("project", {})
    unit = proj.get("unit", "h")
    L = [f"# Plan - {proj.get('name','(unnamed)')}", ""]
    L.append(f"**Outcome:** {proj.get('outcome','-')}")
    if proj.get("definition_of_done"):
        L.append("\n**Definition of Done**")
        L += [f"- {d}" for d in proj["definition_of_done"]]
    if proj.get("non_goals"):
        L.append("\n**Non-goals:** " + "; ".join(proj["non_goals"]))
    if proj.get("constraints"):
        L.append("\n**Constraints:** " + "; ".join(map(str, proj["constraints"])))
    L.append("")
    L.append("## Schedule")
    L.append(f"- Total ideal effort: **{fmt(sum(sch['dur'].values()), unit)}**")
    L.append(f"- Critical-path length (P50): **{fmt(sch['p50'], unit)}**")
    L.append(f"- With uncertainty (P80): **{fmt(sch['p80'], unit)}** (sigma {sch['cp_sigma']:.2f})")
    par = sum(sch["dur"].values()) / sch["p50"] if sch["p50"] else 0
    L.append(f"- Theoretical parallelism: **{par:.2f}x** (effort / span)")
    L.append(f"- Critical path: {' -> '.join(sch['critical']) or '-'}")
    L.append("")
    L.append("## Waves (parallel batches)")
    waves = defaultdict(list)
    for t in g.order:
        if not g.children.get(t):
            waves[sch["wave"][t]].append(t)
    L.append("| Wave | Tasks | Effort | Can run concurrently |")
    L.append("|---|---|---|---|")
    for w in sorted(waves):
        ts = waves[w]
        eff = sum(sch["dur"][t] for t in ts)
        L.append(f"| {w} | {', '.join(ts)} | {fmt(eff, unit)} | {len(ts)} |")
    L.append("")
    L.append("## Tasks")
    L.append("| ID | Title | Type | Owner | Deps | PERT | Slack | Risk | CP |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    cp = set(sch["critical"])
    for t in sch["order"]:
        task = g.tasks[t]
        rollup = bool(g.children.get(t))
        d = g.subtree_span(t) if rollup else sch["dur"][t]
        L.append("| {id} | {title}{r} | {typ} | {own} | {deps} | {d} | {sl} | {risk} | {cp} |".format(
            id=t, title=task.get("title", ""), r=" *(rollup)*" if rollup else "",
            typ=task.get("type", "task"), own=task.get("owner_role", "-") or "-",
            deps=", ".join(task.get("deps", [])) or "-", d=fmt(d, unit),
            sl=fmt(sch["slack"][t], unit), risk=task.get("risk", "low"),
            cp="YES" if t in cp else ""))
    L.append("")
    L.append("## Acceptance criteria")
    for t in sch["order"]:
        acc = g.tasks[t].get("acceptance") or []
        if acc:
            L.append(f"**{t} - {g.tasks[t].get('title','')}**")
            L += [f"- [ ] {a}" for a in acc]
            arts = g.tasks[t].get("artifacts") or []
            if arts:
                L.append(f"  - artifacts: {', '.join(map(str, arts))}")
            L.append("")
    risks = [t for t in g.order if g.tasks[t].get("risk") == "high"]
    if risks:
        L.append("## Top risks")
        for t in risks:
            L.append(f"- **{t}** {g.tasks[t].get('title','')} - "
                     f"{g.tasks[t].get('notes') or '(no mitigation recorded)'}")
        L.append("")
    if doc.get("assumptions"):
        L.append("## Assumptions")
        L += [f"- {a}" for a in doc["assumptions"]]
        L.append("")
    if doc.get("open_questions"):
        L.append("## Open questions")
        L += [f"- {q}" for q in doc["open_questions"]]
        L.append("")
    warns = [i for i in issues if i.level == "WARN"]
    if warns:
        L.append("## Validator warnings (justify or fix)")
        L += [f"- `{i.code}` {('[' + i.tid + '] ') if i.tid else ''}{i.msg}" for i in warns]
    return "\n".join(L)


def _node(t):
    return t.replace("-", "_").replace(".", "_")


def render_mermaid(doc, g, sch, issues=()):
    cp = set(sch["critical"])
    L = ["graph LR"]
    for t in sch["order"]:
        title = (g.tasks[t].get("title") or t).replace('"', "'")
        shape = '(["{}"])' if g.tasks[t].get("type") == "milestone" else '["{}"]'
        L.append(f"  {_node(t)}" + shape.format(f"{t}: {title}"))
    for t in sch["order"]:
        for d in g.deps[t]:
            L.append(f"  {_node(d)} --> {_node(t)}")
    L.append("  classDef crit fill:#ffe0e0,stroke:#c0392b,stroke-width:2px;")
    L.append("  classDef spike fill:#fff4d6,stroke:#d68910;")
    if cp:
        L.append("  class " + ",".join(sorted(_node(x) for x in cp)) + " crit;")
    sp = [t for t in g.order if g.tasks[t].get("type") == "spike"]
    if sp:
        L.append("  class " + ",".join(sorted(_node(x) for x in sp)) + " spike;")
    return "\n".join(L)


def render_csv(doc, g, sch, issues=()):
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["id", "title", "parent", "type", "owner_role", "deps", "o", "likely", "p",
                 "pert", "sigma", "es", "ef", "slack", "wave", "critical", "risk", "acceptance"])
    cp = set(sch["critical"])
    for t in sch["order"]:
        task = g.tasks[t]
        e = task.get("estimate") or {}
        mean, sig = g.pert(task)
        wr.writerow([t, task.get("title", ""), task.get("parent") or "", task.get("type", "task"),
                     task.get("owner_role", ""), "|".join(task.get("deps", [])),
                     e.get("o", ""), e.get("likely", ""), e.get("p", ""),
                     round(mean, 3), round(sig, 3), round(sch["es"][t], 3), round(sch["ef"][t], 3),
                     round(sch["slack"][t], 3), sch["wave"][t], int(t in cp), task.get("risk", "low"),
                     " | ".join(task.get("acceptance") or [])])
    return buf.getvalue()


def render_json(doc, g, sch, issues=()):
    out = dict(sch)
    out["tasks"] = {t: {"pert": g.pert(g.tasks[t])[0], "subtree_effort": g.subtree_span(t)}
                    for t in g.order}
    out["warnings"] = [i.__dict__ for i in issues if i.level == "WARN"]
    return json.dumps(out, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------------ init
SCAFFOLD = {
    "schema_version": SCHEMA_VERSION,
    "project": {"name": "my-project", "outcome": "Observable end state",
                "definition_of_done": ["..."], "unit": "h",
                "constraints": [], "non_goals": []},
    "assumptions": ["Team of 2 engineers, 6 ideal hours/day each"],
    "open_questions": ["Which system owns the source of truth?"],
    "tasks": [
        {"id": "S1", "title": "Spike: prove the risky integration works", "parent": None,
         "type": "spike", "deps": [], "estimate": {"o": 2, "likely": 4, "p": 8},
         "owner_role": "backend", "acceptance": ["Written go/no-go decision with evidence"],
         "artifacts": ["docs/spike-s1.md"], "risk": "high", "notes": "Timebox 1 day."},
        {"id": "T1", "title": "Define the interface contract", "parent": None,
         "type": "task", "deps": ["S1"], "estimate": {"o": 1, "likely": 2, "p": 4},
         "owner_role": "backend", "acceptance": ["Contract reviewed and merged"],
         "artifacts": ["api/schema.json"], "risk": "low", "notes": ""},
    ],
}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="decompose", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="scaffold tasks.json")
    p.add_argument("--name", default="my-project")
    p.add_argument("--out", default="tasks.json")

    p = sub.add_parser("validate", help="structural + quality gate")
    p.add_argument("file")
    p.add_argument("--strict", action="store_true", help="treat WARN as failure")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("plan", help="render the plan")
    p.add_argument("file")
    p.add_argument("--format", choices=["md", "mermaid", "csv", "json"], default="md")
    p.add_argument("--out")

    p = sub.add_parser("next", help="unblocked tasks")
    p.add_argument("file")
    p.add_argument("--done", default="", help="comma-separated completed ids")

    p = sub.add_parser("stats", help="summary metrics")
    p.add_argument("file")

    a = ap.parse_args(argv)

    if a.cmd == "init":
        doc = json.loads(json.dumps(SCAFFOLD))
        doc["project"]["name"] = a.name
        emit(json.dumps(doc, indent=2, ensure_ascii=False), a.out)
        return 0

    doc = load(a.file)

    if a.cmd == "validate":
        issues = validate(doc)
        errs = [i for i in issues if i.level == "ERROR"]
        warns = [i for i in issues if i.level == "WARN"]
        if a.json:
            emit(json.dumps([i.__dict__ for i in issues], indent=2, ensure_ascii=False))
        else:
            for i in issues:
                print(i)
            print(f"\n{len(errs)} error(s), {len(warns)} warning(s)")
        return 1 if errs or (a.strict and warns) else 0

    issues = validate(doc)
    if any(i.level == "ERROR" for i in issues):
        for i in issues:
            if i.level == "ERROR":
                print(i, file=sys.stderr)
        print("Refusing to render: fix ERRORs first (run `validate`).", file=sys.stderr)
        return 1
    g = Graph(doc)
    sch = g.schedule()
    if sch is None:
        print("cannot schedule: dependency cycle (run `validate` for details)", file=sys.stderr)
        return 1

    if a.cmd == "plan":
        text = {"md": render_md, "mermaid": render_mermaid,
                "csv": render_csv, "json": render_json}[a.format](doc, g, sch, issues)
        emit(text, a.out)
        return 0

    if a.cmd == "next":
        done = {x.strip() for x in a.done.split(",") if x.strip()}
        eff = g.effective_deps()
        ready = [t for t in sch["order"]
                 if t not in done and not g.children.get(t) and all(d in done for d in eff[t])]
        unit = doc.get("project", {}).get("unit", "h")
        if not ready:
            print("Nothing unblocked (all done, or check your --done list).")
        for t in ready:
            crit = " [CRITICAL]" if t in set(sch["critical"]) else ""
            print(f"{t:8s} {fmt(sch['dur'][t], unit):>7s}  {g.tasks[t].get('owner_role','-'):10s} "
                  f"{g.tasks[t].get('title','')}{crit}")
        return 0

    if a.cmd == "stats":
        unit = doc.get("project", {}).get("unit", "h")
        leaves = [t for t in g.order if not g.children.get(t)]
        total = sum(sch["dur"].values())
        byrole, byrisk = defaultdict(float), defaultdict(float)
        for t in leaves:
            byrole[g.tasks[t].get("owner_role") or "-"] += sch["dur"][t]
            byrisk[g.tasks[t].get("risk", "low")] += sch["dur"][t]
        print(f"tasks={len(g.order)} leaves={len(leaves)} "
              f"spikes={sum(1 for t in leaves if g.tasks[t].get('type')=='spike')}")
        print(f"effort={fmt(total,unit)} span_P50={fmt(sch['p50'],unit)} "
              f"span_P80={fmt(sch['p80'],unit)} "
              f"parallelism={total/sch['p50'] if sch['p50'] else 0:.2f}x")
        print("by role: " + ", ".join(f"{k}={fmt(v,unit)}" for k, v in sorted(byrole.items())))
        print("by risk: " + ", ".join(f"{k}={fmt(v,unit)}" for k, v in sorted(byrisk.items())))
        print("critical: " + " -> ".join(sch["critical"]))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())