import assert from "node:assert/strict";
import { describe, it } from "node:test";

// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { ChartDataEncryptionConfigurationError, ChartDataEncryptionIntegrityError, decryptChartDataWithKey, encryptChartDataWithKey } from "./chart-data-crypto.ts";

const key = "0123456789abcdef0123456789abcdef";
const chart = {
  meta: {
    birth_datetime: "2000-01-02T03:04:00",
    birth_lat: 53.3498,
    birth_lon: -6.2603,
    ayanamsa: "LAHIRI",
  },
  planets: { Sun: { longitude: 123.4 } },
};

describe("authenticated horoscope chart_data encryption", () => {
  it("encrypts and decrypts birth PII without mutating chart calculations", async () => {
    const encrypted = await encryptChartDataWithKey(chart, key);
    const meta = encrypted.meta as Record<string, unknown>;
    assert.notEqual(meta.birth_datetime, chart.meta.birth_datetime);
    assert.equal(meta.pii_encryption, "aes-256-gcm:v1");

    const decrypted = await decryptChartDataWithKey(encrypted, key);
    assert.deepEqual(decrypted, {
      ...chart,
      meta: {
        ...chart.meta,
        birth_lat: String(chart.meta.birth_lat),
        birth_lon: String(chart.meta.birth_lon),
      },
    });
  });

  it("fails closed for a new write without an exact 32-byte key", async () => {
    await assert.rejects(
      () => encryptChartDataWithKey(chart, "too-short"),
      ChartDataEncryptionConfigurationError,
    );
  });

  it("preserves complete legacy plaintext reads without requiring a key", async () => {
    assert.deepEqual(await decryptChartDataWithKey(chart, ""), chart);
  });

  it("never returns ciphertext when the key cannot authenticate it", async () => {
    const encrypted = await encryptChartDataWithKey(chart, key);
    await assert.rejects(
      () => decryptChartDataWithKey(encrypted, "abcdef0123456789abcdef0123456789"),
      ChartDataEncryptionIntegrityError,
    );
  });

  it("rejects partial plaintext/ciphertext chart_data", async () => {
    const encrypted = await encryptChartDataWithKey(chart, key);
    const meta = { ...(encrypted.meta as Record<string, unknown>), birth_lat: "53.3498" };
    await assert.rejects(
      () => decryptChartDataWithKey({ ...encrypted, meta }, key),
      ChartDataEncryptionIntegrityError,
    );
  });

  it("rejects malformed values with the legacy ciphertext shape", async () => {
    const malformed = {
      ...chart,
      meta: { ...chart.meta, birth_datetime: "not-valid-ciphertext-iv!:abcd" },
    };
    await assert.rejects(
      () => decryptChartDataWithKey(malformed, key),
      ChartDataEncryptionIntegrityError,
    );
  });
});
