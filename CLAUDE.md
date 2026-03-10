# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Conda environment name: `solar_api_data` (Python 3.14)

```bash
conda activate solar_api_data
jupyter lab  # launch notebooks
```

Key pip packages (not in conda defaults): `enphase-api`, `srpenergy`, `python-dotenv`, `pyjwt`

## Project Structure

This is a Jupyter notebook prototyping project for retrieving and visualizing solar and energy data from two sources:

- **`prototyping_enphase.ipynb`** — Enphase IQ Gateway integration: cloud authentication, local gateway API calls, and a real-time matplotlib animation of power production/consumption data.
- **`prototyping_srp.ipynb`** — SRP (Salt River Project) utility API integration for fetching electricity usage data.
- **`token_retrieval.py`** — Standalone script to fetch a JWT token from Enphase cloud using username/password + gateway serial number.
- **`configuration/gateway.cer`** — TLS certificate downloaded from the local IQ Gateway (used for secure local HTTPS calls).

## Credentials

Credentials are loaded from `local.env` (untracked by git) via `python-dotenv`:

```
ENPHASE_USERNAME=...
ENPHASE_PASSWORD=...
IQ_GATEWAY_SERIAL_NUMBER=...
```

The IQ Gateway host is the local LAN IP (e.g., `https://192.168.0.34`) or `envoy.local`.

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
