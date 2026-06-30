# AGENTS.md

VedicAstro is a two-service product. See `README.md`, `LOCAL_DEV.md`, `CONTEXT.md`, and `STATUS.md` for full context.

- **CVCE** (`cvce/`) — Python 3.12 / FastAPI sidereal calculation engine (PyJHora + Swiss Ephemeris). Runs on `:8400`.
- **Portal** (`portal/`) — Next.js 16 / React 19 / Tailwind v4 frontend. Runs on `:3000`. Server-renders horoscopes by calling CVCE.

## Cursor Cloud specific instructions

The startup update script already provisions both services (creates `cvce/.venv` + installs Python deps, runs `cvce/patch_pyjhora.py`, and runs `npm install` in `portal/`). System packages `python3.12-venv` and `python3.12-dev` are baked into the VM image (needed to build the `pyswisseph` C extension). The notes below are the non-obvious gotchas.

### Running the services
- Preferred launcher: `./dev.sh` from the repo root — starts CVCE (waits for `/health`) then the portal. It exports the CVCE env vars inline and expects `cvce/.venv` to exist.
- To run individually: CVCE via `cvce/.venv/bin/uvicorn app.server:app --host 0.0.0.0 --port 8400 --reload` (from `cvce/`); portal via `npm run dev` (from `portal/`).
- Hello-world / smoke: `POST /chart` to CVCE, or open `http://localhost:3000/chart?name=Mohan&date=1975-04-22&time=19:15&lat=12.2958&lon=76.6394&tz=5.5` (Lagna should be Libra / Swati).

### Portal env (`portal/.env.local`) — required for local CVCE
- The portal defaults to the live Fly.io engine (`https://vedicastro-cvce.fly.dev`). To use the **local** CVCE you must have `portal/.env.local` with `CVCE_BASE_URL=http://localhost:8400`. This file is git-ignored (it persists in the VM snapshot but is not committed); recreate it if it is missing.
- Optionally add `AUTH_SECRET=<any-random-string>` to silence the noisy `[auth][error] MissingSecret` next-auth log. Auth is just a seam — the chart flow works without it; pages still return 200.

### Lint / test / build
- CVCE lint: `cvce/.venv/bin/ruff check .` (run from repo root, per `README.md`). The repo currently has pre-existing ruff findings, mostly in `vedicshastra_master_bundle/`.
- CVCE tests: run from the **repo root** (`cvce/.venv/bin/python -m pytest cvce/tests`), NOT from `cvce/`. Several `tests/test_graph_rules.py` cases load `knowledge-graph/graphify-out/graph.json` via a path relative to the working directory, so they only resolve from the repo root. Note: 2 graph-rules tests fail when the full suite runs together but pass in isolation — a pre-existing test-isolation issue, not an environment problem. The golden chart suite passes.
- Portal lint: `npm run lint` (eslint). `npm run typecheck` for types. Both have pre-existing findings.
- Portal build: `npm run build`. `npm run dev` for development (Turbopack).

### Notes
- `cvce/patch_pyjhora.py` patches PyJHora inside `site-packages`; it is idempotent and must be re-run after any reinstall of `cvce/.venv` (the update script does this). Reinstalling deps without re-running it can break the engine.
- Knowledge-graph features in CVCE resolve `graph.json` relative to the working directory; the engine has a hardcoded fallback so `/chart` works regardless of where uvicorn is launched.
