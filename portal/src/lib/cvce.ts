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
  DashaPredictions,
  DayWindows,
  GraphEnhancements,
  KalachakraDeepData,
  MuhurtaResult,
  ReportFacts,
  ForecastV2Input,
  ForecastV2Response,
  PersonTimeline,
  PersonTimelineDetailResponse,
} from "./types";
import { cvceServiceHeaders } from "./cvce-auth";
import { isForecastV2Enabled } from "./features";

const CVCE_BASE_URL =
  process.env.CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";

function cvceHeaders(json = false): Record<string, string> {
  const headers = cvceServiceHeaders(json);
  if (!headers) {
    throw new CvceError("CVCE service authentication is not configured.", 503);
  }
  return headers;
}

export class CvceError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "CvceError";
  }
}

/** Submit an already-canonical claim; this never adapts legacy prediction prose. */
export async function getForecastBriefV2(
  claim: ForecastV2Input,
): Promise<ForecastV2Response> {
  if (!isForecastV2Enabled()) {
    throw new CvceError("Forecast v2 is disabled.", 404);
  }
  return post<ForecastV2Response>("/v2/forecasts", claim, 0);
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
      headers: cvceHeaders(true),
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
    headers: cvceHeaders(true),
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
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20_000);
  try {
    const res = await fetch(`${CVCE_BASE_URL}/dasha-deep`, {
      method: "POST",
      headers: cvceHeaders(true),
      body: JSON.stringify({
        birth_datetime: birth.birth_datetime,
        birth_lat: birth.birth_lat,
        birth_lon: birth.birth_lon,
        birth_tz: birth.birth_tz,
      }),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) throw new CvceError(`Engine error for /dasha-deep`);
    return (await res.json()) as DashaDeepData;
  } catch (e) {
    if (e instanceof CvceError) throw e;
    throw new CvceError("Dasha engine unavailable");
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Transit-fused predictions for the current + next Mahadasha Antardasha periods.
 * Runs in parallel with getDashaDeep on the Dasha page.
 * Keyed by "MahaLord/AntarLord" to match tree node lookup.
 */
export async function getDashaPredictions(birth: BirthInput): Promise<DashaPredictions> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30_000);
  try {
    const res = await fetch(`${CVCE_BASE_URL}/dasha-predict`, {
      method: "POST",
      headers: cvceHeaders(true),
      body: JSON.stringify({
        birth_datetime: birth.birth_datetime,
        birth_lat: birth.birth_lat,
        birth_lon: birth.birth_lon,
        birth_tz: birth.birth_tz,
      }),
      signal: controller.signal,
      // Predictions are transit-dependent — cache 6h (transits shift daily).
      next: { revalidate: 60 * 60 * 6 },
    });
    if (!res.ok) throw new CvceError(`Engine error for /dasha-predict`);
    return (await res.json()) as DashaPredictions;
  } catch (e) {
    if (e instanceof CvceError) throw e;
    throw new CvceError("Dasha predictions engine unavailable");
  } finally {
    clearTimeout(timer);
  }
}

/** Unified report facts — natal, dasha ladder, dasha + transit intelligence. */
export async function getReportFacts(birth: BirthInput): Promise<ReportFacts> {
  return post<ReportFacts>(
    "/report/facts",
    { ayanamsa: "LAHIRI", ...birth },
    60 * 30,
  );
}

/** Person-centred event and prediction timeline. Always fresh: observed events
 * and outcome resolutions are append-only records that may change at any time. */
export async function getPersonTimeline(
  birth: BirthInput,
  subjectId: string,
): Promise<PersonTimeline> {
  return post<PersonTimeline>("/timeline/query", { ...birth, subject_id: subjectId }, 0);
}

export async function getPersonTimelineMilestone(
  birth: BirthInput,
  milestoneId: string,
  subjectId: string,
): Promise<PersonTimelineDetailResponse> {
  return post<PersonTimelineDetailResponse>(
    `/timeline/milestones/${encodeURIComponent(milestoneId)}/detail`,
    { ...birth, subject_id: subjectId },
    0,
  );
}

export interface MuhurtaQuery {
  instant: string;
  place: string;
  lat: number;
  lon: number;
  timezone: string;
  disambiguation: "exact" | "earlier" | "later";
}

export interface MuhurtaBundle {
  chart: ChartData;
  prediction: MuhurtaResult;
  windows: DayWindows;
  query: MuhurtaQuery;
}

