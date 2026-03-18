ALTER TABLE inverter_readings ADD COLUMN recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE inverter_readings SET recorded_at = reported_at;
