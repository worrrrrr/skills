#!/usr/bin/env python3
"""Regression checks for name.py. Run: python scripts/selftest.py"""
from __future__ import annotations

from name import letters, reduce_number, summarize

checks = 0


def check(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


w = letters("วรกฤช")
check(sum(item["value"] for item in w) == 14, "วรกฤช = 14")

s = letters("สุนทรธรรมนิติ")
check(sum(item["value"] for item in s) == 51, "สุนทรธรรมนิติ = 51")

data = summarize("วรกฤช", "สุนทรธรรมนิติ")
check(data["name"]["total"] == 14, "name total")
check(data["surname"]["total"] == 51, "surname total")
check(data["combined"]["total"] == 65, "combined total")
check(data["combined"]["reduced"] == [65, 11, 2], "65 reduces to 11 then 2")

check(sum(item["value"] for item in letters("สุ")) == 8, "สุ = 7 + 1")
check(sum(item["value"] for item in letters("นิ")) == 9, "นิ = 5 + 4")
check(sum(item["value"] for item in letters("ธ์")) == 13, "ธ์ = 4 + 9")

check(letters("ํ")[0]["value"] == 0, "นิคหิต = 0")
check(letters("ฅ")[0]["kind"] == "unmapped", "obsolete ฅ is unmapped")

check(reduce_number(14) == [14, 5], "14 reduces to 5")
check(reduce_number(51) == [51, 6], "51 reduces to 6")

print(f"selftest: {checks} checks passed")
