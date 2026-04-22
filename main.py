from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime
import swisseph as swe
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

# -------- AI IMPORTS --------
from ai.prompt_builder import build_system_prompt, build_user_prompt
from ai.ai_service import get_ai_response

from astro_engine import (
    calculate_planet,
    calculate_lagna,
    get_rashi,
    get_nakshatra,
    is_combust
)

from varga_engine import calculate_d9, calculate_d10
from dasha_engine import VimshottariDasha

app = FastAPI()


# ----------------------------
# MODELS
# ----------------------------

class BirthDetails(BaseModel):
    date: str
    time: str
    place: str


class ChatRequest(BaseModel):
    chart_summary: str
    current_dasha: str
    history: list
    user_message: str


# ----------------------------
# LOCATION + TIME
# ----------------------------

geolocator = Nominatim(user_agent="vedic_app")
tf = TimezoneFinder()

RASHIS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]


def get_location_data(place_name):
    location = geolocator.geocode(place_name)
    if not location:
        raise Exception("Location not found")

    lat = location.latitude
    lon = location.longitude
    timezone_str = tf.timezone_at(lat=lat, lng=lon)

    return lat, lon, timezone_str


def get_julian_day(date_str, time_str, timezone_str):

    if len(time_str.split(":")) == 2:
        time_str += ":00"

    dt_local = datetime.strptime(
        f"{date_str} {time_str}",
        "%d/%m/%Y %H:%M:%S"
    )

    tz = pytz.timezone(timezone_str)
    dt_local = tz.localize(dt_local)
    dt_utc = dt_local.astimezone(pytz.utc)

    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600
    )

    return jd, dt_utc


# ----------------------------
# HOUSE ASSIGNMENT (Whole Sign)
# ----------------------------

def assign_whole_sign_houses(chart_block):

    lagna_sign = chart_block["Lagna"]["rashi"]
    lagna_index = RASHIS.index(lagna_sign)

    for body in chart_block:
        planet_sign = chart_block[body]["rashi"]
        planet_index = RASHIS.index(planet_sign)
        chart_block[body]["house"] = (
            (planet_index - lagna_index) % 12 + 1
        )

    return chart_block


# ----------------------------
# GENERATE CHART
# ----------------------------

@app.post("/generate-chart")
def generate_chart(
    birth: BirthDetails,
    dasha_depth: int = Query(5, ge=1, le=5)
):

    swe.set_sid_mode(swe.SIDM_LAHIRI)

    lat, lon, timezone_str = get_location_data(birth.place)
    jd, birth_datetime_utc = get_julian_day(
        birth.date,
        birth.time,
        timezone_str
    )

    planets_ids = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mars": swe.MARS,
        "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS,
        "Saturn": swe.SATURN,
        "Rahu": swe.MEAN_NODE
    }

    final_output = {}

    # ---------- D1 ----------
    lagna_d1 = calculate_lagna(jd, lat, lon)

    d1_planets = {}
    for name, pid in planets_ids.items():
        d1_planets[name] = calculate_planet(jd, pid)

    sun_long = d1_planets["Sun"]["longitude"]

    # Derive Ketu
    rahu_long = d1_planets["Rahu"]["longitude"]
    ketu_long = (rahu_long + 180) % 360

    ketu_rashi = get_rashi(ketu_long)
    ketu_nak, ketu_pada = get_nakshatra(ketu_long)

    divisions = {
        "D1": None,
        "D9": calculate_d9,
        "D10": calculate_d10
    }

    for key, func in divisions.items():

        chart_block = {}

        if key == "D1":
            lagna_data = lagna_d1
        else:
            lagna_data = func(lagna_d1["longitude"])

        chart_block["Lagna"] = lagna_data

        for name, pid in planets_ids.items():

            if key == "D1":
                planet_data = d1_planets[name].copy()

                if name not in ["Sun", "Rahu"]:
                    planet_data["combust"] = is_combust(
                        sun_long,
                        planet_data["longitude"],
                        pid
                    )
            else:
                planet_data = func(d1_planets[name]["longitude"])

            chart_block[name] = planet_data

        if key == "D1":
            ketu_data = {
                "longitude": round(ketu_long, 6),
                "degree_in_sign": round(ketu_long % 30, 6),
                "rashi": ketu_rashi,
                "nakshatra": ketu_nak,
                "pada": ketu_pada,
                "retrograde": True
            }
        else:
            ketu_data = func(ketu_long)

        chart_block["Ketu"] = ketu_data
        chart_block = assign_whole_sign_houses(chart_block)
        final_output[key] = chart_block

    # ---------- DASHA ----------
    moon_data = final_output["D1"]["Moon"]

    dasha_engine = VimshottariDasha(
        birth_datetime_utc,
        moon_data["nakshatra_index"],
        moon_data["degree_in_nakshatra"],
        depth=dasha_depth
    )

    dashas = dasha_engine.build_full_tree()

    mahadasha_list = [
        {
            "planet": md["planet"],
            "start": md["start"],
            "end": md["end"]
        }
        for md in dashas["vimshottari"]["mahadashas"]
    ]

    final_output["Mahadashas"] = mahadasha_list
    final_output["Current_Dasha"] = dasha_engine.get_current_dasha(dashas)

    return final_output


# ----------------------------
# CHAT ENDPOINT
# ----------------------------

@app.post("/chat")
def chat(request: ChatRequest):

    system_prompt = build_system_prompt()

    user_prompt = build_user_prompt(
        request.chart_summary,
        request.current_dasha,
        request.history,
        request.user_message
    )

    ai_reply = get_ai_response(system_prompt, user_prompt)

    return {
        "assistant_message": ai_reply
    }