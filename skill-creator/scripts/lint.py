#!/usr/bin/env python3
"""Validate an Agent Skill directory against the Agent Skills specification.

Usage:
    python scripts/lint.py ../my-skill
    python scripts/lint.py ../my-skill --strict
    python scripts/lint.py ../my-skill --json
    python scripts/lint.py --list-codes

Exit codes:
    0  no errors (warnings allowed unless --strict)
    1  at least one error
    2  the path is not a skill directory / could not be read
"""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FM_RE = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", re.S)
REF_RE = re.compile(r"(?:references|scripts|assets)/[A-Za-z0-9._/\-]+")
LINK_RE = re.compile(r"\]\(\s*<?([^)\s>]+)>?\s*\)")
SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".idea"}

KNOWN_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}

CODES = {
    "E001": "SKILL.md is missing",
    "E002": "SKILL.md has no YAML frontmatter delimited by ---",
    "E003": "frontmatter has no non-empty `name`",
    "E004": "`name` is not lowercase alphanumeric with single hyphens",
    "E005": "`name` does not match the skill's directory name",
    "E006": "frontmatter has no non-empty `description`",
    "E007": "`description` exceeds 1024 characters",
    "E008": "`compatibility` exceeds 500 characters",
    "E009": "SKILL.md body is empty",
    "E010": "`name` exceeds 64 characters",
    "E011": "a Python script does not compile",
    "E012": "frontmatter is not a valid YAML mapping",
    "E013": "`compatibility` is not a string",
    "E014": "`metadata` is not a map",
    "E020": "a file referenced by the skill does not exist",
    "E021": "a bundled script fails to run",
    "E022": "SKILL.md has no `## When to use` section",
    "W001": "`description` is too short to trigger reliably",
    "W002": "`description` does not say when to use the skill",
    "W015": "`description` lists fewer than two trigger phrases",
    "W003": "SKILL.md is longer than the recommended 500 lines",
    "W004": "SKILL.md is above the recommended ~5000 tokens",
    "W006": "a bundled file is never referenced",
    "W007": "a metadata value is not a string",
    "W008": "allowed-tools should be space-separated",
    "W009": "a reference file is large enough to bloat context",
    "W010": "a reference is nested deeper than one level",
    "W011": "SKILL.md has no markdown headings",
    "W012": "frontmatter has a key the spec does not define",
    "W014": "`license` is not a string",
}


class Report:
    def __init__(self) -> None:
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def error(self, code: str, message: str) -> None:
        self.errors.append({"code": code, "message": message})

    def warn(self, code: str, message: str) -> None:
        self.warnings.append({"code": code, "message": message})

    @property
    def ok(self) -> bool:
        return not self.errors


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def split_frontmatter(text: str):
    match = FM_RE.match(text)
    if not match:
        return None, text
    return match.group(1), text[match.end():]


def _strip_comment(value: str) -> str:
    out: list[str] = []
    quote = None
    for i, ch in enumerate(value):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#" and (i == 0 or value[i - 1].isspace()):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        if value[0] == '"':
            return inner.replace('\\"', '"').replace("\\n", "\n")
        return inner.replace("''", "'")
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return []
        return [_scalar(part) for part in body.split(",") if part.strip()]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.lower() in ("null", "~"):
        return None
    return value


def _parse_nested(lines: list[str]):
    items = [line for line in lines if line.strip()]
    if not items:
        return ""
    if all(line.lstrip().startswith("- ") or line.strip() == "-" for line in items):
        return [_scalar(line.strip()[2:]) for line in items]
    if any(":" in line for line in items):
        mapping = {}
        for line in items:
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            mapping[key.strip()] = _scalar(_strip_comment(value))
        return mapping
    return " ".join(item.strip() for item in items)


def _parse_lite(raw: str):
    """Small YAML subset parser used when PyYAML is unavailable."""
    data = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent > 0 or ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = _strip_comment(rest).strip()
        if rest in ("", "|", "|-", "|+", ">", ">-", ">+"):
            style = rest[:1]
            block: list[str] = []
            base = None
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    block.append("")
                    i += 1
                    continue
                ind = len(nxt) - len(nxt.lstrip(" "))
                if ind == 0:
                    break
                if base is None:
                    base = ind
                block.append(nxt[base:] if ind >= base else nxt.strip())
                i += 1
            if style == "|":
                data[key] = "\n".join(block).rstrip("\n")
            elif style == ">":
                data[key] = " ".join(part.strip() for part in block if part.strip())
            else:
                data[key] = _parse_nested(block)
            continue
        data[key] = _scalar(rest)
        i += 1
    return data


