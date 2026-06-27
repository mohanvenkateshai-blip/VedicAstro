"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function PrashnaCaster({
  lat,
  lon,
  tz,
}: {
  lat: number;
  lon: number;
  tz: number;
}) {
  const router = useRouter();
  const [coords, setCoords] = useState({ lat, lon, tz });
  const [locating, setLocating] = useState(false);

  function castNow() {
    const qs = new URLSearchParams({
      cast: "1",
      lat: String(coords.lat),
      lon: String(coords.lon),
      tz: String(coords.tz),
    });
    router.push(`/prashna?${qs.toString()}`);
  }

  function useGeolocation() {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          tz: -pos.coords.longitude / 15,
        });
        setLocating(false);
      },
      () => setLocating(false),
    );
  }

  return (
    <Card className="p-5 space-y-4">
      <div className="grid grid-cols-3 gap-3 text-sm">
        <label className="space-y-1">
          <span className="text-text-muted">Latitude</span>
          <input
            type="number"
            step="0.0001"
            value={coords.lat}
            onChange={(e) =>
              setCoords((c) => ({ ...c, lat: parseFloat(e.target.value) || 0 }))
            }
            className="w-full rounded-lg border border-hairline bg-transparent px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-text-muted">Longitude</span>
          <input
            type="number"
            step="0.0001"
            value={coords.lon}
            onChange={(e) =>
              setCoords((c) => ({ ...c, lon: parseFloat(e.target.value) || 0 }))
            }
            className="w-full rounded-lg border border-hairline bg-transparent px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-text-muted">TZ offset</span>
          <input
            type="number"
            step="0.5"
            value={coords.tz}
            onChange={(e) =>
              setCoords((c) => ({ ...c, tz: parseFloat(e.target.value) || 0 }))
            }
            className="w-full rounded-lg border border-hairline bg-transparent px-3 py-2"
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button type="button" onClick={castNow}>
          Cast Prashna now
        </Button>
        <Button type="button" variant="ghost" onClick={useGeolocation} disabled={locating}>
          {locating ? "Locating…" : "Use my location"}
        </Button>
      </div>
    </Card>
  );
}
