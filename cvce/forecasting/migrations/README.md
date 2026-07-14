# Forecast ledger reference migration

The executable v1 SQLite schema is deliberately colocated with
`forecasting/ledger.py`, which creates the tables and database-level append-only
triggers. This directory records the migration boundary without wiring a
production database.

The production adapter must preserve these invariants:

- `tenant_id` plus an opaque `subject_key` is the only subject identity. Never
  persist raw name, birth date/time, location, coordinates, email, or phone.
- A model release, issued claim snapshot, consent event, resolution event, and
  tombstone is append-only. Corrections supersede; they do not overwrite.
- Store the canonical claim snapshot, point-in-time cutoff, model manifest hash,
  claim hash, wording hash, and composite content hash.
- Outcome writes require the ledger feature flag and active, explicit
  `outcome_research` consent at write time.
- Withdrawal stops future outcome collection. It does not silently erase prior
  evaluation history.
- Export is tenant/subject scoped. After an erasure or retention tombstone, the
  subject-specific linkage/encryption key is destroyed and detailed export is
  redacted while the tombstone remains auditable.
