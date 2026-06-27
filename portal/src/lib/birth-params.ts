import type { BirthInput } from "./types";

/** Known-good demo birth (Mohan) — first-load default across chart routes. */
export const DEMO_BIRTH_DEFAULTS = {
  name: "Mohan",
  date: "1975-04-22",
  time: "19:15",
  place: "Mysore, IN",
  lat: "12.2958",
  lon: "76.6394",
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
    name: one(sp.name) ?? DEMO_BIRTH_DEFAULTS.name,
    date: one(sp.date) ?? DEMO_BIRTH_DEFAULTS.date,
    time: one(sp.time) ?? DEMO_BIRTH_DEFAULTS.time,
    place: one(sp.place) ?? DEMO_BIRTH_DEFAULTS.place,
    lat: one(sp.lat) ?? DEMO_BIRTH_DEFAULTS.lat,
    lon: one(sp.lon) ?? DEMO_BIRTH_DEFAULTS.lon,
    tz: one(sp.tz) ?? DEMO_BIRTH_DEFAULTS.tz,
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
