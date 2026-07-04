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

-- Saved charts for authenticated users
CREATE TABLE IF NOT EXISTS saved_charts (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_saved_charts_user_id
  ON saved_charts (user_id);

CREATE INDEX IF NOT EXISTS idx_saved_charts_user_created
  ON saved_charts (user_id, created_at DESC);

-- Enable RLS
ALTER TABLE saved_charts ENABLE ROW LEVEL SECURITY;

-- Users can only see their own saved charts
CREATE POLICY "Users can view their own saved charts"
  ON saved_charts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own saved charts"
  ON saved_charts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own saved charts"
  ON saved_charts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own saved charts"
  ON saved_charts FOR DELETE
  USING (auth.uid() = user_id);
