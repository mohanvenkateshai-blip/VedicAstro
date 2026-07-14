PRAGMA foreign_keys = ON;

CREATE TABLE timeline_schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  checksum TEXT NOT NULL UNIQUE,
  applied_at TEXT NOT NULL
);

CREATE TABLE person_timelines (
  timeline_id TEXT PRIMARY KEY,
  subject_reference_id TEXT NOT NULL UNIQUE,
  content_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE timeline_milestones (
  milestone_id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL,
  origin TEXT NOT NULL,
  origin_identity_hash TEXT NOT NULL UNIQUE,
  supersedes_milestone_id TEXT,
  created_at TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (timeline_id) REFERENCES person_timelines(timeline_id),
  FOREIGN KEY (supersedes_milestone_id) REFERENCES timeline_milestones(milestone_id)
);
CREATE UNIQUE INDEX timeline_milestone_one_successor
  ON timeline_milestones(supersedes_milestone_id)
  WHERE supersedes_milestone_id IS NOT NULL;
CREATE INDEX timeline_milestone_range
  ON timeline_milestones(timeline_id, created_at);

CREATE TABLE milestone_prediction_links (
  link_id TEXT PRIMARY KEY,
  milestone_id TEXT NOT NULL,
  prediction_milestone_id TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (milestone_id) REFERENCES timeline_milestones(milestone_id),
  FOREIGN KEY (prediction_milestone_id) REFERENCES timeline_milestones(milestone_id)
);

CREATE TABLE milestone_evidence_links (
  evidence_link_id TEXT PRIMARY KEY,
  milestone_id TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (milestone_id) REFERENCES timeline_milestones(milestone_id)
);

CREATE TABLE milestone_resolutions (
  resolution_id TEXT PRIMARY KEY,
  prediction_milestone_id TEXT NOT NULL,
  supersedes_resolution_id TEXT,
  resolved_at TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (prediction_milestone_id) REFERENCES timeline_milestones(milestone_id),
  FOREIGN KEY (supersedes_resolution_id) REFERENCES milestone_resolutions(resolution_id)
);
CREATE UNIQUE INDEX milestone_resolution_one_successor
  ON milestone_resolutions(supersedes_resolution_id)
  WHERE supersedes_resolution_id IS NOT NULL;
CREATE UNIQUE INDEX milestone_resolution_one_root
  ON milestone_resolutions(prediction_milestone_id)
  WHERE supersedes_resolution_id IS NULL;
CREATE INDEX milestone_resolution_prediction
  ON milestone_resolutions(prediction_milestone_id, resolved_at);

CREATE TRIGGER person_timelines_no_update BEFORE UPDATE ON person_timelines
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER person_timelines_no_delete BEFORE DELETE ON person_timelines
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER timeline_milestones_no_update BEFORE UPDATE ON timeline_milestones
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER timeline_milestones_no_delete BEFORE DELETE ON timeline_milestones
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER milestone_prediction_links_no_update BEFORE UPDATE ON milestone_prediction_links
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER milestone_prediction_links_no_delete BEFORE DELETE ON milestone_prediction_links
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER milestone_evidence_links_no_update BEFORE UPDATE ON milestone_evidence_links
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER milestone_evidence_links_no_delete BEFORE DELETE ON milestone_evidence_links
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER milestone_resolutions_no_update BEFORE UPDATE ON milestone_resolutions
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
CREATE TRIGGER milestone_resolutions_no_delete BEFORE DELETE ON milestone_resolutions
BEGIN SELECT RAISE(ABORT, 'append-only timeline store'); END;
