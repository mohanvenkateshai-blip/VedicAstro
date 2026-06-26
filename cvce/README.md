# CVCE — Canonical Vedic Calculation Engine

The single source of truth for sidereal calculations in the VedicAstro portal.
A hardened FastAPI service wrapping PyJHora (Swiss Ephemeris), forked from the
standalone MuhurtaCosmos backend and extended with a composed `/chart` endpoint
that returns the canonical [`chart_data`](../docs/chart_data.schema.json) payload.

> The standalone Muhurta module (`…/Panchang/panchanga_muhurtha`) is frozen and
> untouched. This is an independent extraction — the two never share a process.

## Layout

```
cvce/
  app/
    server.py   FastAPI app + endpoints
    ephem.py    low-level sidereal primitives (the only place that calls PyJHora)
    chart.py    canonical chart_data composition (vargas + ashtakavarga)
    config.py   env-driven settings (CORS, port, ayanamsa, vargas)
  vedic_engine/ optional prediction engine (powers /predict if importable)
  tests/golden/ reference-chart regression suite
  patch_pyjhora.py  PyJHora runtime compatibility patches (idempotent)
```

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python patch_pyjhora.py      # apply PyJHora patches + smoke test
cp .env.example .env                   # adjust CORS origins if needed
./start.sh                             # http://localhost:8400
```

## Key endpoint

`POST /chart` → full canonical `chart_data` (geometry + dasha + shadbala +
yogas + birth panchanga) in one round-trip. The portal stores this once per
horoscope; the Muhurta sub-module consumes it via props.

```bash
curl -s localhost:8400/chart -H 'content-type: application/json' -d '{
  "birth_datetime":"1975-04-22T19:15:00",
  "birth_lat":12.2958,"birth_lon":76.6394,"birth_tz":5.5,"name":"Mohan"
}' | jq .
```

Granular endpoints remain for transit/incremental use: `/positions`,
`/panchanga`, `/rahu-kalam`, `/dasha`, `/shadbala`, `/yogas`, `/natal`,
`/cross-validate` (independent jyotishganit check), `/predict`.

## Tests

```bash
.venv/bin/python -m pytest        # golden charts + schema validation + cross-check
```

The golden suite runs each reference chart through `/chart`, asserts placements
against a professionally cast horoscope, validates the payload against the JSON
Schema, and confirms PyJHora agrees with jyotishganit within 0.1° (after the
expected ayanamsa offset).

## Deploy

Containerized via `Dockerfile` (build context = this directory). PyJHora bundles
the Swiss Ephemeris data files, so no separate ephemeris provisioning is needed.
Recommended hosts: **Render** or **Railway** (persistent Python service). Set
`CVCE_ALLOWED_ORIGINS` to the portal origin in production.
