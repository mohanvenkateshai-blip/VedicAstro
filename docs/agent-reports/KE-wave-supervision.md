# KE Wave — Supervision & Tracking Report

**Agent:** G (GraphRAG / Integration / Floor) + O (Orchestration) supervision slice  
**Date:** 2026-06-30  
**Scope (non-overlapping):** tracker, refresh_auditor, integration (safe + registration), ke_wave_status.py, light engine/registry, "no cracks" checklist.

## Baseline (script-style discovery, narrow)

- Source scan for `register_engine("NAME"...)`: **9 unique engines**
  - ashtakavarga, dasha, gochar, kp_system, muhurta, panchanga, prashna, report, yoga
- Existing dedicated probes in `refresh_auditor.ENGINE_PROBES`: **5**
  - dasha, gochar, muhurta, report, yoga
- Auditor `run_all_probes()` / status script baseline (pre-extension): registered_targets often empty until side-effect imports; script falls back to source scan.

Health / integration smoke (narrow):
- `get_knowledge_engine()` returns; `health()` and `get_safe_knowledge` surface version + stats.
- `get_registered_engines_with_status()` added (returns count + per-engine crack flags).

## Probes Added (this wave)

Extended `cvce/knowledge_engine/refresh_auditor.py`:

- `_probe_ashtakavarga`: domain node query `*ashtakavarga*` + structured book check; reports `source` + fingerprint.
- `_probe_panchanga`: `*panchanga*` domain; source classification.
- `_probe_kp` (also bound to `kp_system`): `*kp*` domain.
- `_probe_prashna`: `*prashna*` domain.

`ENGINE_PROBES` now lists **10** keys (aliases for kp/kp_system):
`ashtakavarga, dasha, gochar, kp, kp_system, muhurta, panchanga, prashna, report, yoga`

New public helper:
```python
from cvce.knowledge_engine.refresh_auditor import run_all_probes
res = run_all_probes()  # {"probes_run": N, "registered": [...], "results": {name: {...}}, ...}
```

Concrete improvement in `cvce/knowledge_engine/integration.py`:
```python
from cvce.knowledge_engine.integration import get_registered_engines_with_status
st = get_registered_engines_with_status()  # count, engines[{name, has_on_refresh, real_reload, crack}], version
```

## Registration Audit (counts only)

Source scan (authoritative for this env where heavy imports are blocked):
- Total registrations found: 9
- Engines whose `on_refresh` performs **real data reload** (loads structured books + warms chapter nodes):
  - dasha (BPHS ch-48, Jaimini, etc.)
  - yoga (BPHS ch-36, PD, SC)
  - ashtakavarga (BPHS ch-67, handbook)
  - report (partial; BPHS + Phaladeepika + nodes)
  - gochar (partial; Gochar_Phaladeepika)
- Engines with **cache-clear only** (no structured load in on_refresh body):
  - muhurta
  - kp_system
  - prashna
  - panchanga (minimal structured touch in try)

`register_engine` calls all go through `ke.registry.register(...)` and are notified by `trigger_global_refresh` / `revive_knowledge` / `on_embeddings_updated`.

Runtime `registered_names()` may be 0 until registrars are imported; supervision script uses source scan fallback.

## Status Script

Created: `scripts/ke_wave_status.py`

Run:
```
python3 scripts/ke_wave_status.py
```

Sample output (numbers from run):
```
Registered (source scan): 9
Registered (runtime): 0

name           real   crack                  source      count  fingerprint
...
kp_system      no     cache_clear_only       graph           3  ...
muhurta        no     cache_clear_only       graph       ...
...
SUMMARY: engines=9  probed=10  cracks=4
probe_supported: ['ashtakavarga', 'dasha', 'gochar', 'kp', 'kp_system', 'muhurta', 'panchanga', 'prashna', 'report', 'yoga']
```

Crack definition (heuristic): `cache_clear_only` for known minimal on_refresh, or missing on_refresh at runtime when others are present.

## Tracker Updates

- Row "GraphRAG / Integration / Floor" (G): **PARTIAL**
  - Evidence: src=9 engines; probes=10; cracks=4; script + run_all_probes + get_*_status added.
  - Next: upgrade 4 cache-only on_refresh; re-verify via script.
- Row "Orchestration / CVCE App" (O): **PARTIAL**
  - Evidence: src scan=9; 4/9 real reloads; cracks flagged by status script.
  - Next: ensure all on app start; extend golden with ke_version + fingerprint.

## "No Cracks" Checklist (this scope)

- [x] Auditor probes added for required areas (dasha/yoga/ashtakavarga/panchanga/synthesis-report/kp/prashna covered; gochar/muhurta/report pre-existing)
- [x] Status script created and emits table + counts
- [x] Registration audit performed (9 engines, classified real vs cache-only)
- [x] `get_registered_engines_with_status()` helper in integration
- [x] `run_all_probes()` machine-readable entry in auditor
- [x] Tracker rows G/O updated with counts/evidence
- [x] This report written under `docs/agent-reports/`
- [ ] (outside scope) All 9 engines upgraded to real_reload on_refresh
- [ ] (outside scope) Runtime registration at app start for all
- [ ] (outside scope) golden tests snapshot ke_version + fingerprints

## Verification (end-of-turn)

Command:
```
python3 scripts/ke_wave_status.py
python3 -c "
from cvce.knowledge_engine.refresh_auditor import ENGINE_PROBES, run_all_probes
print('probes:', len(ENGINE_PROBES))
print('run_all keys sample:', sorted(run_all_probes().get('results',{}).keys())[:5])
"
```

Last run summary:
- engines=9
- probed=10
- cracks=4
- PASS: script exits 0; table printed; counts reported.

Final script stdout (counts only):
```
KE Wave Status — VedicAstro
Registered (source scan): 9
Registered (runtime): 0

name           real   crack                  source      count  fingerprint
ashtakavarga   yes                           graph         486  a7b6f7a5...
dasha          yes                                         400  257ad2de...
gochar         yes                           graph       26722  5117e048...
kp_system      no     cache_clear_only       graph           3  e248838f...
muhurta        no     cache_clear_only       graph       26722  06accbf1...
panchanga      no     cache_clear_only       graph          11  5a4ff394...
prashna        no     cache_clear_only       hardcoded   26722  987311bf...
report         yes                                       26722  15b5a8a9...
yoga           yes                                         500  7a977e37...

SUMMARY: engines=9  probed=10  cracks=4
probe_supported: ['ashtakavarga', 'dasha', 'gochar', 'kp', 'kp_system', 'muhurta', 'panchanga', 'prashna', 'report', 'yoga']
```

## Artifacts

- `scripts/ke_wave_status.py` (new, narrow CLI)
- `cvce/knowledge_engine/refresh_auditor.py` (+4 probes + run_all_probes)
- `cvce/knowledge_engine/integration.py` (+get_registered_engines_with_status)
- `docs/KE_FULL_UPDATE_WAVE_2026-06-30.md` (G/O rows updated)
- `docs/agent-reports/KE-wave-supervision.md` (this file)

**X probes added: 4 dedicated (+5 aliases/entries) → total 10 supported**  
**Y engines audited: 9 (source authoritative)**  
**Z cracks flagged: 4 (muhurta, kp_system, prashna, panchanga)**

All within non-overlapping scope. No edits to other agents' areas.
