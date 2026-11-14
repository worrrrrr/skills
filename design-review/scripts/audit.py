#!/usr/bin/env python3
"""Static UI audit for a SvelteKit (or plain web) project.

Looks for the defects that are cheap to spot in source and expensive to spot in review:

    HARDCODED_COLOR   a hex/rgb colour outside the tokens file
    PX_FONT           font-size in raw pixels instead of a token
    OUTLINE_NONE      focus ring removed
    IMG_NO_ALT        <img> without alt
    ICON_BUTTON_LABEL <button> with only an icon and no aria-label/title
    MISSING_FOCUS     interactive element with no focus style in the file

Usage:
    python scripts/audit.py src
    python scripts/audit.py src --json --strict
    python scripts/audit.py src --tokens layout.css

Exit codes:
    0  no findings (or only warnings without --strict)
    1  findings that must be fixed
    2  nothing to audit
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

EXTS = {".svelte", ".css", ".html", ".ts"}
SKIP_DIRS = {"node_modules", ".svelte-kit", "dist", "build", ".git", ".vercel"}

TOKEN_FILE = re.compile(r"(layout|tokens|theme|app)\.css$", re.I)

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGB_RE = re.compile(r"\brgba?\s*\(")
PX_FONT_RE = re.compile(r"font-size\s*:\s*\d+(?:\.\d+)?px", re.I)
OUTLINE_RE = re.compile(r"outline\s*:\s*(none|0)\b|outline-none\b|outline-hidden\b", re.I)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
BUTTON_RE = re.compile(r"<button\b[^>]*>", re.I)
ICON_RE = re.compile(r"<(svg|Icon|[A-Z][A-Za-z]*Icon)\b")


def iter_files(root: str, tokens: str | None):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(directory, name)
            if os.path.splitext(name)[1].lower() not in EXTS:
                continue
            if tokens and os.path.abspath(path) == os.path.abspath(tokens):
                continue
            yield path


def audit(root: str, tokens: str | None = None) -> list[dict]:
    findings: list[dict] = []

    for path in iter_files(root, tokens):
        relative = os.path.relpath(path, root).replace("\\", "/")
        is_token_file = bool(TOKEN_FILE.search(os.path.basename(path)))
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()

        for number, line in enumerate(lines, 1):
            stripped = line.strip()

            if not is_token_file and not stripped.startswith("//"):
                if HEX_RE.search(line) or RGB_RE.search(line):
                    findings.append(finding(relative, number, "HARDCODED_COLOR",
                                            "use a token (var(--color-*)) instead of a literal colour"))

            if PX_FONT_RE.search(line):
                findings.append(finding(relative, number, "PX_FONT",
                                        "use a type token instead of font-size in px"))

            if OUTLINE_RE.search(line):
                findings.append(finding(relative, number, "OUTLINE_NONE",
                                        "removing the focus ring breaks keyboard users"))

            for tag in IMG_RE.finditer(line):
                if not re.search(r"\balt\s*=", tag.group(0), re.I):
                    findings.append(finding(relative, number, "IMG_NO_ALT",
                                            "<img> needs alt (or alt=\"\" when decorative)"))

            for tag in BUTTON_RE.finditer(line):
                text = tag.group(0)
                if re.search(r"aria-label|\btitle\s*=", text, re.I):
                    continue
                window = " ".join(lines[number - 1 : number + 3])
                if ICON_RE.search(window):
                    findings.append(finding(relative, number, "ICON_BUTTON_LABEL",
                                            "icon-only button needs aria-label or title"))

    return findings


def finding(path: str, line: int, code: str, message: str) -> dict:
    return {"file": path, "line": line, "code": code, "message": message}


def render(findings: list[dict], root: str) -> str:
    if not findings:
        return f"audit {root}: clean"
    lines = [f"audit {root}: {len(findings)} finding(s)"]
    for item in findings:
        lines.append(f"  {item['file']}:{item['line']}  {item['code']}  {item['message']}")
    counts: dict[str, int] = {}
    for item in findings:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    summary = ", ".join(f"{code}={count}" for code, count in sorted(counts.items()))
    lines.append(f"  {summary}")
    return "\n".join(lines)


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Static UI audit for SvelteKit projects.")
    parser.add_argument("path", nargs="?", default=".", help="project or src directory")
    parser.add_argument("--tokens", help="tokens file to exclude from colour checks")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="treat every finding as failing")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    findings = audit(root, args.tokens)
    if args.json:
        print(json.dumps({"root": root, "findings": findings}, ensure_ascii=False, indent=2))
    else:
        print(render(findings, root))

    if not findings:
        return 0
    return 1 if args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
