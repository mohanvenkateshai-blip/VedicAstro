import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const runtime = "nodejs";

// Minimal public asset proxy for corpus-vault images / media.
// Supports ?path=relative/path/in/bucket
// Returns a short-lived signed URL redirect so the bucket can stay private.
// Falls back to 404 JSON if not found.

const DEFAULT_TTL = 60 * 15; // 15 minutes

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const rawPath = searchParams.get("path") || searchParams.get("p") || "";
  const path = rawPath.replace(/^\/+/, "").trim();

  if (!path) {
    return NextResponse.json({ error: "Missing path" }, { status: 400 });
  }

  try {
    // Try a signed URL first (works for private buckets)
    const { data, error } = await supabase.storage
      .from("corpus-vault")
      .createSignedUrl(path, DEFAULT_TTL);

    if (!error && data?.signedUrl) {
      // 302 to the signed URL so <img> can fetch it directly
      return NextResponse.redirect(data.signedUrl, 302);
    }

    // If signed URL fails (e.g. object truly missing), try a direct public URL as last resort
    // (if the bucket/object is configured public, this will work; otherwise it will 404 naturally)
    const publicBase = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
    if (publicBase) {
      const pub = `${publicBase.replace(/\/$/, "")}/storage/v1/object/public/corpus-vault/${encodeURIComponent(path)}`;
      // We can't easily HEAD from here without extra roundtrips; just redirect and let the browser handle 404.
      return NextResponse.redirect(pub, 302);
    }

    return NextResponse.json({ error: "Asset not found", path }, { status: 404 });
  } catch (e: any) {
    return NextResponse.json({ error: "Asset error", detail: String(e?.message || e) }, { status: 500 });
  }
}
