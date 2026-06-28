# Core Jyotisha Ingest — COMPLETE

Finished at: 2026-06-28T22:46:11.698263+00:00

## Summary
- **Markdown sources in raw/**: 20 / 20
- **Scans still pending**: 0
- **Graph nodes**: 6437 → **16485** (+12232 vs baseline 4253)
- **Output graph**: `knowledge-graph/graphify-out/graph-core-jyotisha.json`

## Phases
{
  "deepseek_text": "done",
  "marker_ocr": "done",
  "deepseek_ocr": "done",
  "gemini_batch": "done",
  "merge": "done"
}

## Logs
- Supervisor: `knowledge-graph/ingest-logs/supervisor.log`
- Phase logs: `knowledge-graph/ingest-logs/supervisor-*.log`

## Next step (manual)
Review `graph-core-jyotisha.json` then optionally:
```bash
python3 scripts/ingest-core-jyotisha.py merge --promote
```
