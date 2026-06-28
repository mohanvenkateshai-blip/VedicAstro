"use client";

import { useState, useEffect, useRef } from "react";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PlaceResult {
  name: string;
  label: string;
  state: string;
  country: string;
  lat: number;
  lon: number;
  tz: number;
}

// ── Form ──────────────────────────────────────────────────────────────────────

export interface Defaults {
  name: string; date: string; time: string;
  place: string; lat: string; lon: string; tz: string;
}

const field = "w-full rounded-lg border border-hairline bg-card px-3 py-2 text-sm outline-none focus:border-accent transition-colors";
const label = "block text-xs font-medium text-text-muted mb-1.5";

export function BirthForm({
  defaults,
  action = "/vedicastro",
  sticky = false,
}: {
  defaults: Defaults;
  action?: string;
  sticky?: boolean;
}) {
  const [place, setPlace]       = useState(defaults.place);
  const [lat, setLat]           = useState(defaults.lat);
  const [lon, setLon]           = useState(defaults.lon);
  const [tz, setTz]             = useState(defaults.tz);
  const [results, setResults]   = useState<PlaceResult[]>([]);
  const [open, setOpen]         = useState(false);
  const [fetching, setFetching] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapRef  = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function onPlaceChange(v: string) {
    setPlace(v);
    if (debounce.current) clearTimeout(debounce.current);
    if (v.length < 2) { setResults([]); setOpen(false); return; }

    debounce.current = setTimeout(async () => {
      setFetching(true);
      try {
        const res = await fetch(`/api/cvce/places?q=${encodeURIComponent(v)}`);
        const data = await res.json();
        const list: PlaceResult[] = data.results ?? [];
        setResults(list);
        setOpen(list.length > 0);
      } catch {
        setResults([]);
      } finally {
        setFetching(false);
      }
    }, 300);
  }

  function pickResult(r: PlaceResult) {
    setPlace(r.label);
    setLat(String(r.lat));
    setLon(String(r.lon));
    // PyJHora GeoNames already has correct UTC offset for each city
    setTz(String(r.tz));
    setResults([]);
    setOpen(false);
  }

  return (
    <Card className={`p-6 h-fit${sticky ? " lg:sticky lg:top-24" : ""}`}>
      <form method="get" action={action} className="flex flex-col gap-4">
        <div>
          <label className={label} htmlFor="name">Name</label>
          <input id="name" name="name" defaultValue={defaults.name} className={field} placeholder="Optional" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={label} htmlFor="date">Birth date</label>
            <input id="date" name="date" type="date" required defaultValue={defaults.date} className={field} />
          </div>
          <div>
            <label className={label} htmlFor="time">Birth time</label>
            <input id="time" name="time" type="time" required defaultValue={defaults.time} className={field} />
          </div>
        </div>

        {/* Place with live geocoding dropdown */}
        <div ref={wrapRef} className="relative">
          <label className={label} htmlFor="place">Place</label>
          <div className="relative">
            <input
              id="place"
              name="place"
              value={place}
              onChange={(e) => onPlaceChange(e.target.value)}
              onFocus={() => results.length > 0 && setOpen(true)}
              onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
              className={field}
              placeholder="Type a city name…"
              autoComplete="off"
            />
            {fetching && (
              <span className="absolute right-3 inset-y-0 flex items-center text-[10px] font-mono text-text-muted pointer-events-none">
                ···
              </span>
            )}
          </div>
          {open && results.length > 0 && (
            <ul
              className="absolute z-50 top-full mt-1 w-full rounded-xl border border-hairline overflow-hidden"
              style={{
                backgroundColor: "var(--color-card, #1a1a2e)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
              }}
            >
              {results.map((r, i) => (
                <li key={i} className="border-b border-hairline last:border-0">
                  <button
                    type="button"
                    onClick={() => pickResult(r)}
                    className="w-full text-left px-4 py-3 hover:bg-white/5 transition-colors"
                  >
                    <span className="block text-sm font-medium text-text-main leading-tight">
                      {r.name}
                    </span>
                    <span className="block text-xs text-text-muted mt-0.5">
                      {[r.state, r.country].filter(Boolean).join(", ")}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Coords — auto-filled by geocoding, editable for power users */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={label} htmlFor="lat">Lat</label>
            <input id="lat" name="lat" required inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} className={field} placeholder="12.30" />
          </div>
          <div>
            <label className={label} htmlFor="lon">Lon</label>
            <input id="lon" name="lon" required inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} className={field} placeholder="76.65" />
          </div>
          <div>
            <label className={label} htmlFor="tz">TZ</label>
            <input id="tz" name="tz" required inputMode="decimal" value={tz} onChange={(e) => setTz(e.target.value)} className={field} placeholder="5.5" />
          </div>
        </div>

        <Button type="submit" variant="accent" className="w-full mt-1">Compute chart</Button>
        <p className="text-[11px] text-text-muted">
          Type any city (or enter coordinates directly). Lat/Lon/TZ auto-fill on city selection.
          TZ is the UTC offset in hours at birth (India = 5.5, Ireland = 0).
        </p>
      </form>
    </Card>
  );
}
