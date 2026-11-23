# setup.ps1 — Automated setup for Solar and Energy Data project
# Run: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n=== Solar and Energy Data — Setup ===" -ForegroundColor Cyan

# --- 1. Check conda ---
Write-Host "`n[1/6] Checking conda..." -ForegroundColor Yellow
if (Get-Command conda -ErrorAction SilentlyContinue) {
    Write-Host "  conda found." -ForegroundColor Green

    $envExists = conda env list | Select-String "solar_api_data"
    if ($envExists) {
        Write-Host "  Environment 'solar_api_data' already exists." -ForegroundColor Green
    } else {
        Write-Host "  Creating conda environment from environment.yml..."
        conda env create -f "$ProjectDir\environment.yml"
        Write-Host "  Environment created." -ForegroundColor Green
    }
} else {
    Write-Host "  conda not found. Install Miniconda from https://docs.anaconda.com/miniconda/install/" -ForegroundColor Red
    Write-Host "  Then re-run this script." -ForegroundColor Red
    exit 1
}

# --- 2. Create local.env template ---
Write-Host "`n[2/6] Checking local.env..." -ForegroundColor Yellow
$envFile = Join-Path $ProjectDir "local.env"
if (Test-Path $envFile) {
    Write-Host "  local.env already exists. Skipping." -ForegroundColor Green
} else {
    @"
# Enphase credentials (required)
ENPHASE_USERNAME=your-enphase-email@example.com
ENPHASE_PASSWORD=your-enphase-password
IQ_GATEWAY_SERIAL_NUMBER=your-gateway-serial

# Gateway host (optional, defaults to https://envoy.local)
IQ_GATEWAY_HOST=https://envoy.local

# PostgreSQL connection string (required)
DATABASE_URL=postgresql://postgres:your-pg-password@localhost:5432/solar_data
"@ | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "  Created local.env template. Edit it with your credentials before running the collector." -ForegroundColor Green
}

# --- 3. Check psql ---
Write-Host "`n[3/6] Checking PostgreSQL..." -ForegroundColor Yellow
if (Get-Command psql -ErrorAction SilentlyContinue) {
    Write-Host "  psql found." -ForegroundColor Green
} else {
    Write-Host "  psql not found in PATH." -ForegroundColor Red
    Write-Host "  Install PostgreSQL from https://www.postgresql.org/download/windows/" -ForegroundColor Red
    Write-Host "  Then add its bin directory to PATH (e.g., C:\Program Files\PostgreSQL\17\bin)" -ForegroundColor Red
    Write-Host "  Re-run this script after installing." -ForegroundColor Red
    exit 1
}

# --- 4. Prompt for PostgreSQL credentials ---
Write-Host "`n[4/6] Database setup..." -ForegroundColor Yellow
$pgUser = Read-Host "  PostgreSQL username (default: postgres)"
if ([string]::IsNullOrWhiteSpace($pgUser)) { $pgUser = "postgres" }

# Create database (ignore error if it already exists)
Write-Host "  Creating database 'solar_data'..."
$createResult = psql -U $pgUser -c "CREATE DATABASE solar_data;" 2>&1
if ($createResult -match "already exists") {
    Write-Host "  Database 'solar_data' already exists. Skipping." -ForegroundColor Green
} elseif ($LASTEXITCODE -eq 0) {
    Write-Host "  Database created." -ForegroundColor Green
} else {
    Write-Host "  Warning: $createResult" -ForegroundColor Yellow
}

# --- 5. Run migrations ---
Write-Host "`n[5/6] Running migrations..." -ForegroundColor Yellow
$migrations = Get-ChildItem -Path "$ProjectDir\db" -Filter "*.sql" |
    Where-Object { $_.Name -match "^\d{3}_" } |
    Sort-Object Name

foreach ($migration in $migrations) {
    Write-Host "  Running $($migration.Name)..."
    $result = psql -U $pgUser -d solar_data -f $migration.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        $errorText = $result | Out-String
        if ($errorText -match "already exists") {
            Write-Host "    Already applied. Skipping." -ForegroundColor Yellow
        } else {
            Write-Host "    Error: $errorText" -ForegroundColor Red
        }
    } else {
        Write-Host "    Done." -ForegroundColor Green
    }
}

# --- 6. Create logs directory ---
Write-Host "`n[6/6] Creating logs directory..." -ForegroundColor Yellow
$logsDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
    Write-Host "  Created logs/" -ForegroundColor Green
} else {
    Write-Host "  logs/ already exists." -ForegroundColor Green
}

# --- Done ---
Write-Host "`n=== Setup complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Edit local.env with your Enphase credentials and PostgreSQL password"
Write-Host "  2. Ensure your Enphase IQ Gateway is reachable on the local network"
Write-Host "  3. Test the collector:  conda activate solar_api_data && python collect_enphase.py"
Write-Host "  4. Start the API:      conda activate solar_api_data && uvicorn api.server:app --host 0.0.0.0 --port 8000"
Write-Host "  5. See SETUP.md for scheduling instructions (Task Scheduler)"
Write-Host ""
