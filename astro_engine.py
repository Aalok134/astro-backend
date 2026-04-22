import swisseph as swe

RASHIS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

NAKSHATRAS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta",
    "Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

NAKSHATRA_SIZE = 360 / 27

EXALTATION = {
    swe.SUN: 1,
    swe.MOON: 2,
    swe.MARS: 10,
    swe.MERCURY: 6,
    swe.JUPITER: 4,
    swe.VENUS: 12,
    swe.SATURN: 7
}

DEBILITATION = {
    swe.SUN: 7,
    swe.MOON: 8,
    swe.MARS: 4,
    swe.MERCURY: 12,
    swe.JUPITER: 10,
    swe.VENUS: 6,
    swe.SATURN: 1
}

OWN_SIGNS = {
    swe.SUN: [5],
    swe.MOON: [4],
    swe.MARS: [1, 8],
    swe.MERCURY: [3, 6],
    swe.JUPITER: [9, 12],
    swe.VENUS: [2, 7],
    swe.SATURN: [10, 11]
}


def normalize(L):
    return L % 360


def get_rashi(longitude):
    return RASHIS[int(normalize(longitude) // 30)]


def get_nakshatra(longitude):
    longitude = normalize(longitude)
    nak_index = int(longitude // NAKSHATRA_SIZE)
    pada = int((longitude % NAKSHATRA_SIZE) // (NAKSHATRA_SIZE / 4)) + 1
    return NAKSHATRAS[nak_index], pada


def calculate_planet(jd, planet_id):

    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    result = swe.calc_ut(jd, planet_id, flags)[0]

    longitude_raw = normalize(result[0])
    speed = result[3]

    nak_index = int(longitude_raw // NAKSHATRA_SIZE)
    degree_in_nak = longitude_raw % NAKSHATRA_SIZE

    sign_index = int(longitude_raw // 30) + 1
    degree_in_sign = round(longitude_raw % 30, 6)

    rashi = get_rashi(longitude_raw)
    nak, pada = get_nakshatra(longitude_raw)

    longitude = round(longitude_raw, 6)

    if planet_id == swe.MEAN_NODE:
        exalted = sign_index == 2
        debilitated = sign_index == 8

        return {
            "longitude": longitude,
            "degree_in_sign": degree_in_sign,
            "rashi": rashi,
            "nakshatra": nak,
            "pada": pada,
            "nakshatra_index": nak_index,
            "degree_in_nakshatra": round(degree_in_nak, 8),
            "retrograde": True,
            "exalted": exalted,
            "debilitated": debilitated
        }

    retrograde = speed < 0
    exalted = sign_index == EXALTATION.get(planet_id)
    debilitated = sign_index == DEBILITATION.get(planet_id)
    own_sign = sign_index in OWN_SIGNS.get(planet_id, [])

    return {
        "longitude": longitude,
        "degree_in_sign": degree_in_sign,
        "rashi": rashi,
        "nakshatra": nak,
        "pada": pada,
        "nakshatra_index": nak_index,
        "degree_in_nakshatra": round(degree_in_nak, 8),
        "retrograde": retrograde,
        "exalted": exalted,
        "debilitated": debilitated,
        "own_sign": own_sign
    }


def calculate_lagna(jd, lat, lon):

    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P', flags)

    asc_longitude = normalize(ascmc[0])

    rashi = get_rashi(asc_longitude)
    nak, pada = get_nakshatra(asc_longitude)

    return {
        "longitude": round(asc_longitude, 6),
        "degree_in_sign": round(asc_longitude % 30, 6),
        "rashi": rashi,
        "nakshatra": nak,
        "pada": pada
    }


def is_combust(sun_long, planet_long, planet_id):

    diff = abs(sun_long - planet_long)
    if diff > 180:
        diff = 360 - diff

    combustion_orbs = {
        swe.MERCURY: 14,
        swe.VENUS: 10,
        swe.MARS: 17,
        swe.JUPITER: 11,
        swe.SATURN: 15
    }

    if planet_id not in combustion_orbs:
        return False

    return diff <= combustion_orbs[planet_id]
