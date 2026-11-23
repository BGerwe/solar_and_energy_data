-- Full schema reference for fresh installs.
-- Equivalent to running all migrations (001–006) in order.
-- Run: psql -U <user> -f db/init.sql

CREATE DATABASE solar_data;

\c solar_data

CREATE TABLE IF NOT EXISTS solar_production (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    watts_now REAL,
    watts_now_meter REAL,
    wh_today REAL,
    wh_last_seven_days REAL,
    wh_lifetime REAL,
    active_inverter_count INT
);

CREATE INDEX IF NOT EXISTS idx_solar_production_recorded_at ON solar_production (recorded_at);

CREATE TABLE IF NOT EXISTS devices (
    eid INT PRIMARY KEY NOT NULL,
    serialnum BIGINT,
    array_id VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS inverter_readings (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(20) NOT NULL,
    reported_at TIMESTAMPTZ NOT NULL,
    last_report_watts INT,
    max_report_watts INT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inverter_readings_reported_at ON inverter_readings (reported_at);
CREATE INDEX IF NOT EXISTS idx_inverter_readings_serial_number ON inverter_readings (serial_number);
