#!/usr/bin/env node
/**
 * Apply schema on the Vercel server (uses production DATABASE_URL — no local secret needed).
 *
 *   npm run db:schema:remote
 *
 * Requires AUTH_SECRET in the shell (from Vercel → Environment Variables → Reveal).
 * Optional: PORTAL_URL=https://portal-omega-two-10.vercel.app
 */
const portal =
  process.env.PORTAL_URL?.trim() || "https://portal-omega-two-10.vercel.app";
const secret = process.env.AUTH_SECRET?.trim();

if (!secret) {
  console.error(`
AUTH_SECRET is required to authorize the remote migration.

  AUTH_SECRET='your-auth-secret' npm run db:schema:remote

Get AUTH_SECRET from: Vercel → vedicastro → Settings → Environment Variables → AUTH_SECRET → Reveal

Schema also auto-applies on first DB use after deploy (no action needed if /status shows Neon connected).
`);
  process.exit(1);
}

const url = `${portal.replace(/\/$/, "")}/api/db/migrate?force=1`;

console.log("→ POST", url.replace(secret, "***"));

const res = await fetch(url, {
  method: "POST",
  headers: { Authorization: `Bearer ${secret}` },
});

const body = await res.json().catch(() => ({}));

if (!res.ok) {
  console.error("Migration failed:", res.status, body);
  process.exit(1);
}

console.log("✓", JSON.stringify(body, null, 2));
