# AGENTS.md

## Cursor Cloud specific instructions

This repo has two runnable services (see `LOCAL_DEV.md` and `README.md`):

| Service | Path | Port | Stack |
|---|---|---|---|
| CVCE (calculation engine) | `cvce/` | 8400 | Python 3.12 / FastAPI / PyJHora + Swiss Ephemeris |
| Portal (web app) | `portal/` | 3000 | Next.js 16 / React 19 / Tailwind v4 |

### Running

- Both at once: `./dev.sh` (starts CVCE, waits for its `/health`, then starts the portal).
- CVCE alone: `cvce/start.sh` or `cvce/.venv/bin/uvicorn app.server:app --host 0.0.0.0 --port 8400 --reload` (run from `cvce/`).
- Portal alone: `npm run dev` in `portal/`.

### Non-obvious caveats

- **CVCE virtualenv lives at `cvce/.venv`**, not the repo root. `dev.sh` and `cvce/start.sh` both `source cvce/.venv/bin/activate`. The root `.envrc`/`pyproject.toml` (uv-based) is only for repo-wide `ruff`.
- **`patch_pyjhora.py` must run after any (re)install of PyJHora.** The PyPI build of PyJHora 4.8.7 is patched in-place under `site-packages`, so the patch is wiped whenever deps are reinstalled. It is idempotent and its smoke test is non-fatal. The update script re-runs it automatically.
- **Portal → CVCE wiring:** the portal calls CVCE server-side only. For local dev, `portal/.env.local` must set `CVCE_BASE_URL=http://localhost:8400`, otherwise the portal falls back to the hosted Fly.io engine (`vedicastro-cvce.fly.dev`). `.env.local` is gitignored, so recreate it if missing.
- **Anonymous mode:** the portal runs fully without `AUTH_SECRET`/`AUTH_GOOGLE_*`/`DATABASE_URL`. Chart casting works without any secrets; auth/dashboard/admin features are simply gated off when those are unset.
- **Casting a chart (smoke test):** open `http://localhost:3000/chart?name=Mohan&date=1975-04-22&time=19:15&lat=12.2958&lon=76.6394&tz=5.5&place=Mysore`. Correct output has Lagna = Libra, nakshatra = Swati.

### Lint / test / build (commands already in `pyproject.toml` / `portal/package.json`)

- Python lint: `cvce/.venv/bin/ruff check .` (run at repo root). The repo currently has pre-existing violations in `scripts/` and `vedicshastra_master_bundle/`.
- CVCE tests: from `cvce/`, `.venv/bin/python -m pytest` (golden charts + schema + cross-validate; ~80s).
- Portal lint / typecheck / build: `npm run lint`, `npm run typecheck`, `npm run build` in `portal/`. `lint` also has pre-existing violations.
- `predev`/`prebuild` run `scripts/sync-structured-data.mjs`, which copies knowledge-graph JSON/markdown into `portal/data/`.
