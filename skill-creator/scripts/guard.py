#!/usr/bin/env python3
"""Repo guard - the strict gate for a skills collection.

Stdlib only. Python 3.11+.

`lint.py` checks one skill. This checks the collection: layout, catalog,
README index, trigger collisions, cross-skill references, duplicated rules,
and every bundled selftest. Run it at the repo root.

Usage
    python scripts/guard.py .                 # report
    python scripts/guard.py . --strict        # warnings fail too
    python scripts/guard.py . --json
    python scripts/guard.py . --no-selftest   # skip running selftests

Exit codes
    0 clean
    1 at least one ERROR (or WARN with --strict)
    2 root is not a skills collection or catalog is unreadable
    3 usage
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint  # noqa: E402  - same folder, one frontmatter parser

CATALOG = "catalog.json"
TIERS = ("core", "specialist", "product", "domain")
ALLOWED = {"SKILL.md", "references", "scripts", "assets"}
CAT_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CAT_FILE_RE = re.compile(r"^\s*[*+-]\s+\[?([a-z0-9-]+)\]?")
LINK_RE = re.compile(r"\]\(([^)/]+)/SKILL\.md\)")
QUOTED_RE = re.compile(r"[\"“]([^\"”]{2,60})[\"”]")
SCRIPT_RE = re.compile(r"`([A-Za-z0-9_.-]+\.(?:py|mjs))`")
SCAN_LANGS = {"js", "jsx", "ts", "tsx", "svelte", "css", "html"}
DEPRECATED = [
    (r"\bon:click\b", "Svelte 4 event directive; use onclick={fn}"),
    (r"\bexport let\b", "Svelte 4 prop declaration; use $props()"),
    (r"\$:\s", "Svelte 4 reactive label; use $derived"),
    (r"<slot\b", "Svelte 4 slot; use snippets with {@render}"),
    (r"@tailwind\b", "Tailwind 3 directive; use @import \"tailwindcss\""),
    (r"\bmaxTokens\b", "AI SDK 4 option; use maxOutputTokens"),
    (r"\bconvertToCoreMessages\b", "AI SDK 4 helper; use convertToModelMessages"),
    (r"\bgetServerSideProps\b", "Next.js pages router; use a server loader or component"),
    (r"\bReact\.FC\b", "legacy React typing; type the props directly"),
]
STOP = set("""a an and are as at be been but by can do does for from has have how if in into is it
its may must not of on or over so than that the their them then there these they this to use used
under up was were what when where which while who why will with without you your skill user agent
work using works run runs make made same one two first next before after""".split())


class GuardParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(3)


class Issue:
    def __init__(self, level, code, message, skill=None):
        self.level, self.code, self.message, self.skill = level, code, message, skill

    def __str__(self):
        where = f"{self.skill}: " if self.skill else ""
        return f"{self.level:5s} {self.code:16s} {where}{self.message}"

    def as_dict(self):
        return {"level": self.level, "code": self.code, "skill": self.skill, "message": self.message}


def load_skill(path):
    """(frontmatter, body) or (None, text) when the file cannot be parsed."""
    text = lint.read_text(path / "SKILL.md")
    raw, body = lint.split_frontmatter(text)
    if raw is None:
        return None, body
    try:
        front, _ = lint.parse_frontmatter(raw)
    except ValueError:
        return None, body
    return front if isinstance(front, dict) else None, body


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 2}


def norm_line(line):
    line = re.sub(r"[`*_#>|]+", " ", line.lower())
    line = re.sub(r"[^a-z0-9\u0e00-\u0e7f ]+", " ", line)
    return " ".join(line.split())


def code_lines(text):
    """Yield (line number, line) inside language-tagged fences only.

    Untagged fences hold sample output, not code, so they are never scanned.
    """
    lang = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*```(\S*)", line)
        if match:
            lang = None if lang else match.group(1).lower()
            continue
        if lang in SCAN_LANGS:
            yield number, line


class Guard:
    def __init__(self, root, run_selftests=True):
        self.root = Path(root).resolve()
        self.run_selftests = run_selftests
        self.issues = []
        self.skills = {}
        self.catalog = {}

    def add(self, level, code, message, skill=None):
        self.issues.append(Issue(level, code, message, skill))

    # ------------------------------------------------------------------ load
    def discover(self):
        for child in sorted(self.root.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file() and not child.name.startswith("."):
                front, body = load_skill(child)
                self.skills[child.name] = {"path": child, "front": front or {}, "body": body}
        if not self.skills:
            print(f"no skills found under {self.root}", file=sys.stderr)
            raise SystemExit(2)

    def load_catalog(self):
        path = self.root / CATALOG
        if not path.is_file():
            self.add("ERROR", "E_CATALOG", f"{CATALOG} is missing - the collection has no taxonomy")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.add("ERROR", "E_CATALOG", f"{CATALOG} cannot be read: {exc}")
            return
        if not isinstance(data, dict) or data.get("version") != 1:
            self.add("ERROR", "E_CATALOG", f"{CATALOG} must be an object with version 1")
            return
        if "skills" in data:
            self.add("ERROR", "E_CATALOG_SKILLS", f"{CATALOG} must not list skills; membership lives in SKILL.md")
        cats = data.get("categories")
        if not isinstance(cats, list) or not cats:
            self.add("ERROR", "E_CATALOG", f"{CATALOG} needs a non-empty categories list")
            return
        seen, orders = set(), set()
        for cat in cats:
            if not isinstance(cat, dict):
                self.add("ERROR", "E_CATALOG_SHAPE", "each category must be an object")
                continue
            cid, label, order = cat.get("id"), cat.get("label"), cat.get("order")
            if not isinstance(cid, str) or not CAT_ID_RE.match(cid):
                self.add("ERROR", "E_CATALOG_ID", f"category id {cid!r} must be kebab-case")
                continue
            if cid in seen:
                self.add("ERROR", "E_CATALOG_DUP", f"duplicate category id {cid}")
            seen.add(cid)
            if not isinstance(label, str) or not label.strip():
                self.add("ERROR", "E_CATALOG_LABEL", f"category {cid} needs a label")
            if not isinstance(order, int) or isinstance(order, bool):
                self.add("ERROR", "E_CATALOG_ORDER", f"category {cid} needs an integer order")
            elif order in orders:
                self.add("ERROR", "E_CATALOG_ORDER", f"duplicate category order {order}")
            else:
                orders.add(order)
        self.catalog = {c["id"]: c for c in cats if isinstance(c, dict) and "id" in c}

    # ----------------------------------------------------------------- checks
    def check_metadata(self):
        used = set()
        for name, info in self.skills.items():
            front = info["front"]
            meta = front.get("metadata") if isinstance(front, dict) else None
            if not isinstance(meta, dict):
                self.add("ERROR", "E_NO_META", "metadata map is missing; add metadata.category and tier", name)
                continue
            category, tier = meta.get("category"), meta.get("tier")
            if not isinstance(category, str) or not CAT_ID_RE.match(category):
                self.add("ERROR", "E_CATEGORY", "metadata.category must be a kebab-case id", name)
            elif self.catalog and category not in self.catalog:
                self.add("ERROR", "E_CATEGORY_UNKNOWN", f"category {category!r} is not in {CATALOG}", name)
            else:
                used.add(category)
            if tier not in TIERS:
                self.add("ERROR", "E_TIER", f"metadata.tier must be one of {', '.join(TIERS)}", name)
        for cid in set(self.catalog) - used:
            self.add("WARN", "W_UNUSED_CATEGORY", f"category {cid!r} has no skills")

    def check_layout(self):
        for name, info in self.skills.items():
            for entry in info["path"].iterdir():
                if entry.name in ALLOWED or entry.name.startswith("."):
                    continue
                kind = "directory" if entry.is_dir() else "file"
                self.add("ERROR", "E_STRAY", f"stray {kind} at skill root: {name}/{entry.name} "
                                             "(only SKILL.md, references/, scripts/, assets/)", name)

    def check_readme(self):
        path = self.root / "README.md"
        if not path.is_file():
            self.add("ERROR", "E_README", "README.md is missing")
            return
        listed = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            match = LINK_RE.search(line)
            if match:
                listed.add(match.group(1))
        missing = sorted(set(self.skills) - listed)
        extra = sorted(listed - set(self.skills))
        for name in missing:
            self.add("ERROR", "E_README_ROW", "skill has no row in the README table", name)
        for name in extra:
            self.add("ERROR", "E_README_ROW", f"README links {name}/SKILL.md but no such skill exists")

    def check_triggers(self):
        seen = {}
        for name, info in self.skills.items():
            desc = info["front"].get("description") if isinstance(info["front"], dict) else ""
            for phrase in QUOTED_RE.findall(desc if isinstance(desc, str) else ""):
                key = norm_line(phrase)
                if not key:
                    continue
                if key in seen and seen[key] != name:
                    self.add("ERROR", "E_TRIGGER", f"trigger {phrase!r} is also claimed by {seen[key]}", name)
                seen.setdefault(key, name)

    def check_description_overlap(self):
        sets = {}
        for name, info in self.skills.items():
            desc = info["front"].get("description") if isinstance(info["front"], dict) else ""
            sets[name] = words(desc if isinstance(desc, str) else "")
        names = sorted(sets)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if not sets[a] or not sets[b]:
                    continue
                jac = len(sets[a] & sets[b]) / len(sets[a] | sets[b])
                if jac >= 0.30:
                    self.add("WARN", "W_DESC_OVERLAP", f"description overlap {jac:.0%} with {b}; "
                                                       "tighten the trigger words", a)

    def check_cross_refs(self):
        owners = {}
        for name, info in self.skills.items():
            scripts = info["path"] / "scripts"
            if scripts.is_dir():
                for item in scripts.iterdir():
                    if item.is_file() and item.suffix in {".py", ".mjs"}:
                        owners.setdefault(item.name, set()).add(name)
        for name, info in self.skills.items():
            local = {p.name for p in (info["path"] / "scripts").iterdir()} if (info["path"] / "scripts").is_dir() else set()
            for token in SCRIPT_RE.findall(info["body"]):
                if "/" in token or token in local:
                    continue
                peer = owners.get(token, set()) - {name}
                if len(peer) == 1:
                    other = next(iter(peer))
                    self.add("ERROR", "E_CROSS_REF", f"`{token}` is not in this skill; it lives in {other}. "
                                                     f"Write `{other}/scripts/{token}` or inline the command", name)

    def check_duplicate_rules(self):
        seen = {}
        for name, info in self.skills.items():
            for line in info["body"].splitlines():
                key = norm_line(line)
                if len(key.split()) < 10 or key.startswith(("http", "python ", "git ")):
                    continue
                if key in seen and seen[key] != name:
                    self.add("WARN", "W_DUP_RULE", f"same sentence also in {seen[key]}: "
                                                   f"{key[:70]}...", name)
                seen.setdefault(key, name)

    def check_deprecated(self):
        """Only language-tagged fences are code; untagged fences are sample output."""
        for name, info in self.skills.items():
            paths = [info["path"] / "SKILL.md"]
            refs = info["path"] / "references"
            if refs.is_dir():
                paths += sorted(refs.glob("*.md"))
            for path in paths:
                for number, line in code_lines(lint.read_text(path)):
                    for pattern, message in DEPRECATED:
                        if re.search(pattern, line):
                            rel = path.relative_to(self.root).as_posix()
                            self.add("ERROR", "E_DEPRECATED", f"{rel}:{number} {message}", name)

    def check_selftests(self):
        if not self.run_selftests:
            return
        for name, info in self.skills.items():
            path = info["path"] / "scripts" / "selftest.py"
            if not path.is_file():
                self.add("WARN", "W_NO_SELFTEST", "scripts/selftest.py is missing", name)
                continue
            try:
                proc = subprocess.run([sys.executable, str(path)], cwd=str(info["path"]),
                                      capture_output=True, text=True, timeout=90)
            except subprocess.TimeoutExpired:
                self.add("ERROR", "E_SELFTEST", "selftest timed out after 90s", name)
                continue
            if proc.returncode != 0:
                tail = [l for l in (proc.stderr or proc.stdout).splitlines() if l.strip()]
                self.add("ERROR", "E_SELFTEST", f"selftest exited {proc.returncode}: "
                                               f"{tail[-1][:160] if tail else 'no output'}", name)

    def run(self):
        self.discover()
        self.load_catalog()
        self.check_metadata()
        self.check_layout()
        self.check_readme()
        self.check_triggers()
        self.check_description_overlap()
        self.check_cross_refs()
        self.check_deprecated()
        self.check_duplicate_rules()
        self.check_selftests()
        return self.issues


def main(argv=None):
    parser = GuardParser(prog="guard.py", description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=".", help="skills collection root")
    parser.add_argument("--strict", action="store_true", help="warnings fail too")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-selftest", action="store_true", help="skip running skill selftests")
    args = parser.parse_args(argv)

    guard = Guard(args.root, run_selftests=not args.no_selftest)
    issues = guard.run()
    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARN"]
    if args.json:
        print(json.dumps({"root": str(guard.root), "skills": len(guard.skills),
                          "issues": [i.as_dict() for i in issues]}, indent=2, ensure_ascii=False))
    else:
        for issue in issues:
            print(issue)
        print(f"\n{len(guard.skills)} skills, {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
