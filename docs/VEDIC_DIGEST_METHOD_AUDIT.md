# Vedic Digest Method Audit — handwritten notes vs. our engine

**Date:** 2026-07-17
**Sources reviewed:** `Panchang/Gyan/Vedic Digest/` —
`vedic-astrology-accurate-predictions-handwritten-study-notes.pdf` (15 pp, read in full),
`vedic-panchanga-muhurta-handwritten-study-notes.pdf` (5 pp, read in full),
`vedic-calendar-complete-handwritten-study-notes-v3.pdf` (pp 1–8 read; pp 9–15 are festival/era/regional-calendar material outside the prediction engine's scope).

The notes are a modern, source-cited method synthesis (Phaladeepika, Brihat Jataka, BPHS, Jataka Parijata, Brihat Samhita, Surya Siddhanta, Muhurta Cintamani), not a new rule corpus. Their value to us is the **prediction discipline**: the 5-Lock chain (Promise → Power → Period → Trigger → Manifestation) and the 10-gate Master Prediction Flow ending in *publish with confidence + limits, then score without rewriting rules*.

## Verdict in one line

**Our calculation core is aligned; our prediction/presentation layer deviates in one fundamental way — it is yoga-first where the method (and our users) demand event-first — plus five specific gaps.**

## Where we already comply

| Notes' requirement | Our implementation | Status |
|---|---|---|
| Exact five-limb math, no rounding at boundaries | `vedic_engine/core/panchanga.py` — same formulas (tithi 12°, nakshatra 13°20′, yoga sum, karana half-tithi) | ✅ |
| Named ayanamsa, sidereal, declared settings | Lahiri declared everywhere; PyJHora + Swiss Ephemeris; provenance in payloads | ✅ |
| Wall-clock + historical zone handling | PyJHora place convention preserved (`ephem.py parse_dt`); IANA timezone election context in native muhūrta | ✅ |
| Muhūrta = veto-first, no universal good day, red-flag language banned | Native `/chart/muhurta` verdict/factors/avoid-windows design; frozen standalone | ✅ |
| Score outcomes without rewriting the rule | Timeline append-only ledger; sealed forecasts untouched by resolutions | ✅ |
| Only a prewritten, timestamped forecast measures true accuracy (Einstein p13) | Exactly our sealed-prediction architecture and non-prospective labelling of migrated candidates | ✅ (workflow still unbuilt) |
| 3-clock model: natal promise / dasha active / transit trigger | Architecture exists: yogas + dasha analyzers + TransitAnalyzer + `fructification.py` + AV transit verdicts | ✅ in parts, not composed (see D3) |

## Deviations (ranked)

**D1 — Yoga-first instead of event-first (fundamental).**
`_priority_predictions` ranks *yogas* by SAV+Shadbala+dignity and attaches the involved planet's MD. The notes (pp 5, 10, 15) start from the **event endpoint** (marriage, childbirth, career, foreign move…), find its promise via bhava + lord + occupants + karaka (the six witnesses), then time it. Users cannot act on "Harsha Yoga window"; they can act on "marriage window". *Fix: build the Life-Event Prediction layer on the notes' Domain Keys table (Career 10th+lord/Sun-Saturn-Mercury/D10; Marriage 7th+lord/Venus/D9; Children 5th/Jupiter/D7; Home 4th/Moon-Mars/D4; Health 1-6-8-12/D1; Finance 2-11/Jupiter-Venus/D2; plus p15's high-specificity map).*

**D2 — Timing windows are not gated on house-network activation.**
Our windows = the involved planet's Mahadasha, full stop. The notes (p8) require MD/AD lords to **activate the same house network** as the promise (lordship, occupation, aspect, dispositor chain — "read the lord chain"). *Fix: window = dasha periods whose MD/AD lords connect to the event house/lord/karaka; PD only inside qualified AD.*

**D3 — No transit trigger layer on published windows.**
The 3-clock model demands slow transit (Saturn/Jupiter/nodes) + fast trigger + Ashtakavarga context to narrow an AD window to months. We have every component (`fructification.py`, `compute_transit_bindu_verdict`, graph transit rules) but the priority path deliberately skips them (documented V1 scope limit in `report_facts.py`). *Fix: run fructification for the selected event windows only (cheap: few windows, not 40 yogas).*

**D4 — No witness-count confidence.**
Notes: 1 witness = clue, 2 = theme, 3+ = usable promise; publish confidence + alternatives + limits (p10 output template). Our score is a single additive number presented without calibration. *Fix: count independent witnesses (bhava, lord, occupant, karaka, varga, yoga) → low/medium/high confidence; adopt the output template verbatim.*

**D5 — No birth-time stability test on claims.**
Notes (pp 2, 6): recompute at recorded ± plausible error; publish only stable claims, else a range/downgrade. We have `rectification.py` but predictions never run the stability gate. *Fix: recompute lagna/vargas at ±2 min (configurable); flag unstable event claims "verify birth time" and suppress minute-level precision.*

**D6 — Varga confirmation not enforced.**
D1 promise → varga confirmation → dasha activation (p6) is the mandated order; we compute vargas but the prediction path doesn't require domain-varga agreement (D9 for marriage, D10 for career…). *Fix: varga check becomes one of the counted witnesses (D4).*

Minor notes: derived-house questions (spouse's career etc.) unsupported — backlog; cross-system corroboration (Yogini/Jaimini counted only when rules were fixed pre-event) — we compute Yogini/Kalachakra but never use them as convergence witnesses; node choice (true/mean) should be stated in provenance explicitly.

## Knowledge-graph ingestion

These are method/meta-rules rather than classical source text. Recommended treatment: ingest as a distinct `method` source (this audit + a full transcription) via `ingest-newbooks-md.py → merge --promote → sync-graph.sh --deploy`, so GraphRAG can cite the discipline (e.g. "3+ witnesses required") without conflating it with śāstra. Not yet run — the graph rebuild + redeploy is its own operation.

## Direct consequence for the product

The user-facing Person Timeline must present **event-first predictions**: "Marriage window: Nov 1999 – Oct 2002 (confidence: high — 4 witnesses)" with a *did-this-happen?* control, and the running hit/partial/miss tally as the trust surface. D1–D6 above are exactly the engine work required; the notes provide the algorithm and the classical citations for every step.
