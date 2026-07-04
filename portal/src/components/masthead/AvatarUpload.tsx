"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera, Loader2 } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";

/** Profile-page avatar with an upload control. Posts to /api/prefs/avatar, which
 *  stores the image in Supabase Storage and writes the URL to users.image. */
export function AvatarUpload({
  name,
  email,
  image,
}: {
  name?: string | null;
  email?: string | null;
  image?: string | null;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file) return;

    setErr(null);
    setBusy(true);
    setPreview(URL.createObjectURL(file));

    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("/api/prefs/avatar", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Upload failed");
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Upload failed");
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="relative w-fit">
        <Avatar name={name} email={email} image={preview ?? image} size="lg" />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          aria-label="Change profile photo"
          className="absolute -bottom-1 -right-1 grid h-6 w-6 place-items-center rounded-full bg-primary text-primary-fg ring-2 ring-card transition-colors hover:bg-primary/90 disabled:opacity-60"
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Camera size={12} />}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          hidden
          onChange={onFile}
        />
      </div>
      {err && <p className="mt-1.5 text-xs text-danger">{err}</p>}
    </div>
  );
}
