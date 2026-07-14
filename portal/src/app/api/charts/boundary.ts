import { z } from "zod";

export const SAVED_CHART_CACHE_CONTROL = "private, no-store";

export const SAVED_CHART_FIELDS = [
  "name",
  "birth_date",
  "birth_time",
  "place",
  "lat",
  "lon",
  "tz",
] as const;

export type SavedChartSensitiveData = Record<(typeof SAVED_CHART_FIELDS)[number], string>;

export type SavedChartInput = {
  name: string;
  date: string;
  time: string;
  place: string;
  lat: string;
  lon: string;
  tz: string;
};

const boundedNumberString = (minimum: number, maximum: number) => z.coerce
  .string()
  .trim()
  .min(1)
  .refine((value) => {
    const number = Number(value);
    return Number.isFinite(number) && number >= minimum && number <= maximum;
  })
  .transform((value) => String(Number(value)));

function isCalendarDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1 || month < 1 || month > 12 || day < 1) return false;
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day <= days[month - 1];
}

export const savedChartInputSchema = z.object({
  name: z.string().trim().min(1).max(100).default("Unnamed chart"),
  date: z.string().refine(isCalendarDate, "Invalid calendar date"),
  time: z.string().regex(/^(?:[01]\d|2[0-3]):[0-5]\d$/, "Invalid 24-hour time"),
  place: z.string().trim().max(240).default(""),
  lat: boundedNumberString(-90, 90),
  lon: boundedNumberString(-180, 180),
  tz: boundedNumberString(-14, 14),
}).strict();

export function parseSavedChartInput(value: unknown) {
  return savedChartInputSchema.safeParse(value);
}

export function sensitiveData(row: SavedChartSensitiveData): SavedChartSensitiveData {
  return Object.fromEntries(
    SAVED_CHART_FIELDS.map((field) => [field, row[field]]),
  ) as SavedChartSensitiveData;
}

type Encryptor = (
  data: SavedChartSensitiveData,
  owner: string,
) => Promise<SavedChartSensitiveData>;

type Decryptor = Encryptor;

export async function prepareSavedChartInsert(
  body: SavedChartInput,
  owner: string,
  sortOrder: number,
  encrypt: Encryptor,
): Promise<SavedChartSensitiveData & { guest_id: string; sort_order: number }> {
  const encrypted = await encrypt({
    name: body.name,
    birth_date: body.date,
    birth_time: body.time,
    place: body.place,
    lat: body.lat,
    lon: body.lon,
    tz: body.tz,
  }, owner);
  return { guest_id: owner, ...encrypted, sort_order: sortOrder };
}

export async function decodeSavedChartRows<T extends SavedChartSensitiveData>(
  rows: T[],
  owner: string,
  decrypt: Decryptor,
): Promise<T[]> {
  return Promise.all(rows.map(async (row) => ({
    ...row,
    ...(await decrypt(sensitiveData(row), owner)),
  })));
}

export function findDuplicateChart<T extends SavedChartSensitiveData & { id: string }>(
  rows: T[],
  body: Pick<SavedChartInput, "date" | "time" | "lat">,
): T | undefined {
  return rows.find((row) => (
    row.birth_date === body.date && row.birth_time === body.time && row.lat === body.lat
  ));
}

export type OwnerScopedQuery<T> = {
  eq(column: "guest_id", owner: string): T;
};

export function scopeSavedChartsToOwner<T>(query: OwnerScopedQuery<T>, owner: string): T {
  return query.eq("guest_id", owner);
}

export function savedChartPrivacyFailure(error: unknown): { status: number; message: string } {
  if (error instanceof Error && error.name === "EncryptionConfigurationError") {
    return {
      status: 503,
      message: "Saved charts are temporarily unavailable because secure storage is not configured.",
    };
  }
  if (error instanceof Error && error.name === "EncryptionIntegrityError") {
    return {
      status: 500,
      message: "A saved chart could not be securely read. No data was returned.",
    };
  }
  return { status: 500, message: "Saved charts are temporarily unavailable." };
}
