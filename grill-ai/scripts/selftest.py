#!/usr/bin/env python3
"""Regression tests for scripts/grill.py.

Run after any change to the gate or the report:

    python scripts/selftest.py

Exit 0 when every check passes, 1 when one fails. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRILL = HERE / "grill.py"
failures: list[str] = []
checks = 0


def expect(condition: bool, label: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(label)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GRILL), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def valid_ledger() -> dict:
    return {
        "schema_version": "1.0",
        "ask": "Should we migrate the parser to the new API?",
        "deliverable": "answer",
        "round": 1,
        "max_rounds": 2,
        "draft": "Yes: the new API removes the deprecation warning.",
        "challenges": [
            {
                "id": "C1",
                "round": 1,
                "kind": "fact",
                "claim": "the new API exists",
                "challenge": "the name may be wrong",
                "status": "resolved",
                "answer": "it exists in 2.1",
                "evidence": ["package.json:14"],
            },
            {
                "id": "C2",
                "round": 1,
                "kind": "feasibility",
                "claim": "it runs on Python 3.15",
                "challenge": "wheels may stop at 3.13",
                "status": "resolved",
                "answer": "pure python, no wheels needed",
                "evidence": ["https://example.com/docs#install"],
            },
            {
                "id": "C3",
                "round": 1,
                "kind": "cost",
                "claim": "migration is one afternoon",
                "challenge": "call sites may be many",
                "status": "assumed",
                "answer": "assume under 20 call sites",
                "impact": "if 200, the estimate is a week and needs a phased plan",
            },
        ],
        "counter": {
            "text": "The deprecation warning is harmless; migration adds risk for no gain.",
            "verdict": "revised",
            "change": "recommend migrating only the entry point first",
        },
        "verdict": {
            "answer": "Migrate the entry point now; leave the rest until the next release.",
            "confidence": "medium",
            "would_change": "more than 100 call sites, or no patch release this quarter",
        },
    }


def write(path: Path, ledger: dict) -> None:
    path.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run grill.py regression tests.")
    parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ledger_path = root / "grill.json"

        # init
        result = run("init", "--ask", "test ask", "--out", str(ledger_path))
        expect(result.returncode == 0, "init should exit 0")
        expect(ledger_path.is_file(), "init should create the ledger")
        created = json.loads(ledger_path.read_text(encoding="utf-8"))
        expect(created["ask"] == "test ask", "init should copy the ask verbatim")

        # empty ledger fails the gate and refuses the report
        empty = run("check", str(ledger_path))
        expect(empty.returncode == 1, "empty ledger should fail check")
        expect("E_EMPTY" in empty.stdout, "empty ledger should report E_EMPTY")
        refused = run("report", str(ledger_path), "--out", str(root / "early.md"))
        expect(refused.returncode == 1, "report should refuse an empty ledger")
        expect(not (root / "early.md").exists(), "report should not write on failure")

        # valid ledger passes
        write(ledger_path, valid_ledger())
        good = run("check", str(ledger_path))
        expect(good.returncode == 0, f"valid ledger should pass check:\n{good.stdout}")
        expect("confidence medium" in good.stdout, "computed confidence should be medium")
        status = run("status", str(ledger_path))
        expect(status.returncode == 0 and "PASS" in status.stdout, "status should report PASS")

        report_path = root / "GRILL.md"
        rendered = run("report", str(ledger_path), "--out", str(report_path))
        expect(rendered.returncode == 0, f"valid ledger should render:\n{rendered.stderr}")
        body = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
        expect("## Challenge log" in body, "report should contain a challenge log")
        expect("migrating only the entry point" in body.lower(), "report should carry the counter")

        # json output
        as_json = run("check", str(ledger_path), "--json")
        expect(as_json.returncode == 0, "check --json should exit 0")
        try:
            payload = json.loads(as_json.stdout)
            expect(payload["ok"] is True, "check --json should say ok")
        except json.JSONDecodeError:
            expect(False, "check --json should emit valid JSON")

        # open challenge
        ledger = valid_ledger()
        ledger["challenges"][0]["status"] = "open"
        write(ledger_path, ledger)
        result = run("check", str(ledger_path))
        expect(result.returncode == 1 and "E_OPEN" in result.stdout, "open challenge should fail with E_OPEN")

        # resolved without evidence
        ledger = valid_ledger()
        ledger["challenges"][0]["evidence"] = []
        write(ledger_path, ledger)
        result = run("check", str(ledger_path))
        expect(result.returncode == 1 and "E_EVIDENCE" in result.stdout, "missing evidence should fail with E_EVIDENCE")

        # assumed without impact
        ledger = valid_ledger()
        ledger["challenges"][2]["impact"] = ""
        write(ledger_path, ledger)
        result = run("check", str(ledger_path))
        expect(result.returncode == 1 and "E_IMPACT" in result.stdout, "missing impact should fail with E_IMPACT")

        # overclaim
        ledger = valid_ledger()
        ledger["verdict"]["confidence"] = "high"
        write(ledger_path, ledger)
        result = run("check", str(ledger_path))
        expect(
            result.returncode == 1 and "E_OVERCLAIM" in result.stdout,
            "high confidence with an assumption should fail with E_OVERCLAIM",
        )

        # missing counter
        ledger = valid_ledger()
        ledger["counter"]["text"] = ""
        write(ledger_path, ledger)
        result = run("check", str(ledger_path))
        expect(result.returncode == 1 and "E_COUNTER" in result.stdout, "missing counter should fail with E_COUNTER")

    if failures:
        print(f"selftest: {len(failures)} of {checks} checks failed", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"selftest: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
