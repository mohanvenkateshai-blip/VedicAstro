/**
 * PII encryption for birth chart data at rest.
 *
 * Uses AES-256-GCM with a key derived from ENCRYPTION_KEY (env).
 * Encrypts the birth_datetime, birth_lat, birth_lon fields inside
 * chart_data before storing in the horoscopes table.
 */

/** Web Crypto uses "AES-GCM"; key size (256-bit) comes from the 32-byte raw key. */
const ALGO = "AES-GCM";
const KEY_LEN = 32; // 256 bits

let _keyPromise: Promise<CryptoKey | null> | null = null;

function getKey(): Promise<CryptoKey | null> {
  if (_keyPromise) return _keyPromise;
  const raw = process.env.ENCRYPTION_KEY;
  if (!raw) {
    _keyPromise = Promise.resolve(null);
    return _keyPromise;
  }
  _keyPromise = (async () => {
    try {
      return await crypto.subtle.importKey(
        "raw",
        new TextEncoder().encode(raw.padEnd(KEY_LEN, "0").slice(0, KEY_LEN)),
        { name: ALGO },
        false,
        ["encrypt", "decrypt"],
      );
    } catch (e) {
      console.error("ENCRYPTION_KEY could not be loaded:", e);
      return null;
    }
  })();
  return _keyPromise;
}

/**
 * Encrypt the birth-sensitive fields in chart_data.
 * Replaces birth_datetime, birth_lat, birth_lon in meta with their
 * encrypted hex representations. Non-destructive — the original chart
 * positions/planets remain readable.
 */
export async function encryptChartData(chartData: Record<string, unknown>): Promise<Record<string, unknown>> {
  const key = await getKey();
  if (!key) return chartData; // No encryption key set — store plaintext (dev mode)

  const meta = (chartData.meta ?? {}) as Record<string, unknown>;
  const toEncrypt: Record<string, string> = {};
  if (meta.birth_datetime) toEncrypt["birth_datetime"] = String(meta.birth_datetime);
  if (meta.birth_lat != null) toEncrypt["birth_lat"] = String(meta.birth_lat);
  if (meta.birth_lon != null) toEncrypt["birth_lon"] = String(meta.birth_lon);

  for (const [field, value] of Object.entries(toEncrypt)) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const enc = await crypto.subtle.encrypt(
      { name: ALGO, iv },
      key,
      new TextEncoder().encode(value),
    );
    meta[field] = `${Buffer.from(iv).toString("hex")}:${Buffer.from(enc).toString("hex")}`;
  }

  return { ...chartData, meta };
}

/**
 * Decrypt chart data for display. Returns original plaintext.
 */
export async function decryptChartData(chartData: Record<string, unknown>): Promise<Record<string, unknown>> {
  const key = await getKey();
  if (!key) return chartData;

  const meta = { ...(chartData.meta ?? {}) as Record<string, unknown> };
  for (const field of ["birth_datetime", "birth_lat", "birth_lon"]) {
    const value = meta[field];
    if (typeof value !== "string" || !value.includes(":")) continue;
    try {
      const [ivHex, encHex] = value.split(":");
      const iv = new Uint8Array(Buffer.from(ivHex, "hex"));
      const enc = new Uint8Array(Buffer.from(encHex, "hex"));
      const dec = await crypto.subtle.decrypt({ name: ALGO, iv }, key, enc);
      meta[field] = new TextDecoder().decode(dec);
    } catch {
      // Leave as-is if decryption fails (dev data)
    }
  }

  return { ...chartData, meta };
}
