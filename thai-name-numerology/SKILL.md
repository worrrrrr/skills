---
name: thai-name-numerology
description: >-
  Calculates Thai name numerology (เลขศาสตร์ชื่อ) from a name and surname: maps every
  Thai consonant, vowel and tone mark to its digit, sums the first name, the surname and
  the combined total, then reduces the total and reads the traditional meaning. Use when
  the user asks to วิเคราะห์ชื่อ, ตรวจชื่อ, ตั้งชื่อ, ดูเลขศาสตร์ชื่อ, ดูเลขชื่อ-นามสกุล,
  or says "ชื่อนี้ได้เลขอะไร", "เลขศาสตร์ชื่อ", "name numerology", "ชื่อมงคล".
license: MIT
metadata:
  version: "1.0.0"
  tags: "numerology, thai, names, onomastics, divination"
allowed-tools: Read Write Edit Bash Glob Grep
---

# Thai Name Numerology

Turn a Thai name and surname into three numbers — first name, surname, combined — then read
them with the traditional digit table. The script is deterministic; the reading is traditional.

One job: **name numbers**. Birth charts, Bazi and Human Design belong to the separate
`divination-charts` skill.

## When to use

- The user gives a Thai name and asks what number it carries.
- The user asks whether a name is good/bad by เลขศาสตร์, or compares two spellings.
- The user asks for the meaning of a name total, surname total, combined total or reduced number.
- The user is choosing a name and wants the numeric effect of a spelling.

## When not to use

- Birth-chart questions: use `divination-charts`.
- A request to predict health, money, law or safety: give the traditional meaning, not advice.
- A name in a script the table does not cover (English, Chinese): say the table is Thai-only.
- No Thai spelling: ask for it; transliteration changes the values.

## Workflow

### 1. Collect the exact spelling

Ask for **ชื่อ** and **นามสกุล** as written in Thai. Spelling is the calculation:

- `ส` = 7, `ศ` = 7, `ษ` = 4 — same sound, different number.
- `ธ` = 4, `ท` = 1, `ต` = 3 — a missing or extra letter changes the total.
- Confirm the surname spelling when it is ambiguous (for example `สุนทรธรรมนิติ` vs
  `สุนทรรมนิติ`).

Do not romanize, do not "fix" a name, and do not add a middle name the user did not give.

### 2. Calculate

```bash
python scripts/name.py --name "วรกฤช" --surname "สุนทรธรรมนิติ" --json
```

- `--full "ชื่อ นามสกุล"` splits at the first space.
- `--md` prints a ready report.
- Requires Python 3.11+, standard library only.
- Exit `0` ok, `2` no Thai letters, `3` usage.

The JSON carries each character with its value, the three totals, the reduction steps and
the verdict for numbers the script knows.

### 3. Read the three numbers

| Number | Meaning |
|---|---|
| Name total | the person's own name power (ตำราให้ความสำคัญประมาณ 40%) |
| Surname total | family/background power (ประมาณ 20%) |
| Combined total | the overall life picture (ประมาณ 40%) |
| Reduced number | a secondary note; reduce `65 → 6+5=11 → 1+1=2` |

Read the **full totals first**; the reduced number is a nuance, not a replacement. If the full
total is auspicious and the reduced one is not, say so plainly instead of treating the name as
bad.

### 4. Present

- Show the letter-by-letter sum for the first name and surname (one line each).
- Give the verdict — ให้คุณ / ปานกลาง / ให้โทษ — only when the table records it.
- Quote a meaning only from `references/meanings.md`; if the number is not there, give the
  number and point to the source table instead of inventing a reading.
- Keep it short: three numbers, one meaning each, then a two-sentence synthesis.

### 5. State the limits

End with one line:

> เป็นความเชื่อเชิงตำราเลขศาสตร์ไทย เพื่อความบันเทิง ไม่ใช่คำทำนายตายตัว

Also say which table was used if the user is comparing sites, because tables differ on a few
characters (notably ไม้ตรี = 7, ํ = 0, and some versions put ฎ/ฮ/ฬ in another row).

## Rules

1. **Spelling first.** Never calculate from a transliteration or a guessed surname.
2. **Use the shipped table.** Do not mix in another site's values mid-calculation.
3. **Full total before reduced total.** Do not lead with 11/22/33 or a single digit.
4. **No invented meanings.** Unknown total → number + source pointer, not a fabricated reading.
5. **No high-stakes advice.** Health, money, law, safety: describe the tradition, decline the advice.
6. **Do not shame.** A "ให้โทษ" number is a traditional caution, not a verdict on a person.
7. **Respect privacy.** A name is personal data; do not publish it without permission.

## Progressive disclosure

- `references/table.md` — the complete digit table, edge characters, and source links.
- `references/meanings.md` — verdicts and readings shipped with this skill.
- `assets/report-template.md` — a three-number report skeleton.
- `scripts/name.py` — the calculator (import `summarize`/`letters` for other tools).
- `scripts/selftest.py` — regression checks; run after editing the table.
