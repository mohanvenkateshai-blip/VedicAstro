// @ts-expect-error -- explicit extension keeps this shared module executable in Node's TS test runner.
import { buildTransitObservationRequest, type TransitDisambiguation, type TransitObservationInput } from "./transit-context.ts";

export type MuhurtaMomentContext = TransitObservationInput & {
  effectiveInstant: string;
  utcOffsetHours: number;
};

export type MuhurtaSearchParams = Record<string, string | string[] | undefined>;

const one = (value: string | string[] | undefined) =>
  Array.isArray(value) ? value[0] : value;

function requiredNumber(
  value: string | string[] | undefined,
  label: string,
): number {
  const raw = one(value)?.trim();
  if (!raw) throw new Error(`${label} is required.`);
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) throw new Error(`${label} must be a finite number.`);
  return parsed;
}

function offsetHours(instant: string): number {
  if (instant.endsWith("Z")) return 0;
  const match = /([+-])(\d{2}):(\d{2})$/.exec(instant);
  if (!match) throw new Error("The effective election instant has no UTC offset.");
  const minutes = Number(match[2]) * 60 + Number(match[3]);
  return (match[1] === "-" ? -minutes : minutes) / 60;
}

export function parseMuhurtaMoment(
  params: MuhurtaSearchParams,
): { context: MuhurtaMomentContext | null; error: string | null } {
  const date = one(params.m_date)?.trim() ?? "";
  const time = one(params.m_time)?.trim() ?? "";
  const place = one(params.m_place)?.trim() ?? "";
  const timezone = one(params.m_zone)?.trim() ?? "";
  const supplied = [
    date,
    time,
    place,
    one(params.m_lat),
    one(params.m_lon),
    timezone,
    one(params.m_disambiguation),
  ].some(Boolean);
  if (!supplied) return { context: null, error: null };

  try {
    if (!date) throw new Error("Election date is required.");
    if (!time) throw new Error("Election time is required.");
    if (!place) throw new Error("Election place is required.");
    if (!timezone) throw new Error("Election IANA timezone is required.");
    const disambiguation = (one(params.m_disambiguation) ?? "exact") as TransitDisambiguation;
    if (!["exact", "earlier", "later"].includes(disambiguation)) {
      throw new Error("DST occurrence must be exact, earlier, or later.");
    }
    const raw: TransitObservationInput = {
      date,
      time,
      place,
      latitude: requiredNumber(params.m_lat, "Election latitude"),
      longitude: requiredNumber(params.m_lon, "Election longitude"),
      timezone,
      disambiguation,
    };
    const request = buildTransitObservationRequest(raw);
    return {
      context: {
        ...raw,
        effectiveInstant: request.transit_instant,
        utcOffsetHours: offsetHours(request.transit_instant),
      },
      error: null,
    };
  } catch (caught) {
    return {
      context: null,
      error: caught instanceof Error ? caught.message : "Invalid election moment context.",
    };
  }
}
