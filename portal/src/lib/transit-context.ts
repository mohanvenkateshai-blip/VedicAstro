export interface TransitObservationInput {
  date: string;
  time: string;
  place: string;
  latitude: number;
  longitude: number;
  timezone: string;
  disambiguation?: TransitDisambiguation;
}

export type TransitDisambiguation = "exact" | "earlier" | "later";

export interface TransitObservationRequest {
  transit_instant: string;
  transit_place: string;
  transit_lat: number;
  transit_lon: number;
  transit_timezone: string;
  transit_disambiguation: TransitDisambiguation;
}

export interface ZonedLocalCandidate {
  instant: string;
  utcInstant: string;
  offset: string;
  disambiguation: "earlier" | "later" | "exact";
}

type LocalParts = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
};

const LOCAL_FORMATTERS = new Map<string, Intl.DateTimeFormat>();

function formatter(timezone: string): Intl.DateTimeFormat {
  let value = LOCAL_FORMATTERS.get(timezone);
  if (!value) {
    value = new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23",
    });
    LOCAL_FORMATTERS.set(timezone, value);
  }
  return value;
}

function localPartsAt(instant: Date, timezone: string): LocalParts {
  const fields = Object.fromEntries(
    formatter(timezone)
      .formatToParts(instant)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, Number(part.value)]),
  );
  return {
    year: fields.year,
    month: fields.month,
    day: fields.day,
    hour: fields.hour,
    minute: fields.minute,
    second: fields.second,
  };
}

function offsetMinutesAt(epochMs: number, timezone: string): number {
  const local = localPartsAt(new Date(epochMs), timezone);
  const representedAsUtc = Date.UTC(
    local.year,
    local.month - 1,
    local.day,
    local.hour,
    local.minute,
    local.second,
  );
  return Math.round((representedAsUtc - epochMs) / 60_000);
}

function parseLocal(date: string, time: string): LocalParts {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  const clock = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(time);
  if (!match || !clock) throw new Error("Enter a valid observation date and time.");
  const parts = {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
    hour: Number(clock[1]),
    minute: Number(clock[2]),
    second: Number(clock[3] ?? 0),
  };
  const check = new Date(
    Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second),
  );
  if (
    check.getUTCFullYear() !== parts.year ||
    check.getUTCMonth() + 1 !== parts.month ||
    check.getUTCDate() !== parts.day ||
    parts.hour > 23 ||
    parts.minute > 59 ||
    parts.second > 59
  ) {
    throw new Error("Enter a valid observation date and time.");
  }
  return parts;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function offsetLabel(offsetMinutes: number): string {
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const absolute = Math.abs(offsetMinutes);
  return `${sign}${pad(Math.floor(absolute / 60))}:${pad(absolute % 60)}`;
}

/** Enumerate every real instant represented by a named-zone civil time. */
export function resolveZonedLocalInstants(
  date: string,
  time: string,
  timezone: string,
): ZonedLocalCandidate[] {
  const local = parseLocal(date, time);
  const wallMs = Date.UTC(
    local.year,
    local.month - 1,
    local.day,
    local.hour,
    local.minute,
    local.second,
  );
  const possibleOffsets = new Set<number>();
  for (const deltaHours of [-48, -24, -6, 0, 6, 24, 48]) {
    possibleOffsets.add(offsetMinutesAt(wallMs + deltaHours * 3_600_000, timezone));
  }

  const candidates = [...possibleOffsets]
    .map((offset) => ({ offset, instantMs: wallMs - offset * 60_000 }))
    .filter(({ offset, instantMs }) => {
      const resolved = localPartsAt(new Date(instantMs), timezone);
      const sameCivilTime = Object.keys(local).every(
        (key) => local[key as keyof LocalParts] === resolved[key as keyof LocalParts],
      );
      return sameCivilTime && offsetMinutesAt(instantMs, timezone) === offset;
    })
    .sort((a, b) => a.instantMs - b.instantMs);

  return candidates.map(({ offset, instantMs }, index) => {
    const offsetText = offsetLabel(offset);
    return {
      instant: `${date}T${pad(local.hour)}:${pad(local.minute)}:${pad(local.second)}${offsetText}`,
      utcInstant: new Date(instantMs).toISOString(),
      offset: offsetText,
      disambiguation:
        candidates.length === 1 ? "exact" : index === 0 ? "earlier" : "later",
    };
  });
}

/** Convert named-zone civil time to an ISO instant carrying an explicit offset. */
export function zonedLocalToOffsetIso(
  date: string,
  time: string,
  timezone: string,
  disambiguation: TransitDisambiguation = "exact",
): string {
  const candidates = resolveZonedLocalInstants(date, time, timezone);
  if (candidates.length === 0) {
    throw new Error("That local time does not exist in the selected timezone due to a DST change.");
  }
  if (candidates.length === 2) {
    if (disambiguation === "exact") {
      throw new Error("That local time occurs twice due to a DST change. Choose the earlier or later occurrence.");
    }
    return candidates.find((candidate) => candidate.disambiguation === disambiguation)!.instant;
  }
  if (disambiguation !== "exact") {
    throw new Error("Earlier/later disambiguation is only valid for a repeated local time.");
  }
  return candidates[0].instant;
}

export function buildTransitObservationRequest(
  input: TransitObservationInput,
): TransitObservationRequest {
  if (!input.place.trim()) throw new Error("Select or describe the transit observation place.");
  if (!Number.isFinite(input.latitude) || input.latitude < -90 || input.latitude > 90) {
    throw new Error("Transit latitude must be between -90 and 90.");
  }
  if (!Number.isFinite(input.longitude) || input.longitude < -180 || input.longitude > 180) {
    throw new Error("Transit longitude must be between -180 and 180.");
  }
  if (!input.timezone.trim()) throw new Error("Select an IANA timezone for the observation place.");
  const candidates = resolveZonedLocalInstants(input.date, input.time, input.timezone.trim());
  const disambiguation: TransitDisambiguation =
    candidates.length === 2 ? input.disambiguation ?? "exact" : "exact";
  return {
    transit_instant: zonedLocalToOffsetIso(
      input.date,
      input.time,
      input.timezone.trim(),
      disambiguation,
    ),
    transit_place: input.place.trim(),
    transit_lat: input.latitude,
    transit_lon: input.longitude,
    transit_timezone: input.timezone.trim(),
    transit_disambiguation: disambiguation,
  };
}

export function localDateTimeAt(instant: Date, timezone: string): { date: string; time: string } {
  const parts = localPartsAt(instant, timezone);
  return {
    date: `${parts.year}-${pad(parts.month)}-${pad(parts.day)}`,
    time: `${pad(parts.hour)}:${pad(parts.minute)}`,
  };
}
