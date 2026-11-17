#!/usr/bin/env python3
"""Self-tests for project-onboarding (stdlib only).

Run: python scripts/selftest.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bookdir  # noqa: E402
import scan  # noqa: E402

fails = []


def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)


check("modules import", hasattr(scan, "scan") and hasattr(bookdir, "resolve"))

check("slugify lowercases nothing but strips punctuation", bookdir.slugify("My Project") == "My-Project")
check("slugify empty falls back", bookdir.slugify("***") == "project")
check("slugify keeps dots", bookdir.slugify("v1.2 notes") == "v1.2-notes")

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "package.json").write_text(json.dumps({
        "name": "demo",
        "scripts": {"dev": "vite", "test": "vitest run"},
        "dependencies": {"svelte": "^5.0.0"},
    }), encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")

    data = scan.scan(root, 80, versions=False)
    check("scan finds the manifest", "package.json" in data["manifests"])
    check("scan reads npm scripts", data["commands"].get("npm", {}).get("dev") == "vite")
    check("scan reads the README", any("README.md" in doc for doc in data["docs"]))
    check("scan records node deps", "node" in data["deps"])
    check("scan keeps notes a list", isinstance(data["notes"], list))

    empty = root / "empty"
    empty.mkdir()
    blank = scan.scan(empty, 80, versions=False)
    check("scan survives an empty dir", blank["commands"] == {} and blank["manifests"] == [])

    books = root / "books"
    resolved = bookdir.resolve(root, override=str(books), flat=False, name="demo")
    check("resolve honours --dir", resolved["source"] == "--dir")
    check("resolve nests by project name", Path(resolved["book"]).parent.name == "demo")
    check("resolve points plan beside book", Path(resolved["plan"]).parent == Path(resolved["book"]).parent)
    flat = bookdir.resolve(root, override=str(books), flat=True, name="demo")
    check("resolve --flat drops the project folder", Path(flat["book"]) == books / "BOOK.md")

print()
print(f"{len(fails)} failure(s)" if fails else "all checks passed")
sys.exit(1 if fails else 0)
