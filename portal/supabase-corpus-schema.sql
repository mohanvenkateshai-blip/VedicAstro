-- VedicShastra corpus vault — run in Supabase SQL Editor (once).
-- Private: service_role only (RLS enabled, no policies for anon/authenticated).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ── Corpus markdown metadata ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS corpus_sources (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name  TEXT UNIQUE NOT NULL,
  storage_path    TEXT NOT NULL,
  sha256          TEXT NOT NULL,
  bytes           BIGINT NOT NULL DEFAULT 0,
  book_family     TEXT,
  ingest_method   TEXT,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_corpus_sources_sha ON corpus_sources (sha256);

-- ── Graph ingest audit ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS graph_ingest_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  graph_version TEXT NOT NULL,
  provider      TEXT,
  node_count    INT NOT NULL DEFAULT 0,
  link_count    INT NOT NULL DEFAULT 0,
  storage_path  TEXT,
  completed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_graph_ingest_version ON graph_ingest_runs (graph_version);

-- ── Knowledge graph nodes ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS graph_nodes (
  id               TEXT NOT NULL,
  graph_version    TEXT NOT NULL,
  label            TEXT,
  file_type        TEXT,
  source_file      TEXT,
  source_location  TEXT,
  community        INT,
  properties       JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (id, graph_version)
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_version ON graph_nodes (graph_version);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_source ON graph_nodes (source_file);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_community ON graph_nodes (community);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_label ON graph_nodes (label);

-- ── Knowledge graph links ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS graph_links (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  graph_version TEXT NOT NULL,
  source_id     TEXT NOT NULL,
  target_id     TEXT NOT NULL,
  relation      TEXT,
  properties    JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (graph_version, source_id, target_id, relation)
);

CREATE INDEX IF NOT EXISTS idx_graph_links_version ON graph_links (graph_version);
CREATE INDEX IF NOT EXISTS idx_graph_links_source ON graph_links (source_id);
CREATE INDEX IF NOT EXISTS idx_graph_links_target ON graph_links (target_id);

-- ── RLS: deny all client access; service_role bypasses ───────────────────
ALTER TABLE corpus_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_ingest_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_links ENABLE ROW LEVEL SECURITY;

-- Storage bucket: create via Dashboard or sync script API
-- Name: corpus-vault (private, not public)
INSERT INTO storage.buckets (id, name, public)
VALUES ('corpus-vault', 'corpus-vault', false)
ON CONFLICT (id) DO UPDATE SET public = false;
