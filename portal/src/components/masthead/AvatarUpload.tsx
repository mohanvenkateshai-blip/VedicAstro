"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera, Loader2, Check } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";

/** Profile-page avatar with upload. The photo SAVES AUTOMATICALLY when a file is
 *  chosen — it posts to /api/prefs/avatar (Supabase Storage → users.image); there
 *  is no separate Save button for it (the "Save" under Display name is only for
 *  the name). */
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
  const [shown, setShown] = useState<string | null>(null); // stored URL after success
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file) return;

    setErr(null);
    setSaved(false);
    setBusy(true);

    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("/api/prefs/avatar", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.url) throw new Error(data.error || "Upload failed");
      // Show the ACTUAL stored URL — confirms Supabase served it (not a local blob),
      // so a broken storage config shows as a broken image rather than a false success.
      setShown(data.url);
      setSaved(true);
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="relative w-fit">
        <Avatar name={name} email={email} image={shown ?? image} size="lg" />
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

      {err ? (
        <p className="mt-1.5 max-w-[180px] text-xs text-danger">{err}</p>
      ) : saved ? (
        <p className="mt-1.5 flex items-center gap-1 text-xs text-success">
          <Check size={12} /> Photo saved
        </p>
      ) : busy ? (
        <p className="mt-1.5 text-xs text-text-muted">Uploading…</p>
      ) : (
        <p className="mt-1.5 max-w-[180px] text-[11px] text-text-muted">
          Tap the camera — your photo saves automatically.
        </p>
      )}
    </div>
  );
}