def parse_frontmatter(raw: str):
    try:
        import yaml  # type: ignore
    except ImportError:
        return _parse_lite(raw), "builtin"
    data = yaml.safe_load(raw)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping of keys to values")
    return data, "pyyaml"


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def normalise_ref(ref: str) -> str:
    ref = ref.replace("\\", "/").strip()
    ref = ref.split("#", 1)[0]
    while ref.startswith("./"):
        ref = ref[2:]
    return ref.lstrip("/")


def lint_skill(root: Path, max_lines: int = 500, max_tokens: int = 5000):
    report = Report()
    stats = {"files": 0, "bytes": 0, "tokens": 0}
    skill_md = root / "SKILL.md"

    if not root.is_dir():
        report.error("E001", f"{root} is not a directory")
        return report, stats
    if not skill_md.is_file():
        report.error("E001", "SKILL.md is missing")
        return report, stats

    text = read_text(skill_md)
    raw_fm, body = split_frontmatter(text)
    if raw_fm is None:
        report.error("E002", "SKILL.md must start with YAML frontmatter delimited by ---")
        return report, stats

    try:
        data, _parser = parse_frontmatter(raw_fm)
    except Exception as exc:  # noqa: BLE001 - surface any YAML failure as E012
        report.error("E012", f"frontmatter is not valid YAML: {exc}")
        return report, stats
    if not isinstance(data, dict):
        report.error("E012", "frontmatter must be a mapping of keys to values")
        return report, stats

    for key in data:
        if key not in KNOWN_FIELDS:
            report.warn("W012", f"frontmatter key `{key}` is not defined by the spec")

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        report.error("E003", "frontmatter is missing a non-empty `name`")
    else:
        name = name.strip()
        if len(name) > 64:
            report.error("E010", f"`name` is {len(name)} characters (max 64)")
        if not NAME_RE.match(name):
            report.error(
                "E004",
                f"`name` {name!r} must be lowercase letters, digits and single hyphens",
            )
        if name != root.name:
            report.error("E005", f"`name` {name!r} must match directory {root.name!r}")

    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        report.error("E006", "frontmatter is missing a non-empty `description`")
        description = ""
    else:
        description = " ".join(description.split())
        if len(description) > 1024:
            report.error("E007", f"`description` is {len(description)} characters (max 1024)")
        if len(description) < 40:
            report.warn("W001", f"`description` is only {len(description)} characters; aim for 150+")
        if not re.search(r"\buse when\b|\buse this\b|\bwhen\b|ใช้เมื่อ|เมื่อ|for .* tasks", description, re.I):
            report.warn("W002", "`description` does not state when the skill should be used")
        triggers = re.findall(r"\"([^\"]{2,60})\"|“([^”]{2,60})”", description)
        if len(triggers) < 2:
            report.warn("W015", "`description` lists fewer than two quoted trigger phrases")

    compatibility = data.get("compatibility")
    if compatibility is not None:
        if not isinstance(compatibility, str):
            report.error("E013", "`compatibility` must be a string")
        elif len(compatibility) > 500:
            report.error("E008", f"`compatibility` is {len(compatibility)} characters (max 500)")

    license_value = data.get("license")
    if license_value is not None and not isinstance(license_value, str):
        report.warn("W014", "`license` should be a short string such as MIT or Apache-2.0")

    metadata = data.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            report.error("E014", "`metadata` must be a map of string keys to string values")
        else:
            for key, value in metadata.items():
                if not isinstance(value, str):
                    report.warn(
                        "W007",
                        f"metadata.{key} is {type(value).__name__}; quote it so it stays a string",
                    )

    allowed = data.get("allowed-tools")
    if isinstance(allowed, str) and "," in allowed:
        report.warn("W008", "allowed-tools is comma-separated; the spec expects a space-separated string")

    if len(body.strip()) < 50:
        report.error("E009", "SKILL.md body is empty or too short to instruct an agent")

    line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
    if line_count > max_lines:
        report.warn("W003", f"SKILL.md is {line_count} lines (recommended under {max_lines})")
    token_estimate = len(text) // 4
    if token_estimate > max_tokens:
        report.warn("W004", f"SKILL.md is about {token_estimate} tokens (recommended under {max_tokens})")
    if not re.search(r"^#{1,6}\s", body, re.M):
        report.warn("W011", "SKILL.md has no markdown headings")
    if not re.search(r"(?mi)^##\s+when to use\b", body):
        report.error("E022", "SKILL.md needs a `## When to use` section so activation is reviewable")

    files = list(iter_files(root))
    stats["files"] = len(files)
    stats["bytes"] = sum(path.stat().st_size for path in files)
    stats["tokens"] = sum(len(read_text(path)) // 4 for path in files if path.suffix.lower() in {".md", ".py", ".txt"})

    refs: set[str] = set()
    for source in [skill_md] + [p for p in files if p.suffix.lower() == ".md" and p != skill_md]:
        content = read_text(source)
        for match in REF_RE.finditer(content):
            refs.add(normalise_ref(match.group(0).rstrip(".,;:!?)'\"`")))
        for match in LINK_RE.finditer(content):
            target = match.group(1)
            if re.match(r"^(https?:|mailto:|tel:|#|data:)", target, re.I):
                continue
            refs.add(normalise_ref(target))

    body_text = text
    for ref in sorted(ref for ref in refs if ref):
        if ref.startswith("../"):
            report.error("E020", f"{ref} escapes the skill directory; use a path inside the skill")
            continue
        if not (root / ref).exists():
            report.error("E020", f"referenced file {ref} does not exist")
        parts = ref.split("/")
        if len(parts) > 2:
            report.warn("W010", f"{ref} is nested deeper than one level from SKILL.md")

    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel == "SKILL.md":
            continue
        if path.suffix.lower() == ".md":
            size = len(read_text(path))
            if size > 12000:
                report.warn("W009", f"{rel} is {size} characters; split it into focused files")
        if rel.startswith(("references/", "scripts/", "assets/")):
            if rel in refs or path.name in body_text:
                continue
            report.warn("W006", f"{rel} is bundled but never referenced from SKILL.md")

    for path in files:
        if path.suffix != ".py":
            continue
        rel = path.relative_to(root).as_posix()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                py_compile.compile(str(path), cfile=str(Path(tmp) / "check.pyc"), doraise=True)
            except py_compile.PyCompileError as exc:
                first = str(exc).splitlines()[0] if str(exc) else "syntax error"
                report.error("E011", f"{rel} does not compile: {first}")

    # A script that compiles can still be broken at runtime: run its --help.
    for path in files:
        if path.suffix != ".py" or path.parent.name != "scripts":
            continue
        rel = path.relative_to(root).as_posix()
        source = read_text(path)
        if "argparse" not in source and "ArgumentParser" not in source:
            continue
        try:
            completed = subprocess.run(
                [sys.executable, str(path), "--help"],
                cwd=str(root), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=25,
            )
        except Exception as exc:  # noqa: BLE001 - any failure means the script is unusable
            report.error("E021", f"{rel}: could not run --help ({exc})")
            continue
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip().splitlines()
            report.error(
                "E021",
                f"{rel}: --help exited {completed.returncode}"
                + (f": {detail[0][:160]}" if detail else ""),
            )

    return report, stats


def _enable_colour() -> bool:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
                return True
        except Exception:
            return False
    return True


def render(report: Report, root: Path, stats: dict, colour: bool) -> str:
    red = "\033[31m" if colour else ""
    yellow = "\033[33m" if colour else ""
    green = "\033[32m" if colour else ""
    dim = "\033[2m" if colour else ""
    reset = "\033[0m" if colour else ""

    lines = [f"{root.name}  {dim}({root}){reset}"]
    for item in report.errors:
        lines.append(f"  {red}ERROR{reset} {item['code']}  {item['message']}")
    for item in report.warnings:
        lines.append(f"  {yellow}WARN {reset} {item['code']}  {item['message']}")
    if not report.errors and not report.warnings:
        lines.append(f"  {green}clean{reset}")
    lines.append(
        f"  {stats.get('files', 0)} files, ~{stats.get('tokens', 0):,} tokens"
    )
    status = f"{green}PASS{reset}" if report.ok else f"{red}FAIL{reset}"
    lines.append(f"{status}: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return "\n".join(lines)


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Validate an Agent Skill directory against the Agent Skills spec.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", default=".", help="skill directory (default: .)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--quiet", action="store_true", help="only report failures")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    parser.add_argument("--max-lines", type=int, default=500, help="SKILL.md line budget")
    parser.add_argument("--max-tokens", type=int, default=5000, help="SKILL.md token budget")
    parser.add_argument("--list-codes", action="store_true", help="print diagnostic codes and exit")
    args = parser.parse_args(argv)

    if args.list_codes:
        for code, message in sorted(CODES.items()):
            print(f"{code}  {message}")
        return 0

    root = Path(args.path).resolve()
    if root.is_file() and root.name == "SKILL.md":
        root = root.parent
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    report, stats = lint_skill(root, max_lines=args.max_lines, max_tokens=args.max_tokens)
    if args.strict:
        report.errors.extend(report.warnings)
        report.warnings = []

    if args.json:
        payload = {
            "path": str(root),
            "ok": report.ok,
            "errors": report.errors,
            "warnings": report.warnings,
            "stats": stats,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if report.ok else 1

    if args.quiet and report.ok:
        return 0

    print(render(report, root, stats, _enable_colour() and not args.no_color))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
