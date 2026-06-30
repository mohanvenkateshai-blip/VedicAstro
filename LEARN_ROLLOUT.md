# LEARN_ROLLOUT

All books now serve full chapter content directly from local Graphify sources (raw markdown + structured JSONs in the portal bundle via prebuild sync). Reader no longer depends on Supabase for text bodies.

- Structured path: authoritative chapters/sections + line-range slicing.
- Full text path: improved `parseMarkdownToSections` fallback (expanded junk filter + body-quality filter) when no structured chapters present.
- Index (`/learn`) shows chapter counts for both (via structured or parse fallback).
- Page header shows "Structured" (chapter-precise) vs "Full text from source" indicator + full text provenance (local/remote).

See ROLLOUT_NOTE.md and LEARN_FULL_CHAPTERS_STATUS.md for verification details and per-book status.
