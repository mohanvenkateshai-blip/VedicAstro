-- VedicAstro — guest charts table
-- Run this once in the Supabase SQL Editor.
--
-- PRIVACY FORMAT (application-managed): new values in name, birth_date,
-- birth_time, place, lat, lon, and tz are AES-256-GCM envelopes beginning
-- `enc:v1:`. Existing plaintext rows remain readable during a rolling upgrade.
-- A row must be entirely plaintext or entirely enc:v1; mixed rows are rejected
-- by the API and must be recovered from backup before migration resumes.
-- The API fails closed for new writes if ENCRYPTION_KEY is absent or invalid.
-- Do not run a bulk UPDATE in SQL: encryption uses per-owner authenticated data
-- and must be performed by a separately reviewed application migration tool.

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

-- No RLS — access is controlled by guest_id in application logic. This is BOTH
-- guest AND authenticated charts: signed-in users' charts are stored with
-- guest_id = "user_<accountId>" (see src/lib/chart-owner.ts), so they are
-- private per-account and portable across devices. Because the app uses the
-- Supabase service-role key (which bypasses RLS), that application-layer
-- guest_id filter is the ONLY privacy boundary and must be applied on every
-- read/write/delete in the /api/charts routes.
--
-- DEPLOYMENT / MIGRATION ORDER:
--   1. Set a stable 32-byte ENCRYPTION_KEY in every application environment.
--   2. Deploy the mixed-read / encrypted-write API.
--   3. Back up the table and record plaintext/encrypted row counts.
--   4. Run a resumable owner-scoped application migration (not included here),
--      atomically replacing all sensitive fields only after verifying that the
--      complete encrypted row decrypts correctly.
--   5. Retain the same key until every encrypted row has been re-encrypted under
--      a reviewed key-rotation procedure.

-- NOTE: a `saved_charts` table (user_id UUID REFERENCES auth.users) was added
-- earlier for authenticated charts, but it never worked for this app and has
-- been removed here: this app authenticates via NextAuth (Google sub is TEXT,
-- not a Supabase auth.users UUID) and accesses Supabase with the service-role
-- key, so its auth.uid()-based RLS never applied. Nothing reads or writes it.
-- If it was already created in your Supabase project you may drop it:
--   DROP TABLE IF EXISTS saved_charts CASCADE;
-- (Harmless to leave — it is simply unused.)
