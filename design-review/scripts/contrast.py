#!/usr/bin/env python3
"""WCAG contrast for the colours a design actually uses.

Accepts hex (#rgb, #rrggbb), rgb()/rgba(), and oklch(L C H) - the same syntax the
design tokens are written in - and prints the contrast ratio with a pass/fail verdict.

Usage:
    python scripts/contrast.py "#ffffff" "oklch(0.55 0.2 262)"
    python scripts/contrast.py --fg "#fff" --bg "#111" --json
    python scripts/contrast.py --pairs pairs.txt

Exit codes:
    0  every pair passes AA for normal text (4.5:1)
    1  at least one pair fails AA
    2  bad input
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys

HEX_RE = re.compile(r"^#([0-9a-f]{3,8})$", re.I)
RGB_RE = re.compile(r"^rgba?\(([^)]+)\)$", re.I)
OKLCH_RE = re.compile(
    r"^oklch\(\s*([0-9.]+%?)\s+([0-9.]+%?)\s+([0-9.]+)(?:deg)?\s*(?:/\s*[0-9.]+%?\s*)?\)$",
    re.I,
)


class ColorError(ValueError):
    pass


def _srgb_to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _parse_channel(token: str) -> float:
    token = token.strip()
    if token.endswith("%"):
        return float(token[:-1]) / 100.0
    return float(token)


def parse_color(text: str) -> tuple[float, float, float]:
    """Return linear-light sRGB in 0..1."""
    value = text.strip()

    match = HEX_RE.match(value)
    if match:
        digits = match.group(1)
        if len(digits) in (3, 4):
            digits = "".join(ch * 2 for ch in digits[:3])
        elif len(digits) in (6, 8):
            digits = digits[:6]
        else:
            raise ColorError(f"unsupported hex: {text}")
        srgb = [int(digits[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
        return tuple(_srgb_to_linear(ch) for ch in srgb)  # type: ignore[return-value]

    match = RGB_RE.match(value)
    if match:
        parts = [part for part in re.split(r"[,\s/]+", match.group(1).strip()) if part]
        if len(parts) < 3:
            raise ColorError(f"rgb() needs three channels: {text}")
        srgb = [_parse_channel(parts[i]) for i in range(3)]
        return tuple(_srgb_to_linear(max(0.0, min(1.0, ch))) for ch in srgb)  # type: ignore[return-value]

    match = OKLCH_RE.match(value)
    if match:
        lightness = _parse_channel(match.group(1))
        chroma = _parse_channel(match.group(2))
        hue = math.radians(float(match.group(3)))

        a = chroma * math.cos(hue)
        b = chroma * math.sin(hue)

        l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
        m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
        s_ = lightness - 0.0894841775 * a - 1.2914855480 * b

        l, m, s = l_**3, m_**3, s_**3

        linear = (
            4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
        )
        return tuple(max(0.0, min(1.0, ch)) for ch in linear)  # type: ignore[return-value]

    raise ColorError(f"unsupported colour: {text}")


def luminance(color: tuple[float, float, float]) -> float:
    r, g, b = color
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = luminance(parse_color(fg)), luminance(parse_color(bg))
    lighter, darker = max(a, b), min(a, b)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def verdict(ratio: float) -> str:
    if ratio >= 7:
        return "AAA"
    if ratio >= 4.5:
        return "AA"
    if ratio >= 3:
        return "AA-large"
    return "FAIL"


def check(fg: str, bg: str) -> dict:
    ratio = contrast_ratio(fg, bg)
    grade = verdict(ratio)
    return {
        "fg": fg,
        "bg": bg,
        "ratio": ratio,
        "verdict": grade,
        "passes_aa": ratio >= 4.5,
        "passes_aaa": ratio >= 7,
    }


def render(payload: dict) -> str:
    mark = "PASS" if payload["passes_aa"] else "FAIL"
    return (
        f"{mark}  {payload['fg']} on {payload['bg']}  "
        f"{payload['ratio']}:1  {payload['verdict']}"
    )


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="WCAG contrast for design tokens.")
    parser.add_argument("fg", nargs="?", help="foreground colour")
    parser.add_argument("bg", nargs="?", help="background colour")
    parser.add_argument("--fg", dest="fg_flag", help="foreground colour")
    parser.add_argument("--bg", dest="bg_flag", help="background colour")
    parser.add_argument("--pairs", help="file with one 'fg bg' pair per line")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    pairs: list[tuple[str, str]] = []
    if args.pairs:
        try:
            with open(args.pairs, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    pairs.append((parts[0], parts[1]))
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        fg = args.fg_flag or args.fg
        bg = args.bg_flag or args.bg
        if not fg or not bg:
            print("error: pass fg and bg, or --pairs FILE", file=sys.stderr)
            return 2
        pairs.append((fg, bg))

    results = []
    try:
        for fg, bg in pairs:
            results.append(check(fg, bg))
    except ColorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for payload in results:
            print(render(payload))

    return 0 if all(item["passes_aa"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
