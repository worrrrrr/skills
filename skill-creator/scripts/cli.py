#!/usr/bin/env python3
"""One CLI for the whole skill workflow: new, lint, fix, doctor.

    python scripts/cli.py new my-skill --scripts --references
    python scripts/cli.py lint ../my-skill
    python scripts/cli.py fix ../my-skill          # create the files a skill references but lacks
    python scripts/cli.py doctor ...               # lint every skill under the given folders

`fix` resumes where a half-finished scaffold stopped: it reads SKILL.md, finds every
referenced file that does not exist, creates a stub, then lints again.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lint as lint_mod  # noqa: E402

BROKEN_REF_RE = re.compile(r"referenced file (\S+) does not exist")


def run_script(name: str, args: list[str]) -> int:
    return subprocess.run([sys.executable, str(HERE / name), *args]).returncode


def cmd_new(args) -> int:
    forward = [args.name, "--dir", args.dir]
    for flag in ("--title", "--description", "--summary", "--license", "--compatibility",
                 "--allowed-tools"):
        value = getattr(args, flag.lstrip("-").replace("-", "_"), None)
        if value:
            forward += [flag, value]
    for flag in ("scripts", "references", "assets"):
        if getattr(args, flag):
            forward.append(f"--{flag}")
    if args.force:
        forward.append("--force")
    if args.no_lint:
        forward.append("--no-lint")
    if args.dry_run:
        forward.append("--dry-run")
    return run_script("new.py", forward)


def cmd_lint(args) -> int:
    return run_script("lint.py", [args.path, *(["--strict"] if args.strict else [])])


def cmd_fix(args) -> int:
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    created = []
    changed = True
    while changed:
        changed = False
        report, _stats = lint_mod.lint_skill(root)
        for item in report.errors:
            if item["code"] != "E020":
                continue
            match = BROKEN_REF_RE.search(item["message"])
            if not match:
                continue
            relative = match.group(1)
            if relative.startswith("../") or relative.startswith("/"):
                continue
            target = root / relative
            if target.is_file():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            title = target.stem.replace("-", " ").replace("_", " ").title()
            if target.suffix == ".md":
                body = f"# {title}\n\nTODO: fill this in. Referenced from `SKILL.md`.\n"
            elif target.suffix == ".py":
                body = (
                    "#!/usr/bin/env python3\n"
                    f'"""{title}.\n\nTODO: implement. Referenced from SKILL.md.\n"""\n\n'
                    "from __future__ import annotations\n\nimport sys\n\n\n"
                    "def main(argv=None) -> int:\n"
                    f'    print("TODO: {title}")\n'
                    "    return 0\n\n\n"
                    'if __name__ == "__main__":\n'
                    "    raise SystemExit(main())\n"
                )
            else:
                body = f"# {title}\n\nTODO: fill this in. Referenced from `SKILL.md`.\n"
            target.write_text(body, encoding="utf-8", newline="\n")
            created.append(relative)
            changed = True

    if not created:
        print("nothing to fix")
    else:
        print("created:")
        for item in created:
            print(f"  {item}")

    return run_script("lint.py", [str(root)])


def cmd_doctor(args) -> int:
    roots = [Path(item).resolve() for item in args.paths]
    skills = []
    for root in roots:
        if (root / "SKILL.md").is_file():
            skills.append(root)
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                skills.append(child)

    if not skills:
        print("no skills found")
        return 2

    failed = 0
    for skill in skills:
        report, stats = lint_mod.lint_skill(skill)
        status = "PASS" if report.ok else "FAIL"
        if not report.ok:
            failed += 1
        print(f"{status}  {skill.name:<20} {len(report.errors)}E/{len(report.warnings)}W  "
              f"{stats.get('files', 0)} files  ~{stats.get('tokens', 0):,} tokens")
        if args.verbose:
            for item in report.errors + report.warnings:
                print(f"      {item['code']}  {item['message']}")

    print()
    print(f"{len(skills) - failed}/{len(skills)} skills pass")
    return 0 if failed == 0 else 1


def main(argv=None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Create, lint, fix and audit Agent Skills.")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="scaffold a new skill")
    new.add_argument("name")
    new.add_argument("--dir", default=".")
    new.add_argument("--title")
    new.add_argument("--description")
    new.add_argument("--summary")
    new.add_argument("--license")
    new.add_argument("--compatibility")
    new.add_argument("--allowed-tools")
    new.add_argument("--scripts", action="store_true")
    new.add_argument("--references", action="store_true")
    new.add_argument("--assets", action="store_true")
    new.add_argument("--force", action="store_true")
    new.add_argument("--no-lint", action="store_true")
    new.add_argument("--dry-run", action="store_true")
    new.set_defaults(func=cmd_new)

    lint = sub.add_parser("lint", help="validate a skill")
    lint.add_argument("path")
    lint.add_argument("--strict", action="store_true")
    lint.set_defaults(func=cmd_lint)

    fix = sub.add_parser("fix", help="create missing referenced files, then lint")
    fix.add_argument("path")
    fix.set_defaults(func=cmd_fix)

    doctor = sub.add_parser("doctor", help="lint every skill under these folders")
    doctor.add_argument("paths", nargs="+")
    doctor.add_argument("-v", "--verbose", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
