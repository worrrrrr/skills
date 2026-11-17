#!/usr/bin/env python3
"""Thai name numerology (เลขศาสตร์ชื่อ) for a name and surname.

Supports Thai letters and the English letters A-Z mapped by the same table.

Usage:
    python scripts/name.py "วรกฤช สุนทรธรรมนิติ"
    python scripts/name.py "วรกฤช สุนทรธรรมนิติ" --md
    python scripts/name.py --name "Somchai" --surname "Jaidee" --json

Exit codes: 0 ok, 2 cannot read input, 3 usage/invalid input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ค่าอักษรตามตำราเลขศาสตร์ (สายอาจารย์พลูหลวง) — พยัญชนะ + ฤ
CONSONANT_VALUES = {
    "ก": 1, "ด": 1, "ท": 1, "ถ": 1, "ภ": 1, "ฤ": 1,
    "ข": 2, "ช": 2, "บ": 2, "ป": 2, "ง": 2,
    "ฆ": 3, "ฑ": 3, "ฒ": 3, "ต": 3, "ฃ": 3,
    "ค": 4, "ธ": 4, "ร": 4, "ญ": 4, "ษ": 4,
    "ฉ": 5, "ณ": 5, "ฌ": 5, "น": 5, "ม": 5, "ห": 5, "ฮ": 5, "ฎ": 5, "ฬ": 5,
    "จ": 6, "ล": 6, "ว": 6, "อ": 6,
    "ศ": 7, "ส": 7, "ซ": 7,
    "ย": 8, "พ": 8, "ฟ": 8, "ผ": 8, "ฝ": 8,
    "ฏ": 9, "ฐ": 9,
}

# สระและวรรณยุกต์: ค่าของ "รูปสระ" ไม่รวม อ ที่เป็นพยัญชนะ
MARK_VALUES = {
    "า": 1, "ุ": 1, "ำ": 1, "่": 1,
    "เ": 2, "แ": 2, "ู": 2, "้": 2,
    "๋": 3,
    "ะ": 4, "ิ": 4, "โ": 4, "ั": 4,
    "ึ": 5,
    "ใ": 6,
    "ี": 7, "ื": 7, "๊": 7,
    "็": 8,
    "ไ": 9, "์": 9,
}
ZERO_VALUES = {"ํ"}

# ค่าอักษรอังกฤษตามตารางเดียวกัน (ตัวพิมพ์เล็ก/ใหญ่เท่ากัน)
LATIN_VALUES = {}
for _letters, _value in (
    ("AIJQY", 1),
    ("BKR", 2),
    ("CGLS", 3),
    ("DMT", 4),
    ("EHNX", 5),
    ("UVW", 6),
    ("OZ", 7),
    ("FP", 8),
):
    for _letter in _letters:
        LATIN_VALUES[_letter] = _value

MEANINGS_PATH = Path(__file__).resolve().parent.parent / "assets" / "meanings-0-100.json"
DETAIL_DIR = Path(__file__).resolve().parent.parent / "references"
DETAIL_PATH = DETAIL_DIR / "meaning.md"
try:
    with MEANINGS_PATH.open(encoding="utf-8") as handle:
        MEANINGS = {int(key): value for key, value in json.load(handle).items()}
except (OSError, ValueError, json.JSONDecodeError) as error:
    raise SystemExit(f"error: cannot load the meaning table {MEANINGS_PATH}: {error}") from error

LABELS = {
    "good": "ให้คุณ",
    "neutral": "ปานกลาง",
    "bad": "ให้โทษ",
    "special": "พิเศษ",
}

HELP = """Usage:
  python scripts/name.py "ชื่อ นามสกุล" [--json|--md]
  python scripts/name.py --name "ชื่อ" --surname "นามสกุล" [--json|--md]
  python scripts/name.py --full "ชื่อ นามสกุล" [--json|--md]

Options:
  text        ชื่อและนามสกุลในสตริงเดียว (แนะนำ)
  --name      ชื่อ (อาจไม่มีนามสกุล)
  --surname   นามสกุล
  --full      ชื่อและนามสกุลในสตริงเดียว (แบบเดิม)
  --json      พิมพ์ JSON (ค่าเริ่มต้น)
  --md        พิมพ์รายงาน Markdown
  --help      แสดงวิธีใช้

