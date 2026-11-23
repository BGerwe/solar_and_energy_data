# Setup Guide (Windows)

## 1. Prerequisites

### Miniconda
Download and install from https://docs.anaconda.com/miniconda/install/
During install, check "Add to PATH" or add it manually afterward.

### PostgreSQL
Download and install from https://www.postgresql.org/download/windows/
- Use the Interactive Installer (EnterpriseDB)
- Default port: 5432
- Remember the password you set for the `postgres` user

### Git
Download from https://git-scm.com/download/win (includes Git Bash).

## 2. Clone and Create Environment

```bash
git clone <repo-url>
cd solar_and_energy_data
conda env create -f environment.yml
conda activate solar_api_data
```

## 3. Create `local.env`

Create a file called `local.env` in the project root with the following:

```
# Enphase credentials (required)
ENPHASE_USERNAME=your-enphase-email@example.com
ENPHASE_PASSWORD=your-enphase-password
IQ_GATEWAY_SERIAL_NUMBER=your-gateway-serial

# Gateway host (optional, defaults to https://envoy.local)
IQ_GATEWAY_HOST=https://envoy.local

# PostgreSQL connection string (required)
DATABASE_URL=postgresql://postgres:your-pg-password@localhost:5432/solar_data
```

Where to find these values:
- **ENPHASE_USERNAME / PASSWORD** — your login for https://enlighten.enphaseenergy.com
- **IQ_GATEWAY_SERIAL_NUMBER** — printed on your IQ Gateway device, or visible in the Enphase app
- **IQ_GATEWAY_HOST** — your gateway's LAN IP (e.g., `https://192.168.0.34`) or `https://envoy.local`

## 4. Database Setup

Open a terminal and run:

```bash
# Create the empty database
psql -U postgres -f db/init.sql

# Apply all migrations (requires DATABASE_URL in local.env)
conda activate solar_api_data
python db/migrate.py
```

Applied migrations are recorded in the `schema_migrations` table. Useful commands:

```bash
python db/migrate.py --status         # show applied / pending migrations
python db/migrate.py                  # apply anything pending (e.g. after pulling a branch with a new migration)
python db/migrate.py --baseline 006   # existing DB that predates tracking: mark 001-006 applied without running them
```

To change the schema, add a new numbered file (e.g. `db/007_...sql`). Never edit a migration that has already been applied.

## 5. Download Gateway Certificate

If `configuration/gateway.cer` doesn't exist, download it from your gateway:

```python
conda activate solar_api_data
python -c "from enphase_api.local.gateway import Gateway; Gateway.trust_gateway('https://envoy.local')"
```

Replace `https://envoy.local` with your gateway's address if different.

## 6. Verify Everything Works

```bash
conda activate solar_api_data

# Test data collection (one-off)
python collect_enphase.py

# Check the database has a row
psql -U postgres -d solar_data -c "SELECT * FROM solar_production ORDER BY recorded_at DESC LIMIT 1;"

# Start the API server
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs in your browser to see the API documentation.

Test the endpoints:
- http://localhost:8000/solar/current-power
- http://localhost:8000/solar/today
- http://localhost:8000/solar/yesterday

## 7. Schedule the Data Collector (Every 30 Minutes)

### Using Windows Task Scheduler

1. Open **Task Scheduler** (search "Task Scheduler" in Start)
2. Click **Create Task** (not "Create Basic Task")
3. **General** tab:
   - Name: `Solar Data Collector`
   - Check "Run whether user is logged on or not"
4. **Triggers** tab → New:
   - Begin the task: On a schedule
   - Daily, recur every 1 day
   - Check "Repeat task every" → **30 minutes**, for a duration of **1 day**
5. **Actions** tab → New:
   - Action: Start a program
   - Program/script: `C:\Users\<you>\miniconda3\envs\solar_api_data\python.exe`
   - Add arguments: `collect_enphase.py`
   - Start in: `C:\Users\<you>\OneDrive\Documents\Python\solar_and_energy_data`
6. **Settings** tab:
   - Check "If the task fails, restart every" → 5 minutes, up to 3 times
7. Click OK, enter your Windows password when prompted

### Verify it's running

Check `logs/collect.log` for output, or query the database:

```bash
psql -U postgres -d solar_data -c "SELECT recorded_at, watts_now FROM solar_production ORDER BY recorded_at DESC LIMIT 5;"
```

## 8. Run the API Server Persistently (Optional)

To start the API server automatically on boot, create another Task Scheduler task:

1. **General** tab:
   - Name: `Solar API Server`
   - Check "Run whether user is logged on or not"
2. **Triggers** tab → New:
   - Begin the task: At startup
3. **Actions** tab → New:
   - Program/script: `C:\Users\<you>\miniconda3\envs\solar_api_data\Scripts\uvicorn.exe`
   - Add arguments: `api.server:app --host 0.0.0.0 --port 8000`
   - Start in: `C:\Users\<you>\OneDrive\Documents\Python\solar_and_energy_data`
4. **Settings** tab:
   - Check "If the task fails, restart every" → 1 minute, up to 3 times

## Automated Setup

Instead of following steps 3–5 manually, you can run the setup script:

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

This will create a `local.env` template, set up the database, and run migrations.
