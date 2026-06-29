# Core Jyotisha Ingest — COMPLETE

Finished at: 2026-06-29T00:10:00+00:00 (updated after 10-book Gemini pass)

## Summary
- **Markdown sources (Core 20)**: 20 / 20
- **Graph nodes (all 20 Core books)**: **23,267** nodes / **35,438** links (production `graph.json`)
- **Supabase vault**: synced earlier (16,485 nodes); re-sync pending if network allows
- **CVCE Fly**: deployed with 23,267-node graph

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
  "fly_deploy": "done"
}
```

## Notes
- DeepSeek API returned **402 Insufficient Balance** for the missing-10 pass; completed via **Gemini batch** deterministic extract + cache merge.
- Corpus IP: markdown + merged graph in **Supabase** (`corpus-vault`); not in git.
