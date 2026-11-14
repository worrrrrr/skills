# Methods and conventions

The engine is intentionally approximate and dependency-free. It is accurate enough for
traditional chart work, not for observational astronomy.

## Time

- Inputs are a **local civil date/time** and a **UTC offset**. The Julian Day is computed
  from the local time minus the offset; DST is the user's responsibility (ask for the offset
  in force at birth).
- The Bazi day boundary and hour pillar use **local mean solar time**:
  `LMT = civil time + (longitude - offset × 15°) / 15°`. The day changes at 23:00 LMT.
- The Thai weekday uses the civil date in the given timezone, not the UTC date.

## Sun and Moon

- Sun: Meeus, *Astronomical Algorithms*, low-precision apparent longitude. Error ≈ 0.01°.
- Moon: Meeus chapter 47, truncated series (about 15 periodic terms). Error ≈ 0.1–0.2°.
- Both are tropical longitudes referred to the equinox of date.

## Planets

- Mercury–Pluto: JPL "Approximate Positions of the Planets", Keplerian elements with
  per-century rates, valid 1800–2050. Heliocentric J2000 positions are converted to
  geocentric ecliptic longitude and precessed to the date.
- Error: about 1 arcminute for the inner planets, a few arcminutes for the outer ones.
- The lunar node uses the **mean node**, not the true node. It can differ by up to ~1.5°,
  which matters at a gate or nakshatra boundary.

## Ascendant and midheaven

- Obliquity and Greenwich mean sidereal time follow Meeus.
- The ascendant is solved numerically: scan the ecliptic, find where altitude is zero on the
  eastern horizon, bisect to 0.5° steps then 40 iterations. No Placidus/Koch houses are
  computed; a house request needs a different engine.
- The midheaven is the ecliptic point with right ascension equal to local sidereal time.

## Bazi

- **Year** turns at Li Chun, the moment the apparent Sun reaches 315°.
- **Month** is `floor(((sun - 315°) mod 360°) / 30°) + 1`; branches start at 寅 for month 1.
- **Day** is the sexagenary count `(JDN − 11) mod 60` (0 = 甲子), using the LMT date and the
  23:00 boundary.
- **Hour** branches are 2-hour blocks from 23:00; the hour stem follows the day stem
  (`(dayStem mod 5) × 2 + hourBranch) mod 10`).
- Element counts use all eight characters (four stems + four branches); no hidden stems,
  ten gods, luck pillars or useful-god analysis.
- Solar-term boundaries come from a Newton solve on the Sun's longitude; expect ~15 minutes.

## Vedic

- Sidereal longitude = tropical − **Lahiri ayanamsa**
  (`23.85236 + 1.396971 T + 0.0003086 T²`, T in Julian centuries from J2000). This is an
  approximation of the official Lahiri value; differences of a few arcseconds are possible.
- Nakshatras are 27 equal arcs of 13°20′ from 0° sidereal Aries; each has four padas.
- Vimshottari uses the 120-year cycle (Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18,
  Jupiter 16, Saturn 19, Mercury 17) with a 365.25-day year. The first period is the
  **balance** from the Moon's position in its nakshatra, not a full period.
- Rahu/Ketu use the mean node. No divisional charts (D9 etc.), no ashtakavarga, no yogas.

## Western

- Tropical zodiac, no house system. The ascendant and midheaven are included, but the chart
  does not claim equal/Placidus cusps.
- Aspects: conjunction and opposition orb 8°, trine and square 6°, sextile 4°. The list is
  orb-sorted. No minor aspects, no declinations, no midpoints.

## Thai

- Weekday from the civil date; the planetary ruler and colour follow the traditional
  Sunday–Saturday order.
- Animal year turns at **Songkran, 13 April**: January–early April still belongs to the
  previous animal year. This differs from the Chinese Li Chun boundary used by Bazi.
- The Thai sign is the **sidereal** Sun sign (same Lahiri value as the Vedic section), not the
  tropical Sun sign.

## Human Design

- The wheel divides the tropical zodiac into 64 gates of 5.625°, with **Gate 41 starting at
  302°** (2° Aquarius), then the fixed Rave Mandala order. Each gate has six lines of 0.9375°.
- **Design** is the moment the Sun was 88° earlier in the zodiac (about 88 days before birth),
  solved by Newton iteration on the solar longitude.
- The 26 activations are Sun, Earth (Sun + 180°), Moon, North/South Node, Mercury, Venus, Mars,
  Jupiter, Saturn, Uranus, Neptune and Pluto at both times; the mean node is used.
- Type: Reflector = no defined center; Sacral defined → Generator, or Manifesting Generator
  when a motor reaches the Throat; otherwise Manifestor when a motor reaches the Throat, else
  Projector.
- Authority: Emotional (Solar Plexus), Sacral, Splenic, Ego, Self-projected (G), Mental, or
  Lunar for Reflectors.
- Profile = Personality Sun line / Design Sun line. Definition = number of connected groups
  of defined centers.
- Not computed: colour/tone/base, variable, channels' gate names, incarnation-cross names,
  transit charts.

## Sources

- Jean Meeus, *Astronomical Algorithms* (2nd ed.): Sun ch. 25, Moon ch. 47, sidereal time
  ch. 12, obliquity ch. 22.
- JPL Solar System Dynamics, "Approximate Positions of the Planets":
  <https://ssd.jpl.nasa.gov/planets/approx_pos.html>
- Sexagenary day mapping used by Chinese calendar references
  (`Julian_chinese.html`, Yuk Tung Liu): <https://github.com/ytliu0/ChineseCalendar>
- Rave Mandala gate order and degree anchors: <https://www.herzwandler.net/human-design/tore/>
  and <https://thehumandesignsystem.com/blog/human-design-for-astrologers>
- Lahiri ayanamsa: standard approximation; the official value is published by the Indian
  Astronomical Ephemeris.
