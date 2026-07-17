# VedicAstro — Session Handoff Context

**Snapshot:** 2026-07-17 (Claude Code / Fable 5 — Timeline v2 + E2E infra shipped; Life-Event Prediction engine is the next mission)  
**Purpose:** Preserve working context across tool/model switches. **Read this file first.**

---

## ✅ SESSION 2026-07-16/17 — READ THIS FIRST (authoritative status)

**Everything below is committed AND pushed AND deployed** (Vercel auto-deploy from main; Fly deployed manually this session). `origin/main = 80ffa2a`.

### Shipped
- **Person Timeline v2** (MAFIP final gate **97/100 PASS**): Behind/Active/Ahead digest, whole-life minimap (planet-coloured MD blocks, click-to-travel), valence-first canvas (green/red/amber by direction; origin = border style), drag-pan + Today, List view, observed-event **correction/supersession UI**. View-model lib `portal/src/lib/timeline-view.ts` (+ node:test, 9/9).
- **CVCE valence pipeline**: yoga `benefic` → priority_predictions `direction` → milestone EventDirection (was all MIXED). Suite 340 passed/1 skipped. Deployed to Fly.
- **Playwright E2E suite rebuilt** against the real app: `date`/`time` params (never `dob`), accessible-name selectors, chromium 53/53 functional+axe+responsive, 21 visual baselines (darwin), CI workflow repaired (was invalid YAML; runs chromium `--ignore-snapshots`). Local E2E: CVCE on :8400 + `CVCE_BASE_URL` in portal/.env.local (present, gitignored).
- **portal/package.json restored** after an interim session template-rewrite dropped `server-only`/`zod`/data-sync hooks/verify:gate. Rule: always `git diff HEAD` any wholesale config rewrite.
- **App fixes** found by the suite: masthead overflowed 640–1000px (search lg-only, nav/CTA md+), kundali SVG fixed-460px on mobile (max-w-full), landing h1→h3 skip (sr-only h2).
- **/muhurta restored to the frozen standalone iframe** (owner decision; 80ffa2a). Native `/chart/muhurta` stays feature-gated.
- **docs/VEDIC_DIGEST_METHOD_AUDIT.md**: handwritten notes (accurate-prediction 15pp, panchanga-muhurta 5pp, calendar pp1–8, Jyotisha orientation sheet) vs engine. Calculations aligned; deviations **D1–D6** (headline: yoga-first vs event-first).

### Known issues / caveats
- **Prod timeline writes 503**: Fly has no durable volume/`CVCE_TIMELINE_DATABASE_PATH`; add/correct-event fails in production (reads fine). Provision before advertising the feature.
- **Lint debt**: 90 pre-existing errors in 27 files (NOT timeline) block `npm run ci` — cleanup agent was running at checkpoint; commit its work when green (`npx eslint src/ tests/` must exit 0).
- Visual baselines are darwin-only; CI ignores snapshots until linux baselines land.

### Owner decisions recorded 2026-07-17
1. Muhūrta: iframe restored (done).
2. **Proceed** with programme re-gates: B3 (remediation complete, needs independent re-gate), Transit Context (last 68/100), B2 (last 66/100). The "holds" are the project's own ≥95 MAFIP release policy — not external.
3. **Proceed** with the **Life-Event Prediction engine** — THE next mission. Event-first dated windows (marriage/children/career/foreign/home/health): six-witness promise (bhava+lord+occupants+karaka+varga+yoga → confidence), dasha windows gated on the event's house network (lord chain), fructification/AV transit narrowing to months, published with the notes' output template (window+confidence+alternatives+limits), timeline shows them as checkable claims ("did this happen?") feeding the append-only hit/miss tally per chart — the product's trust engine (user: "I want to know if the app correctly predicted my marriage date, my kid's birth, my international job"). Spec seed = the audit doc D1–D6 + Domain Keys table (p5) + high-specificity map (p15) of the prediction notes.
4. KG ingest of the digest PDFs: recommended, **not yet approved** — ask before running (graph rebuild + redeploy).

### Verification quickstart (all green at checkpoint)
`cd cvce && .venv/bin/python -m pytest -q` (340+1) · `cd portal && npm run typecheck` · `node --test src/lib/timeline-view.test.mts` (9/9) · `npx playwright test --project=chromium tests/app.spec.ts tests/interaction tests/responsive tests/accessibility` (53/53; needs both local servers) · golden chart: Mohan 1975-04-22 19:15 Mysore, Lagna Libra/Swati p4.

---

## ✅ SESSION COMPLETE — 2026-07-04 — READ THIS FIRST (authoritative status)

