# Chart report skeleton

Use the user's language. Drop a section the user did not ask for; keep the order below when
the request is open-ended. Values come from `scripts/chart.py --json`; do not retype numbers.

```markdown
## <Name or "Your chart">

**Born** <date> <time> UTC<offset> · <lat>, <lon>

> One-line method note: sidereal for Vedic/Thai, tropical for Western/Human Design, Bazi from
> solar terms and local mean time.

### สากล · Western
- Sun: <sign> <degree> — <one theme>
- Moon: <sign> <degree> — <one theme>
- Ascendant: <sign> <degree>
- Tight aspects: <a> <aspect> <b> (<orb>°) — <one consequence>

### Bazi
| Pillar | Stem/Branch | Element |
|---|---|---|
| Year | | |
| Month | | |
| Day | | |
| Hour | | |

Day master: <stem> (<element>, <polarity>) — <two sentences>.
Elements: wood <n>, fire <n>, earth <n>, metal <n>, water <n> — <one sentence on balance>.

### อินเดีย · Vedic
- Lagna: <sign> <degree>
- Moon rasi: <sign> <degree>
- Nakshatra: <name>, pada <n>
- Current period: <lord>, <start> to <end>

### Human Design
- Type: <type> · Authority: <authority> · Profile: <profile>
- Defined centers: <list>
- Channels: <list>
- Incarnation cross gates: <four gates>

### ดูดวง · Thai
- Weekday: <day> (<ruler>, <colour>)
- Animal year: <animal>
- Sidereal Sun sign: <sign> <degree>

---

Astrological entertainment, not medical, financial or legal advice. Approximate ephemeris:
solar terms ~15 minutes, lunar longitude ~0.2°, mean lunar node.
```
