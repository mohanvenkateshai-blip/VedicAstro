import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { supabase } from "@/lib/supabase";

const COOKIE = "vedicastro_guest_id";

type Params = { params: Promise<{ id: string }> };

// ── DELETE /api/charts/[id] ───────────────────────────────────────────────────
export async function DELETE(_req: NextRequest, { params }: Params) {
  const { id } = await params;
  const cookieStore = await cookies();
  const guestId = cookieStore.get(COOKIE)?.value;
  if (!guestId) return NextResponse.json({ error: "No session" }, { status: 401 });

  const { error } = await supabase
    .from("guest_charts")
    .delete()
    .eq("id", id)
    .eq("guest_id", guestId); // ensures you can only delete your own charts

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}

// ── PATCH /api/charts/[id] — update sort_order ────────────────────────────────
export async function PATCH(req: NextRequest, { params }: Params) {
  const { id } = await params;
  const cookieStore = await cookies();
  const guestId = cookieStore.get(COOKIE)?.value;
  if (!guestId) return NextResponse.json({ error: "No session" }, { status: 401 });

  const body = await req.json();

  if (typeof body.sort_order !== "number") {
    // Handle move up/down: swap with neighbour
    const direction = body.direction as "up" | "down";
    if (!direction) return NextResponse.json({ error: "Missing sort_order or direction" }, { status: 400 });

    // Fetch all charts sorted
    const { data: all } = await supabase
      .from("guest_charts")
      .select("id, sort_order")
      .eq("guest_id", guestId)
      .order("sort_order", { ascending: true });

    if (!all) return NextResponse.json({ ok: true });

    const idx = all.findIndex((c) => c.id === id);
    if (idx === -1) return NextResponse.json({ error: "Not found" }, { status: 404 });

    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= all.length) return NextResponse.json({ ok: true });

    const a = all[idx], b = all[swapIdx];
    await Promise.all([
      supabase.from("guest_charts").update({ sort_order: b.sort_order }).eq("id", a.id).eq("guest_id", guestId),
      supabase.from("guest_charts").update({ sort_order: a.sort_order }).eq("id", b.id).eq("guest_id", guestId),
    ]);

    return NextResponse.json({ ok: true });
  }

  const { error } = await supabase
    .from("guest_charts")
    .update({ sort_order: body.sort_order })
    .eq("id", id)
    .eq("guest_id", guestId);

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
