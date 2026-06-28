# Core Jyotisha Ingest — Live Status

**Updated:** 2026-06-28 23:21 UTC

## Root cause (fixed tonight)

**`launchd` had no PATH to `gcloud`/`gsutil`.** Supervisor and sync watcher were blind — logged `gcs_md=0` while 7 files sat in GCS. Daemons restarted every ~10s in a crash loop.

**Fix:** `scripts/gcp-env.sh` + `ingest-pipeline-daemon.sh` with explicit Homebrew PATH in launchd.

## Running now

| Process | Role |
|---------|------|
| `com.vedicastro.ingest` (launchd) | Keeps pipeline daemon alive |
| `ingest-pipeline-daemon.sh` | Restarts supervisor + sync + local OCR |
| `gcp-ocr-watch.sh` | Polls GCS every 60s, syncs, kicks incremental DeepSeek |
| `local-ocr-queue.sh` | 4 parallel Mac OCR jobs (books &lt;500 pages) |
| GCP fleet `vedicastro-ocr-0/1/2` | Fast OCR on remaining scans |

## Delivered

- `graph-core-jyotisha.json` — **13,234 nodes** (text books + corpus)
- `graph-deepseek.json` — **11,454 nodes**
- 1 scan synced: `Jataka_Tatva_Mahadeva.md`
- DeepSeek incremental run started on ready scans

## Monitor

```bash
tail -f knowledge-graph/ingest-logs/gcp-sync-watch.log
tail -f knowledge-graph/ingest-logs/local-ocr.log
tail -f knowledge-graph/ingest-logs/deepseek-ocr.log
./scripts/gcp-ocr-fleet.sh --status
```

```bash
# pending scan count
python3 -c "..."  # or ingest-supervisor.py --status
```
