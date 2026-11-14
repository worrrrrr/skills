#!/usr/bin/env python3
"""Deterministic five-system chart from one birth record.

Usage:
    python scripts/chart.py --date 1990-01-01 --time 12:00 --tz 7 \
        --lat 13.7563 --lon 100.5018 [--md]

Exit codes: 0 ok, 2 cannot compute, 3 usage/invalid input.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from engine import (
    BRANCHES,
    NAKSHATRAS,
    SIGNS,
    STEMS,
    STEM_ELEMENT,
    STEM_KEYS,
    STEM_POLARITY,
    BRANCH_ELEMENT,
    compute_all,
    fmt_deg,
)

WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
ANIMALS = ["rat", "ox", "tiger", "rabbit", "dragon", "snake",
           "horse", "goat", "monkey", "rooster", "dog", "pig"]
GRAHAS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]
WESTERN_PLANETS = ["sun", "moon", "mercury", "venus", "mars",
                   "jupiter", "saturn", "uranus", "neptune", "pluto"]


class Parser(argparse.ArgumentParser):
    """argparse exits 2 on usage; this repository reserves 3 for usage errors."""

    def error(self, message: str) -> None:
        print(f"error: {message}", file=sys.stderr)
        self.print_help(sys.stderr)
        raise SystemExit(3)


def build_parser() -> Parser:
    parser = Parser(
        description="Five birth-chart systems from one birth record.",
        epilog=("Astrological entertainment, not medical, financial or legal advice. "
                "Approximate ephemeris: solar terms ~15 min, lunar longitude ~0.2 deg, mean node."),
    )
    parser.add_argument("--date", required=True, help="birth date YYYY-MM-DD (CE, 1800-2050)")
    parser.add_argument("--time", default="12:00", help="birth time HH:MM, 24h (default 12:00)")
    parser.add_argument("--tz", required=True, type=float, help="UTC offset in hours, e.g. 7")
    parser.add_argument("--lat", required=True, type=float, help="latitude, -89.9..89.9")
    parser.add_argument("--lon", required=True, type=float, help="longitude, -180..180")
    parser.add_argument("--md", action="store_true", help="print a Markdown report instead of JSON")
    parser.add_argument("--json", action="store_true", help="print JSON (the default)")
    return parser


def parse_input(args: argparse.Namespace) -> dict:
    try:
        date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("error: --date must be YYYY-MM-DD", file=sys.stderr)
        raise SystemExit(3)
    if not 1800 <= date.year <= 2050:
        print("error: --date must be between 1800 and 2050", file=sys.stderr)
        raise SystemExit(3)
    try:
        hour, minute = (int(part) for part in args.time.split(":", 1))
    except (ValueError, TypeError):
        print("error: --time must be HH:MM", file=sys.stderr)
        raise SystemExit(3)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        print("error: --time must be a valid 24h time", file=sys.stderr)
        raise SystemExit(3)
    if not -14 <= args.tz <= 14:
        print("error: --tz must be between -14 and 14", file=sys.stderr)
        raise SystemExit(3)
    if not -89.9 <= args.lat <= 89.9:
        print("error: --lat must be between -89.9 and 89.9", file=sys.stderr)
        raise SystemExit(3)
    if not -180 <= args.lon <= 180:
        print("error: --lon must be between -180 and 180", file=sys.stderr)
        raise SystemExit(3)
    return {
        "y": date.year, "m": date.month, "d": date.day,
        "hh": hour, "mi": minute, "tz": args.tz, "lat": args.lat, "lon": args.lon,
    }


def sign_block(lon: float | None) -> dict | None:
    if lon is None:
        return None
    return {"sign": SIGNS[int((lon % 360) // 30)], "degree": fmt_deg(lon)}


def summarize(chart: dict, birth: dict) -> dict:
    bz = chart["bazi"]
    vedic = chart["vedic"]
    western = chart["western"]
    hd = chart["hd"]
    points = {point["id"]: point["lon"] for point in western["points"]}
    hd_map = {item["id"]: f"{item['gate']}.{item['line']}" for item in hd["personality"]}
    design_map = {item["id"]: f"{item['gate']}.{item['line']}" for item in hd["design_set"]}
    return {
        "input": {
            "date": f"{birth['y']}-{birth['m']:02d}-{birth['d']:02d}",
            "time": f"{birth['hh']:02d}:{birth['mi']:02d}",
            "utcOffset": birth["tz"],
            "latitude": birth["lat"],
            "longitude": birth["lon"],
        },
        "thai": {
            "weekday": WEEKDAYS[chart["thai"]["weekday"]],
            "animalYear": {"index": chart["thai"]["animal"], "name": ANIMALS[chart["thai"]["animal"]]},
            "sunSign": SIGNS[chart["thai"]["sign"]],
            "sunSidereal": fmt_deg(vedic["sun"]),
            "ascendant": sign_block(vedic["asc"]),
        },
        "bazi": {
            "solarYear": bz["solar_year"],
            "monthNumber": bz["month"],
            "localMeanTime": round(bz["lmt_clock"], 2),
            "dayMaster": {
                "stem": STEMS[bz["pillars"][2]["stem"]],
                "key": STEM_KEYS[bz["pillars"][2]["stem"]],
                "element": STEM_ELEMENT[bz["pillars"][2]["stem"]],
                "polarity": STEM_POLARITY[bz["pillars"][2]["stem"]],
            },
            "pillars": [
                {
                    "id": pillar["id"],
                    "stemChar": STEMS[pillar["stem"]],
                    "branchChar": BRANCHES[pillar["branch"]],
                    "stem": STEM_KEYS[pillar["stem"]],
                    "stemElement": STEM_ELEMENT[pillar["stem"]],
                    "branchElement": BRANCH_ELEMENT[pillar["branch"]],
                }
                for pillar in bz["pillars"]
            ],
            "elements": bz["elements"],
        },
        "vedic": {
            "lagna": sign_block(vedic["asc"]),
            "moonRasi": sign_block(vedic["moon"]),
            "sunRasi": sign_block(vedic["sun"]),
            "nakshatra": {
                "index": vedic["vim"]["nak"]["index"],
                "name": NAKSHATRAS[vedic["vim"]["nak"]["index"]],
                "pada": vedic["vim"]["nak"]["pada"],
            },
            "grahas": [
                {"id": graha, **sign_block(vedic[graha])} for graha in GRAHAS
            ],
            "dashas": [
                {
                    "lord": period["lord"],
                    "years": round(period["years"], 2),
                    "start": period["start"].strftime("%Y-%m-%d"),
                    "end": period["end"].strftime("%Y-%m-%d"),
                }
                for period in vedic["vim"]["periods"]
            ],
        },
        "western": {
            "sun": sign_block(points["sun"]),
            "moon": sign_block(points["moon"]),
            "ascendant": sign_block(western["asc"]),
            "midheaven": sign_block(western["mc"]),
            "planets": [
                {"id": planet, **sign_block(points[planet])} for planet in WESTERN_PLANETS
            ],
            "aspects": [
                {
                    "a": aspect["a"], "b": aspect["b"], "aspect": aspect["aspect"],
                    "orb": round(aspect["orb"], 2),
                }
                for aspect in western["aspects"][:20]
            ],
        },
        "humanDesign": {
            "type": hd["type"],
            "authority": hd["authority"],
            "profile": hd["profile"],
            "definitionParts": hd["phases"],
            "definedCenters": sorted(hd["defined"]),
            "channels": [f"{a}-{b}" for a, b in hd["channels"]],
            "personality": hd_map,
            "design": design_map,
            "incarnationCross": hd["cross"],
        },
    }


def md_report(data: dict) -> str:
    lines = ["# Divination chart", ""]
    lines.append(
        f"Born **{data['input']['date']} {data['input']['time']}** at "
        f"UTC{data['input']['utcOffset']:+g}, {data['input']['latitude']}, {data['input']['longitude']}"
    )
    lines += ["", "## Thai (ดูดวง)"]
    lines.append(f"- Weekday: {data['thai']['weekday']}")
    lines.append(f"- Animal year: {data['thai']['animalYear']['name']}")
    lines.append(f"- Sun sign (sidereal): {data['thai']['sunSign']} {data['thai']['sunSidereal']}")
    if data["thai"]["ascendant"]:
        lines.append(f"- Ascendant: {data['thai']['ascendant']['sign']} {data['thai']['ascendant']['degree']}")
    lines += ["", "## Bazi"]
    lines.append(
        f"- Solar year {data['bazi']['solarYear']}, month {data['bazi']['monthNumber']}, "
        f"local mean time {data['bazi']['localMeanTime']}"
    )
    master = data["bazi"]["dayMaster"]
    lines.append(f"- Day master: {master['stem']} ({master['element']}, {master['polarity']})")
    for pillar in data["bazi"]["pillars"]:
        lines.append(
            f"- {pillar['id']}: {pillar['stemChar']}{pillar['branchChar']} "
            f"({pillar['stemElement']}/{pillar['branchElement']})"
        )
    lines.append("- Elements: " + ", ".join(f"{key} {value}" for key, value in data["bazi"]["elements"].items()))
    lines += ["", "## Vedic (อินเดีย)"]
    if data["vedic"]["lagna"]:
        lines.append(f"- Lagna: {data['vedic']['lagna']['sign']} {data['vedic']['lagna']['degree']}")
    lines.append(f"- Moon: {data['vedic']['moonRasi']['sign']} {data['vedic']['moonRasi']['degree']}")
    lines.append(f"- Nakshatra: {data['vedic']['nakshatra']['name']}, pada {data['vedic']['nakshatra']['pada']}")
    for dasha in data["vedic"]["dashas"]:
        lines.append(f"- {dasha['lord']}: {dasha['years']} years, {dasha['start']} to {dasha['end']}")
    lines += ["", "## Western (สากล)"]
    lines.append(f"- Sun: {data['western']['sun']['sign']} {data['western']['sun']['degree']}")
    lines.append(f"- Moon: {data['western']['moon']['sign']} {data['western']['moon']['degree']}")
    if data["western"]["ascendant"]:
        lines.append(f"- Ascendant: {data['western']['ascendant']['sign']} {data['western']['ascendant']['degree']}")
    if data["western"]["midheaven"]:
        lines.append(f"- Midheaven: {data['western']['midheaven']['sign']} {data['western']['midheaven']['degree']}")
    aspects = data["western"]["aspects"]
    lines.append("- Aspects: " + ("none" if not aspects else "; ".join(
        f"{item['a']}-{item['b']} {item['aspect']} {item['orb']}deg" for item in aspects
    )))
    lines += ["", "## Human Design"]
    lines.append(f"- Type: {data['humanDesign']['type']}")
    lines.append(f"- Authority: {data['humanDesign']['authority']}")
    lines.append(f"- Profile: {data['humanDesign']['profile']}")
    lines.append(f"- Defined centers: {', '.join(data['humanDesign']['definedCenters']) or 'none'}")
    lines.append(f"- Channels: {', '.join(data['humanDesign']['channels']) or 'none'}")
    lines.append("- Incarnation cross: " + "-".join(str(value) for value in data["humanDesign"]["incarnationCross"].values()))
    lines += ["", "> Astrological entertainment, not medical, financial or legal advice. "
              "Approximate ephemeris: solar terms ~15 min, lunar longitude ~0.2 deg, mean lunar node."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    birth = parse_input(args)
    try:
        chart = compute_all(birth)
    except Exception as error:  # noqa: BLE001 - report, never traceback at the user
        print(f"error: could not compute the chart: {error}", file=sys.stderr)
        return 2
    data = summarize(chart, birth)
    if args.md:
        print(md_report(data))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
