-- Fresh install, step 1: create the empty database.
-- Run: psql -U postgres -f db/init.sql
--
-- Step 2: build the schema by applying every numbered migration (and recording
-- them in schema_migrations):
--     python db/migrate.py
--
-- The schema is intentionally NOT duplicated here. The numbered migration files
-- are the single source of truth, so this file can't drift out of sync with them.

CREATE DATABASE solar_data;