ค่าอักษร: 1 ก ด ท ถ ภ ฤ / 2 ข ช บ ป ง / 3 ฆ ฑ ฒ ต ฃ / 4 ค ธ ร ญ ษ /
5 ฉ ณ ฌ น ม ห ฮ ฎ ฬ / 6 จ ล ว อ / 7 ศ ส ซ / 8 ย พ ฟ ผ ฝ / 9 ฏ ฐ
สระ-วรรณยุกต์: า ุ ำ ่=1, เ แ ู ้=2, ๋=3, ะ ิ โ ั=4, ึ=5, ใ=6,
ี ื ๊=7, ็=8, ไ ์=9, ํ=0
อักษรอังกฤษ: A I J Q Y=1, B K R=2, C G L S=3, D M T=4, E H N X=5,
U V W=6, O Z=7, F P=8
"""


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(f"error: {message}", file=sys.stderr)
        self.print_help(sys.stderr)
        raise SystemExit(3)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = Parser(description="Thai name numerology (เลขศาสตร์ชื่อ).")
    parser.add_argument("text", nargs="?", help="ชื่อและนามสกุลในสตริงเดียว")
    parser.add_argument("--name", help="ชื่อ")
    parser.add_argument("--surname", help="นามสกุล")
    parser.add_argument("--full", help="ชื่อและนามสกุลในสตริงเดียว (แบบเดิม)")
    parser.add_argument("--json", action="store_true", help="print JSON (default)")
    parser.add_argument("--md", action="store_true", help="print a Markdown report")
    parser.add_argument("--detail", action="store_true", help="add the long prose from references/meaning.md (with --md)")
    return parser.parse_args(argv)


def split_input(args: argparse.Namespace) -> tuple[str, str]:
    if args.text:
        if args.name or args.surname or args.full:
            print("error: use the positional text or --name/--surname/--full, not both", file=sys.stderr)
            raise SystemExit(3)
        parts = args.text.split()
        if not parts:
            print("error: the name is empty", file=sys.stderr)
            raise SystemExit(3)
        return parts[0], " ".join(parts[1:])
    if args.full:
        parts = args.full.split()
        if not parts:
            print("error: --full is empty", file=sys.stderr)
            raise SystemExit(3)
        return parts[0], " ".join(parts[1:])
    if not args.name:
        print("error: pass the name as text, or --name (and optionally --surname)", file=sys.stderr)
        raise SystemExit(3)
    return args.name.strip(), (args.surname or "").strip()


def letters(text: str) -> list[dict]:
    out = []
    for char in text:
        if char.isspace():
            continue
        if char in CONSONANT_VALUES:
            out.append({"char": char, "value": CONSONANT_VALUES[char], "kind": "consonant"})
        elif char in MARK_VALUES:
            out.append({"char": char, "value": MARK_VALUES[char], "kind": "mark"})
        elif char in ZERO_VALUES:
            out.append({"char": char, "value": 0, "kind": "zero"})
        elif char.upper() in LATIN_VALUES:
            out.append({"char": char, "value": LATIN_VALUES[char.upper()], "kind": "latin"})
        else:
            out.append({"char": char, "value": 0, "kind": "unmapped"})
    return out


def reduce_number(number: int) -> list[int]:
    steps = [number]
    current = number
    while current > 9:
        current = sum(int(digit) for digit in str(current))
        steps.append(current)
    return steps


def part(text: str) -> dict:
    chars = letters(text)
    total = sum(item["value"] for item in chars)
    return {
        "text": text,
        "chars": chars,
        "total": total,
        "reduced": reduce_number(total),
        "verdict": verdict(total),
        "meaning": meaning(total),
        "unmapped": [item["char"] for item in chars if item["kind"] == "unmapped"],
    }


def verdict(number: int) -> str | None:
    item = MEANINGS.get(number)
    return item["verdict"] if item else None


def meaning(number: int) -> str | None:
    item = MEANINGS.get(number)
    return item["meaning"] if item else None


def load_detail() -> dict[int, dict]:
    """Read references/meaning-*.md into {number: {title, text}}."""
    paths = sorted(DETAIL_DIR.glob("meaning-*.md"))
    if not paths:
        paths = [DETAIL_PATH]
    out: dict[int, dict] = {}
    for path in paths:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            match = re.search(r"เลข\s+(\d+)\s*$", line)
            if not match:
                continue
            number = int(match.group(1))
            title = line[: match.start()].strip()
            if not title:
                for previous in range(index - 1, -1, -1):
                    if lines[previous].strip():
                        title = lines[previous].strip()
                        break
            paragraph = []
            for following in range(index + 1, len(lines)):
                text = lines[following].strip()
                if not text:
                    if paragraph:
                        break
                    continue
                if re.search(r"เลข\s+\d+\s*$", text):
                    break
                paragraph.append(text)
            out[number] = {"title": title, "text": " ".join(paragraph)}
    return out


def summarize(name: str, surname: str) -> dict:
    name_part = part(name)
    surname_part = part(surname) if surname else None
    combined_total = name_part["total"] + (surname_part["total"] if surname_part else 0)
    combined = {
        "total": combined_total,
        "reduced": reduce_number(combined_total),
        "verdict": verdict(combined_total),
        "meaning": meaning(combined_total),
        "reduced_items": [
            {"number": number, "verdict": verdict(number), "meaning": meaning(number)}
            for number in reduce_number(combined_total)
        ],
    }
    return {
        "name": name_part,
        "surname": surname_part,
        "combined": combined,
        "numbers": {
            "name": name_part["total"],
            "surname": surname_part["total"] if surname_part else None,
            "combined": combined_total,
            "reduced": combined["reduced"],
        },
    }


def md_report(data: dict, detail: dict[int, dict] | None = None) -> str:
    lines = ["# Name numerology (เลขศาสตร์ชื่อ)", ""]
    name = data["name"]
    surname = data["surname"]
    lines.append(f"**ชื่อ** {name['text']} = **{name['total']}** (ทอน { ' → '.join(map(str, name['reduced'])) })")
    if surname:
        lines.append(f"**นามสกุล** {surname['text']} = **{surname['total']}** (ทอน { ' → '.join(map(str, surname['reduced'])) })")
        lines.append(f"**รวม** = **{data['combined']['total']}** (ทอน { ' → '.join(map(str, data['combined']['reduced'])) })")
    lines += ["", "## คำทำนาย", ""]
    for number in [name["total"], surname["total"] if surname else None, data["combined"]["total"]]:
        if number is None:
            continue
        label = LABELS.get(verdict(number) or "", "ไม่ระบุ")
        text = meaning(number) or "ไม่มีคำทำนายในชุดนี้ — ดูตารางอ้างอิง"
        lines.append(f"- **{number}** ({label}) — {text}")
    reduced = data["combined"]["reduced"]
    for number in reduced[1:]:
        label = LABELS.get(verdict(number) or "", "ไม่ระบุ")
        text = meaning(number) or "ไม่มีคำทำนายในชุดนี้ — ดูตารางอ้างอิง"
        lines.append(f"- **{number}** ({label}, เลขทอน) — {text}")
    unmapped = sorted(set(name["unmapped"] + (surname["unmapped"] if surname else [])))
    if unmapped:
        lines += ["", f"> อักษรที่ตารางไม่กำหนดค่า: {' '.join(unmapped)} (นับ 0)"]
    if detail:
        numbers = [name["total"]]
        if surname:
            numbers.append(surname["total"])
        numbers.append(data["combined"]["total"])
        numbers += data["combined"]["reduced"][1:]
        lines += ["", "## รายละเอียด"]
        seen = set()
        for number in numbers:
            if number in seen or number not in detail:
                continue
            seen.add(number)
            item = detail[number]
            lines += ["", f"### {number} — {item['title']}", item["text"]]
    lines += ["", "> เป็นความเชื่อเชิงตำราตามหลักเลขศาสตร์ไทย เพื่อความบันเทิง ไม่ใช่คำทำนายตายตัว"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    name, surname = split_input(args)
    if not any(
        char in CONSONANT_VALUES or char in MARK_VALUES or char.upper() in LATIN_VALUES
        for char in name
    ):
        print("error: no mapped Thai or English letters found in the name", file=sys.stderr)
        return 2
    if args.detail and not args.md:
        print("error: use --detail together with --md", file=sys.stderr)
        return 3
    data = summarize(name, surname)
    if args.md:
        print(md_report(data, load_detail() if args.detail else None))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
