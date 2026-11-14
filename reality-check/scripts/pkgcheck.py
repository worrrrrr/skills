#!/usr/bin/env python3
"""Check whether a package, version or URL actually exists, before claiming it does.

Subcommands:
    pkgcheck.py npm      <name> [--version <v>]
    pkgcheck.py pypi     <name> [--version <v>]
    pkgcheck.py crates   <name> [--version <v>]
    pkgcheck.py nuget    <name> [--version <v>]
    pkgcheck.py gem      <name> [--version <v>]
    pkgcheck.py go       <module> [--version <v>]
    pkgcheck.py github   <owner/repo>
    pkgcheck.py url      <https://...>
    pkgcheck.py installed python <module>
    pkgcheck.py installed node   <package> [--cwd <dir>]
    pkgcheck.py inspect   node   <package> [--cwd <dir>] [--no-network]
    pkgcheck.py inspect   python <module>
    pkgcheck.py project   <dir|package.json> [--state [file]] [--rules]
    pkgcheck.py scan      <dir>                     # old-style code in the repo
    pkgcheck.py docs      <pkg> --symbol <name>     # the exact shipped signature
    pkgcheck.py docs      <pkg> --readme <heading>  # a README section

Options:
    --json        machine-readable output
    --timeout N   per-request timeout in seconds (default 12)
    --no-network  inspect only what is on disk

Exit codes:
    0  exists (and the requested version exists)
    1  does not exist / version not published / not installed
    2  network or registry error - treat the claim as unverified, not false
    3  usage error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "reality-check/1.0 (package existence check; +https://agentskills.io)"
TIMEOUT = 12


class NotFound(Exception):
    pass


class Unreachable(Exception):
    pass


def http_json(url: str, timeout: float = TIMEOUT) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NotFound(f"404 from {url}") from exc
        raise Unreachable(f"HTTP {exc.code} from {url}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise Unreachable(f"{type(exc).__name__}: {exc}") from exc


def clean_range(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    value = re.sub(r"^[\^~><=v\s]+", "", value)
    return value or None


def version_present(versions, wanted: str) -> bool:
    if wanted in versions:
        return True
    wanted_core = wanted.split("-")[0]
    return any(v == wanted or v.split("-")[0] == wanted_core for v in versions)


def result(ecosystem, name, exists, **extra):
    payload = {"ecosystem": ecosystem, "name": name, "exists": exists}
    payload.update(extra)
    return payload


def check_npm(name, wanted, timeout):
    url = "https://registry.npmjs.org/" + urllib.parse.quote(name, safe="")
    data = http_json(url, timeout)
    versions = sorted(data.get("versions", {}))
    latest = (data.get("dist-tags") or {}).get("latest")
    deprecated = None
    target = wanted or latest
    if target and target in data.get("versions", {}):
        deprecated = data["versions"][target].get("deprecated")
    if wanted and not version_present(versions, wanted):
        return result("npm", name, False, latest=latest, requested=wanted,
                      error="version not published", versions_count=len(versions), url=url), 1
    return result(
        "npm", name, True, latest=latest, requested=wanted, deprecated=bool(deprecated),
        deprecation_note=deprecated if isinstance(deprecated, str) else None,
        license=(data.get("license") if isinstance(data.get("license"), str) else None),
        updated=((data.get("time") or {}).get("modified")),
        versions_count=len(versions), url=url,
    ), 0


def check_pypi(name, wanted, timeout):
    url = f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json"
    data = http_json(url, timeout)
    info = data.get("info", {})
    releases = data.get("releases", {})
    versions = sorted(releases)
    latest = info.get("version")
    target = wanted or latest
    yanked = bool(target and releases.get(target) and all(r.get("yanked") for r in releases[target]))
    if wanted and not version_present(versions, wanted):
        return result("pypi", name, False, latest=latest, requested=wanted,
                      error="version not published", versions_count=len(versions), url=url), 1
    return result(
        "pypi", name, True, latest=latest, requested=wanted, yanked=yanked,
        requires_python=info.get("requires_python"),
        license=(info.get("license") or None),
        summary=(info.get("summary") or None),
        versions_count=len(versions), url=url,
    ), 0


def check_crates(name, wanted, timeout):
    url = f"https://crates.io/api/v1/crates/{urllib.parse.quote(name)}"
    data = http_json(url, timeout)
    crate = data.get("crate", {})
    versions = [v.get("num") for v in data.get("versions", []) if v.get("num")]
    latest = crate.get("max_version") or (versions[0] if versions else None)
    if wanted and not version_present(versions, wanted):
        return result("crates", name, False, latest=latest, requested=wanted,
                      error="version not published", versions_count=len(versions), url=url), 1
    return result("crates", name, True, latest=latest, requested=wanted,
                  updated=crate.get("updated_at"), downloads=crate.get("downloads"),
                  versions_count=len(versions), url=url), 0


def check_nuget(name, wanted, timeout):
    url = f"https://api.nuget.org/v3-flatcontainer/{urllib.parse.quote(name.lower())}/index.json"
    data = http_json(url, timeout)
    versions = data.get("versions", [])
    latest = versions[-1] if versions else None
    if wanted and not version_present(versions, wanted):
        return result("nuget", name, False, latest=latest, requested=wanted,
                      error="version not published", versions_count=len(versions), url=url), 1
    return result("nuget", name, True, latest=latest, requested=wanted,
                  versions_count=len(versions), url=url), 0


def check_gem(name, wanted, timeout):
    url = f"https://rubygems.org/api/v1/gems/{urllib.parse.quote(name)}.json"
    data = http_json(url, timeout)
    latest = data.get("version")
    if wanted and wanted != latest:
        versions_url = f"https://rubygems.org/api/v1/versions/{urllib.parse.quote(name)}.json"
        versions = [v.get("number") for v in http_json(versions_url, timeout)]
        if not version_present(versions, wanted):
            return result("gem", name, False, latest=latest, requested=wanted,
                          error="version not published", versions_count=len(versions), url=url), 1
    return result("gem", name, True, latest=latest, requested=wanted,
                  updated=data.get("version_created_at"), url=url), 0


def check_go(module, wanted, timeout):
    url = f"https://proxy.golang.org/{urllib.parse.quote(module, safe='/')}/@v/list"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NotFound("module not found in the Go proxy") from exc
        raise Unreachable(f"HTTP {exc.code} from {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Unreachable(f"{type(exc).__name__}: {exc}") from exc
    versions = [line.strip() for line in text.splitlines() if line.strip()]
    if wanted and not version_present(versions, wanted):
        return result("go", module, False, latest=(versions[-1] if versions else None),
                      requested=wanted, error="version not published",
                      versions_count=len(versions), url=url), 1
    return result("go", module, True, latest=(versions[-1] if versions else None),
                  requested=wanted, versions_count=len(versions), url=url), 0


def check_github(repo, timeout):
    url = f"https://api.github.com/repos/{repo}"
    data = http_json(url, timeout)
    return result("github", repo, True,
                  archived=bool(data.get("archived")),
                  stars=data.get("stargazers_count"),
                  license=((data.get("license") or {}).get("spdx_id")),
                  pushed_at=data.get("pushed_at"),
                  default_branch=data.get("default_branch"),
                  url=data.get("html_url")), 0


def check_url(target, timeout):
    if not re.match(r"^https?://", target, re.I):
        raise ValueError("url must start with http:// or https://")
    request = urllib.request.Request(target, headers={"User-Agent": UA}, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return result("url", target, True, status=response.status,
                          content_type=response.headers.get("content-type"), url=target), 0
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 405, 501):
            request = urllib.request.Request(
                target, headers={"User-Agent": UA, "Range": "bytes=0-0"}, method="GET"
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return result("url", target, True, status=response.status,
                                  content_type=response.headers.get("content-type"), url=target), 0
            except urllib.error.HTTPError as inner:
                if inner.code in (404, 410):
                    return result("url", target, False, status=inner.code, url=target), 1
                raise Unreachable(f"HTTP {inner.code} from {target}") from inner
        if exc.code in (404, 410):
            return result("url", target, False, status=exc.code, url=target), 1
        raise Unreachable(f"HTTP {exc.code} from {target}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Unreachable(f"{type(exc).__name__}: {exc}") from exc


def check_installed(kind, name, cwd):
    if kind == "python":
        from importlib import metadata

        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            return result("installed-python", name, False,
                          error="no installed distribution by that name (stdlib modules are not distributions)",
                          interpreter=sys.executable), 1
        return result("installed-python", name, True, version=version,
                      interpreter=sys.executable), 0
    if kind == "node":
        start = os.path.abspath(cwd)
        while True:
            manifest = os.path.join(start, "node_modules", *name.split("/"), "package.json")
            if os.path.isfile(manifest):
                try:
                    with open(manifest, encoding="utf-8") as handle:
                        data = json.load(handle)
                except (OSError, json.JSONDecodeError):
                    data = {}
                return result("installed-node", name, True,
                              version=data.get("version"), path=manifest), 0
            parent = os.path.dirname(start)
            if parent == start:
                break
            start = parent
        return result("installed-node", name, False,
                      error="no node_modules entry found up from the working directory"), 1
    raise ValueError(f"unknown install ecosystem {kind!r} (use python or node)")


CHECKS = {
    "npm": check_npm,
    "pypi": check_pypi,
    "crates": check_crates,
    "nuget": check_nuget,
    "gem": check_gem,
    "go": check_go,
}

SYMBOL_PATTERNS = [
    r"export\s+(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)",
    r"export\s+(?:declare\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)",
    r"export\s+(?:declare\s+)?(?:const|let|var|enum)\s+([A-Za-z_$][\w$]*)",
    r"export\s+(?:declare\s+)?(?:type|interface)\s+([A-Za-z_$][\w$]*)",
]
EXPORT_LIST_RE = re.compile(r"export\s*\{([^}]*)\}")
CHANGELOG_RE = re.compile(r"(?m)^#{1,3}\s*\[?v?(\d+\.\d+\.\d+[^\]\s]*)")


def find_node_package(name, cwd):
    start = os.path.abspath(cwd)
    while True:
        direct = os.path.join(start, "node_modules", *name.split("/"), "package.json")
        if os.path.isfile(direct):
            return direct
        pnpm_dir = os.path.join(start, "node_modules", ".pnpm")
        if os.path.isdir(pnpm_dir):
            prefix = name.replace("/", "+") + "@"
            try:
                entries = sorted(os.listdir(pnpm_dir))
            except OSError:
                entries = []
            for entry in entries:
                if not entry.startswith(prefix):
                    continue
                candidate = os.path.join(pnpm_dir, entry, "node_modules", *name.split("/"), "package.json")
                if os.path.isfile(candidate):
                    return candidate
        parent = os.path.dirname(start)
        if parent == start:
            return None
        start = parent


def _export_map_keys(exports):
    keys = []

    def walk(node):
        if isinstance(node, str):
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if key.startswith(".") and key not in keys:
                    keys.append(key)
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(exports)
    return keys


def _types_files(manifest, package_dir):
    candidates = []
    for key in ("types", "typings", "module", "main"):
        value = manifest.get(key)
        if isinstance(value, str):
            candidates.append(value)
    for value in _walk_strings(manifest.get("exports")):
        if value.endswith(".d.ts") or value.endswith(".d.mts") or value.endswith(".d.cts"):
            candidates.append(value)
    candidates.extend([
        "index.d.ts", "dist/index.d.ts", "types/index.d.ts",
        "dist/types/index.d.ts", "build/index.d.ts",
    ])
    found = []
    for rel in candidates:
        if not rel.endswith((".d.ts", ".d.mts", ".d.cts")):
            continue
        path = os.path.normpath(os.path.join(package_dir, rel.lstrip("./")))
        if os.path.isfile(path) and path not in found:
            found.append(path)
    return found


def _walk_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _walk_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_strings(value)


def extract_symbols(paths, limit=200):
    symbols = set()
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        for pattern in SYMBOL_PATTERNS:
            symbols.update(re.findall(pattern, text))
        for block in EXPORT_LIST_RE.findall(text):
            for part in block.split(","):
                part = part.strip()
                if not part:
                    continue
                if " as " in part:
                    part = part.split(" as ")[-1].strip()
                if re.match(r"^[A-Za-z_$][\w$]*$", part):
                    symbols.add(part)
    return sorted(symbols)[:limit], len(symbols)


def _semver(value):
    core = re.sub(r"^[v^~>=<\s]+", "", str(value or ""))
    core = core.split("-")[0].split("+")[0]
    parts = core.split(".")
    try:
        return tuple(int(part) for part in (parts + ["0", "0"])[:3])
    except ValueError:
        return None


def _gap_note(installed, latest):
    a, b = _semver(installed), _semver(latest)
    if not a or not b:
        return None
    if a == b:
        return "up to date"
    if b[0] > a[0]:
        return f"{b[0] - a[0]} major behind - breaking changes likely; read the changelog"
    if b[:2] > a[:2]:
        return "minor behind - new APIs may exist, existing ones usually stable"
    return "patch behind"


def _changelog_info(package_dir, installed, latest):
    for name in ("CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md"):
        path = os.path.join(package_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        versions = CHANGELOG_RE.findall(text)
        top = text[:6000]
        breaking = len(re.findall(r"(?i)\bbreaking\b", top))
        return {
            "changelog": name,
            "changelog_versions": versions[:12],
            "changelog_entries": len(versions),
            "breaking_mentions": breaking,
        }
    return {}


def inspect_node(name, cwd, timeout, allow_network=True):
    manifest_path = find_node_package(name, cwd)
    if not manifest_path:
        return result("inspect-node", name, False,
                      error="not installed in node_modules (run from the project root)"), 1
    package_dir = os.path.dirname(manifest_path)
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return result("inspect-node", name, False, error=f"unreadable package.json: {exc}"), 1

    installed = manifest.get("version")
    latest = None
    network_note = None
    if allow_network:
        try:
            data = http_json("https://registry.npmjs.org/" + urllib.parse.quote(name, safe=""), timeout)
            latest = (data.get("dist-tags") or {}).get("latest")
        except (NotFound, Unreachable) as exc:
            network_note = f"registry unavailable: {exc}"

    types_files = _types_files(manifest, package_dir)
    symbols, total_symbols = extract_symbols(types_files)
    payload = result(
        "inspect-node", name, True,
        installed=installed,
        latest=latest,
        gap=_gap_note(installed, latest),
        path=package_dir,
        types=[os.path.relpath(path, package_dir).replace("\\", "/") for path in types_files[:3]],
        symbols_count=total_symbols,
        symbols=symbols[:40],
        exports=_export_map_keys(manifest.get("exports"))[:20],
        license=manifest.get("license") if isinstance(manifest.get("license"), str) else None,
        network_note=network_note,
    )
    payload.update(_changelog_info(package_dir, installed, latest))
    return payload, 0


def inspect_python(name):
    from importlib import metadata

    try:
        distribution = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return result("inspect-python", name, False,
                      error="not installed in this interpreter"), 1
    payload = result(
        "inspect-python", name, True,
        installed=distribution.version,
        path=str(distribution.locate_file("")),
        summary=(distribution.metadata.get("Summary") or None),
        requires=[r for r in (distribution.requires or [])][:20],
        requires_count=len(distribution.requires or []),
    )
    return payload, 0



STATE_NAME = ".reality-check.json"
FAILING = {"MAJOR", "DEPRECATED", "MISSING"}


def _major_of(deps, name):
    for dep in deps:
        if dep.get("name") == name and dep.get("installed"):
            version = _semver(dep["installed"])
            if version:
                return version[0]
    return None


def rules_for(deps):
    """Conventions implied by the installed majors, not by memory."""
    rules = []
    svelte_major = _major_of(deps, "svelte")
    kit_major = _major_of(deps, "@sveltejs/kit")
    tailwind_major = _major_of(deps, "tailwindcss")
    ai_major = _major_of(deps, "ai")

    if svelte_major and svelte_major >= 5:
        rules.append(
            "svelte 5: runes only ($state, $derived, $effect, $props, $bindable); "
            "onclick={fn} not on:click; {#snippet}/{@render} not <slot>; "
            "mount(App, {target}) not new App({target}); props via $props() not export let"
        )
    elif svelte_major == 4:
        rules.append("svelte 4: export let, $:, on:click, <slot> - upgrade before adding components")

    if kit_major and kit_major >= 3:
        rules.append(
            "@sveltejs/kit 3: $app/state (page, navigating, updated) not $app/stores; "
            "$app/server exposes remote functions (query, form, command)"
        )
    elif kit_major == 2:
        rules.append("@sveltejs/kit 2: $app/stores is the current API")

    if tailwind_major and tailwind_major >= 4:
        rules.append(
            'tailwind 4: @import "tailwindcss" not @tailwind base/components/utilities; '
            "theme via @theme in CSS (no tailwind.config.js by default); "
            "shadow-sm->shadow-xs, rounded->rounded-sm, outline-none->outline-hidden, ring->ring-3; "
            "important suffix bg-red-500!; @utility not @layer utilities; "
            '@reference "../app.css" before @apply inside a Svelte <style> block'
        )
    elif tailwind_major == 3:
        rules.append("tailwind 3: @tailwind directives + tailwind.config.js")

    if ai_major and ai_major >= 7:
        rules.append(
            "ai 7: @ai-sdk/svelte 5 pins ai 7.0.173; it needs svelte ^5.31 and node >=22 - "
            "upgrade the three together, never one alone"
        )
    return rules


def _project_manifest(path):
    target = os.path.abspath(path)
    if os.path.isdir(target):
        target = os.path.join(target, "package.json")
    if not os.path.isfile(target):
        raise FileNotFoundError(f"no package.json at {target}")
    with open(target, encoding="utf-8-sig") as handle:
        return target, json.load(handle)


def _dep_specs(manifest):
    deps = {}
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        for name, spec in (manifest.get(section) or {}).items():
            deps[name] = str(spec)
    return deps


def _registry_meta(name, timeout):
    data = http_json("https://registry.npmjs.org/" + urllib.parse.quote(name, safe=""), timeout)
    latest = (data.get("dist-tags") or {}).get("latest")
    deprecated = None
    if latest and isinstance(data.get("versions"), dict):
        deprecated = data["versions"].get(latest, {}).get("deprecated")
    return latest, deprecated


def _local_version(root, name):
    manifest_path = find_node_package(name, root)
    if not manifest_path:
        return None
    try:
        with open(manifest_path, encoding="utf-8-sig") as handle:
            return json.load(handle).get("version")
    except (OSError, json.JSONDecodeError):
        return None


def _classify(spec, installed, latest, deprecated):
    if not latest:
        return "UNVERIFIED"
    if deprecated:
        return "DEPRECATED"
    if installed:
        a, b = _semver(installed), _semver(latest)
        if not a or not b:
            return "UNVERIFIED"
        if a == b:
            return "CURRENT"
        if b[0] > a[0]:
            return "MAJOR"
        if b[:2] > a[:2]:
            return "OUTDATED"
        return "PATCH"
    if re.match(r"^(workspace|file|link|git|https?):", spec):
        return "SKIPPED"
    base = _semver(spec)
    newest = _semver(latest)
    if base and newest and newest[0] > base[0]:
        return "MAJOR"
    return "NOT INSTALLED"


def check_project(path, state_path=None, timeout=TIMEOUT, allow_network=True, include_rules=False):
    manifest_path, manifest = _project_manifest(path)
    root = os.path.dirname(manifest_path)
    specs = _dep_specs(manifest)
    deps = []
    for name in sorted(specs):
        spec = specs[name]
        installed = _local_version(root, name)
        latest = deprecated = None
        note = None
        if allow_network and not re.match(r"^(workspace|file|link):", spec):
            try:
                latest, deprecated = _registry_meta(name, timeout)
            except NotFound:
                note = "no such package on npm"
            except Unreachable as exc:
                note = f"unverified: {exc}"
        status = "SKIPPED" if re.match(r"^(workspace|file|link):", spec) else _classify(
            spec, installed, latest, deprecated)
        deps.append({
            "name": name,
            "spec": spec,
            "installed": installed,
            "latest": latest,
            "status": status,
            "deprecated": bool(deprecated),
            "note": note if isinstance(deprecated, str) else note,
            "deprecation_note": deprecated if isinstance(deprecated, str) else None,
        })

    counts = {}
    for dep in deps:
        counts[dep["status"]] = counts.get(dep["status"], 0) + 1

    payload = result("project", manifest_path, True,
                     checked_at=_now(), counts=counts, dependencies=deps,
                     package_name=manifest.get("name"))
    if include_rules:
        payload["conventions"] = rules_for(deps)

    changes = []
    if state_path:
        previous = _read_state(state_path)
        if previous:
            old = previous.get("packages", {})
            for dep in deps:
                before = old.get(dep["name"])
                if not before:
                    changes.append(f"{dep['name']}: newly tracked ({dep['status']})")
                    continue
                if before.get("status") != dep["status"]:
                    changes.append(
                        f"{dep['name']}: {before.get('status')} -> {dep['status']}")
                if before.get("latest") and dep["latest"] and before["latest"] != dep["latest"]:
                    changes.append(
                        f"{dep['name']}: latest {before['latest']} -> {dep['latest']}")
        _write_state(state_path, payload, previous)
        payload["state"] = os.path.abspath(state_path)
    payload["changes"] = changes
    failed = [d["name"] for d in deps if d["status"] in FAILING]
    payload["failed"] = failed
    if not allow_network:
        return payload, 0
    unverified = [d for d in deps if d["status"] == "UNVERIFIED"]
    if unverified and len(unverified) == len(deps):
        return payload, 2
    return payload, 1 if failed else 0


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_state(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _write_state(path, payload, previous):
    state = {
        "version": 1,
        "checkedAt": payload.get("checked_at"),
        "previousCheckedAt": (previous or {}).get("checkedAt"),
        "conventions": payload.get("conventions") or (previous or {}).get("conventions") or [],
        "packages": {
            dep["name"]: {
                "spec": dep["spec"],
                "installed": dep["installed"],
                "latest": dep["latest"],
                "status": dep["status"],
            }
            for dep in payload.get("dependencies", [])
        },
    }
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        payload["state_error"] = str(exc)


def render_project(payload):
    if not payload.get("exists"):
        return f"project {payload.get('name')}: NOT FOUND ({payload.get('error')})"
    deps = payload.get("dependencies", [])
    lines = [f"project {payload.get('name')}  ({len(deps)} deps, checked {payload.get('checked_at')})"]
    lines.append("")
    width = max([26] + [len(dep["name"]) + 2 for dep in deps])
    lines.append(f"  {'package':<{width}}{'installed':<12}{'latest':<12}status")
    for dep in deps:
        installed = dep.get("installed") or "-"
        latest = dep.get("latest") or "-"
        status = dep["status"]
        suffix = ""
        if status == "MAJOR":
            suffix = "  <- breaking changes likely, upgrade"
        elif status == "DEPRECATED":
            suffix = "  <- deprecated, replace it"
        elif status == "MISSING":
            suffix = "  <- not on npm"
        elif status == "UNVERIFIED":
            suffix = "  <- registry unreachable"
        lines.append(f"  {dep['name']:<{width}}{installed:<12}{latest:<12}{status}{suffix}")
    changes = payload.get("changes") or []
    if changes:
        lines.append("")
        lines.append("changed since last save:")
        for item in changes:
            lines.append(f"  - {item}")
    conventions = payload.get("conventions") or []
    if conventions:
        lines.append("")
        lines.append("write in this style (from installed versions):")
        for rule in conventions:
            lines.append(f"  * {rule}")
    failed = payload.get("failed") or []
    if failed:
        lines.append("")
        lines.append("must fix: " + ", ".join(failed))
    if payload.get("state"):
        lines.append("")
        lines.append(f"state saved: {payload['state']}")
    return "\n".join(lines)


SCAN_EXT = {".svelte", ".ts", ".tsx", ".js", ".jsx", ".css"}
SCAN_SKIP = {"node_modules", ".svelte-kit", "build", "dist", ".git", ".vercel", "__pycache__"}


def _declaration_snippets(text: str, symbol: str):
    """Yield (line, snippet, deprecated) for the declaration named symbol, with its own JSDoc."""
    escaped = re.escape(symbol)
    patterns = [
        re.compile(rf"^[ \t]*(?:export\s+)?(?:declare\s+)?(?:async\s+)?"
                   rf"(?:function|const|let|var|class|type|interface|enum)\s+{escaped}\b", re.M),
        re.compile(rf"^[ \t]*(?:export\s+)?(?:declare\s+)?"
                   rf"(?:readonly\s+)?(?:static\s+)?{escaped}\s*[<(?:]", re.M),
    ]

    lines = text.splitlines()
    seen = set()
    for pattern in patterns:
        for match in pattern.finditer(text):
            line_number = text[: match.start()].count("\n") + 1
            if line_number in seen:
                continue
            seen.add(line_number)

            start = line_number - 1

            # JSDoc directly above this declaration only.
            doc: list[str] = []
            probe = start - 1
            if probe >= 0 and lines[probe].strip().endswith("*/"):
                end = probe
                while probe >= 0 and not lines[probe].strip().startswith("/**"):
                    probe -= 1
                if probe >= 0:
                    doc = lines[probe : end + 1]

            # The declaration itself, stopping when braces/parens close and the line ends.
            decl: list[str] = []
            depth = 0
            for cursor in range(start, min(start + 20, len(lines))):
                line = lines[cursor]
                decl.append(line)
                depth += (line.count("{") + line.count("(") + line.count("[")
                          - line.count("}") - line.count(")") - line.count("]"))
                stripped = line.rstrip()
                if depth <= 0 and stripped.endswith(";"):
                    break
                if depth <= 0 and cursor > start and stripped.endswith("}"):
                    break

            snippet = "\n".join(doc + decl).rstrip()
            yield line_number, snippet, "@deprecated" in "\n".join(doc)


def docs_package(package, symbol=None, readme_section=None, cwd="."):
    manifest_path = find_node_package(package, cwd)
    if not manifest_path:
        return result("docs", package, False,
                      error="package is not installed; install it first"), 1

    package_dir = os.path.dirname(manifest_path)
    with open(manifest_path, encoding="utf-8-sig") as handle:
        manifest = json.load(handle)
    version = manifest.get("version")

    if readme_section:
        for name in ("README.md", "readme.md", "README"):
            path = os.path.join(package_dir, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            heading = re.search(rf"(?mi)^(#{{1,4}})\s*{re.escape(readme_section)}.*$", text)
            if not heading:
                return result("docs", package, True, version=version,
                              error=f"no section matching {readme_section!r}"), 1
            level = len(heading.group(1))
            rest = text[heading.end():]
            stop = re.search(rf"(?m)^#{{1,{level}}}\s", rest)
            section = text[heading.start(): heading.end() + (stop.start() if stop else len(rest))]
            return result("docs", package, True, version=version, section=readme_section,
                          text=section.strip()[:4000]), 0
        return result("docs", package, True, version=version, error="no README in the package"), 1

    types_files = _types_files(manifest, package_dir)
    files = []
    seen_files = set()
    for path in types_files + [os.path.join(package_dir, "index.d.ts"),
                               os.path.join(package_dir, "dist", "index.d.ts")]:
        if path in seen_files or not os.path.isfile(path):
            continue
        seen_files.add(path)
        files.append(path)

    if not symbol:
        return result("docs", package, True, version=version,
                      types=[os.path.relpath(path, package_dir).replace("\\", "/") for path in files[:5]],
                      hint="pass --symbol <name> for the exact signature, or --readme <section>"), 0

    for path in files:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        for line, snippet, deprecated in _declaration_snippets(text, symbol):
            return result("docs", package, True, version=version, symbol=symbol,
                          location=f"{os.path.relpath(path, package_dir).replace(chr(92), '/')}:{line}",
                          deprecated=deprecated,
                          signature=snippet[:3000]), 0

    return result("docs", package, True, version=version, symbol=symbol,
                  error=f"no declaration for {symbol!r} in the shipped types"), 1


def _scan_rules(deps):
    """(regex, code, message) for the installed majors. Verified against the migration guides."""
    rules = []
    svelte_major = _major_of(deps, "svelte")
    kit_major = _major_of(deps, "@sveltejs/kit")
    tailwind_major = _major_of(deps, "tailwindcss")
    ai_major = _major_of(deps, "ai")
    ai_svelte_major = _major_of(deps, "@ai-sdk/svelte")

    if svelte_major and svelte_major >= 5:
        rules += [
            (r"\bon:[a-z]+=", "SVELTE_EVENT", "use onclick={fn} instead of on:click (Svelte 5 runes)"),
            (r"\bexport let\b", "SVELTE_PROPS", "use let { x } = $props() instead of export let (Svelte 5)"),
            (r"^\s*\$:\s", "SVELTE_REACTIVE", "use $derived / $effect instead of $: (Svelte 5)"),
            (r"<slot\b", "SVELTE_SLOT", "use {#snippet} + {@render} instead of <slot> (Svelte 5)"),
            (r"\bnew App\(", "SVELTE_MOUNT", "use mount(App, { target }) instead of new App() (Svelte 5)"),
            (r"\$\$props|\$\$restProps", "SVELTE_LEGACY", "use $props() instead of $$props (Svelte 5)"),
        ]
    if kit_major and kit_major >= 3:
        rules.append((r"\$app/stores", "KIT_STORES",
                      "use $app/state (page, navigating, updated) instead of $app/stores (Kit 3)"))
        rules.append((r"\$env/(dynamic|static)/(private|public)", "KIT_ENV",
                      "use src/env.ts with defineEnvVars and $app/env/private|public (Kit 3)"))
    if tailwind_major and tailwind_major >= 4:
        rules.append((r"@tailwind\s+(base|components|utilities)", "TW_DIRECTIVE",
                      'use @import "tailwindcss" instead of @tailwind directives (Tailwind 4)'))
    if ai_major and ai_major >= 7:
        rules += [
            (r"\bmaxTokens\s*:", "AI_MAXTOKENS", "use maxOutputTokens instead of maxTokens (AI SDK 5+)"),
            (r"\bconvertToCoreMessages\b", "AI_CONVERT", "use convertToModelMessages (AI SDK 5+)"),
            (r"\bCoreMessage\b", "AI_COREMESSAGE", "use ModelMessage (AI SDK 5+)"),
            (r"from\s+['\"]ai/react['\"]", "AI_REACT", "import from @ai-sdk/react (AI SDK 5+)"),
            (r"from\s+['\"]ai/rsc['\"]", "AI_RSC", "import from @ai-sdk/rsc (AI SDK 5+)"),
            (r"\bmaxSteps\s*:", "AI_MAXSTEPS", "use stopWhen: isStepCount(n) instead of maxSteps (AI SDK 5+)"),
            (r"\baddToolResult\(", "AI_ADDTOOL", "use addToolOutput instead of addToolResult (AI SDK 5+)"),
            (r"\binitialMessages\s*:", "AI_INITMSG", "use messages: instead of initialMessages (AI SDK 5+)"),
            (r"\bappend\(", "AI_APPEND", "use sendMessage({ text }) instead of append() (AI SDK 5+)"),
            (r"\btoUIMessageStreamResponse\(|\bpipeUIMessageStreamToResponse\(", "AI_STREAMRESP",
             "deprecated in ai 7: use toUIMessageStream + createUIMessageStreamResponse"),
        ]
    if ai_svelte_major and ai_svelte_major >= 2:
        rules.append((r"(?<!new )\bChat\(\{", "AI_CHAT_CTOR",
                      "use new Chat({ transport }) in @ai-sdk/svelte 2+"))
    return rules


def _walk_sources(root):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SCAN_SKIP]
        for filename in filenames:
            path = os.path.join(directory, filename)
            suffix = os.path.splitext(filename)[1].lower()
            if filename.endswith(".svelte.ts") or filename.endswith(".svelte.js"):
                suffix = ".ts"
            if suffix in SCAN_EXT:
                yield path


def scan_project(path):
    manifest_path, manifest = _project_manifest(path)
    root = os.path.dirname(manifest_path)
    specs = _dep_specs(manifest)
    deps = [{"name": name, "installed": _local_version(root, name)} for name in specs]
    rules = _scan_rules(deps)
    if not rules:
        return result("scan", root, False,
                      error="no recognised framework versions installed; nothing to scan against"), 1

    findings = []
    scanned = 0
    for source in _walk_sources(root):
        scanned += 1
        try:
            with open(source, encoding="utf-8-sig", errors="replace") as handle:
                lines = handle.read().splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            for pattern, code, message in rules:
                if re.search(pattern, line):
                    findings.append({
                        "file": os.path.relpath(source, root).replace("\\", "/"),
                        "line": number,
                        "code": code,
                        "message": message,
                        "snippet": line.strip()[:120],
                    })

    tw_major = _major_of(deps, "tailwindcss")
    if tw_major is not None and tw_major >= 4:
        config = os.path.join(root, "tailwind.config.js")
        config_ts = os.path.join(root, "tailwind.config.ts")
        if os.path.isfile(config) or os.path.isfile(config_ts):
            findings.append({
                "file": "tailwind.config.js" if os.path.isfile(config) else "tailwind.config.ts",
                "line": 1,
                "code": "TW_CONFIG",
                "message": "Tailwind 4 reads theme from CSS (@theme); a JS config is not auto-detected",
                "snippet": "",
            })

    counts = {}
    for finding in findings:
        counts[finding["code"]] = counts.get(finding["code"], 0) + 1
    payload = result("scan", root, True, scanned=scanned,
                     findings=findings, counts=counts,
                     rules=[code for _p, code, _m in rules])
    return payload, (1 if findings else 0)


def render_scan(payload):
    if not payload.get("exists"):
        return f"scan {payload.get('name')}: {payload.get('error')}"
    findings = payload.get("findings", [])
    lines = [f"scan {payload.get('name')}  ({payload.get('scanned')} files, "
             f"{len(findings)} findings)"]
    for finding in findings:
        lines.append(f"  {finding['file']}:{finding['line']}  {finding['code']}  {finding['message']}")
        if finding.get("snippet"):
            lines.append(f"      {finding['snippet']}")
    if not findings:
        lines.append("  clean")
    return "\n".join(lines)


def render_docs(payload):
    if not payload.get("exists"):
        return f"docs {payload.get('name')}: {payload.get('error')}"
    head = f"docs {payload['name']} {payload.get('version') or ''}".strip()
    if payload.get("signature"):
        lines = [head, f"  symbol      {payload.get('symbol')}", f"  location    {payload.get('location')}"]
        if payload.get("deprecated"):
            lines.append("  deprecated  yes - do not use in new code")
        lines.append("")
        lines.append(payload["signature"])
        return "\n".join(lines)
    if payload.get("text"):
        return head + "\n\n" + payload["text"]
    if payload.get("types"):
        return head + "\n  types       " + ", ".join(payload["types"]) + "\n  " + str(payload.get("hint", ""))
    return head + f"\n  {payload.get('error')}"


def render(payload: dict, code: int) -> str:
    name = payload.get("name")
    eco = payload.get("ecosystem")
    if payload.get("exists") is None:
        reason = payload.get("error") or "registry unreachable"
        return f"{eco} {name}: UNVERIFIED ({reason})"
    if not payload.get("exists"):
        reason = payload.get("error") or "does not exist"
        return f"{eco} {name}: NOT FOUND ({reason})"

    lines = [f"{eco} {name}: {'INSPECTED' if str(eco or '').startswith('inspect') else 'EXISTS'}"]
    scalar_keys = (
        "installed", "latest", "gap", "requested", "version", "license", "updated",
        "pushed_at", "requires_python", "summary", "status", "content_type",
        "versions_count", "stars", "symbols_count", "changelog_entries",
        "breaking_mentions", "requires_count", "path",
    )
    for key in scalar_keys:
        value = payload.get(key)
        if value is None or value == "" or value is False:
            continue
        lines.append(f"  {key:<17} {value}")
    for key, limit in (("types", 3), ("exports", 12), ("symbols", 12),
                       ("changelog_versions", 8), ("requires", 8)):
        values = payload.get(key)
        if not values:
            continue
        shown = ", ".join(str(item) for item in list(values)[:limit])
        more = len(values) - limit
        lines.append(f"  {key:<17} {shown}" + (f" (+{more} more)" if more > 0 else ""))
    if payload.get("changelog"):
        lines.append(f"  {'changelog':<17} {payload['changelog']}")
    note = payload.get("deprecation_note") or payload.get("network_note")
    if note:
        lines.append(f"  {'note':<17} {note}")
    if payload.get("deprecated"):
        lines.append("  warning           this version is deprecated")
    if payload.get("yanked"):
        lines.append("  warning           this release is yanked")
    if payload.get("archived"):
        lines.append("  warning           repository is archived")
    return "\n".join(lines)


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Check that a package, version or URL really exists.")
    parser.add_argument("subcommand", choices=sorted(list(CHECKS) + ["github", "url", "installed", "inspect", "project", "scan", "docs"]))
    parser.add_argument("name", help="package/module/repo name, or URL for the url subcommand")
    parser.add_argument("extra", nargs="?",
                        help="for `installed`/`inspect`: the module or package name after the runtime")
    parser.add_argument("--version", "-V", help="version or range to confirm is published")
    parser.add_argument("--cwd", default=".", help="starting directory for installed/inspect node")
    parser.add_argument("--no-network", action="store_true", help="inspect offline: skip the registry")
    parser.add_argument("--state", nargs="?", const="__default__",
                        help="record/compare a project snapshot; default file is "
                             f"{STATE_NAME} next to package.json")
    parser.add_argument("--rules", action="store_true",
                        help="also print the coding conventions implied by installed majors")
    parser.add_argument("--symbol", help="for `docs`: the exact export/member to quote")
    parser.add_argument("--readme", help="for `docs`: the README section heading to print")
    parser.add_argument("--timeout", type=float, default=TIMEOUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    wanted = clean_range(args.version)
    try:
        if args.subcommand == "installed":
            if not args.extra:
                raise ValueError("usage: pkgcheck.py installed <python|node> <package>")
            payload, code = check_installed(args.name, args.extra, args.cwd)
        elif args.subcommand == "project":
            state_path = None
            if args.state is not None:
                state_path = args.state
                if state_path == "__default__":
                    manifest_path, _ = _project_manifest(args.name)
                    state_path = os.path.join(os.path.dirname(manifest_path), STATE_NAME)
            payload, code = check_project(args.name, state_path, args.timeout,
                                          allow_network=not args.no_network,
                                          include_rules=args.rules)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(render_project(payload))
            return code
        elif args.subcommand == "scan":
            payload, code = scan_project(args.name)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(render_scan(payload))
            return code
        elif args.subcommand == "docs":
            payload, code = docs_package(args.name, args.symbol, args.readme, args.cwd)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(render_docs(payload))
            return code
        elif args.subcommand == "inspect":
            if not args.extra:
                raise ValueError("usage: pkgcheck.py inspect <node|python> <package>")
            if args.name == "python":
                payload, code = inspect_python(args.extra)
            elif args.name == "node":
                payload, code = inspect_node(args.extra, args.cwd, args.timeout,
                                             allow_network=not args.no_network)
            else:
                raise ValueError("inspect supports node or python")
        elif args.subcommand == "github":
            payload, code = check_github(args.name, args.timeout)
        elif args.subcommand == "url":
            payload, code = check_url(args.name, args.timeout)
        else:
            payload, code = CHECKS[args.subcommand](args.name, wanted, args.timeout)
    except NotFound as exc:
        payload, code = result(args.subcommand, args.name, False, error=str(exc)), 1
    except Unreachable as exc:
        payload, code = result(args.subcommand, args.name, None, error=str(exc),
                               hint="registry unreachable: the claim is unverified"), 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render(payload, code))
        if code == 2:
            print("Verdict: UNVERIFIED - do not state this package as existing or missing.", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
