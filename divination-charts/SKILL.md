---
name: divination-charts
description: >-
  Computes five birth-chart systems from one birth record — Thai (วันเกิด, ราศี,
  ปีนักษัตร), Bazi (four pillars, day master, element balance), Vedic (lagna, nakshatra,
  Vimshottari), Western (planets, ascendant, aspects) and Human Design (type, authority,
  profile, gates) — then presents the result in the user's language. Use when the user asks
  for ดูดวง, a birth chart, Bazi/ปาจื้อ, ราศี, ลัคนา, นักษัตร, Human Design, or says
  "ดูดวงให้หน่อย", "อ่านดวง", "วิเคราะห์ดวง", "check my chart", "human design".
license: MIT
metadata:
  version: "1.0.0"
  tags: "divination, astrology, bazi, vedic, human-design, thai"
allowed-tools: Read Write Edit Bash Glob Grep
---

# Divination Charts

Turn one birth record into five consistent charts, computed by a deterministic script, then
read them back in the user's language without inventing facts.

The value is **one birth record, five systems, the same astronomy**. Do not compute the
astronomy by hand and do not mix vendors' conventions silently: the script fixes the
conventions and reports them.

## When to use

- The user asks for ดูดวง, อ่านดวง, วิเคราะห์ดวง, a birth chart, or one of the five systems.
- The user gives a birth date (and optionally time and place) and wants a reading.
- The user asks how a system sees them: Bazi day master, Vedic lagna/nakshatra, Western
  big three, Human Design type/authority.
- The user wants the same birth data shown through several traditions.

## When not to use

- Medical, financial, legal or safety decisions: refuse the decision, not the chart.
- No birth date: ask for it; do not guess a date or a time.
- A request for a live transit, electional (auspicious time) or synastry chart: this skill
  computes natal charts only. Say what is missing.
- A request for "lucky numbers" as fact: you may label a traditional correspondence, never a
  guarantee.

## Workflow

### 1. Collect the birth record

Ask once, in one message, for the missing fields:

| Field | Required | Notes |
|---|---|---|
| Date | yes | Gregorian/CE, 1800–2050. A Thai Buddhist year (พ.ศ.) must be converted: CE = พ.ศ. − 543 |
| Time | recommended | 24-hour `HH:MM`. If unknown, use `12:00` and say the ascendant, houses and Human Design design are uncertain |
| UTC offset | yes | e.g. `7` for Bangkok, `-5` for New York. DST changes the offset; ask for the offset at birth, not today |
| Latitude | yes | decimal degrees, −89.9..89.9 |
| Longitude | yes | decimal degrees, −180..180 |

If the user gives a city but not coordinates, use coordinates you can state a source for, or
ask. Never invent a place's coordinates. For Thailand, Bangkok is `13.7563, 100.5018`, `+7`.

Treat the birth record as personal data: do not repeat it in a public artifact unless the user
asks, and do not send it to a third-party API.

### 2. Compute

Run the script; do not re-derive the numbers in prose:

```bash
python scripts/chart.py --date 1990-01-01 --time 12:00 --tz 7 \
  --lat 13.7563 --lon 100.5018 --json
```

- Requires Python 3.11+, standard library only. No installs.
- Use `--md` for a ready Markdown report.
- Exit `0` ok, `2` could not compute, `3` usage/invalid input.
- Keep the JSON; quote exact values from it. If the script fails, report the failure instead
  of a chart.

### 3. Read the output

| Key | What it carries |
|---|---|
| `thai` | weekday, animal year (Songkran boundary), sidereal Sun sign, ascendant |
| `bazi` | solar year, month number, local mean time, four pillars, day master, element counts |
| `vedic` | lagna, Moon/Sun rasi, nakshatra + pada, nine grahas, Vimshottari periods |
| `western` | Sun/Moon/ascendant, ten planets, aspects (orb-sorted) |
| `humanDesign` | type, authority, profile, definition parts, channels, 26 activations, incarnation cross |

### 4. Present

Lead with what the user asked for, then the rest. Default order when unspecified:

1. **สากล / Western** — Sun, Moon, ascendant, then notable aspects.
2. **Bazi** — four pillars, day master first, then element balance.
3. **อินเดีย / Vedic** — lagna, Moon rasi, nakshatra + pada, current Vimshottari period.
4. **Human Design** — type → authority → profile → defined channels.
5. **ดูดวง / Thai** — weekday, animal year, sidereal sign.

Rules for the reading:

- Separate **computed** ("Sun is 10° Capricorn") from **interpretation** ("Capricorn is often
  described as…"); never present the second as measurement.
- Give one or two concrete themes per placement, not a paragraph per planet.
- Name the current Vimshottari period by date; do not call a balance period a full period.
- Human Design: state type and authority before gates; a gate alone defines nothing.
- Keep the whole answer readable: tables for placements, prose for the synthesis.

### 5. State the limits

End with a short note, once:

> Astrological entertainment, not medical, financial or legal advice. Approximate ephemeris:
> solar terms ~15 minutes, lunar longitude ~0.2°, mean lunar node. A value on a sign, gate or
> nakshatra boundary can differ from dedicated software.

Do not hide the convention: Bazi uses Li Chun at solar longitude 315°, months every 30°, the
day changes at 23:00 local mean time; Vedic uses Lahiri ayanamsa; Human Design uses the
tropical wheel with Gate 41 at 302° and design at the Sun 88° earlier.

## Rules

1. **Never invent a birth fact.** Missing date/time/place is an `unknown`, not a guess.
2. **Run the script before quoting any number.** The JSON is the source of truth.
3. **Answer in the user's language.** Keep system names recognizable (Bazi, Human Design,
   ลัคนา, นักษัตร).
4. **One reading, not five unrelated essays.** Tie the five views to the same person.
5. **No deterministic predictions.** Prefer "the tradition describes…", "this period is
   associated with…", ranges and options.
6. **No high-stakes advice.** Health, money, law, safety: decline the advice and keep the
   chart descriptive.
7. **Respect privacy.** Do not persist the birth record or paste it into third-party tools.

## DSH delivery

To surface the same engine as a DeepSeek Harness right-sidebar page, read
`references/dsh-rightbar.md`. It gives the tab registration, the client bundle shape, the theme
and locale rules, and the verification limits. Building the plugin is a separate job; this
skill owns the charts.

## Progressive disclosure

- `references/methods.md` — formulas, conventions, accuracy and sources.
- `references/interpretation.md` — what each value means, phrasing and guardrails.
- `references/dsh-rightbar.md` — optional DSH page wrapper around the same engine.
- `assets/birth-record.md` — intake checklist to paste into a question.
- `assets/report-template.md` — five-section report skeleton.
- `scripts/chart.py` — CLI: birth record in, summary JSON/Markdown out.
- `scripts/engine.py` — pure astronomy and chart functions; import it instead of copying.
- `scripts/selftest.py` — regression checks; run after editing the engine.
