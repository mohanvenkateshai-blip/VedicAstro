# launchd agents (macOS)

These plists keep the autonomous ingest pipeline running on the local Mac.

## Files

- `com.vedicastro.ingest.plist` — Main daemon that runs `scripts/ingest-pipeline-daemon.sh` (KeepAlive).
- `com.vedicastro.ingest-status.plist` — Periodic status reporter (every 15 min) that runs `scripts/ingest-status-report.sh`.

## Install / Load

```bash
# Copy or symlink into LaunchAgents (or edit paths below first)
cp launchd/com.vedicastro.*.plist ~/Library/LaunchAgents/

# Load
launchctl load ~/Library/LaunchAgents/com.vedicastro.ingest.plist
launchctl load ~/Library/LaunchAgents/com.vedicastro.ingest-status.plist

# Check
launchctl list | grep vedicastro

# Unload (when needed)
launchctl unload ~/Library/LaunchAgents/com.vedicastro.ingest.plist
launchctl unload ~/Library/LaunchAgents/com.vedicastro.ingest-status.plist
```

## Important

The current plists contain absolute paths for this machine:
- Working directory: `/Users/ganesha/Projects/04-UX-Practice/VedicAstro`
- Scripts under `scripts/`

Update the paths in the plists if you move the repo or run on another machine.

Logs go to `knowledge-graph/ingest-logs/`.

## Notes

- These were originally placed in `~/Library/LaunchAgents/`.
- Ingest is considered complete as of 2026-06-29; the daemons are intentionally idle when `COMPLETE.md` exists.
