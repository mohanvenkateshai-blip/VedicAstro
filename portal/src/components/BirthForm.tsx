"use client";

import { useState } from "react";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";

// name -> [lat, lon, tz]. Suggestions only — the field stays directly typeable.
const PRESETS: Record<string, [string, string, string]> = {
  "Mysore, IN": ["12.2958", "76.6394", "5.5"],
  "Bengaluru, IN": ["12.9716", "77.5946", "5.5"],
  "New Delhi, IN": ["28.6139", "77.2090", "5.5"],
  "Mumbai, IN": ["19.0760", "72.8777", "5.5"],
  "Chennai, IN": ["13.0827", "80.2707", "5.5"],
  "Kolkata, IN": ["22.5726", "88.3639", "5.5"],
  "Hyderabad, IN": ["17.3850", "78.4867", "5.5"],
  "Athlone, IE": ["53.4239", "-7.9407", "0"],
  "London, UK": ["51.5074", "-0.1278", "0"],
  "New York, US": ["40.7128", "-74.0060", "-5"],
};

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
  /** Pin form while scrolling — only on wide sidebar layouts (e.g. /vedicastro). */
  sticky?: boolean;
}) {
  const [place, setPlace] = useState(defaults.place);
  const [lat, setLat] = useState(defaults.lat);
  const [lon, setLon] = useState(defaults.lon);
  const [tz, setTz] = useState(defaults.tz);

  // Typing or picking a place: if it matches a known preset, auto-fill coords.
  function onPlace(v: string) {
    setPlace(v);
    const p = PRESETS[v];
    if (p) { setLat(p[0]); setLon(p[1]); setTz(p[2]); }
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
        <div>
          <label className={label} htmlFor="place">Place</label>
          <input
            id="place"
            name="place"
            list="place-presets"
            value={place}
            onChange={(e) => onPlace(e.target.value)}
            className={field}
            placeholder="Type a city — e.g. Mysuru, London…"
            autoComplete="off"
          />
          <datalist id="place-presets">
            {Object.keys(PRESETS).map((k) => <option key={k} value={k} />)}
          </datalist>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div><label className={label} htmlFor="lat">Lat</label><input id="lat" name="lat" required inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} className={field} placeholder="12.30" /></div>
          <div><label className={label} htmlFor="lon">Lon</label><input id="lon" name="lon" required inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} className={field} placeholder="76.65" /></div>
          <div><label className={label} htmlFor="tz">TZ</label><input id="tz" name="tz" required inputMode="decimal" value={tz} onChange={(e) => setTz(e.target.value)} className={field} placeholder="5.5" /></div>
        </div>
        <Button type="submit" variant="accent" className="w-full mt-1">Compute chart</Button>
        <p className="text-[11px] text-text-muted">
          Type any city (or enter coordinates directly). Presets auto-fill lat/lon/TZ.
          TZ is the UTC offset in hours at birth (India = 5.5, Ireland = 0).
        </p>
      </form>
    </Card>
  );
}
