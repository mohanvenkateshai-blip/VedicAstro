# Core Jyotisha Ingest — COMPLETE

Finished at: 2026-06-29T00:10:00+00:00 (updated after 10-book Gemini pass)

## Summary
- **Markdown sources (Core 20)**: 20 / 20
- **Newbooks MD (2026-06-29)**: 12 ingested, 2 duplicates skipped — see `NEWBOOKS-INGEST.md`
- **Graph nodes (production)**: **26,722** nodes / **38,881** links (`graph_version`: `newbooks-v1`)
- **Supabase vault**: synced **26,722** nodes / 38,881 links (`newbooks-v1`)
- **CVCE Fly**: deployed with 26,722-node graph (2026-06-29)

## Core 20 graph coverage (post-merge)
All 20 classical PDFs have ≥50 nodes each in `graph.json`.

## Phases
```json
{
  "deepseek_text": "done",
  "marker_ocr": "done",
  "deepseek_ocr": "partial",
  "gemini_batch": "done",
  "merge": "done",
  "promote": "done",
  "fly_deploy": "done",
  "supabase_sync": "done",
  "git_commit": "done"
}
```

## Notes
- DeepSeek API returned **402 Insufficient Balance** for the missing-10 pass; completed via **Gemini batch** deterministic extract + cache merge.
- Graph **is** in git: `knowledge-graph/graphify-out/graph.json` + `cvce/graph_rag/graph.json` (26,722 nodes, `newbooks-v1`). Raw markdown stays out. Deterministic layer deployed; Gemini semantic batch (optional additive layer) was still running at end of session.
