"""Five-system divination engine: Thai, Bazi, Vedic, Western and Human Design.

Pure functions, standard library only. The ephemeris is deliberately approximate:
Meeus' low-precision Sun/Moon, JPL's 1800-2050 Keplerian elements for the planets,
and a mean lunar node. Good enough for traditional chart work, not for astronomy.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

DEG = math.pi / 180.0
RAD = 180.0 / math.pi


def norm360(value: float) -> float:
    return value % 360.0


def norm180(value: float) -> float:
    result = norm360(value)
    return result - 360.0 if result > 180.0 else result


def julian_day(year: int, month: int, day: float, hours: float = 0.0) -> float:
    """Julian Day from a civil date and a UT hour, Gregorian after 1582-10-15."""
    y, m = year, month
    if m <= 2:
        y -= 1
        m += 12
    fraction = day + hours / 24.0
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    return (
        math.floor(365.25 * (y + 4716))
        + math.floor(30.6001 * (m + 1))
        + fraction
        + b
        - 1524.5
    )


def julian_day_local(year: int, month: int, day: int, hh: int, mi: int, tz: float) -> float:
    return julian_day(year, month, day, hh + mi / 60.0) - tz / 24.0


def civil_from_jd(jd: float) -> dict:
    z = math.floor(jd + 0.5)
    f = jd + 0.5 - z
    a = z
    if z >= 2299161:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - math.floor(alpha / 4)
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    dd = math.floor(365.25 * c)
    e = math.floor((b - dd) / 30.6001)
    day = b - dd - math.floor(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    d = math.floor(day)
    return {"y": year, "m": month, "d": d, "hours": (day - d) * 24.0}


def obliquity(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return 23.439291 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t * t * t


def sun_longitude(jd: float) -> float:
    """Apparent tropical longitude of the Sun in degrees (Meeus, low precision)."""
    t = (jd - 2451545.0) / 36525.0
    l0 = norm360(280.46646 + 36000.76983 * t + 0.0003032 * t * t)
    m = norm360(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m * DEG)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m * DEG)
        + 0.000289 * math.sin(3 * m * DEG)
    )
    omega = 125.04 - 1934.136 * t
    return norm360(l0 + c - 0.00569 - 0.00478 * math.sin(omega * DEG))


def moon_longitude(jd: float) -> float:
    """Geocentric ecliptic longitude of the Moon in degrees (Meeus, truncated)."""
    t = (jd - 2451545.0) / 36525.0
    lp = norm360(
        218.3164477
        + 481267.88123421 * t
        - 0.0015786 * t * t
        + t**3 / 538841
        - t**4 / 65194000
    )
    d = norm360(
        297.8501921
        + 445267.1114034 * t
        - 0.0018819 * t * t
        + t**3 / 545868
        - t**4 / 113065000
    )
    m = norm360(357.5291092 + 35999.0502909 * t - 0.0001536 * t * t + t**3 / 24490000)
    mp = norm360(
        134.9633964
        + 477198.8675055 * t
        + 0.0087414 * t * t
        + t**3 / 69699
        - t**4 / 14712000
    )
    f = norm360(
        93.272095
        + 483202.0175233 * t
        - 0.0036539 * t * t
        - t**3 / 3526000
        + t**4 / 863310000
    )
    s = lambda deg: math.sin(deg * DEG)  # noqa: E731
    lon = (
        lp
        + 6.288774 * s(mp)
        + 1.274027 * s(2 * d - mp)
        + 0.658314 * s(2 * d)
        + 0.213618 * s(2 * mp)
        - 0.185116 * s(m)
        - 0.114332 * s(2 * f)
        + 0.058793 * s(2 * d - 2 * mp)
        + 0.057066 * s(2 * d - m - mp)
        + 0.053322 * s(2 * d + mp)
        + 0.045758 * s(2 * d - m)
        - 0.040923 * s(mp - m)
        - 0.03472 * s(d)
        - 0.030383 * s(m + mp)
        - 0.015327 * s(2 * f - 2 * d)
        + 0.01098 * s(mp - 4 * d)
    )
    return norm360(lon)


def mean_node(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return norm360(
        125.0445479
        - 1934.1362891 * t
        + 0.0020754 * t * t
        + t**3 / 467441
        - t**4 / 60616000
    )


def gmst(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return norm360(
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
        - t**3 / 38710000
    )


def precession(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return 1.396971 * t + 0.0003086 * t * t


ELEMENTS = {
    "mercury": [0.38709927, 0.00000037, 0.20563593, 0.00001906, 7.00497902, -0.00594749,
                252.2503235, 149472.67411175, 77.45779628, 0.16047689, 48.33076593, -0.12534081],
    "venus": [0.72333566, 0.0000039, 0.00677672, -0.00004107, 3.39467605, -0.0007889,
              181.9790995, 58517.81538729, 131.60246718, 0.00268329, 76.67984255, -0.27769418],
    "earth": [1.00000261, 0.00000562, 0.01671123, -0.00004392, -0.00001531, -0.01294668,
              100.46457166, 35999.37244981, 102.93768193, 0.32327364, 0.0, 0.0],
    "mars": [1.52371034, 0.00001847, 0.0933941, 0.00007882, 1.84969142, -0.00813131,
             -4.55343205, 19140.30268499, -23.94362959, 0.44441088, 49.55953891, -0.29257343],
    "jupiter": [5.202887, -0.00011607, 0.04838624, -0.00013253, 1.30439695, -0.00183714,
                34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106],
    "saturn": [9.53667594, -0.0012506, 0.05386179, -0.00050991, 2.48599187, 0.00193609,
               49.95424423, 1222.49362201, 92.59887831, -0.41897216, 113.66242448, -0.28867794],
    "uranus": [19.18916464, -0.00196176, 0.04725744, -0.00004397, 0.77263783, -0.00242939,
               313.23810451, 428.48202785, 170.9542763, 0.40805281, 74.01692503, 0.04240589],
    "neptune": [30.06992276, 0.00026291, 0.00859048, 0.00005105, 1.77004347, 0.00035372,
                -55.12002969, 218.45945325, 44.96476227, -0.32241464, 131.78422574, -0.00508664],
    "pluto": [39.48211675, -0.00031596, 0.2488273, 0.0000517, 17.14001206, 0.00004818,
              238.92903833, 145.20780515, 224.06891629, -0.04062942, 110.30393684, -0.01183482],
}


def _helio(name: str, t: float) -> dict:
    e = ELEMENTS[name]
    a = e[0] + e[1] * t
    ecc = e[2] + e[3] * t
    inc = (e[4] + e[5] * t) * DEG
    mean_lon = e[6] + e[7] * t
    peri = e[8] + e[9] * t
    node = (e[10] + e[11] * t) * DEG
    m = norm360(mean_lon - peri) * DEG
    ea = m
    for _ in range(10):
        delta = (ea - ecc * math.sin(ea) - m) / (1 - ecc * math.cos(ea))
        ea -= delta
        if abs(delta) < 1e-11:
            break
    xp = a * (math.cos(ea) - ecc)
    yp = a * math.sqrt(1 - ecc * ecc) * math.sin(ea)
    w = (peri - e[10] - e[11] * t) * DEG
    cw, sw = math.cos(w), math.sin(w)
    cO, sO = math.cos(node), math.sin(node)
    ci, si = math.cos(inc), math.sin(inc)
    x = (cw * cO - sw * sO * ci) * xp + (-sw * cO - cw * sO * ci) * yp
    y = (cw * sO + sw * cO * ci) * xp + (-sw * sO + cw * cO * ci) * yp
    z = sw * si * xp + cw * si * yp
    return {"x": x, "y": y, "z": z}


def planet_longitudes(jd: float) -> dict:
    t = (jd - 2451545.0) / 36525.0
    earth = _helio("earth", t)
    out = {}
    for name in ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"):
        p = _helio(name, t)
        x = p["x"] - earth["x"]
        y = p["y"] - earth["y"]
        out[name] = norm360(math.atan2(y, x) * RAD + precession(jd))
    return out


def angles(jd: float, lat_deg: float, lon_deg: float) -> dict:
    """Tropical ascendant and midheaven. Ascendant can be None at the poles."""
    lst = norm360(gmst(jd) + lon_deg)
    eps = obliquity(jd) * DEG
    phi = lat_deg * DEG

    def altitude(lam_deg: float) -> float:
        lam = lam_deg * DEG
        alpha = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
        delta = math.asin(math.sin(eps) * math.sin(lam))
        hour = norm180(lst - alpha * RAD) * DEG
        return math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(hour)

    roots = []
    prev_lam = 0.0
    prev = altitude(0.0)
    for i in range(1, 721):
        lam = i * 0.5
        cur = altitude(lam)
        if (prev <= 0 < cur) or (prev >= 0 > cur):
            lo, hi, f_lo = prev_lam, lam, prev
            for _ in range(40):
                mid = (lo + hi) / 2
                f_mid = altitude(mid)
                if (f_lo <= 0 < f_mid) or (f_lo >= 0 > f_mid):
                    hi = mid
                else:
                    lo = mid
                    f_lo = f_mid
            root = (lo + hi) / 2
            alpha = math.atan2(
                math.cos(eps) * math.sin(root * DEG), math.cos(root * DEG)
            ) * RAD
            hour = norm180(lst - alpha)
            roots.append({"lon": norm360(root), "rising": hour < 0})
        prev_lam, prev = lam, cur

    asc = next((r for r in roots if r["rising"]), roots[0] if roots else None)
    mc = norm360(math.atan2(math.sin(lst * DEG), math.cos(lst * DEG) * math.cos(eps)) * RAD)
    return {"asc": asc["lon"] if asc else None, "mc": mc}


def ayanamsa(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return 23.85236 + 1.396971 * t + 0.0003086 * t * t


SIGNS = ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
         "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
SIGN_GLYPHS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]


def sign_of(lon: float) -> int:
    return int(norm360(lon) // 30)


def deg_in_sign(lon: float) -> float:
    return norm360(lon) % 30


def fmt_deg(lon: float) -> str:
    total = norm360(lon) % 30
    d = int(total)
    m_float = (total - d) * 60
    m = int(m_float)
    s = round((m_float - m) * 60)
    if s == 60:
        s = 0
    return f"{d}°{m:02d}′{s:02d}″"


STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
STEM_KEYS = ["jia", "yi", "bing", "ding", "wu", "ji", "geng", "xin", "ren", "gui"]
BRANCH_KEYS = ["zi", "chou", "yin", "mao", "chen", "si", "wu", "wei", "shen", "you", "xu", "hai"]
STEM_ELEMENT = ["wood", "wood", "fire", "fire", "earth", "earth", "metal", "metal", "water", "water"]
BRANCH_ELEMENT = ["water", "earth", "wood", "wood", "earth", "fire", "fire", "earth", "metal", "metal", "earth", "water"]
STEM_POLARITY = ["yang", "yin", "yang", "yin", "yang", "yin", "yang", "yin", "yang", "yin"]


def sexagenary_day(jdn: int) -> int:
    return ((jdn - 11) % 60 + 60) % 60


def _local_jdn(year: int, month: int, day: int) -> int:
    return round(julian_day(year, month, day, 12))


def solar_term_jd(year: int, target: float) -> float:
    base = julian_day(year, 1, 1, 12)
    best, best_diff = 0, 400.0
    for d in range(366):
        diff = abs(norm180(sun_longitude(base + d) - target))
        if diff < best_diff:
            best_diff, best = diff, d
    t = base + best
    for _ in range(12):
        diff = norm180(sun_longitude(t) - target)
        if abs(diff) < 1e-6:
            break
        t -= diff / 0.98564736
    return t


def compute_bazi(b: dict) -> dict:
    jd = julian_day_local(b["y"], b["m"], b["d"], b["hh"], b["mi"], b["tz"])
    sun = sun_longitude(jd)
    lmt_hours = b["hh"] + b["mi"] / 60.0 + (b["lon"] - b["tz"] * 15.0) / 15.0
    lmt_day_shift = math.floor(lmt_hours / 24.0)
    lmt_clock = ((lmt_hours % 24) + 24) % 24
    day_jdn = _local_jdn(b["y"], b["m"], b["d"]) + lmt_day_shift + (1 if lmt_clock >= 23 else 0)
    day_index = sexagenary_day(day_jdn)

    lichun = solar_term_jd(b["y"], 315)
    solar_year = b["y"] if jd >= lichun else b["y"] - 1
    year_index = ((solar_year - 4) % 60 + 60) % 60
    year_stem = year_index % 10
    year_branch = year_index % 12

    month = int(norm360(sun - 315) // 30) + 1
    month_branch = (month + 1) % 12
    month_stem = ((year_stem % 5) * 2 + 2 + (month - 1)) % 10

    hour_branch = int(((lmt_clock + 1) % 24) // 2) % 12
    day_stem = day_index % 10
    hour_stem = ((day_stem % 5) * 2 + hour_branch) % 10

    pillars = [
        {"id": "year", "stem": year_stem, "branch": year_branch},
        {"id": "month", "stem": month_stem, "branch": month_branch},
        {"id": "day", "stem": day_stem, "branch": day_index % 12},
        {"id": "hour", "stem": hour_stem, "branch": hour_branch},
    ]
    elements = {"wood": 0, "fire": 0, "earth": 0, "metal": 0, "water": 0}
    for pillar in pillars:
        elements[STEM_ELEMENT[pillar["stem"]]] += 1
        elements[BRANCH_ELEMENT[pillar["branch"]]] += 1
    return {
        "jd": jd,
        "sun": sun,
        "lmt_clock": lmt_clock,
        "lmt_day_shift": lmt_day_shift,
        "month": month,
        "solar_year": solar_year,
        "pillars": pillars,
        "elements": elements,
        "day_master": STEM_KEYS[day_stem],
        "day_master_element": STEM_ELEMENT[day_stem],
        "day_master_polarity": STEM_POLARITY[day_stem],
        "year_index": year_index,
    }


NAKSHATRAS = [
    "ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra", "punarvasu", "pushya", "ashlesha",
    "magha", "purvaPhalguni", "uttaraPhalguni", "hasta", "chitra", "swati", "vishakha", "anuradha", "jyeshtha",
    "mula", "purvaAshadha", "uttaraAshadha", "shravana", "dhanishta", "shatabhisha", "purvaBhadrapada",
    "uttaraBhadrapada", "revati",
]
DASHA_ORDER = ["ketu", "venus", "sun", "moon", "mars", "rahu", "jupiter", "saturn", "mercury"]
DASHA_YEARS = {"ketu": 7, "venus": 20, "sun": 6, "moon": 10, "mars": 7, "rahu": 18,
               "jupiter": 16, "saturn": 19, "mercury": 17}


def nakshatra_of(lon: float) -> dict:
    sid = norm360(lon)
    span = 360.0 / 27.0
    index = int(sid // span)
    within = sid - index * span
    return {"index": index, "pada": int(within // (span / 4)) + 1, "fraction": within / span}


def vimshottari(birth: datetime, moon_sidereal: float) -> dict:
    nak = nakshatra_of(moon_sidereal)
    start_index = nak["index"] % 9
    lord = DASHA_ORDER[start_index]
    total = DASHA_YEARS[lord]
    balance = (1 - nak["fraction"]) * total
    periods = []
    cursor = birth
    periods.append({"lord": lord, "years": balance, "start": cursor,
                    "end": cursor + timedelta(days=balance * 365.25)})
    cursor = cursor + timedelta(days=balance * 365.25)
    for i in range(1, 6):
        next_lord = DASHA_ORDER[(start_index + i) % 9]
        years = DASHA_YEARS[next_lord]
        periods.append({"lord": next_lord, "years": years, "start": cursor,
                        "end": cursor + timedelta(days=years * 365.25)})
        cursor = cursor + timedelta(days=years * 365.25)
    return {"nak": nak, "periods": periods}


ASPECTS = [
    {"id": "conjunction", "angle": 0, "orb": 8},
    {"id": "opposition", "angle": 180, "orb": 8},
    {"id": "trine", "angle": 120, "orb": 6},
    {"id": "square", "angle": 90, "orb": 6},
    {"id": "sextile", "angle": 60, "orb": 4},
]


def compute_aspects(points: list[dict]) -> list[dict]:
    out = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            delta = abs(norm180(points[i]["lon"] - points[j]["lon"]))
            for aspect in ASPECTS:
                if abs(delta - aspect["angle"]) <= aspect["orb"]:
                    out.append({"a": points[i]["id"], "b": points[j]["id"],
                                "aspect": aspect["id"], "orb": abs(delta - aspect["angle"])})
                    break
    return sorted(out, key=lambda item: item["orb"])


GATE_ORDER = [
    41, 19, 13, 49, 30, 55, 37, 63, 22, 36, 25, 17, 21, 51, 42, 3, 27, 24, 2, 23, 8, 20, 16, 35,
    45, 12, 15, 52, 39, 53, 62, 56, 31, 33, 7, 4, 29, 59, 40, 64, 47, 6, 46, 18, 48, 57, 32, 50,
    28, 44, 1, 43, 14, 34, 9, 5, 26, 11, 10, 58, 38, 54, 61, 60,
]
GATE_CENTER = {
    "head": [63, 64, 61],
    "ajna": [17, 24, 4, 47, 43, 11],
    "throat": [23, 8, 20, 16, 35, 45, 12, 62, 56, 31, 33],
    "g": [13, 25, 2, 15, 7, 46, 1, 10],
    "heart": [21, 51, 40, 26],
    "solar": [49, 30, 55, 37, 22, 36, 6],
    "sacral": [42, 3, 27, 29, 59, 14, 34, 9, 5],
    "spleen": [18, 48, 57, 32, 50, 28, 44],
    "root": [41, 19, 52, 39, 53, 58, 38, 54, 60],
}
CENTERS = ["head", "ajna", "throat", "g", "heart", "solar", "sacral", "spleen", "root"]
MOTORS = ["sacral", "root", "solar", "heart"]
CHANNELS = [
    (1, 8), (2, 14), (3, 60), (4, 63), (5, 15), (6, 59), (7, 31), (9, 52), (10, 20), (10, 34),
    (10, 57), (11, 56), (12, 22), (13, 33), (16, 48), (17, 62), (18, 58), (19, 49), (20, 34),
    (20, 57), (21, 45), (23, 43), (24, 61), (25, 51), (26, 44), (27, 50), (28, 38), (29, 46),
    (30, 41), (32, 54), (34, 57), (35, 36), (37, 40), (39, 55), (42, 53), (47, 64),
]
GATE_TO_CENTER = {}
for _center, _gates in GATE_CENTER.items():
    for _gate in _gates:
        GATE_TO_CENTER[_gate] = _center


def gate_of(lon: float) -> dict:
    off = norm360(lon - 302)
    raw = off // 5.625
    index = int(raw) % 64
    within = off - raw * 5.625
    return {"gate": GATE_ORDER[index], "line": int(within // 0.9375) + 1, "idx": index}


def bodygraph(active_gates: set[int]) -> dict:
    defined = set()
    channels = []
    for a, b in CHANNELS:
        if a in active_gates and b in active_gates:
            channels.append((a, b))
            ca, cb = GATE_TO_CENTER.get(a), GATE_TO_CENTER.get(b)
            if ca:
                defined.add(ca)
            if cb:
                defined.add(cb)
    adjacency = {center: [] for center in CENTERS}
    for a, b in channels:
        ca, cb = GATE_TO_CENTER.get(a), GATE_TO_CENTER.get(b)
        if ca and cb and ca != cb:
            adjacency[ca].append(cb)
            adjacency[cb].append(ca)

    motor_to_throat = False
    for motor in MOTORS:
        if motor not in defined:
            continue
        seen, queue = {motor}, [motor]
        while queue:
            current = queue.pop()
            if current == "throat":
                motor_to_throat = True
                break
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        if motor_to_throat:
            break

    sacral = "sacral" in defined
    if not defined:
        hd_type = "reflector"
    elif sacral:
        hd_type = "manifestingGenerator" if motor_to_throat else "generator"
    else:
        hd_type = "manifestor" if motor_to_throat else "projector"

    if hd_type == "reflector":
        authority = "lunar"
    elif "solar" in defined:
        authority = "emotional"
    elif sacral:
        authority = "sacral"
    elif "spleen" in defined:
        authority = "splenic"
    elif "heart" in defined:
        authority = "ego"
    elif "g" in defined:
        authority = "selfProjected"
    else:
        authority = "mental"

    groups = []
    seen = set()
    for center in defined:
        if center in seen:
            continue
        group = []
        stack = [center]
        seen.add(center)
        while stack:
            current = stack.pop()
            group.append(current)
            for nxt in adjacency[current]:
                if nxt in defined and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        groups.append(group)
    return {
        "defined": defined,
        "channels": channels,
        "type": hd_type,
        "authority": authority,
        "phases": len(groups),
        "motor_to_throat": motor_to_throat,
    }


def compute_human_design(b: dict) -> dict:
    jd = julian_day_local(b["y"], b["m"], b["d"], b["hh"], b["mi"], b["tz"])
    sun_birth = sun_longitude(jd)
    target = norm360(sun_birth - 88)
    design = jd - 88
    for _ in range(14):
        diff = norm180(sun_longitude(design) - target)
        if abs(diff) < 1e-7:
            break
        design -= diff / 0.98564736

    def bodies(moment: float) -> dict:
        sun = sun_longitude(moment)
        planets = planet_longitudes(moment)
        node = mean_node(moment)
        return {
            "sun": sun,
            "earth": norm360(sun + 180),
            "moon": moon_longitude(moment),
            "northNode": node,
            "southNode": norm360(node + 180),
            **planets,
        }

    def activations(values: dict) -> list[dict]:
        out = []
        for body_id, lon in values.items():
            gate = gate_of(lon)
            out.append({"id": body_id, "lon": lon, "gate": gate["gate"], "line": gate["line"]})
        return out

    personality = activations(bodies(jd))
    design_set = activations(bodies(design))
    active = {item["gate"] for item in personality} | {item["gate"] for item in design_set}
    graph = bodygraph(active)
    p_sun = next(item for item in personality if item["id"] == "sun")
    d_sun = next(item for item in design_set if item["id"] == "sun")
    cross = {
        "sun": p_sun["gate"],
        "earth": next(item for item in personality if item["id"] == "earth")["gate"],
        "designSun": d_sun["gate"],
        "designEarth": next(item for item in design_set if item["id"] == "earth")["gate"],
    }
    return {
        "jd": jd,
        "design_jd": design,
        "personality": personality,
        "design_set": design_set,
        **graph,
        "profile": f"{p_sun['line']}/{d_sun['line']}",
        "cross": cross,
    }


THAI_DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def thai_day_of(year: int, month: int, day: int) -> dict:
    weekday = (datetime(year, month, day).weekday() + 1) % 7
    return {"weekday": weekday}


def thai_animal_year(year: int, month: int, day: int) -> int:
    solar_year = year - 1 if (month < 4 or (month == 4 and day < 13)) else year
    return ((solar_year - 4) % 12 + 12) % 12


def compute_all(b: dict) -> dict:
    jd = julian_day_local(b["y"], b["m"], b["d"], b["hh"], b["mi"], b["tz"])
    sun = sun_longitude(jd)
    moon = moon_longitude(jd)
    planets = planet_longitudes(jd)
    house = angles(jd, b["lat"], b["lon"])
    ayan = ayanamsa(jd)
    sun_sid = norm360(sun - ayan)
    moon_sid = norm360(moon - ayan)
    asc_sid = None if house["asc"] is None else norm360(house["asc"] - ayan)
    node = mean_node(jd)
    sidereal = {
        "sun": sun_sid,
        "moon": moon_sid,
        "asc": asc_sid,
        "mars": norm360(planets["mars"] - ayan),
        "mercury": norm360(planets["mercury"] - ayan),
        "jupiter": norm360(planets["jupiter"] - ayan),
        "venus": norm360(planets["venus"] - ayan),
        "saturn": norm360(planets["saturn"] - ayan),
        "rahu": norm360(node - ayan),
        "ketu": norm360(node + 180 - ayan),
    }
    birth = datetime(b["y"], b["m"], b["d"], b["hh"], b["mi"])
    vim = vimshottari(birth, moon_sid)
    western_points = [{"id": "sun", "lon": sun}, {"id": "moon", "lon": moon}]
    western_points += [{"id": key, "lon": value} for key, value in planets.items()]
    hd = compute_human_design(b)
    bazi = compute_bazi(b)
    return {
        "meta": {
            "jd": jd, "sun": sun, "moon": moon, "asc": house["asc"], "mc": house["mc"],
            "ayanamsa": ayan, "ascSid": asc_sid, "sunSid": sun_sid, "moonSid": moon_sid,
            "planets": planets, "birthDate": birth,
        },
        "bazi": bazi,
        "vedic": {**sidereal, "vim": vim},
        "western": {
            "points": western_points,
            "asc": house["asc"],
            "mc": house["mc"],
            "aspects": compute_aspects(western_points),
        },
        "thai": {
            "weekday": (datetime(b["y"], b["m"], b["d"]).weekday() + 1) % 7,
            "animal": thai_animal_year(b["y"], b["m"], b["d"]),
            "sign": int(sun_sid // 30),
            "lunarPhase": None,
        },
        "hd": hd,
    }
