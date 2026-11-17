#!/usr/bin/env python3
"""AIWOR interview ledger - prove the request is clear before writing a plan.

Stdlib only. Python 3.11+.

Commands
    init      create interview.json from the user's request
    validate  schema + convergence gate (exit 1 on any ERROR)
    status    counts, verdict and the single next action
    next      print the open question batch JSON for the answerer
    render    interview.md - every round, every answer, for the user
    plan      plan.md scaffold prefilled with settled facts; refuses while unclear

Model
    A question is open | answered | assumed. "answered" needs an answer and at
    least one evidence item (path:line or a command). "assumed" needs the
    assumption and the impact if it is wrong. Nothing is "clear" while a
    question is open, a conflict is unresolved, or the round cap is exceeded.

Exit codes
    0 ok / converged
    1 not converged, or validation ERROR (with --strict: WARN too)
    2 ledger unreadable or not a JSON object
    3 usage
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

SCHEMA_VERSION = "1.0"
Q_STATUS = ("open", "answered", "assumed")
OWNERS = ("repo", "user", "external")
CONFLICT_STATUS = ("open", "resolved")
QID_RE = re.compile(r"^Q[0-9]+$")
DID_RE = re.compile(r"^D[0-9]+$")
CID_RE = re.compile(r"^C[0-9]+$")
DEFAULT_MAX_ROUNDS = 4
HARD_MAX_ROUNDS = 6
QUESTION_WARN = 20
SCRIPT = os.path.abspath(__file__)


class UsageParser(argparse.ArgumentParser):
    """argparse exits 2 on bad usage; this tool reserves 2 for unreadable input."""

    def error(self, message):  # noqa: D102 - argparse hook
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(3)


class Issue:
    def __init__(self, level, code, msg, ref=None):
        self.level, self.code, self.msg, self.ref = level, code, msg, ref

    def __str__(self):
        where = f"[{self.ref}] " if self.ref else ""
        return f"{self.level:5s} {self.code:18s} {where}{self.msg}"

    def as_dict(self):
        return {"level": self.level, "code": self.code, "message": self.msg, "ref": self.ref}


# --------------------------------------------------------------------------- io
def load(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON in {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)


def emit(text, out=None):
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def text_of(value):
    return value.strip() if isinstance(value, str) else ""


def as_int(value, default=None):
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def as_list(value):
    return value if isinstance(value, list) else []


# -------------------------------------------------------------------- validate
def validate(doc):
    """Return every issue, ordered schema first then convergence."""
    issues = []
    if not isinstance(doc, dict):
        return [Issue("ERROR", "E_DOC", "ledger is not a JSON object")]

    def err(code, msg, ref=None):
        issues.append(Issue("ERROR", code, msg, ref))

    def warn(code, msg, ref=None):
        issues.append(Issue("WARN", code, msg, ref))

    if str(doc.get("schema_version", "")) != SCHEMA_VERSION:
        err("E_SCHEMA", f"schema_version must be {SCHEMA_VERSION!r}")
    if not text_of(doc.get("topic")):
        err("E_TOPIC", "topic is required")
    if not text_of(doc.get("request")):
        err("E_REQUEST", "request is required - copy the user's words, do not paraphrase")

    max_rounds = as_int(doc.get("max_rounds"), DEFAULT_MAX_ROUNDS)
    if not 1 <= max_rounds <= HARD_MAX_ROUNDS:
        err("E_MAX_ROUNDS", f"max_rounds must be 1..{HARD_MAX_ROUNDS}")
    current = as_int(doc.get("round"), 1)
    if current < 1:
        err("E_ROUND", "round must be >= 1")
    elif current > max_rounds:
        err("E_ROUND_OVER", f"round {current} exceeds max_rounds {max_rounds} - stop and escalate")

    raw_questions = doc.get("questions")
    if not isinstance(raw_questions, list):
        err("E_QUESTIONS", "questions must be a list")
        raw_questions = []

    qids = set()
    open_ids, assumed_ids = [], []
    for pos, q in enumerate(raw_questions, 1):
        if not isinstance(q, dict):
            err("E_Q_SHAPE", f"question #{pos} is not an object")
            continue
        qid = text_of(q.get("id"))
        if not QID_RE.match(qid):
            err("E_QID", f"question #{pos} id must look like Q1", qid or f"#{pos}")
            qid = qid or f"#{pos}"
        elif qid in qids:
            err("E_QID", f"duplicate question id {qid}", qid)
        qids.add(qid)

        if not text_of(q.get("ask")):
            err("E_ASK", "question text is required", qid)
        if not text_of(q.get("why")):
            err("E_WHY", "why is required - name the decision the answer unblocks", qid)

        owner = q.get("owner", "repo")
        if owner not in OWNERS:
            err("E_OWNER", f"owner must be one of {', '.join(OWNERS)}", qid)

        status = q.get("status")
        if status not in Q_STATUS:
            err("E_QSTATUS", f"status must be one of {', '.join(Q_STATUS)}", qid)
            continue

        q_round = as_int(q.get("round"), current)
        if not 1 <= q_round <= max_rounds:
            err("E_QROUND", f"question round must be 1..{max_rounds}", qid)

        evidence = as_list(q.get("evidence"))
        if status == "open":
            open_ids.append(qid)
        elif status == "answered":
            if not text_of(q.get("answer")):
                err("E_ANSWER", "answered question needs answer text", qid)
            if not [e for e in evidence if text_of(e)]:
                err("E_EVIDENCE", "answered question needs evidence: path:line or a command", qid)
        else:  # assumed
            assumed_ids.append(qid)
            if not text_of(q.get("assumption")):
                err("E_ASSUMPTION", "assumed question needs the assumption being acted on", qid)
            if not text_of(q.get("impact")):
                err("E_IMPACT", "assumed question needs the impact if the assumption is wrong", qid)

    dids = set()
    raw_decisions = doc.get("decisions", [])
    if not isinstance(raw_decisions, list):
        err("E_DECISIONS", "decisions must be a list")
        raw_decisions = []
    for pos, d in enumerate(raw_decisions, 1):
        if not isinstance(d, dict):
            err("E_D_SHAPE", f"decision #{pos} is not an object")
            continue
        did = text_of(d.get("id"))
        if not DID_RE.match(did):
            err("E_DID", f"decision #{pos} id must look like D1", did or f"#{pos}")
            did = did or f"#{pos}"
        elif did in dids:
            err("E_DID", f"duplicate decision id {did}", did)
        dids.add(did)
        if not text_of(d.get("text")):
            err("E_DECISION", "decision text is required", did)
        source = text_of(d.get("question"))
        if source and source not in qids:
            err("E_DECISION_SRC", f"decision points at unknown question {source}", did)

    raw_conflicts = doc.get("conflicts", [])
    if not isinstance(raw_conflicts, list):
        err("E_CONFLICTS", "conflicts must be a list")
        raw_conflicts = []
    open_conflicts = []
    for pos, c in enumerate(raw_conflicts, 1):
        if not isinstance(c, dict):
            err("E_C_SHAPE", f"conflict #{pos} is not an object")
            continue
        cid = text_of(c.get("id"))
        if not CID_RE.match(cid):
            err("E_CID", f"conflict #{pos} id must look like C1", cid or f"#{pos}")
            cid = cid or f"#{pos}"
        between = [text_of(x) for x in as_list(c.get("between")) if text_of(x)]
        if len(between) < 2:
            err("E_CONFLICT_PAIR", "conflict needs at least two decision ids in `between`", cid)
        for did in between:
            if did not in dids:
                err("E_CONFLICT_REF", f"conflict references unknown decision {did}", cid)
        status = c.get("status")
        if status not in CONFLICT_STATUS:
            err("E_CONFLICT_STATUS", f"conflict status must be one of {', '.join(CONFLICT_STATUS)}", cid)
        if status == "resolved" and not text_of(c.get("resolution")):
            err("E_CONFLICT_RESOLUTION", "resolved conflict needs resolution text", cid)
        if status == "open":
            open_conflicts.append(cid)
        if not text_of(c.get("text")):
            err("E_CONFLICT_TEXT", "conflict text is required", cid)

    if not raw_questions:
        err("E_EMPTY", "no questions recorded - run the asker before writing a plan")
    if open_ids:
        err("E_OPEN_Q", f"{len(open_ids)} question(s) still open: {', '.join(open_ids)}")
    if open_conflicts:
        err("E_OPEN_CONFLICT", f"{len(open_conflicts)} conflict(s) unresolved: {', '.join(open_conflicts)}")

    if raw_questions and not raw_decisions:
        warn("W_NO_DECISIONS", "round has questions but no decisions recorded")
    if assumed_ids:
        warn("W_ASSUMED", f"{len(assumed_ids)} assumption(s) in force: {', '.join(assumed_ids)}")
    if len(raw_questions) > QUESTION_WARN:
        warn("W_MANY_QUESTIONS", f"{len(raw_questions)} questions - the loop is drifting; re-read the request")
    return issues


def stats(doc):
    questions = [q for q in as_list(doc.get("questions")) if isinstance(q, dict)]
    by = {s: 0 for s in Q_STATUS}
    by["user_open"] = 0
    for q in questions:
        status = q.get("status")
        if status in by:
            by[status] += 1
        if status == "open" and q.get("owner", "repo") == "user":
            by["user_open"] += 1
    conflicts = [c for c in as_list(doc.get("conflicts")) if isinstance(c, dict)]
    issues = validate(doc)
    return {
        "topic": text_of(doc.get("topic")),
        "round": as_int(doc.get("round"), 1),
        "max_rounds": as_int(doc.get("max_rounds"), DEFAULT_MAX_ROUNDS),
        "questions": len(questions),
        "open": by["open"],
        "answered": by["answered"],
        "assumed": by["assumed"],
        "user_open": by["user_open"],
        "decisions": len(as_list(doc.get("decisions"))),
        "conflicts": len(conflicts),
        "conflicts_open": sum(1 for c in conflicts if c.get("status") == "open"),
        "errors": sum(1 for i in issues if i.level == "ERROR"),
        "warnings": sum(1 for i in issues if i.level == "WARN"),
        "converged": not any(i.level == "ERROR" for i in issues),
    }


# ---------------------------------------------------------------------- render
def render_interview(doc):
    s = stats(doc)
    lines = [f"# Interview: {s['topic'] or '(untitled)'}", ""]
    lines += [f"Request: {text_of(doc.get('request'))}", "",
              f"Round {s['round']}/{s['max_rounds']} - "
              + ("CONVERGED" if s["converged"] else "NOT CONVERGED"), ""]
    lines += ["## Questions", ""]
    questions = [q for q in as_list(doc.get("questions")) if isinstance(q, dict)]
    if not questions:
        lines.append("_None yet._")
    rounds = {}
    for q in questions:
        rounds.setdefault(as_int(q.get("round"), s["round"]), []).append(q)
    for rnd in sorted(rounds):
        lines += [f"### Round {rnd}", ""]
        for q in rounds[rnd]:
            status = text_of(q.get("status")) or "?"
            lines.append(f"**{text_of(q.get('id'))} - {status} ({text_of(q.get('owner')) or 'repo'})**")
            lines.append(f"- Ask: {text_of(q.get('ask'))}")
            lines.append(f"- Why: {text_of(q.get('why'))}")
            if status == "answered":
                lines.append(f"- Answer: {text_of(q.get('answer'))}")
                ev = [text_of(e) for e in as_list(q.get("evidence")) if text_of(e)]
                lines.append(f"- Evidence: {', '.join(ev) or '-'}")
            elif status == "assumed":
                lines.append(f"- Assumption: {text_of(q.get('assumption'))}")
                lines.append(f"- If wrong: {text_of(q.get('impact'))}")
            lines.append("")
    lines += ["## Decisions", ""]
    decisions = [d for d in as_list(doc.get("decisions")) if isinstance(d, dict)]
    if not decisions:
        lines.append("_None yet._")
    for d in decisions:
        ev = [text_of(e) for e in as_list(d.get("evidence")) if text_of(e)]
        tail = f" (from {text_of(d.get('question'))})" if text_of(d.get("question")) else ""
        lines.append(f"- **{text_of(d.get('id'))}** {text_of(d.get('text'))}{tail}"
                     + (f" - `{'`, `'.join(ev)}`" if ev else ""))
    conflicts = [c for c in as_list(doc.get("conflicts")) if isinstance(c, dict)]
    if conflicts:
        lines += ["", "## Conflicts", ""]
        for c in conflicts:
            lines.append(f"- **{text_of(c.get('id'))}** ({text_of(c.get('status'))}) "
                         f"{text_of(c.get('text'))} - {text_of(c.get('resolution')) or 'unresolved'}")
    return "\n".join(lines)


def render_plan(doc):
    s = stats(doc)
    lines = [f"# Plan: {s['topic'] or '<topic>'}", "",
             "<!-- Fill every <...> below, then delete this line. -->", "",
             "## Request", "", f"> {text_of(doc.get('request'))}", "",
             "## Decisions", "",
             "| # | Decision | From | Evidence |", "|---|---|---|---|"]
    decisions = [d for d in as_list(doc.get("decisions")) if isinstance(d, dict)]
    for d in decisions:
        ev = [text_of(e) for e in as_list(d.get("evidence")) if text_of(e)]
        lines.append(f"| {text_of(d.get('id'))} | {text_of(d.get('text'))} | "
                     f"{text_of(d.get('question')) or '-'} | {', '.join(ev) or '-'} |")
    if not decisions:
        lines.append("| - | none recorded | - | - |")

    assumed = [q for q in as_list(doc.get("questions"))
               if isinstance(q, dict) and q.get("status") == "assumed"]
    lines += ["", "## Assumptions in force", ""]
    if assumed:
        lines += ["| # | Assumption | If wrong |", "|---|---|---|"]
        for q in assumed:
            lines.append(f"| {text_of(q.get('id'))} | {text_of(q.get('assumption'))} | "
                         f"{text_of(q.get('impact'))} |")
    else:
        lines.append("_None._")

    lines += ["", "## Out of scope", "",
              "- <what this plan deliberately does not touch>", "",
              "## Steps", "",
              "1. <action> - touches `<paths>` - verify: `<command>`", "",
              "## Done when", "",
              "- [ ] <binary check a stranger could run>", ""]
    conflicts = [c for c in as_list(doc.get("conflicts")) if isinstance(c, dict)]
    if conflicts:
        lines += ["## Conflicts", ""]
        for c in conflicts:
            lines.append(f"- {text_of(c.get('id'))}: {text_of(c.get('text'))} -> "
                         f"{text_of(c.get('resolution')) or 'UNRESOLVED'}")
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------------ main
def cmd_init(a):
    if a.max_rounds < 1 or a.max_rounds > HARD_MAX_ROUNDS:
        print(f"--max-rounds must be 1..{HARD_MAX_ROUNDS}", file=sys.stderr)
        return 3
    if os.path.exists(a.out) and not a.force:
        print(f"{a.out} exists; pass --force to replace it", file=sys.stderr)
        return 3
    doc = {
        "schema_version": SCHEMA_VERSION,
        "topic": a.topic,
        "request": a.request,
        "round": 1,
        "max_rounds": a.max_rounds,
        "questions": [],
        "decisions": [],
        "conflicts": [],
    }
    emit(json.dumps(doc, indent=2, ensure_ascii=False), a.out)
    if not a.json:
        print(f"wrote {a.out} - next: ask the asker for 3-7 questions, then record them")
    return 0


def cmd_validate(a):
    issues = validate(load(a.file))
    bad = [i for i in issues if i.level == "ERROR" or (a.strict and i.level == "WARN")]
    if a.json:
        emit(json.dumps([i.as_dict() for i in issues], indent=2, ensure_ascii=False))
    else:
        for i in issues:
            print(i)
        errs = sum(1 for i in issues if i.level == "ERROR")
        warns = sum(1 for i in issues if i.level == "WARN")
        print(f"\n{errs} error(s), {warns} warning(s)")
    return 1 if bad else 0


def cmd_status(a):
    doc = load(a.file)
    s = stats(doc)
    if a.json:
        print(json.dumps(s, indent=2, ensure_ascii=False))
    else:
        print(f"topic: {s['topic'] or '(untitled)'}")
        print(f"round: {s['round']}/{s['max_rounds']}")
        print(f"questions: {s['questions']} (answered {s['answered']}, assumed {s['assumed']}, "
              f"open {s['open']} of which user {s['user_open']})")
        print(f"decisions: {s['decisions']} | conflicts: {s['conflicts_open']} open / {s['conflicts']}")
        print(f"verdict: {'CONVERGED' if s['converged'] else 'NOT CONVERGED'}")
        if s["converged"]:
            print(f"next: python {SCRIPT} plan {a.file} --out PLAN.md")
        elif not s["questions"]:
            print("next: ask the asker for 3-7 questions, then record them in the ledger")
        elif s["open"]:
            print(f"next: answer {s['open']} open question(s) -> python {SCRIPT} next {a.file}")
        elif s["conflicts_open"]:
            print("next: resolve the open conflict(s) before asking anything new")
        else:
            print(f"next: fix the errors -> python {SCRIPT} validate {a.file}")
    return 0 if s["converged"] else 1


def cmd_next(a):
    doc = load(a.file)
    batch = [{
        "id": text_of(q.get("id")),
        "ask": text_of(q.get("ask")),
        "why": text_of(q.get("why")),
        "owner": text_of(q.get("owner")) or "repo",
    } for q in as_list(doc.get("questions"))
        if isinstance(q, dict) and q.get("status") == "open"]
    if a.json:
        print(json.dumps(batch, indent=2, ensure_ascii=False))
    else:
        for q in batch:
            print(f"{q['id']} [{q['owner']}] {q['ask']}")
            print(f"    unblocks: {q['why']}")
    return 0 if batch else 1


def cmd_render(a):
    doc = load(a.file)
    emit(render_interview(doc), a.out)
    return 0


def cmd_plan(a):
    doc = load(a.file)
    s = stats(doc)
    if not s["converged"]:
        print("Refusing to write a plan: the request is not clear yet.", file=sys.stderr)
        for i in validate(doc):
            if i.level == "ERROR":
                print(i, file=sys.stderr)
        print("Fix these, re-run validate, then write the plan.", file=sys.stderr)
        return 1
    emit(render_plan(doc), a.out)
    return 0


def build_parser():
    p = UsageParser(prog="interview.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=UsageParser)

    init = sub.add_parser("init", help="create a ledger")
    init.add_argument("--topic", required=True)
    init.add_argument("--request", required=True, help="the user's words, verbatim")
    init.add_argument("--out", default="interview.json")
    init.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    init.add_argument("--force", action="store_true")
    init.add_argument("--json", action="store_true", help="quiet success")
    init.set_defaults(func=cmd_init)

    for name, func, helptext in (
        ("validate", cmd_validate, "schema + convergence gate"),
        ("status", cmd_status, "counts, verdict, next action"),
        ("next", cmd_next, "open question batch as JSON"),
        ("render", cmd_render, "write interview.md"),
        ("plan", cmd_plan, "write plan.md scaffold"),
    ):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("file", nargs="?", default="interview.json")
        sp.add_argument("--json", action="store_true")
        sp.add_argument("--out", help="write to a file instead of stdout")
        if name == "validate":
            sp.add_argument("--strict", action="store_true", help="warnings fail too")
        sp.set_defaults(func=func)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