function assertSameChartIdentity(loaded: ChartData, recomputed: ChartData): void {
  const sameAyanamsa = loaded.ayanamsa === recomputed.ayanamsa;
  const sameJd = Number.isFinite(loaded.jd) && Math.abs(loaded.jd - recomputed.jd) <= 1e-8;
  const loadedMoon = loaded.planets.find((planet) => planet.planet === "Moon");
  const recomputedMoon = recomputed.planets.find((planet) => planet.planet === "Moon");
  const sameMoon =
    loadedMoon !== undefined &&
    recomputedMoon !== undefined &&
    Math.abs(loadedMoon.longitude - recomputedMoon.longitude) <= 1e-6;
  const sameBirthContext =
    loaded.meta?.birth_datetime === recomputed.meta?.birth_datetime &&
    loaded.meta?.birth_lat === recomputed.meta?.birth_lat &&
    loaded.meta?.birth_lon === recomputed.meta?.birth_lon &&
    loaded.meta?.birth_tz === recomputed.meta?.birth_tz;
  if (!sameAyanamsa || !sameJd || !sameMoon || !sameBirthContext) {
    throw new CvceError("The loaded natal chart changed during Muhurta verification. Reload the chart before continuing.", 409);
  }
}

/**
 * Accuracy-gated Muhurta research calculation. The loaded natal chart is
 * recomputed and identity-checked before the one canonical CVCE request.
 */
export async function getMuhurta(
  birth: BirthInput,
  query: MuhurtaQuery,
  loadedChart: ChartData,
): Promise<MuhurtaBundle> {
  const chart = await getChart(birth);
  assertSameChartIdentity(loadedChart, chart);
  if (birth.ayanamsa !== loadedChart.ayanamsa) {
    throw new CvceError("The Muhurta request ayanamsa does not match the loaded natal chart.", 409);
  }

  const prediction = await post<MuhurtaResult>("/muhurta/canonical", {
    transit_instant: query.instant,
    transit_place: query.place,
    transit_lat: query.lat,
    transit_lon: query.lon,
    transit_timezone: query.timezone,
    transit_disambiguation: query.disambiguation,
    expected_natal_jd: chart.jd,
    ayanamsa: loadedChart.ayanamsa,
    birth_datetime: birth.birth_datetime,
    birth_lat: birth.birth_lat,
    birth_lon: birth.birth_lon,
    birth_tz: birth.birth_tz,
    name: birth.name,
  }, 0);
  if (
    !prediction.calculation_context ||
    prediction.calculation_context.fallback_used ||
    prediction.calculation_context.engine !== "PyJHora" ||
    prediction.calculation_context.backend !== "Swiss Ephemeris" ||
    prediction.calculation_context.calculation_path !== "app.ephem + jhora.panchanga.drik"
  ) {
    throw new CvceError("Canonical Muhurta provenance was missing or reported a fallback.", 502);
  }
  if (
    prediction.calculation_context.ayanamsa !== loadedChart.ayanamsa ||
    prediction.natal_context?.identity_verified !== true ||
    Math.abs((prediction.natal_context?.jd ?? Number.NaN) - loadedChart.jd) > 1e-8
  ) {
    throw new CvceError("Canonical Muhurta natal identity verification failed.", 409);
  }
  if (!prediction.windows) {
    throw new CvceError("Canonical Muhurta windows were not returned.", 502);
  }
  if (
    prediction.election_context?.instant !== query.instant ||
    prediction.election_context?.timezone !== query.timezone ||
    prediction.election_context?.latitude !== query.lat ||
    prediction.election_context?.longitude !== query.lon ||
    prediction.election_context?.place !== query.place
  ) {
    throw new CvceError("Canonical Muhurta election context verification failed.", 409);
  }

  return { chart, prediction, windows: prediction.windows, query };
}

/** Kalachakra Dasha — 86-year sign-based cycle with deha/jeeva and citations. */
export async function getKalachakraDasha(birth: BirthInput): Promise<unknown> {
  return post<unknown>(
    "/kalachakra-dasha",
    {
      birth_datetime: birth.birth_datetime,
      birth_lat: birth.birth_lat,
      birth_lon: birth.birth_lon,
      birth_tz: birth.birth_tz,
    },
    60 * 60 * 24,
  );
}

/**
 * Kalachakra Dasha — rich view: Deha/Jeeva Rasi, the 9-sign cycle with Gati
 * (leap) flags, current MD/AD/PD ladder, the active leap (if any), a 3-level
 * MD->AD->PD tree, and a chronological leap timeline (past/current/future).
 */
export async function getKalachakraDeep(birth: BirthInput): Promise<KalachakraDeepData> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20_000);
  try {
    const res = await fetch(`${CVCE_BASE_URL}/kalachakra-deep`, {
      method: "POST",
      headers: cvceHeaders(true),
      body: JSON.stringify({
        birth_datetime: birth.birth_datetime,
        birth_lat: birth.birth_lat,
        birth_lon: birth.birth_lon,
        birth_tz: birth.birth_tz,
      }),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) throw new CvceError(`Engine error for /kalachakra-deep`);
    return (await res.json()) as KalachakraDeepData;
  } catch (e) {
    if (e instanceof CvceError) throw e;
    throw new CvceError("Kalachakra engine unavailable");
  } finally {
    clearTimeout(timer);
  }
}

export async function getHealth(): Promise<{ status: string; engine: string } | null> {
  try {
    const res = await fetch(`${CVCE_BASE_URL}/health`, {
      // /health is deliberately public liveness; no service token is needed.
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
      headers: cvceHeaders(true),
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
