import type { BirthInput } from "./types";

/** Blank defaults — form is empty until the user fills in birth details. */
export const DEMO_BIRTH_DEFAULTS = {
  name: "",
  date: "",
  time: "",
  place: "",
  lat: "",
  lon: "",
  tz: "5.5",
} as const;

export type BirthDefaults = {
  name: string;
  date: string;
  time: string;
  place: string;
  lat: string;
  lon: string;
  tz: string;
};

export type SearchParams = Record<string, string | string[] | undefined>;

const one = (v: string | string[] | undefined) =>
  Array.isArray(v) ? v[0] : v;

export function parseBirthDefaults(sp: SearchParams): BirthDefaults {
  return {
    name:  one(sp.name)  ?? "",
    date:  one(sp.date)  ?? "",
    time:  one(sp.time)  ?? "",
    place: one(sp.place) ?? "",
    lat:   one(sp.lat)   ?? "",
    lon:   one(sp.lon)   ?? "",
    tz:    one(sp.tz)    ?? "5.5",
  };
}

export function defaultsToBirthInput(f: BirthDefaults): BirthInput {
  return {
    name: f.name,
    birth_datetime: `${f.date}T${(f.time || "12:00").slice(0, 5)}:00`,
    birth_lat: Number(f.lat),
    birth_lon: Number(f.lon),
    birth_tz: Number(f.tz),
  };
}

export function birthQueryString(f: BirthDefaults): string {
  const p = new URLSearchParams({
    name: f.name,
    date: f.date,
    time: f.time,
    place: f.place,
    lat: f.lat,
    lon: f.lon,
    tz: f.tz,
  });
  return p.toString();
}
