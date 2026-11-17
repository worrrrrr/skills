#!/usr/bin/env python3
"""Regression checks for name.py. Run: python scripts/selftest.py"""
from __future__ import annotations

from name import MEANINGS, letters, load_detail, meaning, reduce_number, summarize, verdict

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

check(sum(item["value"] for item in letters("Somchai")) == 24, "Somchai = 24 (A-Z table)")
check(letters("A")[0]["value"] == 1, "A = 1")
check(letters("z")[0]["value"] == 7, "z = 7")
check(letters("Q")[0]["value"] == 1, "Q = 1")
check(letters("S")[0]["value"] == 3, "English S = 3 (not Thai ส = 7)")

check(reduce_number(14) == [14, 5], "14 reduces to 5")
check(reduce_number(51) == [51, 6], "51 reduces to 6")

check(set(MEANINGS) >= set(range(0, 101)), "meanings cover 0-100")
check(verdict(14) == "good", "14 verdict")
check(verdict(11) == "bad", "11 verdict")
check(verdict(0) == "special", "0 verdict")
check(bool(meaning(0)), "0 has a meaning")
check(bool(meaning(100)), "100 has a meaning")
check(data["combined"]["reduced_items"][1]["number"] == 11, "reduced item 11")
check(data["combined"]["reduced_items"][2]["number"] == 2, "reduced item 2")

detail = load_detail()
check(set(detail) == set(range(1, 101)), "detail covers 1-100 (0 is the special case)")
check(bool(detail[14]["text"]), "14 has detail text")
check(bool(detail[100]["title"]), "100 has a title")

print(f"selftest: {checks} checks passed")
