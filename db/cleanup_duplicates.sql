-- Remove duplicate rows caused by the collector task firing twice per 5-minute interval.
-- Run: psql -U <user> -d solar_data -f db/cleanup_duplicates.sql
--
-- Runs in a transaction and ends with ROLLBACK so you can review the counts first.
-- Change the final ROLLBACK to COMMIT to actually delete.

BEGIN;

-- solar_production: keep the earliest row in each 5-minute bucket.
WITH ranked AS (
    SELECT id,
           row_number() OVER (
               PARTITION BY to_timestamp(floor(extract(epoch FROM recorded_at) / 300) * 300)
               ORDER BY recorded_at, id
           ) AS rn
    FROM solar_production
)
DELETE FROM solar_production
WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

-- inverter_readings: keep one row per inverter report (serial_number + reported_at).
-- Inverters report less often than the collector polls, so this also removes
-- repeats of the same report from separate (non-duplicate) runs.
--WITH ranked AS (
--    SELECT id,
--           row_number() OVER (
--               PARTITION BY serial_number, reported_at
--               ORDER BY id
--           ) AS rn
--    FROM inverter_readings
--)
--DELETE FROM inverter_readings
--WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

SELECT 'solar_production' AS table_name, count(*) AS remaining_rows FROM solar_production
UNION ALL
SELECT 'inverter_readings', count(*) FROM inverter_readings;

ROLLBACK;  -- change to COMMIT once the counts look right
