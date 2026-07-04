"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";

/** Inline editor for the user's display name. */
export function ProfileNameForm({ initialName }: { initialName: string }) {
  const router = useRouter();
  const [name, setName] = useState(initialName);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save() {
    const clean = name.trim();
    if (!clean || clean === initialName) return;
    setSaving(true);
    setSaved(false);
    try {
      const res = await fetch("/api/prefs/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: clean }),
      });
      if (res.ok) {
        setSaved(true);
        router.refresh();
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex-1 min-w-[200px]">
        <span className="mb-1.5 block text-xs font-medium text-text-muted">Display name</span>
        <input
          type="text"
          value={name}
          maxLength={80}
          onChange={(e) => {
            setName(e.target.value);
            setSaved(false);
          }}
          className="w-full rounded-lg border border-hairline bg-card px-3 py-2 text-sm focus:outline-none focus:border-accent/60"
        />
      </label>
      <Button
        variant="primary"
        className="!px-5 !py-2 text-sm"
        disabled={saving || !name.trim() || name.trim() === initialName}
        onClick={save}
      >
        {saving ? "Saving…" : saved ? "Saved ✓" : "Save"}
      </Button>
    </div>
  );
}
