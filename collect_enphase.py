"""Collect solar production data from the Enphase IQ Gateway and store in PostgreSQL.

Designed to be invoked by a scheduler (cron / Task Scheduler) every 30 minutes.
"""

import datetime
import os
import sys

import psycopg2
from dotenv import load_dotenv
from enphase_api.local.gateway import Gateway

from token_manager import get_valid_token

load_dotenv("local.env")

ENPHASE_USERNAME = os.environ["ENPHASE_USERNAME"]
ENPHASE_PASSWORD = os.environ["ENPHASE_PASSWORD"]
IQ_GATEWAY_SERIAL_NUMBER = os.environ["IQ_GATEWAY_SERIAL_NUMBER"]
IQ_GATEWAY_HOST = os.environ.get("IQ_GATEWAY_HOST", "https://envoy.local")
DATABASE_URL = os.environ["DATABASE_URL"]

INSERT_PRODUCTION_SQL = """
    INSERT INTO solar_production
        (watts_now, watts_now_meter, wh_today, wh_last_seven_days, wh_lifetime, active_inverter_count)
    VALUES (%s, %s, %s, %s, %s, %s)
"""

INSERT_INVERTER_SQL = """
    INSERT INTO inverter_readings
        (serial_number, reported_at, last_report_watts, max_report_watts)
    VALUES (%s, %s, %s, %s)
"""


def collect():
    # Get a valid token (cached or refreshed).
    token = get_valid_token(ENPHASE_USERNAME, ENPHASE_PASSWORD, IQ_GATEWAY_SERIAL_NUMBER)

    # Connect to the local gateway.
    gw = Gateway(IQ_GATEWAY_HOST)
    if not gw.login(token):
        print("Failed to log in to the gateway.", file=sys.stderr)
        sys.exit(1)

    # Fetch energy totals from the micro-inverters (PCU). The EIM whToday /
    # whLastSevenDays / whLifetime fields in /production.json are unreliable
    # (all three report the same lifetime value), so use /ivp/pdm/energy instead.
    energy = gw.api_call("/ivp/pdm/energy")
    pcu = energy["production"]["pcu"]

    watts_now = pcu.get("wattsNow")
    wh_today = pcu.get("wattHoursToday")
    wh_seven = pcu.get("wattHoursSevenDays")
    wh_lifetime = pcu.get("wattHoursLifetime")

    # Fetch inverter count and EIM meter power from /production.json.
    data = gw.api_call("/production.json")

    inverters = next(
        p for p in data["production"] if p["type"] == "inverters"
    )

    # EIM meter stats (may not be present on non-metered gateways).
    eim = next(
        (p for p in data["production"] if p["type"] == "eim"),
        None,
    )

    active_count = inverters.get("activeCount")
    watts_now_meter = eim["wNow"] if eim and eim.get("activeCount", 0) > 0 else None

    # Fetch per-inverter data.
    inverter_data = gw.api_call("/api/v1/production/inverters")

    # Write to PostgreSQL.
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(INSERT_PRODUCTION_SQL, (
                watts_now,
                watts_now_meter,
                wh_today,
                wh_seven,
                wh_lifetime,
                active_count,
            ))
            for inv in inverter_data:
                reported_at = datetime.datetime.fromtimestamp(
                    inv["lastReportDate"], tz=datetime.timezone.utc
                )
                cur.execute(INSERT_INVERTER_SQL, (
                    inv["serialNumber"],
                    reported_at,
                    inv["lastReportWatts"],
                    inv["maxReportWatts"],
                ))
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    collect()
