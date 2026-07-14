/** Pure cryptography for authenticated users' horoscope chart_data JSON. */

const ALGO = "AES-GCM";
const KEY_LEN = 32;
const MARKER_FIELD = "pii_encryption";
const MARKER_VALUE = "aes-256-gcm:v1";
const SENSITIVE_META_FIELDS = ["birth_datetime", "birth_lat", "birth_lon"] as const;
const LEGACY_CIPHERTEXT = /^[0-9a-f]{24}:[0-9a-f]{32,}$/i;
const CIPHERTEXT_SHAPE = /^[^:]{24}:/;

export class ChartDataEncryptionConfigurationError extends Error {
  constructor() {
    super("Birth-data encryption is not configured");
    this.name = "EncryptionConfigurationError";
  }
}

export class ChartDataEncryptionIntegrityError extends Error {
  constructor() {
    super("Encrypted birth data could not be authenticated");
    this.name = "EncryptionIntegrityError";
  }
}

let cachedKey: { raw: string; promise: Promise<CryptoKey> } | null = null;

function getKey(raw: string): Promise<CryptoKey> {
  const bytes = new TextEncoder().encode(raw);
  if (bytes.byteLength !== KEY_LEN) throw new ChartDataEncryptionConfigurationError();
  if (cachedKey?.raw === raw) return cachedKey.promise;
  const promise = crypto.subtle.importKey("raw", bytes, { name: ALGO }, false, ["encrypt", "decrypt"]);
  cachedKey = { raw, promise };
  return promise;
}

function isCiphertext(value: unknown): value is string {
  return typeof value === "string" && LEGACY_CIPHERTEXT.test(value);
}

export async function encryptChartDataWithKey(
  chartData: Record<string, unknown>,
  rawKey: string,
): Promise<Record<string, unknown>> {
  const key = await getKey(rawKey);
  const meta = { ...((chartData.meta ?? {}) as Record<string, unknown>) };

  for (const field of SENSITIVE_META_FIELDS) {
    if (meta[field] == null) continue;
    const iv = new Uint8Array(new ArrayBuffer(12));
    crypto.getRandomValues(iv);
    const encrypted = await crypto.subtle.encrypt(
      { name: ALGO, iv },
      key,
      new TextEncoder().encode(String(meta[field])),
    );
    meta[field] = `${Buffer.from(iv).toString("hex")}:${Buffer.from(encrypted).toString("hex")}`;
  }
  meta[MARKER_FIELD] = MARKER_VALUE;
  return { ...chartData, meta };
}

/**
 * Legacy plaintext JSON remains readable without a key. Once any sensitive
 * field is ciphertext, all sensitive fields present in the payload must be
 * ciphertext and authenticated successfully; ciphertext is never returned.
 */
export async function decryptChartDataWithKey(
  chartData: Record<string, unknown>,
  rawKey: string,
): Promise<Record<string, unknown>> {
  const meta = { ...((chartData.meta ?? {}) as Record<string, unknown>) };
  const present = SENSITIVE_META_FIELDS.filter((field) => meta[field] != null);
  const encrypted = present.filter((field) => isCiphertext(meta[field]));
  const suspicious = present.filter((field) => (
    typeof meta[field] === "string" && CIPHERTEXT_SHAPE.test(meta[field] as string)
  ));
  if (suspicious.length !== encrypted.length) throw new ChartDataEncryptionIntegrityError();
  if (encrypted.length === 0) {
    if (meta[MARKER_FIELD] === MARKER_VALUE) throw new ChartDataEncryptionIntegrityError();
    return { ...chartData, meta };
  }
  if (encrypted.length !== present.length) throw new ChartDataEncryptionIntegrityError();

  const key = await getKey(rawKey);
  for (const field of encrypted) {
    try {
      const [ivHex, encryptedHex] = String(meta[field]).split(":");
      const iv = Uint8Array.from(Buffer.from(ivHex, "hex"));
      const ciphertext = Uint8Array.from(Buffer.from(encryptedHex, "hex"));
      if (iv.byteLength !== 12 || ciphertext.byteLength < 16) throw new Error("Invalid envelope");
      const decrypted = await crypto.subtle.decrypt({ name: ALGO, iv }, key, ciphertext);
      meta[field] = new TextDecoder().decode(decrypted);
    } catch {
      throw new ChartDataEncryptionIntegrityError();
    }
  }
  delete meta[MARKER_FIELD];
  return { ...chartData, meta };
}
