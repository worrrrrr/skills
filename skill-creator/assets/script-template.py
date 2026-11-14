#!/usr/bin/env python3
"""Helper for the {{name}} skill.

Keep scripts self-contained: standard library only, clear error messages,
non-zero exit codes on failure. Read arguments, do one job, print the result.
"""

from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TODO: describe the job of this script")
    parser.add_argument("input", nargs="?", help="TODO")
    args = parser.parse_args(argv)
    if not args.input:
        print("error: missing input", file=sys.stderr)
        return 2
    print(f"TODO: process {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
