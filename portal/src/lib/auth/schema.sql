-- VedicAstro Portal — PostgreSQL schema
-- Applied automatically on Vercel when DATABASE_URL is set (first DB connection).
-- Manual: POST /api/db/migrate with Bearer AUTH_SECRET, or npm run db:schema:remote

CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,                     -- Google OAuth sub
  email         TEXT UNIQUE NOT NULL,
  name          TEXT,
  role          TEXT NOT NULL DEFAULT 'free'          -- free | pro | premium | admin
    CHECK (role IN ('free', 'pro', 'premium', 'admin')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS horoscopes (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  chart_data    JSONB NOT NULL,                      -- canonical chart_data payload
  encrypted     BOOLEAN NOT NULL DEFAULT TRUE,       -- birth PII encrypted at rest
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_horoscopes_user ON horoscopes (user_id);
CREATE INDEX IF NOT EXISTS idx_horoscopes_user_created ON horoscopes (user_id, created_at DESC);

-- Row-level security: horoscopes visible only when app.current_user_id matches
ALTER TABLE horoscopes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS horoscopes_isolate ON horoscopes;
CREATE POLICY horoscopes_isolate ON horoscopes
  FOR ALL
  USING (user_id = current_setting('app.current_user_id', true))
  WITH CHECK (user_id = current_setting('app.current_user_id', true));

-- ── Personalization (added 2026-07-04) ──────────────────────────────────────
-- Profile avatar + per-user theme + resume-last-page. Idempotent ALTERs so the
-- auto-migration on cold start upgrades existing users rows in place.
ALTER TABLE users ADD COLUMN IF NOT EXISTS image     TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS theme     TEXT NOT NULL DEFAULT 'system'
  CHECK (theme IN ('light', 'dark', 'system'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_path TEXT;

-- Notification center — per-user, RLS-isolated (mirrors horoscopes pattern).
CREATE TABLE IF NOT EXISTS notifications (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind       TEXT NOT NULL DEFAULT 'info'              -- info | success | warning | alert
    CHECK (kind IN ('info', 'success', 'warning', 'alert')),
  title      TEXT NOT NULL,
  body       TEXT,
  href       TEXT,                                     -- optional deep-link target
  read_at    TIMESTAMPTZ,                              -- NULL = unread
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_created
  ON notifications (user_id, created_at DESC);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS notifications_isolate ON notifications;
CREATE POLICY notifications_isolate ON notifications
  FOR ALL
  USING (user_id = current_setting('app.current_user_id', true))
  WITH CHECK (user_id = current_setting('app.current_user_id', true));

