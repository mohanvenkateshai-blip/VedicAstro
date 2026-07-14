PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS research_schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  checksum TEXT NOT NULL,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS technique_runs (
  run_id TEXT PRIMARY KEY,
  run_hash TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_annotations (
  annotation_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  supersedes_annotation_id TEXT,
  annotation_hash TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES technique_runs(run_id),
  FOREIGN KEY (supersedes_annotation_id) REFERENCES research_annotations(annotation_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS research_annotations_one_successor
ON research_annotations(supersedes_annotation_id)
WHERE supersedes_annotation_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS event_registries (
  registry_id TEXT NOT NULL,
  version TEXT NOT NULL,
  registry_hash TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL,
  PRIMARY KEY (registry_id, version)
);

CREATE TABLE IF NOT EXISTS timing_registries (
  registry_id TEXT NOT NULL,
  version TEXT NOT NULL,
  registry_hash TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL,
  PRIMARY KEY (registry_id, version)
);

CREATE TRIGGER IF NOT EXISTS technique_runs_no_update
BEFORE UPDATE ON technique_runs BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS technique_runs_no_delete
BEFORE DELETE ON technique_runs BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS research_annotations_no_update
BEFORE UPDATE ON research_annotations BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS research_annotations_no_delete
BEFORE DELETE ON research_annotations BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS event_registries_no_update
BEFORE UPDATE ON event_registries BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS event_registries_no_delete
BEFORE DELETE ON event_registries BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS timing_registries_no_update
BEFORE UPDATE ON timing_registries BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS timing_registries_no_delete
BEFORE DELETE ON timing_registries BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS research_schema_migrations_no_update
BEFORE UPDATE ON research_schema_migrations
BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
CREATE TRIGGER IF NOT EXISTS research_schema_migrations_no_delete
BEFORE DELETE ON research_schema_migrations
BEGIN SELECT RAISE(ABORT, 'append-only research store'); END;
