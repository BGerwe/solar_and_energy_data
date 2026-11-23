CREATE TABLE solar_production (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    watts_now REAL,
    watts_now_meter REAL,
    wh_today REAL,
    wh_last_seven_days REAL,
    wh_lifetime REAL,
    active_inverter_count INT
);

CREATE INDEX idx_solar_production_recorded_at ON solar_production (recorded_at);
