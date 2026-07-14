"use client";

import { useEffect, useRef, useState } from "react";
import { CalendarCheck, Crosshair } from "lucide-react";

import { Card, CardLabel } from "@/components/ui/Card";
import { localDateTimeAt, resolveZonedLocalInstants } from "@/lib/transit-context";
import {
  invalidateMuhurtaPlace,
  selectedMuhurtaPlace,
  type MuhurtaPlaceResult,
} from "@/lib/muhurta-place";

type InitialContext = {
  date: string;
  time: string;
  place: string;
  latitude: string;
  longitude: string;
  timezone: string;
  disambiguation: string;
};

const field =
  "w-full rounded-lg border border-hairline bg-card px-3 py-2 text-sm outline-none focus:border-accent transition-colors";
const label = "block text-xs font-medium text-text-muted mb-1.5";

export function MuhurtaContextForm({
  initial,
  natalParams,
}: {
  initial: InitialContext;
  natalParams: Array<[string, string]>;
}) {
  const [date, setDate] = useState(initial.date);
  const [time, setTime] = useState(initial.time);
  const [place, setPlace] = useState(initial.place);
  const [latitude, setLatitude] = useState(initial.latitude);
  const [longitude, setLongitude] = useState(initial.longitude);
  const [timezone, setTimezone] = useState(initial.timezone);
  const [disambiguation, setDisambiguation] = useState(initial.disambiguation);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [results, setResults] = useState<MuhurtaPlaceResult[]>([]);
  const [resultsOpen, setResultsOpen] = useState(false);
  const [activeResult, setActiveResult] = useState(-1);
  const [searching, setSearching] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchRequest = useRef<AbortController | null>(null);
  const dateEdited = useRef(Boolean(initial.date));
  const timeEdited = useRef(Boolean(initial.time));

  function populateNow(zone: string) {
    if (!zone) return;
    try {
      const now = localDateTimeAt(new Date(), zone);
      if (!dateEdited.current) setDate(now.date);
      if (!timeEdited.current) setTime(now.time);
    } catch {
      // Named-zone validation remains visible on submit.
    }
  }

  useEffect(() => {
    const zone = initial.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const initialization = window.setTimeout(() => {
      if (!initial.timezone) setTimezone(zone);
      populateNow(zone);
    }, 0);
    return () => {
      window.clearTimeout(initialization);
      if (searchTimer.current) clearTimeout(searchTimer.current);
      searchRequest.current?.abort();
    };
    // Initial query values deliberately define the one-time hydration seed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyPlace(result: MuhurtaPlaceResult) {
    const selected = selectedMuhurtaPlace(result);
    if (selected.timezone !== timezone) setDisambiguation("");
    setPlace(selected.place);
    setLatitude(selected.latitude);
    setLongitude(selected.longitude);
    setTimezone(selected.timezone);
    setResults([]);
    setResultsOpen(false);
    setActiveResult(-1);
    setLocationError(null);
    populateNow(selected.timezone);
  }

  function changePlace(value: string) {
    const invalidated = invalidateMuhurtaPlace(value);
    setPlace(invalidated.place);
    setLatitude(invalidated.latitude);
    setLongitude(invalidated.longitude);
    setTimezone(invalidated.timezone);
    setDisambiguation("");
    setResults([]);
    setResultsOpen(false);
    setActiveResult(-1);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchRequest.current?.abort();
    if (value.trim().length < 2) return;
    searchTimer.current = setTimeout(async () => {
      const controller = new AbortController();
      searchRequest.current = controller;
      setSearching(true);
      try {
        const response = await fetch(`/api/cvce/places?q=${encodeURIComponent(value.trim())}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("place search failed");
        const payload = (await response.json()) as { results?: MuhurtaPlaceResult[] };
        if (searchRequest.current !== controller) return;
        const next = payload.results ?? [];
        setResults(next);
        setResultsOpen(next.length > 0);
        setActiveResult(next.length ? 0 : -1);
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setLocationError("Place search is unavailable. Try again before submitting.");
      } finally {
        if (searchRequest.current === controller) setSearching(false);
      }
    }, 300);
  }

  function placeKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!resultsOpen || !results.length) {
      if (event.key === "Escape") setResultsOpen(false);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveResult((current) => (current + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveResult((current) => (current - 1 + results.length) % results.length);
    } else if (event.key === "Enter" && activeResult >= 0) {
      event.preventDefault();
      applyPlace(results[activeResult]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setResultsOpen(false);
    }
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setLocationError("This browser does not provide location access. Enter an election place manually.");
      return;
    }
    setLocating(true);
    setLocationError(null);
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const response = await fetch(
            `/api/cvce/timezone?lat=${encodeURIComponent(coords.latitude)}&lon=${encodeURIComponent(coords.longitude)}`,
          );
          if (!response.ok) throw new Error("timezone lookup failed");
          const payload = (await response.json()) as { timezone?: string };
          if (!payload.timezone) throw new Error("timezone unavailable");
          applyPlace({
            label: "Current location (browser permission)",
            lat: Number(coords.latitude.toFixed(6)),
            lon: Number(coords.longitude.toFixed(6)),
            timezone: payload.timezone,
          });
        } catch {
          setLocationError("The coordinates were received, but their IANA timezone could not be verified.");
        } finally {
          setLocating(false);
        }
      },
      () => {
        setLocating(false);
        setLocationError("Location permission was not granted. Enter the election context manually.");
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
    );
  }

  let overlapCandidates: ReturnType<typeof resolveZonedLocalInstants> = [];
  if (date && time && timezone.trim()) {
    try {
      const candidates = resolveZonedLocalInstants(date, time, timezone.trim());
      if (candidates.length === 2) overlapCandidates = candidates;
    } catch {
      // Submission displays invalid-zone and DST-gap errors.
    }
  }

  return (
    <Card className="p-5 md:p-6">
      <CardLabel>Election moment</CardLabel>
      <h2 className="mt-1 font-[family-name:var(--font-display)] text-xl font-semibold">Choose the moment to assess</h2>
      <p className="mt-1 text-sm text-text-muted">
        This context is independent of the natal birthplace. Date and time initialize to now in the selected IANA timezone.
      </p>
      <form method="get" action="/chart/muhurta" className="mt-5 grid gap-4 md:grid-cols-2">
        {natalParams.map(([name, value], index) => <input key={`${name}-${index}`} type="hidden" name={name} value={value} />)}
        <div><label className={label} htmlFor="m-date">Election date</label><input id="m-date" name="m_date" type="date" required value={date} onChange={(event) => { dateEdited.current = true; setDate(event.target.value); setDisambiguation(""); }} className={field} /></div>
        <div><label className={label} htmlFor="m-time">Election time</label><input id="m-time" name="m_time" type="time" required value={time} onChange={(event) => { timeEdited.current = true; setTime(event.target.value); setDisambiguation(""); }} className={field} /></div>
        <div className="relative md:col-span-2"><label className={label} htmlFor="m-place">Election place</label><input id="m-place" name="m_place" role="combobox" aria-autocomplete="list" aria-expanded={resultsOpen} aria-controls="m-place-results" aria-activedescendant={activeResult >= 0 ? `m-place-option-${activeResult}` : undefined} autoComplete="off" required value={place} onChange={(event) => changePlace(event.target.value)} onKeyDown={placeKeyDown} placeholder="Search Athlone, Dublin, Mysuru…" className={field} />{searching ? <span className="absolute right-3 top-9 text-xs text-text-muted">Searching…</span> : null}{resultsOpen ? <ul id="m-place-results" role="listbox" className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-hairline bg-card p-1 shadow-xl">{results.map((result, index) => <li id={`m-place-option-${index}`} key={`${result.label}-${result.lat}-${result.lon}`} role="option" aria-selected={index === activeResult} onMouseDown={(event) => { event.preventDefault(); applyPlace(result); }} onMouseEnter={() => setActiveResult(index)} className={`cursor-pointer rounded-md px-3 py-2 text-sm ${index === activeResult ? "bg-accent/10 text-accent" : "hover:bg-accent/5"}`}>{result.label}<span className="ml-2 font-mono text-[10px] text-text-muted">{result.lat}, {result.lon} · {result.timezone}</span></li>)}</ul> : null}</div>
        <div><label className={label} htmlFor="m-lat">Latitude</label><input id="m-lat" name="m_lat" type="number" min="-90" max="90" step="any" required readOnly value={latitude} placeholder="Select a place" className={field} /></div>
        <div><label className={label} htmlFor="m-lon">Longitude</label><input id="m-lon" name="m_lon" type="number" min="-180" max="180" step="any" required readOnly value={longitude} placeholder="Select a place" className={field} /></div>
        <div className="md:col-span-2"><label className={label} htmlFor="m-zone">IANA timezone</label><input id="m-zone" name="m_zone" required readOnly value={timezone} placeholder="Selected with place" className={field} /><p className="mt-1 text-[11px] text-text-muted">Place, coordinates, and timezone are selected together and re-verified by the server.</p></div>
        <button type="button" onClick={useCurrentLocation} disabled={locating} className="md:col-span-2 inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-hairline px-4 py-2 text-sm hover:bg-accent/5 disabled:opacity-50"><Crosshair size={15} />{locating ? "Locating…" : "Use current location and timezone"}</button>
        {locationError ? <p className="md:col-span-2 text-sm text-danger" role="alert">{locationError}</p> : null}
        {overlapCandidates.length === 2 ? <fieldset className="md:col-span-2 rounded-lg border border-hairline p-3"><legend className="px-1 text-xs font-medium">Repeated DST time — choose one occurrence</legend><div className="mt-2 grid gap-2 sm:grid-cols-2">{overlapCandidates.map((candidate) => <label key={candidate.disambiguation} className="flex items-center gap-2 text-sm"><input type="radio" name="m_disambiguation" value={candidate.disambiguation} required checked={disambiguation === candidate.disambiguation} onChange={() => setDisambiguation(candidate.disambiguation)} /><span className="capitalize">{candidate.disambiguation}: {candidate.instant} ({candidate.utcInstant})</span></label>)}</div></fieldset> : null}
        <button type="submit" className="md:col-span-2 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-accent px-6 py-3 font-medium text-accent-fg transition-colors hover:bg-accent-strong"><CalendarCheck size={16} />Assess this moment</button>
      </form>
    </Card>
  );
}
