# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Conda environment name: `solar_api_data` (Python 3.14)

```bash
conda activate solar_api_data
jupyter lab  # launch notebooks
```

Key pip packages (not in conda defaults): `enphase-api`, `srpenergy`, `python-dotenv`, `pyjwt`, `psycopg2-binary`, `fastapi`, `uvicorn`

## Project Structure

Solar and energy data retrieval, storage, and API serving from two sources (Enphase IQ Gateway, SRP utility).

### Notebooks (prototyping)
- **`prototyping_enphase.ipynb`** — Enphase IQ Gateway integration: cloud authentication, local gateway API calls, and a real-time matplotlib animation of power production/consumption data.
- **`prototyping_srp.ipynb`** — SRP (Salt River Project) utility API integration for fetching electricity usage data.

### Data collection
- **`collect_enphase.py`** — Scheduled script (every 30 min) that polls the gateway and inserts a row into PostgreSQL.
- **`token_manager.py`** — JWT token caching and auto-refresh. Cached token stored at `configuration/token.json`.

### API server
- **`api/server.py`** — FastAPI app with endpoints for current power, today's production, yesterday's production, and SRP consumption (stub).
- Run: `uvicorn api.server:app --host 0.0.0.0 --port 8000`
- Docs: `http://<host>:8000/docs`

### Database
- **`db/init.sql`** — PostgreSQL schema (`solar_data` database, `solar_production` table).
- Run once: `psql -U <user> -f db/init.sql`

### Deployment
- **`systemd/solar-api.service`** — systemd unit file for the API server (Pi deployment).
- **`systemd/README.txt`** — Setup instructions for systemd + cron (Pi) or Task Scheduler (Windows).

### Other
- **`token_retrieval.py`** — Original standalone script for Enphase JWT token fetching (superseded by `token_manager.py`).
- **`configuration/gateway.cer`** — TLS certificate downloaded from the local IQ Gateway.

## Credentials

Credentials are loaded from `local.env` (untracked by git) via `python-dotenv`:

```
ENPHASE_USERNAME=...
ENPHASE_PASSWORD=...
IQ_GATEWAY_SERIAL_NUMBER=...
IQ_GATEWAY_HOST=https://envoy.local   # optional, defaults to https://envoy.local
DATABASE_URL=postgresql://user:password@localhost:5432/solar_data
```

**Never commit `local.env` or any file containing credentials.**

## Enphase Architecture

Authentication is a two-step process:
1. Cloud auth via `enphase_api.cloud.authentication.Authentication` → retrieves a JWT token scoped to a gateway serial number.
2. Local gateway calls via `enphase_api.local.gateway.Gateway` → uses that token for Bearer auth against the local IQ Gateway over HTTPS.

The gateway cert (`configuration/gateway.cer`) is downloaded once via `Gateway.trust_gateway(host)` to enable verified HTTPS.

Key gateway endpoints used:
- `/production.json` — production, consumption, and storage stats
- `/api/v1/production` — simplified production summary
- `/ivp/meters` — meter status/configuration
- `/ivp/meters/reports` — detailed per-line meter readings
