#!/usr/bin/env python3
"""Gate and render a grill-ai ledger.

The ledger is the proof that an answer was interrogated instead of guessed: every
challenge ends resolved with evidence, or assumed with an impact. This script refuses to
render an answer while a challenge is open or a claim has no source.

Usage:
    python scripts/grill.py init --ask "the user's words" --out grill.json
    python scripts/grill.py check grill.json --json
    python scripts/grill.py status grill.json
    python scripts/grill.py report grill.json --out GRILL.md

Exit codes: 0 ok / passed, 1 gate failed, 2 cannot read or parse the ledger.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_VERSION = "1.0"
KINDS = ("fact", "feasibility", "cost", "risk", "fit", "reversibility")
STATUSES = ("resolved", "assumed", "open")
VERDICTS = ("survives", "revised")
CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}
MAX_PER_ROUND = 7
MAX_TOTAL = 12


class LedgerError(Exception):
    """The file is missing, unreadable or not a ledger."""


def out(text: str = "") -> None:
    print(text)


def err(text: str) -> None:
    print(text, file=sys.stderr)


def load(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerError(f"cannot read {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError(f"{path} must contain a JSON object")
    return data


def text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def challenges_of(ledger: dict) -> list:
    value = ledger.get("challenges")
    return value if isinstance(value, list) else []


def computed_confidence(ledger: dict) -> str:
    assumed = sum(1 for c in challenges_of(ledger) if text(c.get("status")) == "assumed")
    if assumed == 0:
        return "high"
    if assumed <= 2:
        return "medium"
    return "low"


def evidence_ok(evidence) -> bool:
    if not isinstance(evidence, list) or not evidence:
        return False
    return all(isinstance(item, str) and item.strip() for item in evidence)


def check_ledger(ledger: dict) -> tuple[list, list, dict]:
    errors: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []

    def error(code: str, message: str) -> None:
        errors.append((code, message))

    def warn(code: str, message: str) -> None:
        warnings.append((code, message))

    ask = text(ledger.get("ask"))
    if not ask:
        error("E_ASK", "ledger has no `ask`; copy the user's request verbatim")

    items = challenges_of(ledger)
    if not items:
        error("E_EMPTY", "no challenges recorded; the answer was never grilled")

    try:
        max_rounds = int(ledger.get("max_rounds", 2))
    except (TypeError, ValueError):
        max_rounds = 2
        warn("W_ROUNDS", "`max_rounds` is not an integer; using 2")

    seen: set[str] = set()
    per_round: dict[int, int] = {}
    resolved = assumed = open_count = 0

    for index, challenge in enumerate(items, start=1):
        if not isinstance(challenge, dict):
            error("E_FIELD", f"challenge #{index} is not an object")
            continue
        cid = text(challenge.get("id")) or f"#{index}"
        if cid in seen:
            error("E_DUP", f"{cid}: duplicate challenge id")
        seen.add(cid)

        if not text(challenge.get("claim")):
            error("E_FIELD", f"{cid}: missing `claim` - what the draft asserts")
        if not text(challenge.get("challenge")):
            error("E_FIELD", f"{cid}: missing `challenge` - why the claim may be wrong")

        status = text(challenge.get("status"))
        if status not in STATUSES:
            error("E_STATUS", f"{cid}: status {status!r} is not one of {', '.join(STATUSES)}")
        elif status == "open":
            open_count += 1
            error("E_OPEN", f"{cid}: still open - settle it or mark it assumed with an impact")
        elif status == "resolved":
            resolved += 1
            if not evidence_ok(challenge.get("evidence")):
                error("E_EVIDENCE", f"{cid}: resolved without `evidence` (path:line, URL or command)")
            else:
                for entry in challenge.get("evidence", []):
                    if ":" not in entry and "/" not in entry:
                        warn(
                            "W_EVIDENCE_SHAPE",
                            f"{cid}: evidence {entry!r} has no `path:line`, URL or `cmd:` marker",
                        )
        elif status == "assumed":
            assumed += 1
            if not text(challenge.get("impact")):
                error("E_IMPACT", f"{cid}: assumed without `impact` - what breaks if it is wrong")

        kind = text(challenge.get("kind"))
        if kind and kind not in KINDS:
            warn("W_KIND", f"{cid}: kind {kind!r} is not one of {', '.join(KINDS)}")

        try:
            round_no = int(challenge.get("round", 1))
        except (TypeError, ValueError):
            round_no = 1
            warn("W_ROUND", f"{cid}: `round` is not an integer; counting it in round 1")
        per_round[round_no] = per_round.get(round_no, 0) + 1
        if round_no > max_rounds:
            error("E_ROUND_OVER", f"{cid}: round {round_no} exceeds max_rounds {max_rounds}; stop and deliver")

    for round_no, count in sorted(per_round.items()):
        if count > MAX_PER_ROUND:
            warn("W_MANY", f"round {round_no}: {count} challenges (cap {MAX_PER_ROUND}); drop the ones that cannot change the answer")
    if len(items) > MAX_TOTAL:
        warn("W_TOTAL", f"{len(items)} challenges total (cap {MAX_TOTAL}); this request may be too big")

    counter = ledger.get("counter") if isinstance(ledger.get("counter"), dict) else {}
    if not text(counter.get("text")):
        error("E_COUNTER", "`counter.text` is empty - write the strongest objection to your answer")
    verdict_word = text(counter.get("verdict"))
    if verdict_word not in VERDICTS:
        error("E_COUNTER", f"`counter.verdict` {verdict_word!r} must be 'survives' or 'revised'")
    elif verdict_word == "revised" and not text(counter.get("change")):
        warn("W_CHANGE", "`counter.verdict` is revised but `counter.change` is empty")

    verdict = ledger.get("verdict") if isinstance(ledger.get("verdict"), dict) else {}
    if not text(verdict.get("answer")):
        error("E_VERDICT", "`verdict.answer` is empty - state the final answer")
    declared = text(verdict.get("confidence"))
    if declared not in CONFIDENCE_RANK:
        error("E_CONFIDENCE", f"`verdict.confidence` {declared!r} must be high, medium or low")

    computed = computed_confidence(ledger)
    if declared in CONFIDENCE_RANK:
        if CONFIDENCE_RANK[declared] > CONFIDENCE_RANK[computed]:
            error(
                "E_OVERCLAIM",
                f"declared {declared} confidence but {assumed} assumption(s) support only {computed}",
            )
        elif CONFIDENCE_RANK[declared] < CONFIDENCE_RANK[computed]:
            warn(
                "W_UNDERCLAIM",
                f"declared {declared} confidence while the evidence supports {computed}",
            )

    stats = {
        "total": len(items),
        "resolved": resolved,
        "assumed": assumed,
        "open": open_count,
        "computed_confidence": computed,
        "declared_confidence": declared,
    }
    return errors, warnings, stats


def print_failures(errors: list, warnings: list, stats: dict) -> None:
    out(
        f"challenges {stats['total']} "
        f"(resolved {stats['resolved']}, assumed {stats['assumed']}, open {stats['open']}) "
        f"| confidence {stats['declared_confidence'] or '?'} "
        f"(computed {stats['computed_confidence']})"
    )
    for code, message in errors:
        out(f"  ERROR {code}: {message}")
    for code, message in warnings:
        out(f"  WARN  {code}: {message}")
    out("FAIL" if errors else "PASS")


def cmd_init(args) -> int:
    path = Path(args.out)
    if path.exists() and not args.force:
        err(f"error: {path} exists (use --force to overwrite)")
        return 1
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "ask": args.ask.strip(),
        "deliverable": args.deliverable,
        "round": 1,
        "max_rounds": args.max_rounds,
        "draft": "",
        "challenges": [],
        "counter": {"text": "", "verdict": "", "change": ""},
        "verdict": {"answer": "", "confidence": "medium", "would_change": ""},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    out(f"created {path}")
    return 0


def cmd_check(args) -> int:
    ledger = load(Path(args.ledger))
    errors, warnings, stats = check_ledger(ledger)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": not errors,
                    "errors": [{"code": c, "message": m} for c, m in errors],
                    "warnings": [{"code": c, "message": m} for c, m in warnings],
                    "stats": stats,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        ask = text(ledger.get("ask"))
        out(f"grill-ai check: {ask[:70]}{'...' if len(ask) > 70 else ''}")
        print_failures(errors, warnings, stats)
    return 0 if not errors else 1


def cmd_status(args) -> int:
    ledger = load(Path(args.ledger))
    errors, _, stats = check_ledger(ledger)
    state = "PASS" if not errors else "FAIL"
    out(
        f"grill-ai: {state} | confidence {stats['computed_confidence']} | "
        f"{stats['total']} challenges ({stats['resolved']} resolved, "
        f"{stats['assumed']} assumed, {stats['open']} open)"
    )
    return 0


def cell(value) -> str:
    return text(value).replace("|", "\\|").replace("\n", " ") or "-"


def cmd_report(args) -> int:
    ledger = load(Path(args.ledger))
    errors, warnings, stats = check_ledger(ledger)
    if errors:
        err("error: the ledger does not pass the gate; an answer is not ready")
        print_failures(errors, warnings, stats)
        err("hint: run `grill.py check` after settling every challenge")
        return 1

    lines = [
        f"# Grill: {text(ledger.get('ask'))}",
        "",
        f"**Deliverable:** {text(ledger.get('deliverable')) or 'answer'} | "
        f"**Confidence:** {stats['computed_confidence']} | "
        f"**Challenges:** {stats['total']} "
        f"({stats['resolved']} resolved, {stats['assumed']} assumed)",
        "",
        "## Draft answer",
        "",
        text(ledger.get("draft")) or "_(not recorded)_",
        "",
        "## Challenge log",
        "",
        "| # | Kind | Claim attacked | Verdict | Evidence or assumption |",
        "|---|---|---|---|---|",
    ]
    for index, challenge in enumerate(challenges_of(ledger), start=1):
        cid = text(challenge.get("id")) or f"#{index}"
        status = text(challenge.get("status"))
        if status == "resolved":
            basis = "<br>".join(cell(item) for item in challenge.get("evidence", []))
            result = text(challenge.get("answer")) or "resolved"
            verdict_cell = f"resolved: {cell(result)}<br>{basis}"
        else:
            verdict_cell = f"assumed: {cell(challenge.get('answer'))}<br>impact: {cell(challenge.get('impact'))}"
        lines.append(
            f"| {cell(cid)} | {cell(challenge.get('kind'))} | {cell(challenge.get('claim'))} "
            f"<br>_{cell(challenge.get('challenge'))}_ | {verdict_cell} |"
        )

    counter = ledger.get("counter") or {}
    lines += [
        "",
        "## Strongest counter",
        "",
        cell(counter.get("text")),
        "",
        f"Verdict: **{cell(counter.get('verdict'))}**"
        + (f" - {cell(counter.get('change'))}" if text(counter.get("change")) else ""),
        "",
        "## Verdict",
        "",
        text((ledger.get("verdict") or {}).get("answer")),
        "",
        f"Confidence: **{stats['computed_confidence']}**",
        "",
        f"Would change: {cell((ledger.get('verdict') or {}).get('would_change'))}",
        "",
    ]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    out(f"wrote {out_path} ({stats['total']} challenges, confidence {stats['computed_confidence']})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gate a grill-ai ledger: evidence or assumption, no open challenge, no overclaim.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create an empty ledger")
    init.add_argument("--ask", required=True, help="the user's request, verbatim")
    init.add_argument("--deliverable", default="answer", help="answer, decision or review (default: answer)")
    init.add_argument("--max-rounds", type=int, default=2, help="hard round cap (default: 2)")
    init.add_argument("--out", default="grill.json", help="ledger path (default: grill.json)")
    init.add_argument("--force", action="store_true", help="overwrite an existing ledger")
    init.set_defaults(func=cmd_init)

    check = sub.add_parser("check", help="run the gate; exit 1 on any error")
    check.add_argument("ledger", help="path to grill.json")
    check.add_argument("--json", action="store_true", help="machine-readable output")
    check.set_defaults(func=cmd_check)

    status = sub.add_parser("status", help="one-line summary")
    status.add_argument("ledger", help="path to grill.json")
    status.set_defaults(func=cmd_status)

    report = sub.add_parser("report", help="render GRILL.md; refuses a ledger that fails the gate")
    report.add_argument("ledger", help="path to grill.json")
    report.add_argument("--out", default="GRILL.md", help="markdown output (default: GRILL.md)")
    report.set_defaults(func=cmd_report)

    return parser


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except LedgerError as exc:
        err(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
