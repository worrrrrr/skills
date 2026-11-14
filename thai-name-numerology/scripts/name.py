#!/usr/bin/env python3
"""Thai name numerology (เลขศาสตร์ชื่อ) for a name and surname.

Usage:
    python scripts/name.py --name "วรกฤช" --surname "สุนทรธรรมนิติ" --json
    python scripts/name.py --full "วรกฤช สุนทรธรรมนิติ"
    python scripts/name.py --name "สมชาย" --md

Exit codes: 0 ok, 2 cannot read input, 3 usage/invalid input.
"""

from __future__ import annotations

import argparse
import json
import sys

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

VERDICTS = {
    1: "good", 2: "neutral", 3: "neutral", 4: "good", 5: "good",
    6: "good", 7: "bad", 8: "bad", 9: "good", 11: "bad",
    14: "good", 51: "good", 65: "good",
}

MEANINGS = {
    1: ("good", "ดาวอาทิตย์ — ความเชื่อมั่น ผู้นำ เด่นในสังคม แต่ระวังความหยิ่งทะนง"),
    2: ("neutral", "ดาวจันทร์ — จินตนาการ อ่อนโยน มีเสน่ห์ แต่ใจหวั่นไหวและตัดสินใจยาก"),
    3: ("neutral", "ดาวอังคาร — กล้าหาญ เด็ดเดี่ยว ชอบแข่งขัน แต่ระวังใจร้อนและอุบัติเหตุ"),
    4: ("good", "ดาวพุธ — สติปัญญา ปฏิภาณ เจรจาเก่ง เอาตัวรอดด้วยปัญญา"),
    5: ("good", "ดาวพฤหัสบดี — คุณธรรม ปัญญา ผู้ใหญ่อุปถัมภ์ ชีวิตมั่นคง"),
    6: ("good", "ดาวศุกร์ — ศิลปะ รสนิยม การเงิน ความรัก มีคนช่วยเหลือ"),
    7: ("bad", "ดาวเสาร์ — อดทน ฝ่าอุปสรรค เหนื่อยก่อนสำเร็จ"),
    8: ("bad", "ดาวราหู — พลิกแพลง กล้าเสี่ยง ระวังมัวเมาและอบายมุข"),
    9: ("good", "ดาวเกตุ — ลางสังหรณ์ ต่างประเทศ เรื่องลี้ลับ แคล้วคลาด"),
    11: ("bad", "ความขัดแย้งในตัวเอง ดื้อรั้น ซ่อนความแข็งกร้าวใต้บุคลิกอ่อนโยน ชีวิตดิ้นรน"),
    14: ("good", "สติปัญญาและมงคล ฉลาด มีตำแหน่งก้าวไกล ผู้คนเคารพ รักความยุติธรรม สำเร็จมาก"),
    51: ("good", "รักความสมบูรณ์แบบ ปัญญาดี ผู้ใหญ่อำนวยโชค ระวังเข้มงวดจนตึงเครียด"),
    65: ("good", "คู่ทรัพย์คู่โชค ราบรื่น ผู้ใหญ่สนับสนุน หาเงินเก่ง ความรักมั่นคง"),
}

LABELS = {
    "good": "ให้คุณ",
    "neutral": "ปานกลาง",
    "bad": "ให้โทษ",
}

HELP = """Usage:
  python scripts/name.py --name "วรกฤช" --surname "สุนทรธรรมนิติ" [--json|--md]
  python scripts/name.py --full "วรกฤช สุนทรธรรมนิติ" [--json|--md]

Options:
  --name      ชื่อ (อาจไม่มีนามสกุล)
  --surname   นามสกุล
  --full      ชื่อและนามสกุลในสตริงเดียว คั่นด้วยช่องว่าง
  --json      พิมพ์ JSON (ค่าเริ่มต้น)
  --md        พิมพ์รายงาน Markdown
  --help      แสดงวิธีใช้

ค่าอักษร: 1 ก ด ท ถ ภ ฤ / 2 ข ช บ ป ง / 3 ฆ ฑ ฒ ต ฃ / 4 ค ธ ร ญ ษ /
5 ฉ ณ ฌ น ม ห ฮ ฎ ฬ / 6 จ ล ว อ / 7 ศ ส ซ / 8 ย พ ฟ ผ ฝ / 9 ฏ ฐ
สระ-วรรณยุกต์: า ุ ำ ่=1, เ แ ู ้=2, ๋=3, ะ ิ โ ั=4, ึ=5, ใ=6,
ี ื ๊=7, ็=8, ไ ์=9, ํ=0
"""


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(f"error: {message}", file=sys.stderr)
        self.print_help(sys.stderr)
        raise SystemExit(3)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = Parser(description="Thai name numerology (เลขศาสตร์ชื่อ).")
    parser.add_argument("--name", help="ชื่อ")
    parser.add_argument("--surname", help="นามสกุล")
    parser.add_argument("--full", help="ชื่อและนามสกุลในสตริงเดียว")
    parser.add_argument("--json", action="store_true", help="print JSON (default)")
    parser.add_argument("--md", action="store_true", help="print a Markdown report")
    return parser.parse_args(argv)


def split_input(args: argparse.Namespace) -> tuple[str, str]:
    if args.full:
        parts = args.full.split()
        if not parts:
            print("error: --full is empty", file=sys.stderr)
            raise SystemExit(3)
        return parts[0], " ".join(parts[1:])
    if not args.name:
        print("error: pass --name (and optionally --surname) or --full", file=sys.stderr)
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
        "unmapped": [item["char"] for item in chars if item["kind"] == "unmapped"],
    }


def verdict(number: int) -> str | None:
    return VERDICTS.get(number)


def meaning(number: int) -> str | None:
    item = MEANINGS.get(number)
    return item[1] if item else None


def summarize(name: str, surname: str) -> dict:
    name_part = part(name)
    surname_part = part(surname) if surname else None
    combined_total = name_part["total"] + (surname_part["total"] if surname_part else 0)
    combined = {
        "total": combined_total,
        "reduced": reduce_number(combined_total),
        "verdict": verdict(combined_total),
    }
    for item in (name_part, surname_part):
        if item is not None:
            item["verdict"] = verdict(item["total"])
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


def md_report(data: dict) -> str:
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
    lines += ["", "> เป็นความเชื่อเชิงตำราตามหลักเลขศาสตร์ไทย เพื่อความบันเทิง ไม่ใช่คำทำนายตายตัว"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    name, surname = split_input(args)
    if not any(char in CONSONANT_VALUES or char in MARK_VALUES for char in name):
        print("error: no Thai letters found in the name", file=sys.stderr)
        return 2
    data = summarize(name, surname)
    if args.md:
        print(md_report(data))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
