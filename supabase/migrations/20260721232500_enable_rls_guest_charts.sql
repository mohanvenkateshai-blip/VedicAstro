-- Fix: guest_charts had RLS disabled, making it publicly readable/writable/
-- deletable via the anon key (flagged by Supabase's security advisor as
-- rls_disabled_in_public, 2026-07-21). All legitimate access already goes
-- through portal/src/lib/chart-owner.ts using the service-role key, which
-- bypasses RLS regardless of policies present — see that file's own
-- "SECURITY" comment. So enabling RLS with no permissive policies is safe:
-- it does not change how the app behaves, it only removes the public
-- anon-key access path that should never have existed.
alter table public.guest_charts enable row level security;
