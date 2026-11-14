#!/usr/bin/env python3
"""sudoku - generate, solve and count Sudoku grids with Z3.

    python scripts/sudoku.py --difficulty hard --seed 7
    python scripts/sudoku.py --solve "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
    python scripts/sudoku.py --size 4 --count 3

Exit codes: 0 solved/generated, 1 no solution or not unique, 2 z3 unavailable, 3 usage.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_UNAVAILABLE = 2
EXIT_USAGE = 3

BOX = {4: (2, 2), 6: (2, 3), 9: (3, 3), 16: (4, 4)}
CLUE_RATIO = {"easy": 0.50, "medium": 0.40, "hard": 0.32}


def parse_grid(text: str, size: int) -> list[list[int]]:
    digits = [char for char in text if not char.isspace() and char not in "|-+"]
    if len(digits) != size * size:
        raise ValueError(f"expected {size * size} cells, got {len(digits)}")
    values = []
    for char in digits:
        if char in ".0_":
            values.append(0)
        elif char.isalnum():
            value = int(char, 36)
            if not 1 <= value <= size:
                raise ValueError(f"value {char!r} is outside 1..{size}")
            values.append(value)
        else:
            raise ValueError(f"unexpected character {char!r}")
    return [values[row * size : (row + 1) * size] for row in range(size)]


def build_solver(size: int, grid: list[list[int]], timeout_ms: int):
    import z3

    box_h, box_w = BOX[size]
    cells = [[z3.Int(f"c{row}_{col}") for col in range(size)] for row in range(size)]
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)

    for row in range(size):
        solver.add(z3.Distinct(cells[row]))
    for col in range(size):
        solver.add(z3.Distinct([cells[row][col] for row in range(size)]))
    for br in range(0, size, box_h):
        for bc in range(0, size, box_w):
            solver.add(
                z3.Distinct(
                    [cells[br + i][bc + j] for i in range(box_h) for j in range(box_w)]
                )
            )
    solver.add([z3.And(cells[r][c] >= 1, cells[r][c] <= size) for r in range(size) for c in range(size)])
    for row in range(size):
        for col in range(size):
            if grid[row][col]:
                solver.add(cells[row][col] == grid[row][col])
    return solver, cells


def solve(grid: list[list[int]], size: int, timeout_ms: int) -> tuple[list[list[int]] | None, str]:
    import z3

    solver, cells = build_solver(size, grid, timeout_ms)
    result = solver.check()
    if result == z3.unsat:
        return None, "unsat"
    if result == z3.unknown:
        return None, f"unknown: {solver.reason_unknown()}"
    model = solver.model()
    return [[model.eval(cells[r][c], model_completion=True).as_long() for c in range(size)] for r in range(size)], "sat"


def count_solutions(grid: list[list[int]], size: int, limit: int, timeout_ms: int) -> int:
    import z3

    solver, cells = build_solver(size, grid, timeout_ms)
    found = 0
    while found < limit:
        if solver.check() != z3.sat:
            break
        found += 1
        model = solver.model()
        solver.add(
            z3.Or(
                [
                    cells[r][c] != model.eval(cells[r][c], model_completion=True)
                    for r in range(size)
                    for c in range(size)
                ]
            )
        )
    return found


def _random_full(size: int, rng: random.Random) -> list[list[int]]:
    """Backtracking fill - fast, and independent of the solver."""
    box_h, box_w = BOX[size]
    grid = [[0] * size for _ in range(size)]

    def ok(row: int, col: int, value: int) -> bool:
        if any(grid[row][c] == value for c in range(size)):
            return False
        if any(grid[r][col] == value for r in range(size)):
            return False
        br, bc = row - row % box_h, col - col % box_w
        return all(grid[br + i][bc + j] != value for i in range(box_h) for j in range(box_w))

    def fill(index: int) -> bool:
        if index == size * size:
            return True
        row, col = divmod(index, size)
        values = list(range(1, size + 1))
        rng.shuffle(values)
        for value in values:
            if ok(row, col, value):
                grid[row][col] = value
                if fill(index + 1):
                    return True
                grid[row][col] = 0
        return False

    if not fill(0):
        raise RuntimeError("no complete grid for this size")
    return grid


def generate(size: int, clues: int, seed: int | None, timeout_ms: int) -> tuple[list[list[int]], int, bool]:
    import z3  # noqa: F401 - fail fast when z3 is missing

    rng = random.Random(seed)
    full = _random_full(size, rng)
    puzzle = [row[:] for row in full]
    positions = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(positions)

    deadline = time.perf_counter() + timeout_ms / 1000
    remaining = size * size
    for row, col in positions:
        if remaining <= clues or time.perf_counter() > deadline:
            break
        saved = puzzle[row][col]
        puzzle[row][col] = 0
        if count_solutions(puzzle, size, 2, min(1_500, timeout_ms)) == 1:
            remaining -= 1
        else:
            puzzle[row][col] = saved

    unique = count_solutions(puzzle, size, 2, timeout_ms) == 1
    return puzzle, remaining, unique


def render(grid: list[list[int]], size: int) -> str:
    box_h, box_w = BOX[size]
    width = len(str(size))
    lines = []
    rule = "+" + "+".join("-" * (box_w * (width + 1) + 1) for _ in range(size // box_w)) + "+"
    for row in range(size):
        if row % box_h == 0:
            lines.append(rule)
        cells = []
        for col in range(size):
            value = grid[row][col]
            cells.append(("." * width if value == 0 else str(value).rjust(width)))
        chunks = [" ".join(cells[i : i + box_w]) for i in range(0, size, box_w)]
        lines.append("| " + " | ".join(chunks) + " |")
    lines.append(rule)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sudoku", description="Generate, solve and count Sudoku with Z3.")
    parser.add_argument("--size", type=int, default=9, choices=sorted(BOX))
    parser.add_argument("--solve", metavar="GRID")
    parser.add_argument("--count", type=int, default=0, metavar="N", help="count up to N solutions")
    parser.add_argument("--difficulty", choices=sorted(CLUE_RATIO), default="medium")
    parser.add_argument("--clues", type=int, default=0, help="override the clue count")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=30_000, metavar="MS")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        import z3  # noqa: F401
    except Exception as exc:
        print(f"z3 not importable: {exc}", file=sys.stderr)
        return EXIT_UNAVAILABLE

    started = time.perf_counter()

    if args.solve:
        try:
            grid = parse_grid(args.solve, args.size)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE
        if args.count:
            total = count_solutions(grid, args.size, args.count, args.timeout)
            payload = {"size": args.size, "solutions": total, "limit": args.count}
            print(json.dumps(payload) if args.json else f"solutions: {total} (limit {args.count})")
            return EXIT_OK if total else EXIT_FAIL
        solved, status = solve(grid, args.size, args.timeout)
        payload = {
            "size": args.size,
            "status": status,
            "solved": [row[:] for row in solved] if solved else None,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif solved:
            print(render(solved, args.size))
        else:
            print(f"no solution: {status}", file=sys.stderr)
        return EXIT_OK if solved else EXIT_FAIL

    clues = args.clues or max(4, round(args.size * args.size * CLUE_RATIO[args.difficulty]))
    puzzle, remaining, unique = generate(args.size, clues, args.seed, args.timeout)
    payload = {
        "size": args.size,
        "difficulty": args.difficulty,
        "seed": args.seed,
        "clues": remaining,
        "unique": unique,
        "puzzle": puzzle,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render(puzzle, args.size))
        print(f"size {args.size}  clues {remaining}  unique {unique}  {payload['elapsed_ms']} ms")
    return EXIT_OK if unique else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
