# Implementation Plan

## Scope
- PostgreSQL database for solar production data
- Enphase data collection script (polls gateway every 30 min)
- FastAPI server with 4 endpoints (excluding SRP endpoint for now)
- Scheduling via cron / Task Scheduler

SRP collection script is **out of scope** for this plan.

---

## 1. Database Setup

### 1a. Schema — `solar_production` table

```sql
CREATE TABLE solar_production (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    watts_now REAL,              -- current production (wNow from inverters)
    watts_now_meter REAL,        -- current production from EIM meter
    wh_today REAL,               -- watt-hours produced today
    wh_last_seven_days REAL,     -- watt-hours last 7 days
    wh_lifetime REAL,            -- cumulative lifetime watt-hours
    active_inverter_count INT    -- number of reporting inverters
);

CREATE INDEX idx_solar_production_recorded_at ON solar_production (recorded_at);
```

### 1b. Database creation

Create a setup script `db/init.sql` with:
- `CREATE DATABASE solar_data;`
- The table DDL above
- The index

### 1c. Connection config

Add to `local.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/solar_data
```

---

## 2. Data Collection Script — `collect_enphase.py`

A standalone script that runs once per invocation (designed to be called by a scheduler).

### Flow:
1. Load credentials from `local.env` via `python-dotenv`
2. Load or refresh the Enphase JWT token (see 2a)
3. Connect to the local gateway, call `/production.json`
4. Parse the response — extract inverter and EIM meter production data
5. Insert a row into `solar_production`
6. Exit

### 2a. Token management — `token_manager.py`

JWT tokens expire. This module handles:
- **Read**: Load a cached token from `configuration/token.json`
- **Validate**: Check expiry via `Authentication.check_token_valid()`
- **Refresh**: If expired, re-authenticate via `Authentication.authenticate()` + `get_token_for_commissioned_gateway()`, save the new token to `configuration/token.json`
- `configuration/token.json` will be added to `.gitignore`

### 2b. Dependencies (new pip packages)
- `psycopg2-binary` (PostgreSQL driver)
- No new dependencies for the Enphase side — `enphase-api` is already installed

### 2c. Error handling
- Log connection failures (gateway offline, network issues) to stderr and exit non-zero
- Log DB connection failures to stderr and exit non-zero
- The scheduler will retry on the next 30-min cycle; no in-script retry logic

---

## 3. FastAPI Server — `api/server.py`

### Endpoints:

| Method | Path | Source | Description |
|--------|------|--------|-------------|
| GET | `/solar/current-power` | Live gateway query | Current watts from gateway `/production.json` |
| GET | `/solar/today` | PostgreSQL | Current day's production (latest `wh_today` value) |
| GET | `/solar/yesterday` | PostgreSQL | Previous day's production (max `wh_today` from yesterday's rows) |
| GET | `/energy/yesterday` | *Stub (returns 501)* | Previous day's SRP consumption — placeholder until SRP script is built |

### Architecture:
- Single `server.py` file — 4 routes, no need for a package structure at this scale
- Uses the same `token_manager.py` for live gateway queries
- Database connection via `psycopg2` (or `asyncpg` if we want async — but `psycopg2` is simpler and consistent with the collection script)
- Binds to `0.0.0.0:8000` (LAN-accessible)
- Run via `uvicorn api.server:app --host 0.0.0.0 --port 8000`

### 3a. Dependencies (new pip packages)
- `fastapi`
- `uvicorn`

---

## 4. Scheduling

### Collection script (`collect_enphase.py`)
- **Linux/Pi**: cron job every 30 minutes
  ```
  */30 * * * * cd /path/to/project && /path/to/conda/envs/solar_api_data/bin/python collect_enphase.py >> logs/collect.log 2>&1
  ```
- **Windows**: Task Scheduler task, same idea

### FastAPI server
- **Linux/Pi**: systemd service (auto-start on boot, auto-restart on crash)
- **Windows**: Run as a background process or Windows service

Provide a `systemd/solar-api.service` unit file for the Pi path.

---

## 5. File Structure (new files only)

```
solar_and_energy_data/
├── db/
│   └── init.sql                  # Database + table DDL
├── api/
│   └── server.py                 # FastAPI app (4 endpoints)
├── systemd/
│   └── solar-api.service         # systemd unit file for the API server
├── collect_enphase.py            # Scheduled data collection script
├── token_manager.py              # JWT token caching + refresh
└── (existing files unchanged)
```

---

## 6. Implementation Order

1. `db/init.sql` — schema
2. `token_manager.py` — token caching/refresh (needed by both collector and API)
3. `collect_enphase.py` — data collector
4. `api/server.py` — FastAPI endpoints
5. `.gitignore` updates — add `configuration/token.json`, `logs/`
6. `systemd/solar-api.service` — deployment config
7. Update `CLAUDE.md` with new project structure
8. Update `environment.yml` or add a `requirements.txt` for the new pip deps

---

## Out of Scope
- SRP collection script and the `/energy/yesterday` endpoint implementation
- Authentication/rate limiting on the API (LAN-only, trusted network)
- Docker/containerization
- Frontend/dashboard
