"use client";

import { useEffect, useRef, useState } from "react";
import { Crosshair, MapPin, RotateCw } from "lucide-react";
import type { ChartData } from "@/lib/types";
import {
  buildTransitObservationRequest,
  localDateTimeAt,
  parseCoordinate,
  resolveZonedLocalInstants,
  type TransitDisambiguation,
  type TransitObservationRequest,
} from "@/lib/transit-context";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { GocharPanel } from "@/components/explorers/GocharPanel";
import { GraphicalEphemeris } from "@/components/explorers/GraphicalEphemeris";

interface PlaceResult {
  name: string;
  label: string;
  state: string;
  country: string;
  lat: number;
  lon: number;
  timezone: string;
}

const field =
  "w-full rounded-lg border border-hairline bg-card px-3 py-2 text-sm outline-none focus:border-accent transition-colors";
const label = "block text-xs font-medium text-text-muted mb-1.5";

export function TransitWorkspace({
  chart,
  natalPlace,
}: {
  chart: ChartData;
  natalPlace: string;
}) {
  const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [place, setPlace] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [timezone, setTimezone] = useState(browserTimezone);
  const [disambiguation, setDisambiguation] = useState<"" | Exclude<TransitDisambiguation, "exact">>("");
  const [results, setResults] = useState<PlaceResult[]>([]);
  const [open, setOpen] = useState(false);
  const [activePlaceIndex, setActivePlaceIndex] = useState(-1);
  const [fetching, setFetching] = useState(false);
  const [locating, setLocating] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transit, setTransit] = useState<TransitObservationRequest | null>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const placeRequest = useRef<AbortController | null>(null);
  const placeWrap = useRef<HTMLDivElement>(null);
  const mounted = useRef(true);

  useEffect(() => {
    // Resolve after hydration so server UTC cannot overwrite the browser's
    // actual named-zone clock or create a hydration mismatch near midnight.
    const timer = window.setTimeout(() => {
      const now = localDateTimeAt(new Date(), browserTimezone);
      setDate(now.date);
      setTime(now.time);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [browserTimezone]);

  useEffect(() => {
    function close(event: MouseEvent) {
      if (placeWrap.current && !placeWrap.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", close);
    return () => {
      mounted.current = false;
      document.removeEventListener("mousedown", close);
      if (debounce.current) clearTimeout(debounce.current);
      placeRequest.current?.abort();
    };
  }, []);

  function useCurrentDateTime() {
    // `timezone` is free text the user may have typed manually (e.g. after a
    // failed place search); an invalid IANA zone must surface as the same
    // inline error affordance the rest of the form uses, not an uncaught
    // exception — this route has no error boundary to catch a raw throw.
    try {
      const now = localDateTimeAt(new Date(), timezone || browserTimezone);
      setDate(now.date);
      setTime(now.time);
      setDisambiguation("");
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Invalid timezone.");
    }
  }

  function onPlaceChange(value: string) {
    setPlace(value);
    setLat("");
    setLon("");
    setResults([]);
    setOpen(false);
    setActivePlaceIndex(-1);
    if (debounce.current) clearTimeout(debounce.current);
    placeRequest.current?.abort();
    if (value.trim().length < 2) return;
    debounce.current = setTimeout(async () => {
      const controller = new AbortController();
      placeRequest.current = controller;
      setFetching(true);
      try {
        const response = await fetch(`/api/cvce/places?q=${encodeURIComponent(value)}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("place search failed");
        const payload = await response.json();
        if (!mounted.current || placeRequest.current !== controller) return;
        const list = (payload.results ?? []) as PlaceResult[];
        setResults(list);
        setOpen(list.length > 0);
        setActivePlaceIndex(list.length > 0 ? 0 : -1);
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        if (!mounted.current) return;
        setError("Place search is unavailable. Enter coordinates and an IANA timezone manually.");
      } finally {
        if (mounted.current && placeRequest.current === controller) setFetching(false);
      }
    }, 300);
  }

  function selectPlace(result: PlaceResult) {
    setPlace(result.label);
    setLat(String(result.lat));
    setLon(String(result.lon));
    setTimezone(result.timezone);
    setDisambiguation("");
    setResults([]);
    setOpen(false);
    setActivePlaceIndex(-1);
    setError(null);
  }

  function onPlaceKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      setActivePlaceIndex(-1);
      return;
    }
    if (!results.length || !open) {
      if (event.key === "ArrowDown" && results.length) {
        event.preventDefault();
        setOpen(true);
        setActivePlaceIndex(0);
      }
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActivePlaceIndex((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActivePlaceIndex((index) => (index <= 0 ? results.length - 1 : index - 1));
    } else if (event.key === "Enter" && activePlaceIndex >= 0) {
      event.preventDefault();
      selectPlace(results[activePlaceIndex]);
    }
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setError("This browser does not provide location access. Select a city or enter coordinates.");
      return;
    }
    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const nextLat = position.coords.latitude;
        const nextLon = position.coords.longitude;
        try {
          const response = await fetch(
            `/api/cvce/timezone?lat=${encodeURIComponent(nextLat)}&lon=${encodeURIComponent(nextLon)}`,
          );
          if (!response.ok) throw new Error("timezone lookup failed");
          const payload = (await response.json()) as { timezone: string };
          setPlace("Current location (browser permission)");
          setLat(nextLat.toFixed(6));
          setLon(nextLon.toFixed(6));
          setTimezone(payload.timezone);
          setDisambiguation("");
          const now = localDateTimeAt(new Date(), payload.timezone);
          setDate(now.date);
          setTime(now.time);
        } catch {
          setError("Location was received, but its timezone could not be resolved. Select a city or enter an IANA timezone.");
        } finally {
          setLocating(false);
        }
      },
      (reason) => {
        setLocating(false);
        setError(
          reason.code === reason.PERMISSION_DENIED
            ? "Location permission was not granted. Select a city or enter the observation context manually."
            : reason.code === reason.TIMEOUT
              ? "Location request timed out. Select a city or enter coordinates manually."
              : "Current location could not be read. Select a city or enter coordinates manually.",
        );
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setVerifying(true);
    try {
      const request = buildTransitObservationRequest({
        date,
        time,
        place,
        latitude: parseCoordinate(lat),
        longitude: parseCoordinate(lon),
        timezone,
        disambiguation: disambiguation || undefined,
      });
      const response = await fetch(
        `/api/cvce/timezone?lat=${encodeURIComponent(request.transit_lat)}&lon=${encodeURIComponent(request.transit_lon)}`,
      );
      if (!response.ok) throw new Error("The observation timezone could not be verified for those coordinates.");
      const verified = (await response.json()) as { timezone?: string };
      if (verified.timezone !== request.transit_timezone) {
        throw new Error(
          `The supplied coordinates resolve to ${verified.timezone ?? "an unknown timezone"}, not ${request.transit_timezone}.`,
        );
      }
      setTransit(request);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Invalid transit observation context.");
    } finally {
      setVerifying(false);
    }
  }

  let overlapCandidates: ReturnType<typeof resolveZonedLocalInstants> = [];
  if (date && time && timezone.trim()) {
    try {
      const candidates = resolveZonedLocalInstants(date, time, timezone.trim());
      if (candidates.length === 2) overlapCandidates = candidates;
    } catch {
      // Submission reports invalid named zones and DST gaps in the shared validator.
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <p className="text-[10px] font-mono uppercase tracking-widest text-accent">Natal context</p>
          <h3 className="mt-1 text-sm font-semibold">Birth chart reference — unchanged</h3>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
            <dt className="text-text-muted">Birth date and time</dt>
            <dd className="text-right font-mono">{chart.meta?.birth_datetime ?? "—"}</dd>
            <dt className="text-text-muted">Birth place</dt>
            <dd className="text-right">{natalPlace || "Not recorded"}</dd>
            <dt className="text-text-muted">Birth coordinates</dt>
            <dd className="text-right font-mono">{chart.meta?.birth_lat}, {chart.meta?.birth_lon}</dd>
            <dt className="text-text-muted">Birth UTC offset</dt>
            <dd className="text-right font-mono">UTC{Number(chart.meta?.birth_tz) >= 0 ? "+" : ""}{chart.meta?.birth_tz}</dd>
            <dt className="text-text-muted">Ayanamsa</dt>
            <dd className="text-right font-mono">{chart.ayanamsa}</dd>
          </dl>
        </Card>

        <Card className="p-5">
          <p className="text-[10px] font-mono uppercase tracking-widest text-accent">Transit observation context</p>
          <h3 className="mt-1 text-sm font-semibold">Where and when should transits be observed?</h3>
          <p className="mt-1 text-xs text-text-muted">
            This is separate from the birthplace. No transit is calculated until you confirm it.
          </p>
          <form className="mt-4 space-y-3" onSubmit={submit}>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={label} htmlFor="transit-date">As-of date</label>
                <input id="transit-date" type="date" required value={date} onChange={(event) => { setDate(event.target.value); setDisambiguation(""); }} className={field} />
              </div>
              <div>
                <label className={label} htmlFor="transit-time">Local time</label>
                <input id="transit-time" type="time" required value={time} onChange={(event) => { setTime(event.target.value); setDisambiguation(""); }} className={field} />
              </div>
            </div>

            {overlapCandidates.length === 2 && (
              <fieldset className="rounded-lg border border-accent/30 bg-accent/5 p-3">
                <legend className="px-1 text-xs font-medium">This local time occurs twice</legend>
                <p className="mb-2 text-[11px] text-text-muted">Choose the intended instant. The UTC offset and UTC time make the choice replayable.</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {overlapCandidates.map((candidate) => (
                    <label key={candidate.disambiguation} className="flex cursor-pointer gap-2 rounded-md border border-hairline p-2 text-xs">
                      <input
                        type="radio"
                        name="transit-overlap"
                        required
                        value={candidate.disambiguation}
                        checked={disambiguation === candidate.disambiguation}
                        onChange={() => setDisambiguation(candidate.disambiguation as "earlier" | "later")}
                      />
                      <span>
                        <span className="block font-medium capitalize">{candidate.disambiguation} occurrence · UTC{candidate.offset}</span>
                        <span className="block font-mono text-[10px] text-text-muted">{candidate.utcInstant}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            <div ref={placeWrap} className="relative">
              <label className={label} htmlFor="transit-place">Observation place</label>
              <input
                id="transit-place"
                required
                value={place}
                onChange={(event) => onPlaceChange(event.target.value)}
                onFocus={() => {
                  if (results.length > 0) {
                    setOpen(true);
                    setActivePlaceIndex((index) => (index >= 0 ? index : 0));
                  }
                }}
                onKeyDown={onPlaceKeyDown}
                autoComplete="off"
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={open && results.length > 0}
                aria-controls="transit-place-options"
                aria-activedescendant={
                  open && activePlaceIndex >= 0
                    ? `transit-place-option-${activePlaceIndex}`
                    : undefined
                }
                placeholder="Type and select a city…"
                className={field}
              />
              {fetching && <span className="absolute right-3 bottom-2.5 text-[10px] text-text-muted">···</span>}
              {open && results.length > 0 && (
                <ul id="transit-place-options" role="listbox" className="absolute z-50 top-full mt-1 w-full rounded-xl border border-hairline bg-card overflow-hidden shadow-lg">
                  {results.map((result, index) => (
                    <li
                      id={`transit-place-option-${index}`}
                      role="option"
                      aria-selected={activePlaceIndex === index}
                      key={`${result.label}-${result.lat}-${result.lon}`}
                      className="border-b border-hairline last:border-0"
                    >
                      <button
                        type="button"
                        tabIndex={-1}
                        onMouseEnter={() => setActivePlaceIndex(index)}
                        onClick={() => selectPlace(result)}
                        className={`w-full px-4 py-2.5 text-left hover:bg-accent/5 ${activePlaceIndex === index ? "bg-accent/10" : ""}`}
                      >
                        <span className="block text-sm font-medium">{result.name}</span>
                        <span className="block text-xs text-text-muted">{[result.state, result.country, result.timezone].filter(Boolean).join(" · ")}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div><label className={label} htmlFor="transit-lat">Latitude</label><input id="transit-lat" required inputMode="decimal" value={lat} onChange={(event) => setLat(event.target.value)} className={field} /></div>
              <div><label className={label} htmlFor="transit-lon">Longitude</label><input id="transit-lon" required inputMode="decimal" value={lon} onChange={(event) => setLon(event.target.value)} className={field} /></div>
              <div><label className={label} htmlFor="transit-timezone">Timezone</label><input id="transit-timezone" required value={timezone} onChange={(event) => { setTimezone(event.target.value); setDisambiguation(""); }} placeholder="Europe/Dublin" className={field} /></div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="ghost" onClick={useCurrentDateTime}><RotateCw size={14} />Use current date/time</Button>
              <Button type="button" variant="ghost" onClick={useCurrentLocation} disabled={locating}><MapPin size={14} />{locating ? "Requesting location…" : "Use my current location"}</Button>
              <Button type="submit" variant="accent" disabled={verifying}><Crosshair size={14} />{verifying ? "Verifying context…" : "Calculate transits"}</Button>
            </div>
            <p className="text-[11px] text-text-muted">Current location asks for browser permission. If denied or unavailable, city search and manual coordinates remain available.</p>
            {error && <p role="alert" className="text-xs text-danger">{error}</p>}
          </form>
        </Card>
      </div>

      {transit ? (
        <>
          <Card className="p-5"><GocharPanel key={transit.transit_instant} chart={chart} transit={transit} /></Card>
          <Card className="p-5">
            <h3 className="text-sm font-semibold mb-1">Year at a Glance</h3>
            <p className="text-[11px] text-text-muted font-mono mb-4">Planet sign movements using the confirmed transit observation location and timezone.</p>
            <GraphicalEphemeris key={transit.transit_instant} chart={chart} transit={transit} />
          </Card>
        </>
      ) : (
        <Card className="p-6 text-sm text-text-muted">Confirm a transit observation context to calculate personalized Gochar results.</Card>
      )}
    </div>
  );
}
