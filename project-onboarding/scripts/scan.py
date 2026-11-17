#!/usr/bin/env python3
"""Scan a project for the facts a session needs before it starts working.

Reports the layout, docs, manifests, project-defined commands, pins, toolchain
versions and declared/installed dependency versions. Read-only: it never writes
or installs anything.

Exit codes: 0 ok, 2 path is missing or not a directory, 3 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover - reported through notes
    tomllib = None  # type: ignore[assignment]

NOISE = {
    ".git", ".hg", ".svn", "node_modules", "vendor", ".venv", "venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".next", ".nuxt",
    ".svelte-kit", "dist", "build", "out", "target", "coverage", ".turbo",
    ".cache", ".parcel-cache", ".idea", ".vscode", ".app-locked", ".DS_Store",
}

MANIFESTS = [
    "package.json", "pyproject.toml", "requirements.txt", "setup.py", "Pipfile",
    "go.mod", "Cargo.toml", "composer.json", "Gemfile", "pom.xml",
    "build.gradle", "build.gradle.kts", "Makefile", "Taskfile.yml",
    "justfile", "docker-compose.yml", "compose.yaml", "Dockerfile", ".env.example",
]

LOCKFILES = [
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock",
    "uv.lock", "poetry.lock", "Pipfile.lock", "go.sum", "Cargo.lock",
    "composer.lock", "Gemfile.lock", "gradle.lockfile",
]

DOCS = [
    "AGENTS.md", "CLAUDE.md", ".cursor/rules", "CONTRIBUTING.md",
    "ARCHITECTURE.md", "CHANGELOG.md", "LICENSE", "LICENSE.md", "docs",
]

CI = [
    ".github/workflows", ".gitlab-ci.yml", "azure-pipelines.yml",
    ".circleci/config.yml", "Jenkinsfile", "bitbucket-pipelines.yml",
]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def run(cmd: list[str], cwd: Path, timeout: int = 8) -> str:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def version_of(exe: str, flag: str, cwd: Path) -> str | None:
    path = shutil.which(exe)
    if not path:
        return None
    line = first_line(run([path, flag], cwd))
    return line or None


def git_out(root: Path, *args: str) -> str:
    if not shutil.which("git"):
        return ""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def git_info(root: Path) -> dict:
    commit = first_line(git_out(root, "rev-parse", "--short", "HEAD"))
    if not commit:
        return {}
    branch = first_line(git_out(root, "branch", "--show-current"))
    status = git_out(root, "status", "--porcelain")
    changed = len([line for line in status.splitlines() if line.strip()])
    return {"branch": branch, "commit": commit, "changed": changed}


def top_level(root: Path, limit: int) -> list[str]:
    entries: list[str] = []
    try:
        children = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return entries
    for child in children:
        if child.name in NOISE:
            continue
        entries.append(child.name + ("/" if child.is_dir() else ""))
    if len(entries) > limit:
        extra = len(entries) - limit
        entries = entries[:limit] + [f"+{extra} more"]
    return entries


def existing(root: Path, names: list[str]) -> list[str]:
    found = []
    for name in names:
        target = root / name
        if target.exists():
            found.append(name + ("/" if target.is_dir() else ""))
    return found


def readme(root: Path) -> list[str]:
    return sorted(p.name for p in root.glob("README*") if p.is_file())


def load_json(path: Path, notes: list[str]) -> dict:
    try:
        return json.loads(read(path))
    except (json.JSONDecodeError, ValueError):
        notes.append(f"{path.name} is not valid JSON")
        return {}


def load_toml(path: Path, notes: list[str]) -> dict:
    if tomllib is None:
        notes.append("tomllib unavailable; python 3.11+ needed to read TOML")
        return {}
    try:
        return tomllib.loads(read(path))
    except Exception:  # noqa: BLE001 - malformed TOML is reported, not fatal
        notes.append(f"{path.name} is not valid TOML")
        return {}


def makefile_targets(path: Path, limit: int) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in read(path).splitlines():
        match = re.match(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):(?!=)", line)
        if not match:
            continue
        name = match.group(1)
        if name in out or name.startswith("."):
            continue
        out[name] = f"make {name}"
        if len(out) >= limit:
            break
    return out


def yaml_tasks(path: Path, limit: int) -> dict[str, str]:
    out: dict[str, str] = {}
    in_tasks = False
    for line in read(path).splitlines():
        if re.match(r"^tasks:\s*$", line):
            in_tasks = True
            continue
        if in_tasks and line and not line.startswith(" "):
            break
        if not in_tasks:
            continue
        match = re.match(r"^ {2}([A-Za-z0-9_.-]+):\s*$", line)
        if match:
            out[match.group(1)] = f"task {match.group(1)}"
        if len(out) >= limit:
            break
    return out


def just_targets(path: Path, limit: int) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in read(path).splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+)(?:\s+[^:]+)?:\s*(?:#.*)?$", line)
        if not match or line.lstrip().startswith(("@", "#", "=", "[")):
            continue
        name = match.group(1)
        if name in out or name == "set":
            continue
        out[name] = f"just {name}"
        if len(out) >= limit:
            break
    return out


def commands(root: Path, notes: list[str], limit: int) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    pkg = root / "package.json"
    if pkg.exists():
        data = load_json(pkg, notes)
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        if scripts:
            found["npm"] = {str(k): str(v) for k, v in list(scripts.items())[:limit]}
    py = root / "pyproject.toml"
    if py.exists():
        data = load_toml(py, notes)
        scripts = data.get("project", {}).get("scripts", {})
        if isinstance(scripts, dict) and scripts:
            found["pyproject"] = {str(k): f"python -m {k}" for k in list(scripts)[:limit]}
    for name, parser in (("Makefile", makefile_targets), ("Taskfile.yml", yaml_tasks), ("justfile", just_targets)):
        target = root / name
        if target.exists():
            parsed = parser(target, limit)
            if parsed:
                found[name] = parsed
    composer = root / "composer.json"
    if composer.exists():
        data = load_json(composer, notes)
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        if scripts:
            found["composer"] = {str(k): f"composer {k}" for k in list(scripts)[:limit]}
    return found


def node_pm(root: Path, pkg: dict) -> str:
    declared = str(pkg.get("packageManager") or "")
    for name in ("pnpm", "yarn", "bun", "npm"):
        if declared.startswith(name + "@"):
            return name
    for lock, name in (
        ("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"), ("bun.lock", "bun"), ("package-lock.json", "npm"),
    ):
        if (root / lock).exists():
            return name
    return "npm"


def pins(root: Path, pkg: dict, pyproject: dict, notes: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    if pkg.get("packageManager"):
        out["packageManager"] = str(pkg["packageManager"])
    engines = pkg.get("engines") if isinstance(pkg.get("engines"), dict) else {}
    for key, value in engines.items():
        out[f"engines.{key}"] = str(value)
    for name in (".nvmrc", ".node-version", ".python-version"):
        target = root / name
        if target.exists():
            out[name] = first_line(read(target))
    tool_versions = root / ".tool-versions"
    if tool_versions.exists():
        out[".tool-versions"] = " ".join(read(tool_versions).split())
    required = pyproject.get("project", {}).get("requires-python")
    if required:
        out["requires-python"] = str(required)
    rust = root / "rust-toolchain.toml"
    if rust.exists():
        channel = load_toml(rust, notes).get("toolchain", {}).get("channel")
        if channel:
            out["rust-toolchain"] = str(channel)
    elif (root / "rust-toolchain").exists():
        out["rust-toolchain"] = first_line(read(root / "rust-toolchain"))
    go = root / "go.mod"
    if go.exists():
        for line in read(go).splitlines():
            if line.startswith("go "):
                out["go"] = line.strip()
                break
    return out


def node_deps(root: Path, pkg: dict, notes: list[str], limit: int) -> dict:
    result: dict[str, list[dict]] = {}
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        table = pkg.get(section)
        if not isinstance(table, dict):
            continue
        rows = []
        for name, spec in list(table.items())[:limit]:
            row = {"name": name, "range": str(spec), "installed": None}
            installed = root / "node_modules" / name / "package.json"
            if installed.exists():
                row["installed"] = load_json(installed, []).get("version")
            rows.append(row)
        if rows:
            result[section] = rows
    if result and not (root / "node_modules").is_dir():
        notes.append("node_modules absent; installed node versions unknown")
    return result


def python_deps(root: Path, pyproject: dict, notes: list[str], limit: int) -> list[str]:
    declared: list[str] = []
    project = pyproject.get("project", {})
    deps = project.get("dependencies", [])
    if isinstance(deps, list):
        declared.extend(str(item) for item in deps[:limit])
    groups = project.get("optional-dependencies", {})
    if isinstance(groups, dict):
        for name, items in list(groups.items())[:5]:
            if isinstance(items, list):
                declared.append(f"[{name}] " + ", ".join(str(i) for i in items[:10]))
    req = root / "requirements.txt"
    if req.exists():
        for line in read(req).splitlines():
            clean = line.split("#", 1)[0].strip()
            if clean and not clean.startswith(("-", "git+", "http")):
                declared.append(clean)
            if len(declared) >= limit:
                break
    if declared:
        notes.append("python installed versions: run 'python -m pip show <name>' in the project environment")
    return declared


def go_deps(root: Path, limit: int) -> list[str]:
    out: list[str] = []
    in_block = False
    for line in read(root / "go.mod").splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_block = True
            continue
        if in_block and stripped == ")":
            in_block = False
            continue
        if in_block and stripped:
            out.append(stripped)
        elif stripped.startswith("require "):
            out.append(stripped[len("require "):].strip())
        if len(out) >= limit:
            break
    return out


def cargo_deps(root: Path, notes: list[str], limit: int) -> list[str]:
    data = load_toml(root / "Cargo.toml", notes)
    out: list[str] = []
    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
        table = data.get(section, {})
        if isinstance(table, dict):
            for name, spec in list(table.items())[:limit]:
                version = spec.get("version") if isinstance(spec, dict) else spec
                out.append(f"{name} {version}" if version else str(name))
    return out[:limit]


def ecosystem_files(root: Path) -> set[str]:
    found = set()
    checks = {
        "node": ["package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"],
        "python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "uv.lock", "poetry.lock"],
        "go": ["go.mod"],
        "rust": ["Cargo.toml"],
        "php": ["composer.json"],
        "ruby": ["Gemfile"],
        "java": ["pom.xml", "build.gradle", "build.gradle.kts", "gradlew"],
    }
    for eco, names in checks.items():
        if any((root / name).exists() for name in names):
            found.add(eco)
    if any(root.glob("*.csproj")) or any(root.glob("*.sln")):
        found.add("dotnet")
    return found


def toolchain(root: Path, pkg: dict, ecosystems: set[str], enabled: bool) -> dict[str, str]:
    if not enabled:
        return {}
    out: dict[str, str] = {}
    candidates: list[tuple[str, str, str]] = [("git", "git", "--version")]
    if "node" in ecosystems:
        candidates.append(("node", "node", "--version"))
        pm = node_pm(root, pkg)
        candidates.append((pm, pm, "--version"))
    if "python" in ecosystems:
        candidates.append(("python", "python", "--version"))
    if "go" in ecosystems:
        candidates.append(("go", "go", "version"))
    if "rust" in ecosystems:
        candidates.extend([("rustc", "rustc", "--version"), ("cargo", "cargo", "--version")])
    if "java" in ecosystems:
        candidates.append(("java", "java", "-version"))
    if "dotnet" in ecosystems:
        candidates.append(("dotnet", "dotnet", "--version"))
    if "php" in ecosystems:
        candidates.append(("php", "php", "--version"))
    if "ruby" in ecosystems:
        candidates.append(("ruby", "ruby", "--version"))
    for label, exe, flag in candidates:
        version = version_of(exe, flag, root)
        if version:
            out[label] = version
        elif label == "python":
            out[label] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} (running interpreter)"
    return out


def scan(root: Path, limit: int, versions: bool) -> dict:
    notes: list[str] = []
    pkg_path = root / "package.json"
    pkg = load_json(pkg_path, notes) if pkg_path.exists() else {}
    py_path = root / "pyproject.toml"
    pyproject = load_toml(py_path, notes) if py_path.exists() else {}
    ecosystems = ecosystem_files(root)

    docs = existing(root, DOCS) + [name for name in readme(root) if name not in DOCS]
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        docs.append("docs/: " + ", ".join(sorted(p.name for p in docs_dir.iterdir() if p.is_file())[:10]))
    ci: list[str] = []
    for name in CI:
        target = root / name
        if target.is_dir():
            ci.extend(f"{name}/{p.name}" for p in sorted(target.iterdir()) if p.is_file())
        elif target.is_file():
            ci.append(name)

    deps: dict[str, object] = {}
    node = node_deps(root, pkg, notes, limit)
    if node:
        deps["node"] = node
    python = python_deps(root, pyproject, notes, limit)
    if python:
        deps["python"] = python
    if (root / "go.mod").exists():
        deps["go"] = go_deps(root, limit)
    if (root / "Cargo.toml").exists():
        deps["rust"] = cargo_deps(root, notes, limit)

    return {
        "root": str(root),
        "git": git_info(root),
        "top": top_level(root, limit),
        "docs": docs,
        "manifests": existing(root, MANIFESTS),
        "lockfiles": existing(root, LOCKFILES),
        "ci": ci,
        "ecosystems": sorted(ecosystems),
        "commands": commands(root, notes, limit),
        "pins": pins(root, pkg, pyproject, notes),
        "tools": toolchain(root, pkg, ecosystems, versions),
        "deps": deps,
        "notes": notes,
    }


def render(data: dict) -> str:
    def trim_tool(name: str, value: str) -> str:
        prefix = f"{name.lower()} version "
        return value[len(prefix):] if value.lower().startswith(prefix) else value

    lines: list[str] = []
    lines.append(f"workspace  {data['root']}")
    git = data.get("git") or {}
    if git:
        dirty = f", {git['changed']} changed" if git.get("changed") else ", clean"
        lines.append(f"git        {git.get('branch') or '(detached)'} @ {git['commit']}{dirty}")
    lines.append(f"top        {' '.join(data['top']) or '(empty)'}")
    lines.append(f"docs       {' '.join(data['docs']) or 'none'}")
    lines.append(f"manifests  {' '.join(data['manifests']) or 'none'}")
    lines.append(f"lockfiles  {' '.join(data['lockfiles']) or 'none'}")
    if data["ci"]:
        lines.append(f"ci         {' '.join(data['ci'])}")
    if data["commands"]:
        for source, table in data["commands"].items():
            names = ", ".join(sorted(table))
            lines.append(f"commands   {source}: {names}")
    else:
        lines.append("commands   none declared - do not invent one")
    if data["pins"]:
        pairs = "  ".join(f"{k}={v}" for k, v in data["pins"].items())
        lines.append(f"pins       {pairs}")
    if data["tools"]:
        pairs = " | ".join(f"{name} {trim_tool(name, value)}" for name, value in data["tools"].items())
        lines.append(f"tools      {pairs}")

    deps = data["deps"]
    if "node" in deps:
        for section, rows in deps["node"].items():
            lines.append(f"deps node  {section}: {len(rows)}")
            for row in rows:
                installed = row["installed"] or "not installed"
                lines.append(f"           {row['name']} {installed} (range {row['range']})")
    for eco in ("python", "go", "rust"):
        rows = deps.get(eco)
        if not rows:
            continue
        lines.append(f"deps {eco:<6} {len(rows)} declared")
        for row in rows:
            lines.append(f"           {row}")
    for note in data["notes"]:
        lines.append(f"note       {note}")
    return "\n".join(lines)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # exit 3 on usage errors
        self.print_usage(sys.stderr)
        self.exit(3, f"{self.prog}: error: {message}\n")


def main(argv: list[str] | None = None) -> int:
    parser = Parser(
        prog="scan.py",
        description="Print workspace, docs, commands, pins, toolchain and dependency facts for a project.",
    )
    parser.add_argument("path", nargs="?", default=".", help="project root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--no-versions", action="store_true", help="skip toolchain subprocess checks")
    parser.add_argument("--limit", type=int, default=80, help="max rows per list (default: 80)")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"scan.py: not a directory: {root}", file=sys.stderr)
        return 2
    try:
        root = root.resolve()
    except OSError:
        pass

    data = scan(root, max(5, args.limit), not args.no_versions)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(render(data))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
