#!/usr/bin/env python3
"""Self-test for contrast.py and audit.py (offline).

Usage:
    python scripts/selftest.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contrast = load("contrast", "contrast.py")
audit = load("audit", "audit.py")

failures: list[str] = []
checks = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(f"{label} {detail}".strip())


def run(fn, *args) -> int:
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        return fn(list(args))


# --- contrast -------------------------------------------------------------

check("white on black is 21:1", contrast.contrast_ratio("#ffffff", "#000000") == 21.0,
      str(contrast.contrast_ratio("#ffffff", "#000000")))
check("same colour is 1:1", contrast.contrast_ratio("#777777", "#777") == 1.0)
check("hex and rgb agree",
      contrast.contrast_ratio("#fff", "rgb(0,0,0)") == contrast.contrast_ratio("#ffffff", "#000000"))
check("rgb percent works", contrast.contrast_ratio("rgb(100% 100% 100%)", "#000") == 21.0)

brand_ratio = contrast.contrast_ratio("oklch(0.55 0.2 262)", "#ffffff")
check("oklch parses and is not 1:1", brand_ratio > 1.5, str(brand_ratio))
check("oklch verdict is a known grade", contrast.verdict(brand_ratio) in {"AAA", "AA", "AA-large", "FAIL"})

check("aa passes at 4.5", contrast.verdict(4.5) == "AA")
check("aaa passes at 7", contrast.verdict(7) == "AAA")
check("low contrast fails", contrast.verdict(2.9) == "FAIL")
check("bad colour exits 2", run(contrast.main, "notacolour", "#000") == 2)
check("good pair exits 0", run(contrast.main, "#000", "#fff") == 0)
check("bad pair exits 1", run(contrast.main, "#777", "#888") == 1)

# --- audit ----------------------------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "layout.css").write_text(":root { --color-brand: #123456; }\n", encoding="utf-8")
    (root / "page.svelte").write_text(
        '<script>let x = 1;</script>\n'
        '<div style="color: #ff0000; font-size: 13px"></div>\n'
        '<img src="a.png">\n'
        '<button><svg></svg></button>\n'
        '<style>a { outline: none; }</style>\n',
        encoding="utf-8",
    )

    findings = audit.audit(str(root), str(root / "layout.css"))
    found = {item["code"] for item in findings}
    check("audit finds hardcoded colour", "HARDCODED_COLOR" in found, str(found))
    check("audit finds px font", "PX_FONT" in found)
    check("audit finds missing alt", "IMG_NO_ALT" in found)
    check("audit finds unlabelled icon button", "ICON_BUTTON_LABEL" in found)
    check("audit finds removed focus ring", "OUTLINE_NONE" in found)
    check("audit skips the tokens file",
          not any(item["file"] == "layout.css" for item in findings))

    check("audit exits 1 with findings", run(audit.main, str(root)) == 1)

    clean = Path(tmp) / "clean"
    clean.mkdir()
    (clean / "ok.svelte").write_text('<button aria-label="Close"><svg></svg></button>\n', encoding="utf-8")
    check("audit exits 0 when clean", run(audit.main, str(clean)) == 0)

for failure in failures:
    print(f"FAIL  {failure}")
if failures:
    print(f"\n{len(failures)} of {checks} checks failed")
    raise SystemExit(1)
print(f"PASS  {checks} checks passed")
