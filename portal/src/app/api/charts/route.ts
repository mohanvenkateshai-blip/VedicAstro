import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { supabase } from "@/lib/supabase";

const COOKIE = "vedicastro_guest_id";
const COOKIE_OPTS = {
  httpOnly: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 365, // 1 year
};

function getOrCreateGuestId(cookieStore: Awaited<ReturnType<typeof cookies>>): string {
  const existing = cookieStore.get(COOKIE)?.value;
  if (existing) return existing;
  return crypto.randomUUID();
}

// ── GET /api/charts — list all charts for this guest ─────────────────────────
export async function GET() {
  const cookieStore = await cookies();
  const guestId = cookieStore.get(COOKIE)?.value;
  if (!guestId) return NextResponse.json([]);

  const { data, error } = await supabase
    .from("guest_charts")
    .select("id, name, birth_date, birth_time, place, lat, lon, tz, sort_order, created_at")
    .eq("guest_id", guestId)
    .order("sort_order", { ascending: true })
    .order("created_at", { ascending: true });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data ?? []);
}

// ── POST /api/charts — save a chart ──────────────────────────────────────────
export async function POST(req: NextRequest) {
  const cookieStore = await cookies();
  const guestId = getOrCreateGuestId(cookieStore);
  const body = await req.json();

  // Deduplicate: same birth_date + birth_time + lat = same person/moment
  const { data: existing } = await supabase
    .from("guest_charts")
    .select("id")
    .eq("guest_id", guestId)
    .eq("birth_date", body.date ?? "")
    .eq("birth_time", body.time ?? "")
    .eq("lat", body.lat ?? "")
    .maybeSingle();

  if (existing) {
    const res = NextResponse.json({ id: existing.id, duplicate: true });
    res.cookies.set(COOKIE, guestId, COOKIE_OPTS);
    return res;
  }

  // Get max sort_order for this guest
  const { data: maxRow } = await supabase
    .from("guest_charts")
    .select("sort_order")
    .eq("guest_id", guestId)
    .order("sort_order", { ascending: false })
    .limit(1)
    .maybeSingle();

  const sortOrder = maxRow ? (maxRow.sort_order as number) + 1 : 0;

  const { data, error } = await supabase
    .from("guest_charts")
    .insert({
      guest_id:   guestId,
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

  const res = NextResponse.json({ id: data.id });
  res.cookies.set(COOKIE, guestId, COOKIE_OPTS);
  return res;
}
