import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { updateUserImage } from "@/lib/auth/index";
import { supabase } from "@/lib/supabase";

export const runtime = "nodejs";

const BUCKET = "avatars";
const MAX_BYTES = 2 * 1024 * 1024; // 2MB
const EXT_BY_TYPE: Record<string, string> = {
  "image/png": "png",
  "image/jpeg": "jpg",
  "image/webp": "webp",
  "image/gif": "gif",
};

/** Create the public avatars bucket on first use (service-role can manage storage). */
async function ensureBucket() {
  const { data } = await supabase.storage.getBucket(BUCKET);
  if (!data) {
    await supabase.storage.createBucket(BUCKET, {
      public: true,
      fileSizeLimit: MAX_BYTES,
    });
  }
}

// POST /api/prefs/avatar — multipart form with a `file` image field.
export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const form = await req.formData().catch(() => null);
  const file = form?.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "no file" }, { status: 400 });
  }
  const ext = EXT_BY_TYPE[file.type];
  if (!ext) {
    return NextResponse.json({ error: "Unsupported image type (png, jpg, webp, gif)" }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json({ error: "Image too large (max 2MB)" }, { status: 400 });
  }

  const buffer = Buffer.from(await file.arrayBuffer());
  const path = `${session.userId}/avatar.${ext}`;

  try {
    await ensureBucket();
    const { error } = await supabase.storage
      .from(BUCKET)
      .upload(path, buffer, { contentType: file.type, upsert: true });
    if (error) throw error;
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Upload failed" },
      { status: 500 },
    );
  }

  const { data } = supabase.storage.from(BUCKET).getPublicUrl(path);
  // Cache-bust so the new image shows immediately (public URL/path is stable).
  const url = `${data.publicUrl}?v=${Date.now()}`;
  await updateUserImage(session.userId, url);

  return NextResponse.json({ ok: true, url });
}
