/**
 * Pure saved-chart cryptography.
 *
 * This module never reads process.env and never contains a deployment secret.
 * Server code must use auth/encrypt.ts, which retains the `server-only` guard
 * and supplies ENCRYPTION_KEY. Keeping the primitive pure makes its security
 * behavior executable under Node's built-in test runner.
 */

const ALGO = "AES-GCM";
const KEY_LEN = 32;
const SAVED_CHART_PREFIX = "enc:v1:";
const SAVED_CHART_CONTEXT = "vedicastro:saved-charts:v1";

export const SAVED_CHART_FIELDS = [
  "name",
  "birth_date",
  "birth_time",
  "place",
  "lat",
  "lon",
  "tz",
] as const;

export type SavedChartSensitiveField = (typeof SAVED_CHART_FIELDS)[number];
export type SavedChartSensitiveData = Record<SavedChartSensitiveField, string>;

export class EncryptionConfigurationError extends Error {
  constructor() {
    super("Saved-chart encryption is not configured");
    this.name = "EncryptionConfigurationError";
  }
}

export class EncryptionIntegrityError extends Error {
  constructor() {
    super("Saved-chart ciphertext could not be authenticated");
    this.name = "EncryptionIntegrityError";
  }
}

let cachedKey: { raw: string; promise: Promise<CryptoKey> } | null = null;

function getSavedChartKey(raw: string): Promise<CryptoKey> {
  if (new TextEncoder().encode(raw).byteLength !== KEY_LEN) {
    throw new EncryptionConfigurationError();
  }
  if (cachedKey?.raw === raw) return cachedKey.promise;

  const promise = (async () => {
    const material = new TextEncoder().encode(`${SAVED_CHART_CONTEXT}:${raw}`);
    const digest = await crypto.subtle.digest("SHA-256", material);
    return crypto.subtle.importKey("raw", digest, { name: ALGO }, false, ["encrypt", "decrypt"]);
  })();
  cachedKey = { raw, promise };
  return promise;
}

function additionalData(
  owner: string,
  field: SavedChartSensitiveField,
): Uint8Array<ArrayBuffer> {
  return new TextEncoder().encode(`${SAVED_CHART_CONTEXT}:${owner}:${field}`);
}

function toBase64Url(value: ArrayBuffer | Uint8Array<ArrayBuffer>): string {
  return Buffer.from(value instanceof Uint8Array ? value : new Uint8Array(value)).toString("base64url");
}

function fromBase64Url(value: string): Uint8Array<ArrayBuffer> {
  return Uint8Array.from(Buffer.from(value, "base64url"));
}

export function isEncryptedSavedChartValue(value: unknown): value is string {
  return typeof value === "string" && value.startsWith(SAVED_CHART_PREFIX);
}

export async function encryptSavedChartDataWithKey(
  data: SavedChartSensitiveData,
  owner: string,
  rawKey: string,
): Promise<SavedChartSensitiveData> {
  const key = await getSavedChartKey(rawKey);
  const encrypted = {} as SavedChartSensitiveData;

  for (const field of SAVED_CHART_FIELDS) {
    const iv = new Uint8Array(new ArrayBuffer(12));
    crypto.getRandomValues(iv);
    const ciphertext = await crypto.subtle.encrypt(
      { name: ALGO, iv, additionalData: additionalData(owner, field) },
      key,
      new TextEncoder().encode(data[field]),
    );
    encrypted[field] = `${SAVED_CHART_PREFIX}${toBase64Url(iv)}:${toBase64Url(ciphertext)}`;
  }

  return encrypted;
}

/**
 * Accept exactly one persisted format per row: all legacy plaintext or all
 * enc:v1 fields. Partial/mixed rows are rejected because returning part of a
 * corrupted or interrupted migration would silently weaken confidentiality.
 */
export async function decryptSavedChartDataWithKey(
  data: SavedChartSensitiveData,
  owner: string,
  rawKey: string,
): Promise<SavedChartSensitiveData> {
  const reservedPrefixCount = SAVED_CHART_FIELDS.filter((field) =>
    data[field].startsWith("enc:")
  ).length;
  const encryptedCount = SAVED_CHART_FIELDS.filter((field) =>
    isEncryptedSavedChartValue(data[field])
  ).length;
  if (encryptedCount === 0 && reservedPrefixCount === 0) return { ...data };
  if (reservedPrefixCount !== encryptedCount) throw new EncryptionIntegrityError();
  if (encryptedCount !== SAVED_CHART_FIELDS.length) throw new EncryptionIntegrityError();

  const key = await getSavedChartKey(rawKey);
  const result = { ...data };
  for (const field of SAVED_CHART_FIELDS) {
    const value = data[field];
    try {
      const payload = value.slice(SAVED_CHART_PREFIX.length);
      const parts = payload.split(":");
      if (parts.length !== 2 || !parts[0] || !parts[1]) throw new Error("Invalid envelope");
      const iv = fromBase64Url(parts[0]);
      const ciphertext = fromBase64Url(parts[1]);
      if (iv.byteLength !== 12 || ciphertext.byteLength < 16) throw new Error("Invalid envelope");
      const plaintext = await crypto.subtle.decrypt(
        { name: ALGO, iv, additionalData: additionalData(owner, field) },
        key,
        ciphertext,
      );
      result[field] = new TextDecoder().decode(plaintext);
    } catch {
      throw new EncryptionIntegrityError();
    }
  }
  return result;
}
