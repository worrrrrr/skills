#!/usr/bin/env python3
"""Render references/meanings-0-100.md from assets/meanings-0-100.json.

Usage:
    python scripts/render_meanings.py            # write the reference
    python scripts/render_meanings.py --check    # fail if the reference is stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "meanings-0-100.json"
TARGET = ROOT / "references" / "meanings-0-100.md"

LABELS = {"good": "ให้คุณ", "neutral": "ปานกลาง", "bad": "ให้โทษ", "special": "พิเศษ"}


def render() -> str:
    with SOURCE.open(encoding="utf-8") as handle:
        data = json.load(handle)
    lines = [
        "# ความหมายเลข 0–100",
        "",
        "> สร้างจาก `assets/meanings-0-100.json` — อย่าแก้ไฟล์นี้มือ; แก้ JSON แล้วรัน",
        "> `python scripts/render_meanings.py`",
        "",
        "| เลข | ผล | ความหมาย |",
        "|---:|---|---|",
    ]
    for number in range(0, 101):
        item = data.get(str(number))
        if item is None:
            lines.append(f"| {number} | ไม่ระบุ | ยังไม่มีคำทำนายในชุดนี้ |")
            continue
        label = LABELS.get(item.get("verdict", ""), "ไม่ระบุ")
        meaning = str(item.get("meaning", "")).replace("|", "\\|")
        lines.append(f"| {number} | {label} | {meaning} |")
    lines += [
        "",
        "## หมายเหตุ",
        "",
        "- เลข 0 ใช้เมื่อผลรวมเป็นศูนย์ (หายาก) — ให้ตรวจการสะกดก่อน",
        "- เลข 11/22/33 บางสำนักหยุดเป็นเลขพิเศษ; ตารางนี้ให้ความหมายตามเลขนั้น",
        "- เลขอื่นหรือผลรวมเกิน 100 ให้ใช้ตาราง 1–109 ที่อ้างใน `references/table.md`",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the 0-100 meaning reference.")
    parser.add_argument("--check", action="store_true", help="fail if the reference is stale")
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != text:
            print("reference is stale: run python scripts/render_meanings.py", file=sys.stderr)
            return 1
        print("reference is current")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
