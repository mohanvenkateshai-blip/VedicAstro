import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import {
  GUEST_COOKIE,
  GUEST_COOKIE_OPTS,
  resolveChartOwner,
  resolveChartOwnerForWrite,
} from "@/lib/chart-owner";
import {
  decryptSavedChartData,
  encryptSavedChartData,
} from "@/lib/auth/encrypt";
import {
  decodeSavedChartRows,
  findDuplicateChart,
  parseSavedChartInput,
  prepareSavedChartInsert,
  SAVED_CHART_CACHE_CONTROL,
  savedChartPrivacyFailure,
  scopeSavedChartsToOwner,
  type SavedChartSensitiveData,
} from "./boundary";

type ChartRow = SavedChartSensitiveData & {
  id: string;
  sort_order: number;
  created_at: string;
};

function privacyError(error: unknown): NextResponse {
  const failure = savedChartPrivacyFailure(error);
  return NextResponse.json({ error: failure.message }, { status: failure.status });
}

// ── GET /api/charts — list charts for the current owner ──────────────────────
// Authenticated users see ONLY their own charts (keyed by account id); guests
// see only their per-browser cookie's charts. See lib/chart-owner.ts.
export async function GET() {
  const owner = await resolveChartOwner();
  if (!owner) {
    return NextResponse.json([], { headers: { "Cache-Control": SAVED_CHART_CACHE_CONTROL } });
  }

  const listQuery = supabase
    .from("guest_charts")
    .select("id, name, birth_date, birth_time, place, lat, lon, tz, sort_order, created_at");
  const { data, error } = await scopeSavedChartsToOwner(listQuery, owner)
    .order("sort_order", { ascending: true })
    .order("created_at", { ascending: true });

  if (error) return NextResponse.json({ error: "Saved charts could not be loaded." }, { status: 500 });

  try {
    const rows = await decodeSavedChartRows((data ?? []) as ChartRow[], owner, decryptSavedChartData);
    return NextResponse.json(rows, { headers: { "Cache-Control": SAVED_CHART_CACHE_CONTROL } });
  } catch (error) {
    console.error("Saved-chart decryption failed", error instanceof Error ? error.name : "UnknownError");
    return privacyError(error);
  }
}

// ── POST /api/charts — save a chart for the current owner ────────────────────
export async function POST(req: NextRequest) {
  const { owner, mintedGuestId } = await resolveChartOwnerForWrite();
  const parsed = parseSavedChartInput(await req.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid saved-chart data." }, { status: 400 });
  }
  const body = parsed.data;

  const withCookie = (res: NextResponse) => {
    if (mintedGuestId) res.cookies.set(GUEST_COOKIE, mintedGuestId, GUEST_COOKIE_OPTS);
    return res;
  };

  // Mixed-read deduplication supports legacy plaintext rows and encrypted rows.
  const candidateQuery = supabase
    .from("guest_charts")
    .select("id, name, birth_date, birth_time, place, lat, lon, tz");
  const { data: candidates, error: candidateError } = await scopeSavedChartsToOwner(
    candidateQuery,
    owner,
  );
  if (candidateError) {
    return NextResponse.json({ error: "Saved charts could not be checked." }, { status: 500 });
  }

  try {
    const decoded = await decodeSavedChartRows(
      (candidates ?? []) as Array<SavedChartSensitiveData & { id: string }>,
      owner,
      decryptSavedChartData,
    );
    const duplicate = findDuplicateChart(decoded, body);
    if (duplicate) {
      return withCookie(NextResponse.json({ id: duplicate.id, duplicate: true }));
    }
  } catch (error) {
    console.error("Saved-chart deduplication failed", error instanceof Error ? error.name : "UnknownError");
    return privacyError(error);
  }

  // Get max sort_order for this owner
  const maxQuery = supabase
    .from("guest_charts")
    .select("sort_order");
  const { data: maxRow } = await scopeSavedChartsToOwner(maxQuery, owner)
    .order("sort_order", { ascending: false })
    .limit(1)
    .maybeSingle();

  const sortOrder = maxRow ? (maxRow.sort_order as number) + 1 : 0;

  let insertRow: SavedChartSensitiveData & { guest_id: string; sort_order: number };
  try {
    insertRow = await prepareSavedChartInsert(body, owner, sortOrder, encryptSavedChartData);
  } catch (error) {
    console.error("Saved-chart encryption failed", error instanceof Error ? error.name : "UnknownError");
    return privacyError(error);
  }

  const { data, error } = await supabase
    .from("guest_charts")
    .insert(insertRow)
    .select("id")
    .single();

  if (error) return NextResponse.json({ error: "Saved chart could not be stored." }, { status: 500 });
  return withCookie(NextResponse.json({ id: data.id }));
}
