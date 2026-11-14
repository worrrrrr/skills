#!/usr/bin/env python3
"""Regression checks for engine.py. Run: python scripts/selftest.py"""
from __future__ import annotations

import re

from engine import (
    compute_all,
    gate_of,
    julian_day,
    norm180,
    sexagenary_day,
    sun_longitude,
)

checks = 0


def check(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


check(abs(julian_day(2000, 1, 1, 12) - 2451545) < 1e-9, "JD 2000-01-01 12:00")
check(abs(sun_longitude(2451545) - 280.37) < 0.1, "Sun on 2000-01-01")
check(abs(norm180(sun_longitude(julian_day(2024, 3, 20, 3.1)))) < 0.05, "Sun at the 2024 March equinox")
check(sexagenary_day(2451545) == 54, "Day pillar 2000-01-01 = index 54")

anchor = gate_of(302)
check(anchor["gate"] == 41 and anchor["line"] == 1, "Human Design gate 41 starts at 302 degrees")
check(gate_of(358.25)["gate"] == 25, "Gate 25 starts at 358.25 degrees")

chart = compute_all({
    "y": 1990, "m": 1, "d": 1, "hh": 12, "mi": 0, "tz": 7,
    "lat": 13.7563, "lon": 100.5018,
})
check(len(chart["bazi"]["pillars"]) == 4, "four Bazi pillars")
check(sum(chart["bazi"]["elements"].values()) == 8, "eight Bazi characters counted")
check(len(chart["vedic"]["vim"]["periods"]) >= 4, "Vimshottari periods")
check(len(chart["hd"]["personality"]) == 13, "13 personality activations")
check(len(chart["hd"]["design_set"]) == 13, "13 design activations")
check(bool(re.fullmatch(r"[1-6]/[1-6]", chart["hd"]["profile"])), "Human Design profile shape")
check(isinstance(chart["hd"]["defined"], set), "defined centers is a set")
check(chart["hd"]["type"] in {
    "generator", "manifestingGenerator", "manifestor", "projector", "reflector",
}, "known Human Design type")

for year in range(1900, 2051, 10):
    sample = compute_all({
        "y": year, "m": 6, "d": 15, "hh": 9, "mi": 30, "tz": 7,
        "lat": 13.75, "lon": 100.5,
    })
    check(sample["meta"]["sun"] == sample["meta"]["sun"], f"finite Sun at {year}")

print(f"selftest: {checks} checks passed")
