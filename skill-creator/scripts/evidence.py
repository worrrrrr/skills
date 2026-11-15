#!/usr/bin/env python3
"""Run every skill self-test and create machine-readable execution evidence."""
from __future__ import annotations
import argparse, html, json, os, platform, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

def discover_skills(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("*/SKILL.md") if p.parent.is_dir())

def run_skill(skill: Path, timeout: int) -> dict:
    test = skill / "scripts" / "selftest.py"
    started = time.monotonic()
    if not test.is_file():
        return {"skill": skill.name, "status": "NOT_TESTED", "reason": "No selftest.py found",
                "command": None, "exit_code": None, "duration_seconds": 0, "stdout": "", "stderr": ""}
    try:
        result = subprocess.run([sys.executable, str(test)], cwd=test.parent, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
            env={**os.environ, "PYTHONUNBUFFERED": "1"})
        return {"skill": skill.name, "status": "PASSED" if result.returncode == 0 else "FAILED",
            "reason": "", "command": "python scripts/selftest.py", "exit_code": result.returncode,
            "duration_seconds": round(time.monotonic()-started, 3),
            "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired as exc:
        return {"skill": skill.name, "status": "FAILED", "reason": f"Timed out after {timeout}s",
            "command": "python scripts/selftest.py", "exit_code": None,
            "duration_seconds": round(time.monotonic()-started, 3),
            "stdout": str(exc.stdout or ""), "stderr": str(exc.stderr or "")}
    except OSError as exc:
        return {"skill": skill.name, "status": "UNVERIFIED", "reason": str(exc),
            "command": "python scripts/selftest.py", "exit_code": None,
            "duration_seconds": round(time.monotonic()-started, 3), "stdout": "", "stderr": ""}

def write_report(output: Path, results: list[dict], root: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    logs = output / "logs"; logs.mkdir(exist_ok=True)
    for item in results:
        (logs / (item["skill"] + ".stdout.txt")).write_text(item["stdout"], encoding="utf-8")
        (logs / (item["skill"] + ".stderr.txt")).write_text(item["stderr"], encoding="utf-8")
    counts = {key: sum(x["status"] == key for x in results)
              for key in ("PASSED", "FAILED", "NOT_TESTED", "UNVERIFIED")}
    report = {"schema_version": 1, "run_at": datetime.now(timezone.utc).isoformat(),
        "repository": root.name, "python": platform.python_version(), "platform": platform.platform(),
        "scope": "bundled self-tests only; live LLM-host activation is not tested",
        "counts": counts, "results": results}
    (output / "execution.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for x in results:
        rows.append("<tr><td>" + html.escape(x["skill"]) + "</td><td class='" + x["status"].lower()
            + "'>" + x["status"] + "</td><td>" + str(x["exit_code"] if x["exit_code"] is not None else "—")
            + "</td><td>" + str(x["duration_seconds"]) + "s</td><td>" + html.escape(x["reason"]) + "</td></tr>")
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Skill execution evidence</title>
<style>body{font:15px/1.5 system-ui,sans-serif;margin:40px;color:#18202a;background:#f5f7fa}
main{max-width:1100px;margin:auto;background:white;padding:32px;border:1px solid #dce2e8;border-radius:12px}
h1{margin-top:0}.meta{color:#536170}table{border-collapse:collapse;width:100%;margin:24px 0}
th,td{padding:12px;text-align:left;border-bottom:1px solid #e5e9ef}th{background:#f1f4f8}
.passed{color:#137333;font-weight:700}.failed{color:#b3261e;font-weight:700}
.not_tested,.unverified{color:#8a5200;font-weight:700}.note{padding:14px;background:#fff7e6;border:1px solid #f0d79b;border-radius:8px}
</style></head><body><main><h1>Skill execution evidence</h1>
<p class="meta">Run: """ + html.escape(report["run_at"]) + " · Python " + html.escape(report["python"]) + """</p>
<p>Passed: """ + str(counts["PASSED"]) + " · Failed: " + str(counts["FAILED"]) + " · Not tested: "
        + str(counts["NOT_TESTED"]) + " · Unverified: " + str(counts["UNVERIFIED"]) + """</p>
<table><thead><tr><th>Skill</th><th>Status</th><th>Exit code</th><th>Duration</th><th>Notes</th></tr></thead>
<tbody>""" + "".join(rows) + """</tbody></table>
<p class="note"><strong>Scope limitation:</strong> This report proves only the bundled self-tests ran.
It does not prove that an AI agent discovered, activated, or followed each SKILL.md in a live host.</p>
</main></body></html>"""
    (output / "report.html").write_text(page, encoding="utf-8")
    lines = ["# Skill execution evidence", "", "Run at: " + report["run_at"],
        "Python: " + report["python"], "Platform: " + report["platform"],
        "Summary: " + str(counts["PASSED"]) + " passed, " + str(counts["FAILED"]) + " failed, "
        + str(counts["NOT_TESTED"]) + " not tested, " + str(counts["UNVERIFIED"]) + " unverified",
        "", "| Skill | Status | Exit code | Duration |", "|---|---:|---:|---:|"]
    for x in results:
        lines.append("| " + x["skill"] + " | **" + x["status"] + "** | "
            + str(x["exit_code"] if x["exit_code"] is not None else "—") + " | "
            + str(x["duration_seconds"]) + "s |")
    lines += ["", "Scope: bundled self-tests only. LLM-host discovery, activation and instruction-following",
        "are not verified by this runner.", "", "See execution.json, logs/, and screenshots/report.png."]
    (output / "verification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--output", type=Path, default=Path("artifacts/skill-evidence"))
    p.add_argument("--timeout", type=int, default=180)
    a = p.parse_args(); root = a.root.resolve(); output = a.output.resolve()
    skills = discover_skills(root)
    if not skills:
        print("ERROR: no skill directories found under " + str(root), file=sys.stderr); return 2
    results = [run_skill(s, a.timeout) for s in skills]
    report = write_report(output, results, root)
    for x in results:
        print(x["status"] + "  " + x["skill"] + " (exit=" + str(x["exit_code"]) + ")")
    print("Evidence written to: " + str(output))
    return 1 if report["counts"]["FAILED"] or report["counts"]["UNVERIFIED"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