**Deploy model:** push `main` → **Vercel** auto-deploys `portal/` (frontend, https://portal-omega-two-10.vercel.app).
Backend `cvce/` → **Fly.io** `vedicastro-cvce` (NOT touched this session). Supabase (guest charts +
avatars + KG vault) + Neon (users/auth). **State:** origin/main = `6264d6e`; **UNPUSHED = `f7e7be3`
(admin back-link cleanup) + this handoff commit → run `git push origin main` to deploy them.**
(Claude Code auto-mode blocks pushing to main; the user pushes manually.)

### Shipped this session (newest first; all committed on main)
- **f7e7be3** admin: removed "← Dashboard" back-links + duplicate "Admin" eyebrow from admin pages *(UNPUSHED)*
- **6264d6e** admin: persistent sub-nav (Console/System health/Knowledge graph) via `app/admin/layout.tsx` + `components/admin/AdminNav.tsx`
- **60e2186** admin: dedicated admin-only **Admin tab** in masthead + `/admin` console hub (`app/admin/page.tsx`). Admin reached ONLY via the role-gated tab — never by typing a URL.
- **dbe38ce** csp: `next.config.ts` img-src now allows `https://*.supabase.co` + `https://lh3.googleusercontent.com` (avatars uploaded fine but CSP blocked rendering → looked broken)
- **52dab61** profile: avatar auto-save feedback ("Photo saved"/"Uploading…"/real errors)
- **fe45aa9** profile: avatar **UPLOAD to Supabase Storage** (`POST /api/prefs/avatar` → public `avatars` bucket, auto-created via service-role → `users.image`) + landing page redirects signed-in users to `/resume`
- **d42831c** compatibility: `KootaMatcher` per-partner **city autocomplete** (`/api/cvce/places`) + **"Load a saved chart"** dropdown
- **5a83ee3** theme: light-mode contrast (`hover:bg-white/*`→`hover:bg-accent/5`; `bg-accent text-white`→`text-accent-fg`; hairline 10%→14%) + retired dead `saved_charts` table
- **1052dd5** 🔴 security: **saved charts scoped to ACCOUNT not browser** (`lib/chart-owner.ts`; `/api/charts` + `/api/charts/[id]` filter `guest_charts` by `user_<id>` or guest cookie)
- **0b3eb2e** learn: `loading.tsx` skeleton + `unstable_cache` on `listBooks` (was ~5s dead click → "non-functional")
- **7ac0f34** masthead: resume restores chart (path+query via `useSearchParams`) + account control rightmost in both auth states
- *(same session, already live earlier: the full session-mgmt/personalization/masthead BUILD — see §-2. Landed same day but NOT this AI: `9c7d735/dee610b/4ade94b/58ce40c` ashtakavarga overhaul, `2d04140/4d83715` the earlier INEFFECTIVE saved-charts fix that `1052dd5` superseded.)*

### Feature map (current state)
- **Auth/session**: NextAuth v5 JWT. `Session = {userId,email,role,name,image,theme,lastPath}` (`lib/auth/types.ts`). Role from `ADMIN_EMAILS` env → jwt cb → session; `getSession()` merges DB prefs (`getUserPrefs`).
- **Masthead** (`SiteHeader.tsx`, prop `session`): nav (Compatibility/Muhūrta/Learn/Dashboard + **Admin tab if role==="admin"**), `GlobalSearch`, `NotificationBell`, "Cast a chart", `UserMenu` (Avatar→Profile/Settings/Theme/Sign out). Account control rightmost in both states.
- **Personalization**: per-user theme (`users.theme`, `lib/theme.ts`+`ThemePicker`, no-flash script in `layout.tsx`); resume-last-page (`LastVisitedTracker`→`/api/prefs/last-path`→`/resume`; signin defaults to `/resume`); `/profile` (avatar upload + editable name) + `/settings` (theme, account, sign out). Both proxy-protected.
- **Notifications**: `notifications` table (RLS), `/api/notifications` GET+PATCH, `NotificationBell` polls 60s. **Empty (no seeder yet).**
- **Admin**: `/admin` hub + `/admin/health` + `/admin/knowledge`, all gated by `app/admin/layout.tsx` `requireSession("admin")`, with persistent `AdminNav` sub-nav. Admin tab visible only to admins.
- **Charts privacy**: `guest_charts` scoped by `lib/chart-owner.ts` `resolveChartOwner()` → `user_<id>` for authed (private + cross-device), guest cookie for anon. **This app-layer filter is THE boundary — service-role bypasses RLS; every guest_charts query must keep `.eq("guest_id", owner)`.**

### DB / env prerequisites
- **Neon** (`portal/src/lib/auth/schema.sql`, auto-applies on cold start): `users` +image/theme/last_path; new `notifications` table.
- **Supabase** (`portal/supabase-schema.sql`): `guest_charts` now holds authed charts under `guest_id="user_<id>"`; dead `saved_charts` table removed/documented.
- **Vercel env**: `ADMIN_EMAILS` (comma list; gates Admin tab — change → REDEPLOY → sign out/in). `SUPABASE_URL`+`SUPABASE_SERVICE_ROLE_KEY` (avatars+charts). `AUTH_SECRET`/`AUTH_GOOGLE_ID`/`AUTH_GOOGLE_SECRET`. `DATABASE_URL` (Neon). `ENCRYPTION_KEY`.

### Verified LIVE (prod probes) · Verified by USER · Needs USER verify
- LIVE: Learn 0.3–0.7s; `/api/prefs/avatar` 401 unauth /405 GET; CSP img-src has supabase.co+googleusercontent; `/admin` gated.
- USER-CONFIRMED: admin role works (badge=Admin, Admin tab visible); theme persists on re-login.
- STILL NEEDS USER: 🔴 **saved-charts A/B privacy** (2 accounts, same browser → B's dashboard empty, not A's); avatar renders after CSP fix (hard-reload Cmd+Shift+R); compatibility city/saved-chart; resume-last-page incl. chart.

### Open backlog (not started)
- Notification **seeder** (welcome notif on first sign-in) — bell currently always empty.
- Audit `lib/saved-charts.ts` **localStorage** path (used by `ChartSidebar`?) so it can't resurface others' charts (the DB path is fixed; this legacy path wasn't).
- Light-theme deeper QA: `astroColors` planet palette contrast on white.
- Landing hero copy could be sharpened (currently: signed-in→/resume, anon→hero).
- From prior sessions (deferred): rectification `POST` endpoint + UI; report-redesign frontend (`PriorityInsightsCard`, wire `DashaIntelCard`/`TransitIntelCard`); Learn curriculum revamp; notification-center Phase 2; admin KPI analytics.
- Ashtakavarga module (not this AI's work): sanity-check SAV=337 invariant.

### Housekeeping
- Uncommitted non-feature files left alone: `.gitignore`, `docs/knowledge-engine-status.md`, `knowledge-graph/KNOWLEDGE_CATALOG.md` (other session); stray `Branding/`, `embeddings.pid`, `vedicastro-audit-report.html`.
- Pre-existing lint `any` errors (`corpus.ts`/`db.ts`/`graphify.ts`/`types.ts`) are NOT from this session and don't block `next build` (Vercel's deploy gate).

---

## -2. ACTIVE BUILD — Session Mgmt + Personalization + Masthead (EXECUTION-READY SPEC, 2026-07-04)

> **User intent (verbatim):** "User Name should be captured, Personalization module
> implemented, Theme + page-where-user-left remembered so on re-login they carry on
> from that page. Complete session management with all standards. Username top-right
> shows Profile, Theme, Settings, Log out/in. Standard masthead: search, notification
> center, username top-right. Build ground-up, wire everything, test E2E for normal +
> admin users. ASAP." User authorized >5 agents FOR THIS FEATURE. Then: "PLAN EVERY
> DETAIL, KEEP READY IN HANDOFF" (this section) + "proceed until ~95% context".
>
> **Status (2026-07-04, DEPLOYED):** LIVE on main (commit 87f6b11, pushed by user).
> Verified in prod: home 200; /settings → 307 (new proxy matcher + route serving = new code
> live); /api/db/migrate → configured:true, tablesPresent:true. DB migration auto-applied via
> ensureSchema() on first getSession DB hit (idempotent ALTER/CREATE in schema.sql). If theme
> persistence ever no-ops, belt-and-suspenders: `cd portal && npm run db:schema:remote`.
> REMAINING: only the human E2E sign-in walkthrough (real Google OAuth, can't be curl'd) —
> checklist in PHASE 7 below. Pre-existing lint `any` errors (corpus/db/graphify/types.ts) are
> NOT mine and don't block `next build`.
> OPTIONAL follow-up: seed a "welcome" notification in upsertUser so the bell is non-empty on
> first sign-in (makes the notification center immediately visible/testable).
>
> **What shipped this build:** session now carries name/image/theme/lastPath (jwt+session cb
> + getSession DB-merge); `users` gained image/theme/last_path cols + new `notifications`
> table (RLS); masthead rebuilt (SiteHeader takes `session`) with GlobalSearch (→/api/learn/search)
> + NotificationBell (polls /api/notifications) + UserMenu (Avatar→Profile/Settings/Theme/Admin/
> Sign out); per-user theme (lib/theme.ts + ThemePicker, DB-persisted, server-injected no-flash
> script in layout); resume-last-page (LastVisitedTracker in layout → /api/prefs/last-path →
> /resume redirector; signin defaults to /resume); Profile + Settings pages (proxy matcher +
> PROTECTED_PREFIXES extended to /profile,/settings). New UI primitives Avatar + Menu/MenuItem.

### E2E test results (user, 2026-07-04, live prod) + triage
Signed in as normal user uvwxme@gmail.com (name "Mr.Cool", Free). Findings:
- ✅ Test 1: theme change retained on re-login (per-user DB theme works).
- 🔧 Test 2 (FIXED, pending push): resume restored the *page* (/chart overview) but not
  the *chart*. Root cause: chart identity is in the URL query (chart pages read searchParams;
  saved charts = localStorage birth-params). LastVisitedTracker recorded usePathname() only,
  dropping the query. Fix: tracker now records path+query via useSearchParams (wrapped in
  Suspense in layout to keep static pages static). NOTE remaining edge: saved charts are
  localStorage-per-browser (src/lib/saved-charts.ts, key vedicastro_saved_charts) — resume via
  URL works same-browser; cross-device chart resume would need saved charts in the DB (backlog).
- 🔧 Test 7 (FIXED, pending push): account control jumped sides — Sign in was LEFT of
  "Cast a chart" (signed out) but avatar was RIGHT of it (signed in). Fix: account control
  (avatar / Sign in) is now rightmost in BOTH states, Cast-a-chart immediately left. User also
  asked "why is Cast a chart in the header?" — kept (it's the only header entry to the core
  action; there's no Chart nav item) but styled Sign in as a bordered button. Revisit if user
  still wants it removed.
- 🔧 Test 4 (FIXED, pending push): Learn tab "nothing happens when clicked". ROOT CAUSE (not a
  JS error): /learn RSC navigation took ~4.3-5.9s because listBooks("newbooks-v1") fans out to
  ~240 Supabase count-queries (61 books × up to 4 ilike probes) + per-book markdown parsing, and
  there was NO loading.tsx → a click gave zero feedback for ~5s = "non-functional". Other tabs
  are fast so they felt instant. FIX: (1) added src/app/(main)/learn/loading.tsx skeleton →
  instant navigation feedback; (2) wrapped the book list in unstable_cache (revalidate 3600,
  tag "learn-books") so it's slow only on the first request, instant after. Build passes.
  Follow-up option: same slow-listBooks pattern may affect /learn/[bookId] and dashboard-side
  book loads — consider caching listBooks itself in src/lib/books.ts if other routes drag.
- 🔧 Test 3 (FIXED, commit 5a83ee3, pending push): light theme "not gelling" was components
  using dark-only colors that vanish on light — hover:bg-white/{5,3,0.02} → hover:bg-accent/5
  (BirthForm, DashboardTable, ChartSidebar, GocharPanel); Ashtakavarga chips bg-accent text-white
  → text-accent-fg; light hairline 10%→14% for border definition. Deeper visual QA may still find
  more (e.g. astroColors planet palette contrast on white) — revisit if user flags specific pages.
  Also retired the dead saved_charts table from supabase-schema.sql (documented; drop optional).
- 🔧 Test 5 (DONE, commit d42831c, pending push): Compatibility (KootaMatcher.tsx) now has a
  per-partner city autocomplete (PlaceField → /api/cvce/places fills lat/lon/tz) + a
  SavedChartPicker dropdown that loads an account-scoped saved chart into a partner slot.
  Raw lat/lon/tz remain editable.
- ⏳ UNPUSHED at this point: 5a83ee3 (light theme + cleanup), d42831c (compatibility). Plus
  handoff edits. `git push origin main` to deploy.
- 🔧 Profile picture (DONE, pending push): avatar UPLOAD to Supabase Storage. New
  POST /api/prefs/avatar (png/jpg/webp/gif ≤2MB) → public "avatars" bucket (auto-created via
  service-role on first upload) → users.image (cache-busted URL). Profile page has AvatarUpload
  (camera button, preview, inline errors). New updateUserImage() helper. NOTE: needs
  SUPABASE_SERVICE_ROLE_KEY with storage perms (service role has them); bucket is public-read
  (fine for avatars). First upload creates the bucket — verify in Supabase Storage after.
- 🔧 Test 6 (DONE, pending push): user decision = landing page is acquisition-only. Signed-in
  users hitting / now redirect to /resume (last page / dashboard); anonymous visitors see the hero.
- ⏳ UNPUSHED: 5a83ee3 (light theme+cleanup), d42831c (compatibility), + the avatar/landing commit
  (profile+landing). `git push origin main` to deploy all. ALL Test-list items now resolved.

### 🔴 SECURITY FIX (2026-07-04) — saved charts leaked across all logins
User report: "no matter what google account I login, I see all charts saved in dashboard."
ROOT CAUSE: DashboardTable fetches /api/charts, which scoped rows ONLY by the per-BROWSER
`vedicastro_guest_id` cookie — NEVER by session.userId. Same browser + any Google account =
same guest cookie = everyone sees everyone's charts. The earlier 2d04140 "fix" was ineffective:
it neutered getSavedCharts() in saved-charts.ts, but DashboardTable never calls that (hits
/api/charts directly), and the `saved_charts` RLS table it added is DEAD scaffolding — nothing
reads/writes it, its RLS uses Supabase auth.uid() (app uses NextAuth + service-role key that
BYPASSES RLS), and the policy SQL is malformed (INSERT/UPDATE/DELETE missing CREATE POLICY
headers). FIX (this session, pending push): new src/lib/chart-owner.ts resolves an owner key —
`user_${session.userId}` for authed users (private per-account AND cross-device), else the guest
cookie. Both /api/charts (GET/POST) and /api/charts/[id] (DELETE/PATCH) now filter guest_charts
by that owner. Since service-role bypasses RLS, this APP-LAYER scoping is the only boundary —
every guest_charts query MUST keep the .eq("guest_id", owner) filter. Build passes.
NOTES: (1) Post-deploy, authed users' dashboards start EMPTY — their previously-saved charts sit
under the old browser-guest UUID, not user_<sub>; this is the correct privacy outcome (old shared
rows are quarantined, not served to any account). Optional follow-up: one-time "claim guest charts
into your account on first login" migration (weigh the shared-browser risk). (2) CLEAN UP the dead
`saved_charts` table + malformed policies in supabase-schema.sql. (3) saved-charts.ts localStorage
path still exists (used by ChartSidebar?) — audit that it can't resurface others' charts.

### Ground truth from discovery (do NOT re-investigate)
- **Auth**: NextAuth v5 JWT strategy, no DB adapter. Config `portal/src/app/api/auth/auth.ts`
  (jwt cb ~65-90 sets role; session cb ~91-98 copies ONLY `id`+`role`). Session type
  `portal/src/lib/auth/types.ts` = `{userId,email,role}` — **no name/image/theme**.
  `getSession()` in `portal/src/lib/auth/session.ts` is `cache()`-wrapped, wraps `auth()`.
  `requireSession(minRole,returnPath)` in `portal/src/lib/auth/index.ts` redirects to
  `/auth/signin?callbackUrl=`. Proxy `portal/src/proxy.ts` (Next16 middleware) matcher
  `["/dashboard/:path*","/admin/:path*"]`, checks cookie PRESENCE only.
- **DB**: Neon `@neondatabase/serverless`, raw SQL via `portal/src/lib/db.ts` — tagged
  template `` sql`...` `` for params, `sql.query(stmt,[])` for raw DDL. `withUserContext(userId, makeQuery)`
  runs inside txn with `set_config('app.current_user_id',...)` for RLS. Schema =
  single idempotent file `portal/src/lib/auth/schema.sql`, auto-applied on first prod
  connection via `ensureSchema()` (`migrate.ts`), or `npm run db:schema:remote`.
  Convention: append `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` / `CREATE TABLE IF NOT EXISTS`.
  `users`(id TEXT PK=Google sub, email, name, role, created_at, updated_at) — **no image col**.
  `horoscopes` has the RLS pattern to mirror (`horoscopes_isolate` USING `app.current_user_id`).
- **Theme**: `portal/src/components/ThemeToggle.tsx` client-only, toggles `.dark` on
  `<html>`, persists `localStorage['va-theme']`. No provider, next-themes NOT installed.
  `portal/src/app/layout.tsx` (async SERVER comp) has inline no-flash script (lines ~24-35)
  reading `va-theme` before paint; `<html suppressHydrationWarning>`. CSS tokens in
  `globals.css` (`@custom-variant dark`, indigo `--color-primary`, gold `--color-accent`).
- **UI kit** `portal/src/components/ui/`: `Button`/`ButtonLink` (primary|accent|ghost),
  `Card`+`CardLabel`, `Overlay` (full-screen modal/sheet, motion/react, Escape-close —
  too heavy for a corner dropdown). **MISSING: anchored popover/menu + avatar** — build them.
  `SiteHeader.tsx` (68 lines, client, `usePathname`) props `{signedIn?,role?}`, flat nav
  Links + ThemeToggle + "Cast a chart" CTA. Rendered `layout.tsx:39` `<SiteHeader signedIn role/>`.
  Search pattern to COPY (not the API): `LearnGlobalSearch.tsx` (180ms debounce, outside-click,
  dropdown `rounded-2xl border-hairline bg-card shadow-lg`). Notifications = 100% greenfield.
- **Resume/test**: NO `(main)/layout.tsx` — only root `layout.tsx`; mount any global client
  hook there. No `document.cookie` in src; guest-cookie pattern `api/charts/route.ts:5-16`
  (`httpOnly,sameSite:lax,path:/,maxAge:1yr`). signin `portal/src/app/auth/signin/page.tsx`
  reads/validates `callbackUrl`, default hardcoded `"/dashboard"` (~line 13). **Zero frontend
  test infra** (no Playwright/Jest/Vitest); `npm run ci` = lint+typecheck+build. Admin vs normal
  = `role` field only; no separate admin login.
- **Next.js 16 caveats** (portal/AGENTS.md): breaking changes vs training data — READ
  `node_modules/next/dist/docs/` before writing. Use `proxy.ts` not middleware; `searchParams`
  is awaited; route handlers/pages async server comps by default.

### PHASE 0 — Data foundation (BLOCKS ALL; do first, commit alone)
**0a. `portal/src/lib/auth/schema.sql`** — append (mirror horoscopes' exact UUID-default
expression — check its `id ... DEFAULT` and copy it, likely `gen_random_uuid()`):
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS image     TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS theme     TEXT NOT NULL DEFAULT 'system'
  CHECK (theme IN ('light','dark','system'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_path TEXT;

CREATE TABLE IF NOT EXISTS notifications (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),   -- match horoscopes' default expr
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind       TEXT NOT NULL DEFAULT 'info' CHECK (kind IN ('info','success','warning','alert')),
  title      TEXT NOT NULL,
  body       TEXT,
  href       TEXT,
  read_at    TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS notifications_user_created
  ON notifications (user_id, created_at DESC);
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS notifications_isolate ON notifications;
CREATE POLICY notifications_isolate ON notifications
  USING (user_id = current_setting('app.current_user_id', true));
```
**0b. `portal/src/lib/auth/index.ts`** — (i) `upsertUser` + `ensureUser`: add `image`
to INSERT + `ON CONFLICT DO UPDATE` (don't clobber role logic). (ii) NEW fns, all
`withUserContext(userId,...)` where user-scoped:
- `getUserPrefs(userId) -> {theme, lastPath, image, name} | null`
- `updateUserTheme(userId, theme: 'light'|'dark'|'system')`
- `updateLastPath(userId, path: string)`
- `updateDisplayName(userId, name: string)`
- `listNotifications(userId, {limit=20})`, `unreadCount(userId)`,
  `markNotificationRead(userId, id)`, `markAllRead(userId)`,
  `createNotification(userId, {kind,title,body?,href?})`
**0c. Session threading**:
- `types.ts`: `Session = {userId,email,role,name?,image?,theme:ThemePref,lastPath?}`;
  `type ThemePref='light'|'dark'|'system'`.
- `auth.ts` jwt cb: persist `token.name = user.name; token.picture = (user as any).image`
  on sign-in. session cb: also `session.user.name/image` from token (role stays).
- `session.ts` `getSession()`: after `auth()`, call `getUserPrefs(userId)` and merge
  `theme/lastPath/image/name` (role+email+userId still authoritative from token).
  Keep it inside the existing `cache()` wrap (one DB read/request).

### PHASE 1 — UI primitives (commit with PHASE 2)
- `portal/src/components/ui/Avatar.tsx` — client; props `{name?,email,image?,size?}`;
  render `<img>` if image else initials (first letter of name else email) on
  `bg-primary/10 text-primary` circle. Sizes sm/md.
- `portal/src/components/ui/Menu.tsx` — anchored dropdown. Client. `{trigger, children, align?}`.
  Button toggles `open`; panel `absolute right-0 mt-2 rounded-2xl border-hairline bg-card
  shadow-lg z-50`; outside-click (ref + mousedown listener) + Escape close (copy from
  LearnGlobalSearch). Export `MenuItem` ({href?|onClick, icon?, children, danger?}).

### PHASE 2 — Masthead (rebuild SiteHeader)
- Change `layout.tsx:39` to pass full session: `<SiteHeader session={session} />`
  (session already fetched at `layout.tsx:30`). SiteHeader accepts `{session: Session|null}`.
- Keep existing primary nav Links + logo. Right cluster (signed-in): `<GlobalSearch/>`
  `<NotificationBell/>` `<UserMenu session/>`. Signed-out: keep "Cast a chart" + a
  "Sign in" link to `/auth/signin`.
- `portal/src/components/masthead/UserMenu.tsx` — `<Menu>` triggered by `<Avatar>`; panel:
  header (name + email), `MenuItem` Profile (`/profile`), Settings (`/settings`), a Theme
  row (3 pills light/dark/system → calls setTheme, see PHASE 3), Admin (`/admin/health`,
  only if `role==='admin'`), divider, Sign out (`danger`, calls `signOut({redirectTo:'/'})`
  from `next-auth/react`).
- `portal/src/components/masthead/NotificationBell.tsx` — client; bell icon + unread badge;
  on open fetch `GET /api/notifications`; list rows (kind color dot, title, body, relative
  time, href link); "Mark all read" → `PATCH /api/notifications {all:true}`; clicking a row
  marks it read. Poll unread count on mount + every 60s (cheap).
- `portal/src/components/masthead/GlobalSearch.tsx` — copy LearnGlobalSearch mechanics;
  hit `GET /api/search?q=` (PHASE 6). v1 acceptable = learn results only, labeled.

### PHASE 3 — Per-user theme
- `ThemeToggle.tsx` / a new `setTheme(theme)` helper: still write `localStorage['va-theme']`
  (instant, no-flash) AND if signed-in `POST /api/prefs/theme {theme}`. 'system' → clear
  explicit class, honor matchMedia (existing script already does).
- `layout.tsx`: if `session?.theme` is 'light'|'dark', set `<html className>` accordingly
  server-side (authoritative cross-device); 'system'/guest → leave to inline script. Keep
  inline script for guests + no-flash. Ensure the two don't fight (server class wins on load,
  script only sets when no server class / system).

### PHASE 4 — Resume last page
- `portal/src/components/LastVisitedTracker.tsx` — client, `usePathname` + `useEffect`;
  if signed-in and path is a "real" page (not `/auth`, `/api`, not the current last_path),
  debounce ~1s then `POST /api/prefs/last-path {path}`. Mount in `layout.tsx` next to header.
  (Pass `signedIn` as prop from layout since it's a server comp.)
- `portal/src/app/resume/page.tsx` — server; `requireSession()`; read `session.lastPath`,
  `redirect(lastPath || '/dashboard')`.
- signin: change post-login default `redirectTo` from `/dashboard` → `/resume` (only when no
  explicit callbackUrl). So fresh login resumes last page; deep-link callbackUrl still wins.

### PHASE 5 — Pages (protect via proxy)
- Add `"/profile"`,`"/settings"` to `PROTECTED_PREFIXES` (`types.ts`) AND proxy matcher
  (`proxy.ts` matcher array) so they gate on cookie presence.
- `portal/src/app/profile/page.tsx` — server, `requireSession()`; Avatar + name (editable
  → `/api/prefs/profile`), email, role badge, "member since" (created_at), saved-charts count.
- `portal/src/app/settings/page.tsx` — server, `requireSession()`; Appearance (theme picker,
  reuses PHASE 3 setter), Notifications (future toggles — stub OK), Account (email/role read-only,
  Sign out button, link to `/api/auth/signout`).

### PHASE 6 — API routes (all Next16 route handlers, async, `requireSession` inside)
- `portal/src/app/api/prefs/theme/route.ts` POST `{theme}` → `updateUserTheme`.
- `portal/src/app/api/prefs/last-path/route.ts` POST `{path}` → `updateLastPath`.
- `portal/src/app/api/prefs/profile/route.ts` POST `{name}` → `updateDisplayName`.
- `portal/src/app/api/notifications/route.ts` GET (→ `{items, unread}`), PATCH `{id?|all?}`
  → mark read.
- `portal/src/app/api/search/route.ts` GET `?q=` → v1 delegate to existing
  `/api/learn/search` logic (`getAllStructuredBooksSync`), shape `{hits}`.
- All: validate session, 401 if none; RLS via `withUserContext`.

### PHASE 7 — Verify + deploy
- `cd portal && npm run ci` (lint+typecheck+build) MUST pass — this is the automated gate
  (no E2E framework exists; do NOT add Playwright under the token/time limit unless asked).
- Apply migration to prod: `npm run db:schema:remote` (needs prod AUTH_SECRET) OR rely on
  cold-start `ensureSchema()`; verify with `GET /api/db/migrate` (reports tablesPresent).
- Deploy = push to main (Vercel auto). Verify Vercel `Ready`.
- **Manual E2E checklist** (real Google OAuth can't be curl'd) — record pass/fail in handoff:
  NORMAL USER: sign in → name+avatar top-right; open user menu (Profile/Settings/Theme/Sign
  out present, NO Admin); switch theme → persists after reload + cross-device (DB); visit a
  deep page (e.g. /dashboard/... or a chart) → sign out → sign back in → lands on that page;
  notification bell shows (seed one via `createNotification`), mark read clears badge; Profile
  edit name persists; search returns learn hits. ADMIN USER: same PLUS Admin item → `/admin/health`
  loads; non-admin hitting `/admin/*` is redirected.

### Open decisions already made (don't re-ask)
- Theme source of truth = DB `users.theme`, localStorage only for no-flash mirror.
- Profile/Settings at top-level `/profile`,`/settings` (add to proxy), not under `/dashboard`.
- Notifications stored in Neon `notifications` table w/ RLS (not Supabase).
- Search v1 = learn-only, generalize later (don't block masthead on cross-entity search).
- name/image threaded via JWT token + merged in getSession from DB; role stays token-authoritative.
- No Playwright this pass — `npm run ci` + manual checklist is the gate.

---

## -1. LATEST SNAPSHOT — 2026-07-03 (Claude Code session, Sonnet 5 → Fable 5)

### Product vision (durable, overrides feature-level defaults)
The app is a "superintelligent portal": predictions must be **prioritized, timed,
actionable** — never generic yoga listicles. Realistic remedies, not textbook
mantra boilerplate. Timing ambition is day/time precision via **multi-dasha
confluence** (guru's principle: Vimshottari + Yogini together, not one system
alone), which requires **birth-time rectification first** (~3 months dasha
shift per 1 minute birth-time error). Saved as persistent memory
(`vision_actionable_predictions.md` in the Claude memory dir).

### Shipped this session (15 commits on main, all deployed to Fly + Vercel)
- **Kalachakra Dasha**: full classical rebuild (`cvce/app/kalachakra.py`, ~900
  lines; `portal/src/components/dashas/kalachakra/`) — Deha/Jeeva, 3 Gatis,
  MD/AD/PD tree, SVG wheel, leap timeline/quick-nav, Argala/Yogakaraka/travel-
  direction/Moon's-Navamsa interpretive layer, storytelling narratives.
  Validated against BPHS Vol.2 Ch.46, PVR Rao tutorial, Cosmic Insights
  (which caught + fixed a real MD/AD duration bug, commit `761c997`).
- **Ashtakavarga**: 3 computation bugs fixed (`05cc3fa`) — now delegates to
  PyJHora, SAV 337-invariant restored. New Divisional Charts + Ashtakavarga tabs.
- **UI**: Navagraha/elemental color system (`portal/src/lib/astroColors.ts`)
  cascaded app-wide (`e456aa9`); bigger charts + per-chart North/South toggle;
  degree-on-hover; rotating Vedic loading phrases (`LoadingPhrase.tsx`).
- **Ops**: recovered full backend outage (single Fly machine saturation —
  restart fixed; stayed at 1 machine per free-tier constraint; bill $2.18→$0
  under Fly's $5 waiver).
- **Validation milestone**: user's real marriage date (2007-02-28) landed
  exactly on Venus Pratyantardasha — deep-dasha engine confirmed accurate.
  User then provided 6 precisely-dated life events as calibration data.

### In flight (uncommitted at snapshot time; being committed + deployed now)
1. **Report redesign backend** (`cvce/app/report_facts.py` + new
   `cvce/app/remedies.py` + `cvce/tests/test_report_priority.py`):
   `priority_predictions` — ≤6 yogas ranked by real chart strength
   (SAV+Shadbala+dignity of planets_involved), timed to Mahadasha windows,
   selectively remedied (hand-curated themes; remedies only where a genuine
   affliction or negative classical text warrants). 45/45 tests pass.
   **Frontend half NOT started**: PriorityInsightsCard, collapse YogasCard,
   wire in already-built-but-unrendered DashaIntelCard/TransitIntelCard
   (`HoroscopeReport.tsx:141-288`).
2. **Birth-time rectification engine** (new `cvce/app/rectification.py`):
   multi-dasha confluence scoring (Vimshottari depth-5 + Yogini MD/AD),
   house-lordship-aware per candidate lagna, ±30 min sweep at 1-min steps.
   **Live validation run against user's 6 events was interrupted — re-run
   pending.** No HTTP endpoint yet (deferred until validated).

### User's calibration events (for rectification; birth 1975-04-22 ~19:15, Mysuru 12.2979/76.6393/+5.5)
| Event | Date/time | Domain |
|---|---|---|
| Marriage (1st) | 2007-02-28 | marriage |
| Second marriage | 2014-01-19 09:15 | marriage |
| Birth of son | 2015-07-21 21:15 | children |
| Job loss | 2016-04-29 | career_obstacle |
| Job start | 2018-11-28 | career_status |
| Mother's demise | 2021-07-17 15:20 | mother |

### Standing session rules (user-granted, still in force)
- KnowledgeGraph/KE authoritative over secondary/AI-summarized sources.
- Fix any bug encountered immediately, no per-bug confirmation needed.
- Free tier only — no cost-increasing infra without asking.
- Deploy verification discipline: curl prod endpoints + Vercel `Ready` check.
- The legacy "≥5 parallel agents mandatory" protocol (Cursor/Kilo era, §below)
  is NOT in force in Claude Code sessions; use subagents where they help.

### Next steps (in order)
1. Re-run rectification validation vs 6 events → report ranked candidates.
2. Finish report-redesign frontend (types.ts, PriorityInsightsCard, collapse
   yoga list, wire intel cards) → typecheck/build → deploy.
3. Rectification fast-follows: `POST /rectify-birth-time` endpoint + UI;
   add Ashtottari/Chara/Kalachakra as confluence systems.
4. Roadmap: day/time-precision prediction engine on rectified birth times.

---

## 0. Quick Start for Next AI

```bash
cd /Users/ganesha/Projects/04-UX-Practice/VedicAstro

# KE wave health (9 engines, 10 probes, 0 cracks)
python3 scripts/ke_wave_status.py

# Learn structured library
node portal/scripts/verify-all-learn-books.mjs   # expect 60 structured-pass / 61 manifest

# Portal typecheck
cd portal && npm run typecheck

# Local dev (agent must run this — do not ask user)
cd portal && npm run dev
# → http://localhost:3000/learn

# Production gate for Learn (mandatory before marking Learn DONE)
./scripts/smoke-learn-production.sh
```

**Read order after this file:** `CONTEXT.md` → `docs/KE_FULL_UPDATE_WAVE_2026-06-30.md` → `docs/knowledge-engine-status.md` → `LEARN_FULL_CHAPTERS_STATUS.md`

---

## 1. What Was Accomplished (Full Session Arc)

### A. Learn module — all books with clean chapters (prior milestone, still active)
- **60/61 books** use authoritative structured chapters from `knowledge-graph/structured/*.json` + local raw markdown (`knowledge-graph/raw/` or bundled `portal/data/raw/`).
- **1 edge:** `Jataka_Tatva_Mahadeva` — 0 structured chapters; parse fallback collapses to single "Full Text" chapter for heavy page-scanned OCR.
- Local Graphify is the foundation — **no Supabase download required** for Learn reader bodies.
- NextAuth `MissingSecret` fixed: auth only initializes when real `AUTH_SECRET` + OAuth creds exist; Learn works anonymously.

### B. Learn UI polish (this session, portal)
| Feature | Files | Behavior |
|---------|-------|----------|
| **Global search** | `LearnGlobalSearch.tsx`, `api/learn/search/route.ts`, `learn/page.tsx`, `learn/[bookId]/page.tsx` | Cross-book search on title/chapter/section; debounced dropdown; deep-links with `?chapter=&section=&q=`; "← Back to search results" on book page |
| **Clean tile metadata** | `books.ts` (`humanizeTitle`, `extractDisplayMeta`, `displayTitle`/`author`/`year`) | Tiles show human title + author + year, not raw underscores |
| **Tile overflow fix** | `learn/page.tsx` | `overflow-hidden`, `break-all line-clamp-2` on titles |
| **Scroll-to-top FAB** | `BookReaderClient.tsx` | Fixed bottom-right FAB after scroll (window + reader pane); smooth scroll to top |

### C. KE Full Update Wave (major — merged to `main`)
**Goal:** Every module/feature pulls latest program logic, calculations, and algorithms from the Knowledge Graph with supervision — not just "context for LLM".

**PR (merged locally):** https://github.com/mohanvenkateshai-blip/VedicAstro/pull/3  
**Branch was:** `feat/ke-full-update-wave-2026-06-30` → fast-forward merged into `main` at `c3dc745`.

| Domain | Status | Evidence (counts) |
|--------|--------|-------------------|
| Supervision | DONE | `scripts/ke_wave_status.py`; auditor **10 probes**; **9 engines**, **0 cracks** |
| Panchanga | DONE | 7 panch/tithi books → 28 tithi_lords + 28 effects + 13 yoga attrs + 2 karana; `source_notes` on result |
| Dasha | DONE | 7 dasha books; 8+ Vimshottari variants; period citations e.g. `BPHS:ch-8` |
| Muhurta | PARTIAL (core) | 283 yoga_nodes (was 128); 150+ hits with book citations; portal `/muhurta` still external iframe |
| Transit/Gochar | DONE | 1021 gochara nodes; 9/9 planets enriched; graph citations in compute + analyzer |
| KP/Prashna/Varsha | DONE | 6/6 Jaimini+Prasna books on revive; `ke_version` on special endpoints + proxy |
| Portal surfaces | DONE | `/api/cvce` enriches `ke_version`; Koota, Varshaphala, admin/knowledge show source notes |

**Master tracker:** `docs/KE_FULL_UPDATE_WAVE_2026-06-30.md`  
**Agent reports:** `docs/agent-reports/KE-wave-*.md` (6 files)

**Official KE access (never bypass):** `cvce/knowledge_engine/integration.py`

### D. Registration Fix
- **Runtime registration:** Fixed runtime registration for all 9 engines. `runtime=9` now reflects accurate engine registration status.
- **Golden versioning:** Implemented golden versioning for tests, ensuring consistency and reliability across different versions of the Knowledge Engine.

**Before/After Orchestrator:**
- **Before:** Orchestrator did not properly handle engine registration, leading to incomplete engine status reporting.
- **After:** Orchestrator now correctly registers all engines, ensuring accurate status reporting and proper supervision of the Knowledge Engine.

---

## 2. Current Repository State

| Item | Value |
|------|-------|
| Branch | `main` (KE wave merged; Learn polish committed in same final commit) |
| Graph version | `newbooks-v1` / file-based locally — **26,722 nodes**, **38,881 links** |
| Structured books | 61 manifest; **60 structured-pass**, 1 zero-chapter edge |
| Registered KE engines | 9: ashtakavarga, dasha, gochar, kp_system, muhurta, panchanga, prashna, report, yoga |
| Embeddings | **COMPLETE 2026-07-03** — 28,495 nodes via local `all-MiniLM-L6-v2` (384-dim). 2 transient errors (dim mismatch + Supabase offline) non-blocking. Gemini blocker removed. |
| Raw markdown | 61 files in `knowledge-graph/raw/` (IP — may not all be in git) |
| Patch backups | `knowledge-graph/patches/*.bak-20260630-*` — session backups of node-chapter-map + 4 patch files |

---

## 3. Key Files by Area

### Learn (portal)
- `portal/src/lib/books.ts` — structured resolution, raw loading, display meta, search data
- `portal/src/app/(main)/learn/page.tsx` — library grid + global search
- `portal/src/app/(main)/learn/[bookId]/page.tsx` — book reader server component
- `portal/src/components/BookReaderClient.tsx` — TOC, content, scroll-spy, FAB
- `portal/src/components/LearnGlobalSearch.tsx` — client search UI
- `portal/src/app/api/learn/search/route.ts` — cross-book search API
- `portal/scripts/sync-structured-data.mjs` — copies structured + patches + raw → `portal/data/`

### Auth (conditional — no MissingSecret)
- `portal/src/lib/auth-config.ts` — `isAuthConfigured()`
- `portal/src/app/api/auth/auth.ts` — no-op stubs when auth disabled
- `portal/src/lib/auth/session.ts`

### Knowledge Engine + engines (cvce)
- `cvce/knowledge_engine/integration.py` — **single gateway** (+ `get_registered_engines_with_status()`)
- `cvce/knowledge_engine/refresh_auditor.py` — 10 probes + `run_all_probes()`
- `cvce/vedic_engine/core/panchanga.py` — enriched attrs from structured books
- `cvce/vedic_engine/prediction/{dasha,gochar,muhurta_yogas,kp_system,prashna}.py`
- `cvce/graph_rag/{rules_provider,muhurta_rules_provider}.py` — graph-derived rules
- `cvce/app/server.py` — `/version`, `ke_version` on predict endpoints
- `portal/src/app/api/cvce/[...path]/route.ts` — proxy enriches `ke_version`

### Scripts & verification
- `scripts/ke_wave_status.py` — KE wave dashboard
- `scripts/smoke-learn-production.sh` — prod Learn gate
- `scripts/verify_structured_books.py`
- `tmp_probe_supabase_patches.py` — ad-hoc Supabase patch probe (needs `.env.local` creds)

---

## 4. Learn Pipeline (unchanged core, plus UI)

1. Resolve book via fuzzy `bookId` / stem / canonical (`books.ts`)
2. TOC from `chaptersFromStructured` (structured JSON)
3. Body from `loadLocalRawMarkdown` → slice via `sectionsFromStructured` line ranges
4. Fallback: `parseMarkdownToSections` (junk filter; page-scan collapse for OCR books)
5. Node provenance from per-book patches + `node-chapter-map.json`
6. **New:** Global search indexes all structured books; deep-link scrolls to chapter/section
7. **New:** Tiles show `displayTitle`, `author`, `year`

**Data sync:**
```bash
cd portal && npm run data:sync   # predev/prebuild also runs this
```

---

## 5. Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| KE wave | `python3 scripts/ke_wave_status.py` | `engines=9 probed=10 cracks=0` |
| Structured library | `node portal/scripts/verify-all-learn-books.mjs` | `structured-pass=60` |
| Portal types | `cd portal && npm run typecheck` | exit 0 |
| Learn prod smoke | `./scripts/smoke-learn-production.sh` | **Last run: 7 pass / 1 fail** (Hora structured signal — deploy may be stale until push + Vercel rebuild) |
| Local spot-check | `/learn`, search "dasha", open hit, use FAB, check tile titles | titles clean, search works, FAB appears on scroll |

---

## 6. Git / Deploy

- **All session work committed to `main`** in final commit (Learn polish + handoff + remaining artifacts + KE wave already merged via fast-forward).
- **Push to origin** may still be pending — run `git push origin main` to trigger Vercel and refresh prod smoke.
- Open PR #3 can be closed/merged on GitHub if branch was only ahead of old main.

---

## 7. Explicit Do-Not-Do

1. **Do not run Gemini embeddings** until user confirms credits restored.
2. **Do not ask user to run commands you can run** (dev server, verify, push).
3. **Do not mark Learn DONE** without prod smoke passing.
4. **Do not paste full graph.json / node-chapter-map / structured corpora** — use scripts, report counts only.
5. **Do not restart from scratch** — keep + harden local Graphify + structured library + KE integration.
6. **Muhūrta standalone is FROZEN** — `/muhurta` is iframe to `muhurtha.uvwx.me`; internal muhurta logic lives in cvce.
7. **Do not bypass `knowledge_engine.integration`** for graph/rules access in new code.

---

## 8. Pending / Next Work

| Priority | Task |
|----------|------|
| P0 | `git push origin main` + wait for Vercel + re-run `./scripts/smoke-learn-production.sh` until green |
| P0 | Close/merge PR #3 on GitHub if redundant after push |
| P1 | Rebuild structured for `Jataka_Tatva_Mahadeva` (0 chapters in JSON) |
| P1 | Fix Hora prod smoke detection (content good; grep pattern may need tweak) |
| P2 | Embeddings when credits return (`scripts/generate-embeddings.py`) |
| P2 | Supabase provenance sync (`apply_node_chapter_patch.py --supabase --write`) |
| P2 | Deeper KE extraction — conditional rules from books already loaded in dasha/kp/prashna |
| P3 | Runtime registration at cvce startup for all 9 engines (status script shows `runtime: 0` until imports side-effect) |
| P3 | Golden tests versioned by `ke_version` |

---

## 9. Agent Protocol (Project Law)

- **Token discipline:** `.cursor/rules/token-discipline.mdc` — script-first, no corpus dumps, push before DONE on Learn.
- **Multi-agent:** `.cursor/rules/multi-agent-mandatory-protocol.mdc` — tiered (0–1 trivial, 3–5 library/KE waves).
- **Handoff maintainer:** `python3 scripts/handoff/maintain_context.py --update-all` after major KG changes.

---

## 10. User Context

- User wants **autonomous execution** — run dev, verify, commit, push; minimal manual steps.
- User burned Gemini API credits earlier — **zero-cost local work preferred** until credits restored.
- User switched AI/Cursor accounts mid-session — unrelated to codebase.
- User requested **full commit of everything** + this handoff file for continuity in another AI tool.

---

## 11. Session Commits Reference

| Commit | Summary |
|--------|---------|
| `c3dc745` | KE Full Update Wave (30 files: engines, graph rules, auditor, tracker, agent reports, ke_wave_status, portal ke_version surfaces) |
| *(final)* | Learn global search, FAB, display metadata, tile fixes, handoff, verification docs, patch `.bak`s, tmp_probe |

---

*Regenerate broader handoff after KG ingest:*
```bash
python3 scripts/handoff/maintain_context.py --update-all
```
