"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { BirthForm } from "./BirthForm";
import { DEMO_BIRTH_DEFAULTS, parseBirthDefaults } from "@/lib/birth-params";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";
import { Link, Check, Bookmark, BookmarkCheck } from "lucide-react";

function hasChartParams(sp: URLSearchParams): boolean {
  return Boolean(sp.get("date") && sp.get("time") && sp.get("lat") && sp.get("lon"));
}

function CopyLinkButton() {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <Button type="button" variant="ghost" onClick={copy}
      className="flex items-center gap-1.5 text-text-muted hover:text-text-main text-xs h-8 px-2">
      {copied
        ? <><Check className="w-3.5 h-3.5" /> Copied</>
        : <><Link className="w-3.5 h-3.5" /> Copy link</>}
    </Button>
  );
}

function SaveChartButton({ defaults }: { defaults: ReturnType<typeof parseBirthDefaults> }) {
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  // Check if this chart is already saved (GET returns it)
  useEffect(() => {
    if (!defaults.date || !defaults.lat) return;
    fetch("/api/charts")
      .then((r) => r.json())
      .then((rows: { birth_date: string; birth_time: string; lat: string }[]) => {
        if (!Array.isArray(rows)) return;
        const exists = rows.some(
          (c) => c.birth_date === defaults.date && c.birth_time === defaults.time && c.lat === defaults.lat,
        );
        setSaved(exists);
      })
      .catch(() => {/* db not connected yet — silent */});
  }, [defaults.date, defaults.time, defaults.lat]);

  async function save() {
    if (saved || saving) return;
    setSaving(true);
    try {
      const res = await fetch("/api/charts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: defaults.name || "Unnamed chart",
          date: defaults.date,
          time: defaults.time,
          place: defaults.place || "",
          lat: defaults.lat,
          lon: defaults.lon,
          tz: defaults.tz,
        }),
      });
      if (res.ok) {
        setSaved(true);
        setJustSaved(true);
        setTimeout(() => setJustSaved(false), 2000);
      }
    } catch {
      /* silent — db may not be connected */
    } finally {
      setSaving(false);
    }
  }

  return (
    <Button type="button" variant="ghost" onClick={save} disabled={saved || saving}
      className="flex items-center gap-1.5 text-xs h-8 px-2"
      style={{ color: saved ? "var(--color-accent)" : "var(--color-text-muted)" }}>
      {justSaved
        ? <><Check className="w-3.5 h-3.5" /> Saved!</>
        : saved
          ? <><BookmarkCheck className="w-3.5 h-3.5" /> Saved</>
          : saving
            ? <><Bookmark className="w-3.5 h-3.5" /> Saving…</>
            : <><Bookmark className="w-3.5 h-3.5" /> Save chart</>}
    </Button>
  );
}

export function ChartBirthForm() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const chartLoaded = hasChartParams(searchParams);
  const [expanded, setExpanded] = useState(!chartLoaded);

  useEffect(() => { setExpanded(!chartLoaded); }, [chartLoaded]);

  const defaults = useMemo(() => {
    const sp: Record<string, string> = {};
    searchParams.forEach((v, k) => { sp[k] = v; });
    return Object.keys(sp).length ? parseBirthDefaults(sp) : { ...DEMO_BIRTH_DEFAULTS };
  }, [searchParams]);

  if (chartLoaded && !expanded) {
    const parts = [
      defaults.date,
      defaults.time,
      defaults.place || `${defaults.lat}, ${defaults.lon}`,
    ].filter(Boolean);

    return (
      <Card className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <p className="text-sm min-w-0">
          <span className="font-medium">{defaults.name || "Birth chart"}</span>
          <span className="text-text-muted"> · {parts.join(" · ")}</span>
        </p>
        <div className="flex items-center gap-1 shrink-0 self-start sm:self-center">
          <SaveChartButton defaults={defaults} />
          <CopyLinkButton />
          <Button type="button" variant="ghost" onClick={() => setExpanded(true)}
            className="text-sm h-8 px-3">
            Edit birth details
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {chartLoaded && (
        <div className="flex justify-end">
          <Button type="button" variant="ghost"
            className="text-xs text-text-muted h-8 px-2"
            onClick={() => setExpanded(false)}>
            Collapse form
          </Button>
        </div>
      )}
      <BirthForm defaults={defaults} action={pathname} sticky={false} />
    </div>
  );
}
