"""FastAPI server exposing solar production data.

Run with:
    uvicorn api.server:app --host 0.0.0.0 --port 8000
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv
from enphase_api.local.gateway import Gateway
from fastapi import FastAPI, HTTPException

# Allow imports from the project root (for token_manager).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from token_manager import get_valid_token

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "local.env"))

ENPHASE_USERNAME = os.environ["ENPHASE_USERNAME"]
ENPHASE_PASSWORD = os.environ["ENPHASE_PASSWORD"]
IQ_GATEWAY_SERIAL_NUMBER = os.environ["IQ_GATEWAY_SERIAL_NUMBER"]
IQ_GATEWAY_HOST = os.environ.get("IQ_GATEWAY_HOST", "https://envoy.local")
DATABASE_URL = os.environ["DATABASE_URL"]

app = FastAPI(title="Solar Production API")


def _get_db():
    """Return a new database connection."""
    return psycopg2.connect(DATABASE_URL)


def _get_gateway():
    """Return an authenticated Gateway instance."""
    token = get_valid_token(ENPHASE_USERNAME, ENPHASE_PASSWORD, IQ_GATEWAY_SERIAL_NUMBER)
    gw = Gateway(IQ_GATEWAY_HOST)
    if not gw.login(token):
        raise HTTPException(status_code=502, detail="Failed to log in to the gateway.")
    return gw


@app.get("/solar/current-power")
def current_power():
    """Live current solar production in watts, queried directly from the gateway."""
    gw = _get_gateway()
    data = gw.api_call("/production.json")

    inverters = next(p for p in data["production"] if p["type"] == "inverters")
    eim = next((p for p in data["production"] if p["type"] == "eim"), None)

    return {
        "watts_now": inverters.get("wNow"),
        "watts_now_meter": eim["wNow"] if eim and eim.get("activeCount", 0) > 0 else None,
        "active_inverter_count": inverters.get("activeCount"),
    }


@app.get("/solar/today")
def today_production():
    """Current day's solar production from the most recent collected reading."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT recorded_at, wh_today, watts_now, watts_now_meter, active_inverter_count
                FROM solar_production
                WHERE recorded_at::date = CURRENT_DATE
                ORDER BY recorded_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No data recorded for today.")

    return {
        "date": row[0].date().isoformat(),
        "wh_today": row[1],
        "latest_watts": row[2],
        "latest_watts_meter": row[3],
        "active_inverter_count": row[4],
        "recorded_at": row[0].isoformat(),
    }


@app.get("/solar/yesterday")
def yesterday_production():
    """Previous day's solar production summary from collected readings."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    recorded_at::date AS day,
                    MAX(wh_today) AS wh_total,
                    MAX(watts_now) AS peak_watts,
                    MAX(watts_now_meter) AS peak_watts_meter,
                    COUNT(*) AS reading_count
                FROM solar_production
                WHERE recorded_at::date = CURRENT_DATE - INTERVAL '1 day'
                GROUP BY recorded_at::date
            """)
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No data recorded for yesterday.")

    return {
        "date": row[0].isoformat(),
        "wh_total": row[1],
        "peak_watts": row[2],
        "peak_watts_meter": row[3],
        "reading_count": row[4],
    }


@app.get("/energy/yesterday")
def yesterday_energy_consumption():
    """Previous day's SRP energy consumption. Not yet implemented."""
    raise HTTPException(status_code=501, detail="SRP consumption endpoint not yet implemented.")
