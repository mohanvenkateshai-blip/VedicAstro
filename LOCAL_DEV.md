# Local Dev Setup — Pre-GA

## What runs where

| Component | Pre-GA (now) | Production / GA |
|---|---|---|
| **CVCE** — Python/FastAPI, Swiss Ephemeris | `localhost:8400` via `dev.sh` | `vedicastro-cvce.fly.dev` — Fly.io, always-on |
| **Portal** — Next.js 16 | `localhost:3000` via `dev.sh` | `portal-omega-two-10.vercel.app` — Vercel |

## Why local pre-GA

The production CVCE lives on Fly.io (`shared-cpu-1x`, 1 GB) at ~$6/month.
It is configured always-on (`min_machines_running = 1`), so there are no cold starts
in production. But during heavy development, running the engine locally means:

- **Instant iteration** — `uvicorn --reload` picks up Python changes without a `fly deploy`
- **No latency** — server-side Next.js CVCE calls take <100ms instead of ~200ms over the wire
- **One less thing to debug** — network / CORS / timeout issues don't obscure logic bugs

## How to start

```bash
chmod +x dev.sh   # first time only
./dev.sh
```

Starts CVCE, waits for its `/health` check, then starts the portal.
Both stop cleanly on Ctrl-C.

The portal's `portal/.env.local` sets `CVCE_BASE_URL=http://localhost:8400`
which overrides the default fallback to Fly.io.

## Architecture (unchanged between local and production)

```
Browser
  └─ Portal  (Vercel / localhost:3000)
       ├─ server components ──────────────────────────────→ CVCE directly (cvce.ts, server-only)
       └─ /api/cvce/[...path] proxy  ──────────────────→  CVCE (client-side calls go here)
                                                               ↓
                                                   CVCE  (Fly.io / localhost:8400)
                                                   Python + PyJHora + Swiss Ephemeris
```

**Rule**: browser never hits CVCE directly.  All paths go through Next.js
(server components or the `/api/cvce` proxy).

## GA checklist — plugging the gap

Do these steps in order when ready to go live:

1. **Remove the local override** from `portal/.env.local`:
   ```
   # Delete or comment out this line:
   CVCE_BASE_URL=http://localhost:8400
   ```
   The portal falls back to `process.env.CVCE_BASE_URL` → not set → uses `vedicastro-cvce.fly.dev`.

2. **Verify CVCE is alive**:
   ```bash
   curl https://vedicastro-cvce.fly.dev/health
   ```

3. **Lock CORS** in `cvce/fly.toml` to the final domain(s):
   ```toml
   CVCE_ALLOWED_ORIGINS = "https://your-final-domain.com"
   ```
   Then:
   ```bash
   cd cvce && fly deploy
   ```

4. **Deploy portal to production**:
   ```bash
   cd portal && vercel --prod
   ```
   Or push to `main` — Vercel auto-deploys on every push.

5. **Verify production end-to-end** by loading a chart and checking Dasha Timeline
   and Transits (the two heaviest CVCE routes).

## What is NOT local (always cloud, even during development)

- **Vercel deployment** at `portal-omega-two-10.vercel.app` — the public-facing app,
  tested independently from local dev.
- **Fly.io CVCE** at `vedicastro-cvce.fly.dev` — stays running (always-on) but the
  portal dev server bypasses it via `CVCE_BASE_URL=http://localhost:8400`.
- **Git / GitHub** — source of truth; changes to the local CVCE must be committed and
  pushed before they affect the Fly.io deployment.

## Cost summary

| Resource | Pre-GA | GA |
|---|---|---|
| Fly.io CVCE (shared-cpu-1x, 1 GB) | Always-on, ~$6/mo | Always-on, ~$6/mo |
| Vercel Portal | Free hobby tier | Free hobby tier |
| **Total cloud** | **~$6/mo** | **~$6/mo** |
