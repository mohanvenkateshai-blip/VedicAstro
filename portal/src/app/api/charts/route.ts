import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import {
  GUEST_COOKIE,
  GUEST_COOKIE_OPTS,
  resolveChartOwner,
  resolveChartOwnerForWrite,
} from "@/lib/chart-owner";

// ── GET /api/charts — list charts for the current owner ──────────────────────
// Authenticated users see ONLY their own charts (keyed by account id); guests
// see only their per-browser cookie's charts. See lib/chart-owner.ts.
export async function GET() {
  const owner = await resolveChartOwner();
  if (!owner) return NextResponse.json([]);

  const { data, error } = await supabase
    .from("guest_charts")
    .select("id, name, birth_date, birth_time, place, lat, lon, tz, sort_order, created_at")
    .eq("guest_id", owner)
    .order("sort_order", { ascending: true })
    .order("created_at", { ascending: true });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data ?? []);
}

// ── POST /api/charts — save a chart for the current owner ────────────────────
export async function POST(req: NextRequest) {
  const { owner, mintedGuestId } = await resolveChartOwnerForWrite();
  const body = await req.json();

  const withCookie = (res: NextResponse) => {
    if (mintedGuestId) res.cookies.set(GUEST_COOKIE, mintedGuestId, GUEST_COOKIE_OPTS);
    return res;
  };

  // Deduplicate: same birth_date + birth_time + lat = same person/moment
  const { data: existing } = await supabase
    .from("guest_charts")
    .select("id")
    .eq("guest_id", owner)
    .eq("birth_date", body.date ?? "")
    .eq("birth_time", body.time ?? "")
    .eq("lat", body.lat ?? "")
    .maybeSingle();

  if (existing) {
    return withCookie(NextResponse.json({ id: existing.id, duplicate: true }));
  }

  // Get max sort_order for this owner
  const { data: maxRow } = await supabase
    .from("guest_charts")
    .select("sort_order")
    .eq("guest_id", owner)
    .order("sort_order", { ascending: false })
    .limit(1)
    .maybeSingle();

  const sortOrder = maxRow ? (maxRow.sort_order as number) + 1 : 0;

  const { data, error } = await supabase
    .from("guest_charts")
    .insert({
      guest_id:   owner,
      name:       body.name ?? "Unnamed chart",
      birth_date: body.date ?? "",
      birth_time: body.time ?? "",
      place:      body.place ?? "",
      lat:        body.lat ?? "",
      lon:        body.lon ?? "",
      tz:         body.tz ?? "5.5",
      sort_order: sortOrder,
    })
    .select("id")
    .single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return withCookie(NextResponse.json({ id: data.id }));
}
