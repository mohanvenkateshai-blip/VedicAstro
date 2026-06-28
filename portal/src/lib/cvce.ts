/**
 * Server-side client for the CVCE (Canonical Vedic Calculation Engine).
 *
 * Per the architecture, the browser never calls CVCE directly — only the
 * portal's server does (Server Actions / route handlers). This module is
 * server-only; importing it in a client component will throw.
 */
import "server-only";

import type {
  BirthInput,
  ChartData,
  DashaDeepData,
  DayWindows,
  GraphEnhancements,
  MuhurtaResult,
  ReportFacts,
} from "./types";

const CVCE_BASE_URL =
  process.env.CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";

export class CvceError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "CvceError";
  }
}

/**
 * Fetch the full canonical chart for a birth. Cached per identical input for a
 * short window (a horoscope is deterministic, so this is safe and cheap).
 */
export async function getChart(birth: BirthInput): Promise<ChartData> {
  let res: Response;
  try {
    res = await fetch(`${CVCE_BASE_URL}/chart`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ayanamsa: "LAHIRI", ...birth }),
      // Deterministic output → cache aggressively; the engine scales to zero,
      // so this also smooths over cold starts for repeat views.
      next: { revalidate: 60 * 60 * 24 },
    });
  } catch (e) {
    console.error("CVCE /chart unreachable", (e as Error).message);
    throw new CvceError("The calculation engine is temporarily unavailable. Please try again.");
  }

  if (!res.ok) {
    console.error(`CVCE /chart error: ${res.status}`, await res.text().catch(() => ""));
    throw new CvceError("The calculation engine encountered an error. Please try again.");
  }
  return (await res.json()) as ChartData;
}

/** Horary chart for the current moment at the given location. */
export async function getPrashna(params: {
  lat: number;
  lon: number;
  tz: number;
  datetime?: string;
}): Promise<ChartData> {
  const body: Record<string, unknown> = {
    birth_lat: params.lat,
    birth_lon: params.lon,
    birth_tz: params.tz,
    name: "Prashna",
    ayanamsa: "LAHIRI",
  };
  if (params.datetime) body.birth_datetime = params.datetime;

  return post<ChartData>("/prashna", body, 0);
}

async function post<T>(path: string, body: unknown, revalidate = 60 * 60): Promise<T> {
  const res = await fetch(`${CVCE_BASE_URL}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    next: { revalidate },
  });
  if (!res.ok) {
    console.error(`CVCE ${path} error: ${res.status}`, await res.text().catch(() => ""));
    throw new CvceError(`Engine returned an error for ${path}.`);
  }
  return (await res.json()) as T;
}

/**
 * Full 5-level Vimshottari tree + current ladder.
 * Cached 24h — dasha periods are deterministic per birth input.
 */
export async function getDashaDeep(birth: BirthInput): Promise<DashaDeepData> {
  return post<DashaDeepData>(
    "/dasha-deep",
    {
      birth_datetime: birth.birth_datetime,
      birth_lat: birth.birth_lat,
      birth_lon: birth.birth_lon,
      birth_tz: birth.birth_tz,
    },
    60 * 60 * 24,
  );
}

/** Unified report facts — natal, dasha ladder, dasha + transit intelligence. */
export async function getReportFacts(birth: BirthInput): Promise<ReportFacts> {
  return post<ReportFacts>(
    "/report/facts",
    { ayanamsa: "LAHIRI", ...birth },
    60 * 30,
  );
}

export interface MuhurtaQuery {
  date: string; // YYYY-MM-DD (the day being judged)
  time: string; // HH:MM
  lat: number;
  lon: number;
  tz: number;
}

export interface MuhurtaBundle {
  chart: ChartData;
  prediction: MuhurtaResult;
  windows: DayWindows;
  query: MuhurtaQuery;
}

/**
 * Muhurta analysis for a native on a given day. Pulls the natal chart first
 * (the engine's gochar/daśā/ashtakavarga need janma context), then runs the
 * personalized prediction and the day's inauspicious windows in parallel.
 */
export async function getMuhurta(
  birth: BirthInput,
  query: MuhurtaQuery,
): Promise<MuhurtaBundle> {
  const chart = await getChart(birth);
  const moon = chart.planets.find((p) => p.planet === "Moon");

  const predictBody = {
    date: query.date,
    time: query.time,
    lat: query.lat,
    lon: query.lon,
    tz: query.tz,
    janma_rashi: moon?.rashi,
    janma_nakshatra: moon?.nakshatra,
    birth_moon_lon: moon?.longitude,
    natal_signs: chart.natalSign,
    birth_date: birth.birth_datetime.slice(0, 10),
    birth_time: birth.birth_datetime.slice(11, 16),
    birth_lat: birth.birth_lat,
    birth_lon: birth.birth_lon,
    birth_tz: birth.birth_tz,
  };

  const [prediction, windows] = await Promise.all([
    post<MuhurtaResult>("/predict", predictBody),
    post<DayWindows>("/rahu-kalam", {
      datetime: `${query.date}T${query.time}:00`,
      lat: query.lat,
      lon: query.lon,
      tz_offset: query.tz,
    }),
  ]);

  return { chart, prediction, windows, query };
}

export async function getHealth(): Promise<{ status: string; engine: string } | null> {
  try {
    const res = await fetch(`${CVCE_BASE_URL}/health`, {
      next: { revalidate: 30 },
    });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

/**
 * Fetch graph-enhanced prediction insights for a birth chart + today's transit.
 * Returns only the graph_enhancements block for display below the natal chart.
 */
export async function getGraphInsights(
  chart: ChartData,
): Promise<GraphEnhancements | null> {
  const moon = chart.planets.find((p) => p.planet === "Moon");
  const today = new Date().toISOString().slice(0, 10);
  const body = {
    date: today,
    time: "12:00",
    lat: chart.meta?.birth_lat ?? 12.3,
    lon: chart.meta?.birth_lon ?? 76.65,
    tz: chart.meta?.birth_tz ?? 5.5,
    janma_rashi: moon?.rashi ?? null,
    janma_nakshatra: moon?.nakshatra ?? null,
    birth_moon_lon: moon?.longitude ?? null,
    natal_signs: chart.natalSign ?? null,
    birth_date: chart.meta?.birth_datetime?.slice(0, 10) ?? null,
    birth_time: chart.meta?.birth_datetime?.slice(11, 16) ?? null,
    birth_lat: chart.meta?.birth_lat ?? null,
    birth_lon: chart.meta?.birth_lon ?? null,
    birth_tz: chart.meta?.birth_tz ?? null,
  };
  try {
    const res = await fetch(`${CVCE_BASE_URL}/predict`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      next: { revalidate: 60 * 60 },
    });
    if (!res.ok) return null;
    const data = await res.json();
    return (data as { graph_enhancements?: GraphEnhancements }).graph_enhancements ?? null;
  } catch {
    return null;
  }
}
