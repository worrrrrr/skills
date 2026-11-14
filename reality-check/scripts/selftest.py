#!/usr/bin/env python3
"""Self-test for pkgcheck.py.

Offline checks always run. Pass --network to add live registry smoke tests
(requires internet; skipped automatically on transport errors).

Usage:
    python scripts/selftest.py
    python scripts/selftest.py --network
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("pkgcheck", HERE / "pkgcheck.py")
if _SPEC is None or _SPEC.loader is None:
    raise SystemExit("cannot load pkgcheck.py next to this selftest")
_LOADER = _SPEC.loader
pkgcheck = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(pkgcheck)

failures: list[str] = []
checks = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(f"{label} {detail}".strip())


def run_main(*argv) -> int:
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            return pkgcheck.main(list(argv))
        except SystemExit as exc:
            return int(exc.code or 0)


# --- offline -------------------------------------------------------------

check("clean_range strips caret", pkgcheck.clean_range("^19.0.0") == "19.0.0")
check("clean_range strips range", pkgcheck.clean_range(">=1.2.3") == "1.2.3")
check("clean_range none", pkgcheck.clean_range(None) is None)
check("version_present exact", pkgcheck.version_present(["1.0.0"], "1.0.0"))
check("version_present prerelease core", pkgcheck.version_present(["1.2.3-beta.1"], "1.2.3"))
check("version_present missing", not pkgcheck.version_present(["1.0.0"], "2.0.0"))

found = pkgcheck.render({"ecosystem": "npm", "name": "x", "exists": True, "latest": "1.0.0"}, 0)
check("render found mentions latest", "EXISTS" in found and "1.0.0" in found, found)
missing = pkgcheck.render({"ecosystem": "npm", "name": "x", "exists": False, "error": "404"}, 1)
check("render missing says NOT FOUND", "NOT FOUND" in missing, missing)
unverified = pkgcheck.render({"ecosystem": "npm", "name": "x", "exists": None, "error": "timeout"}, 2)
check("render unreachable says UNVERIFIED", "UNVERIFIED" in unverified, unverified)

check(
    "installed python missing module exits 1",
    run_main("installed", "python", "definitely-not-a-real-module-xyz123") == 1,
)
check("installed without package exits 3", run_main("installed", "python") == 3)

# --- project classification (offline) ------------------------------------

check("classify current", pkgcheck._classify("^1.0.0", "1.2.3", "1.2.3", None) == "CURRENT")
check("classify major", pkgcheck._classify("^1.0.0", "1.2.3", "2.0.0", None) == "MAJOR")
check("classify outdated", pkgcheck._classify("^1.0.0", "1.2.0", "1.4.0", None) == "OUTDATED")
check("classify patch", pkgcheck._classify("^1.0.0", "1.2.0", "1.2.2", None) == "PATCH")
check("classify deprecated wins",
      pkgcheck._classify("^1.0.0", "1.2.3", "1.2.3", "use another package") == "DEPRECATED")
check("classify workspace skipped", pkgcheck._classify("workspace:*", None, "1.0.0", None) == "SKIPPED")
check("classify unverified", pkgcheck._classify("^1.0.0", None, None, None) == "UNVERIFIED")

import tempfile  # noqa: E402  (kept local to the project checks)

with tempfile.TemporaryDirectory() as tmp:
    state_file = str(Path(tmp) / "state.json")
    payload = {
        "checked_at": "2026-01-01T00:00:00+00:00",
        "dependencies": [
            {"name": "ai", "spec": "^4", "installed": "4.0.0", "latest": "7.0.0", "status": "MAJOR"},
        ],
    }
    pkgcheck._write_state(state_file, payload, None)
    saved = pkgcheck._read_state(state_file)
    check("state roundtrip", bool(saved) and saved["packages"]["ai"]["latest"] == "7.0.0")
    check("state is json", isinstance(saved, dict) and saved.get("version") == 1)

check(
    "rules: svelte 5 uses runes",
    any("runes" in rule for rule in pkgcheck.rules_for([{"name": "svelte", "installed": "5.57.3"}])),
)
check(
    "rules: tailwind 4 uses @import",
    any('@import "tailwindcss"' in rule
        for rule in pkgcheck.rules_for([{"name": "tailwindcss", "installed": "4.3.5"}])),
)
check(
    "rules: kit 3 uses $app/state",
    any("$app/state" in rule
        for rule in pkgcheck.rules_for([{"name": "@sveltejs/kit", "installed": "3.2.0"}])),
)
check("rules: empty project", pkgcheck.rules_for([]) == [])

# --- verify.py ------------------------------------------------------------

import subprocess  # noqa: E402

VERIFY = HERE / "verify.py"

with tempfile.TemporaryDirectory() as tmp:
    project = Path(tmp)
    (project / "package.json").write_text(
        json.dumps({"name": "demo", "scripts": {"check": "echo ok", "lint": "echo ok"}}),
        encoding="utf-8",
    )
    listing = subprocess.run(
        [sys.executable, str(VERIFY), str(project), "--list"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    check("verify lists detected scripts", listing.returncode == 0 and "check" in listing.stdout
          and "lint" in listing.stdout, listing.stdout + listing.stderr)
    check("verify reports nothing to verify", subprocess.run(
        [sys.executable, str(VERIFY), str(Path(tmp) / "empty")],
        capture_output=True, text=True,
    ).returncode in (1, 2))

# --- scan (offline) ------------------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "package.json").write_text(json.dumps({"dependencies": {
        "svelte": "^5.0.0", "@sveltejs/kit": "^3.0.0", "tailwindcss": "^4.0.0",
        "ai": "^7.0.0", "@ai-sdk/svelte": "^5.0.0",
    }}), encoding="utf-8")
    for name, version in {"svelte": "5.57.3", "@sveltejs/kit": "3.2.0",
                          "tailwindcss": "4.3.5", "ai": "7.0.173",
                          "@ai-sdk/svelte": "5.0.173"}.items():
        target = root / "node_modules" / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "package.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "a.svelte").write_text(
        "<script>\n  export let x;\n  $: y = x;\n</script>\n<button on:click={f}><slot /></button>\n",
        encoding="utf-8",
    )
    (root / "src" / "b.ts").write_text(
        "const r = streamText({ maxTokens: 5 });\nconst c = Chat({});\nexport const m: CoreMessage = x;\n",
        encoding="utf-8",
    )
    payload, code = pkgcheck.scan_project(str(root))
    found = {item["code"] for item in payload["findings"]}
    check("scan exits 1 on legacy code", code == 1)
    check("scan finds svelte legacy", {"SVELTE_PROPS", "SVELTE_EVENT", "SVELTE_SLOT", "SVELTE_REACTIVE"} <= found)
    check("scan finds ai legacy",
          {"AI_MAXTOKENS", "AI_CHAT_CTOR", "AI_COREMESSAGE"} <= found)

# --- network -------------------------------------------------------------

if "--network" in sys.argv:
    code = run_main("npm", "react")
    if code == 2:
        print("skip network checks: registry unreachable")
    else:
        check("npm react exists", code == 0)
        check("npm bogus name missing", run_main("npm", "zzz-not-a-real-package-xyz123456") == 1)
        check("url example.com reachable", run_main("url", "https://example.com") == 0)

for failure in failures:
    print(f"FAIL  {failure}")
if failures:
    print(f"\n{len(failures)} of {checks} checks failed")
    raise SystemExit(1)
print(f"PASS  {checks} checks passed")
