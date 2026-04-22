from astro_engine import get_nakshatra
import math

RASHIS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

def normalize(L):
    return L % 360

def extract_sign_deg(L):
    L = normalize(L)
    sign = int(L // 30) + 1
    deg = L % 30
    return sign, deg

def advance(sign, n):
    return ((sign - 1 + n) % 12) + 1

def build_output(sign, internal_deg):
    longitude = normalize((sign - 1) * 30 + internal_deg)
    rashi = RASHIS[sign - 1]
    nak, pada = get_nakshatra(longitude)

    return {
        "longitude": round(longitude, 6),
        "degree_in_sign": round(longitude % 30, 6),
        "rashi": rashi,
        "nakshatra": nak,
        "pada": pada
    }

def calculate_d9(longitude):
    sign, deg = extract_sign_deg(longitude)
    part_size = 30 / 9
    index = int(math.floor(deg / part_size)) + 1

    if sign in [1,4,7,10]:
        start = sign
    elif sign in [2,5,8,11]:
        start = advance(sign, 8)
    else:
        start = advance(sign, 4)

    result_sign = advance(start, index - 1)
    internal_deg = (deg % part_size) / part_size * 30

    return build_output(result_sign, internal_deg)

def calculate_d10(longitude):
    sign, deg = extract_sign_deg(longitude)
    part_size = 30 / 10
    index = int(math.floor(deg / part_size)) + 1

    if sign % 2 == 1:
        start = sign
    else:
        start = advance(sign, 8)

    result_sign = advance(start, index - 1)
    internal_deg = (deg % part_size) / part_size * 30

    return build_output(result_sign, internal_deg)
