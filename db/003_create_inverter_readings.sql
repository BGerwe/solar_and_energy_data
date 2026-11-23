CREATE TABLE inverter_readings (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(20) NOT NULL,
    reported_at TIMESTAMPTZ NOT NULL,
    last_report_watts INT,
    max_report_watts INT
);

CREATE INDEX idx_inverter_readings_reported_at ON inverter_readings (reported_at);
CREATE INDEX idx_inverter_readings_serial_number ON inverter_readings (serial_number);
