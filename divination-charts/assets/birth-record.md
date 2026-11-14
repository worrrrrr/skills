# Birth record intake

Paste this once and ask the user to fill the missing lines. Do not ask one field at a time.

```text
Birth date (CE, YYYY-MM-DD):
Birth time (HH:MM, 24h):
UTC offset at birth (e.g. +7, -5):
Birth place (city, country):
Latitude (decimal, optional if city is known):
Longitude (decimal, optional if city is known):
```

## Rules

- **Buddhist year:** if the user writes พ.ศ., convert with `CE = พ.ศ. − 543`. Confirm the
  converted year before computing.
- **Unknown time:** use `12:00`, and say the ascendant, the Thai ascendant and the Human
  Design profile are uncertain. Never move the time to make a chart "nicer".
- **DST:** ask for the offset that was in force at birth, not the current offset.
- **Coordinates:** if the city is known and its coordinates are verifiable, state the pair you
  use. If not, ask; do not invent a location.
- **Privacy:** the birth record is personal data. Keep it in the conversation; do not write it
  to a repo, a log or a third-party service.

## Thailand defaults

| Place | Latitude | Longitude | UTC |
|---|---|---|---|
| Bangkok | 13.7563 | 100.5018 | +7 |
| Chiang Mai | 18.7883 | 98.9853 | +7 |
| Khon Kaen | 16.4419 | 102.8360 | +7 |
| Phuket | 7.8804 | 98.3923 | +7 |

Use these only when the user names the place; they are a starting point, not a guess.
