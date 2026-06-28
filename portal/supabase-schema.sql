-- VedicAstro — guest charts table
-- Run this once in the Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS guest_charts (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  guest_id    TEXT        NOT NULL,
  name        TEXT        NOT NULL,
  birth_date  TEXT,
  birth_time  TEXT,
  place       TEXT,
  lat         TEXT,
  lon         TEXT,
  tz          TEXT,
  sort_order  INTEGER     NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_guest_charts_guest_id
  ON guest_charts (guest_id);

CREATE INDEX IF NOT EXISTS idx_guest_charts_guest_created
  ON guest_charts (guest_id, created_at DESC);

-- No RLS — access is controlled by guest_id in application logic.
