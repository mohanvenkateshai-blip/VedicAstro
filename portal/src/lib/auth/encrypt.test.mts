import assert from "node:assert/strict";
import { describe, it } from "node:test";

// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { decryptSavedChartDataWithKey, encryptSavedChartDataWithKey, EncryptionConfigurationError, EncryptionIntegrityError, isEncryptedSavedChartValue, type SavedChartSensitiveData } from "./saved-chart-crypto.ts";

const key = "0123456789abcdef0123456789abcdef";

const plaintext: SavedChartSensitiveData = {
  name: "Test chart",
  birth_date: "2000-01-02",
  birth_time: "03:04",
  place: "Dublin",
  lat: "53.3498",
  lon: "-6.2603",
  tz: "0",
};

describe("saved-chart encryption", () => {
  it("round-trips every sensitive field without deterministic ciphertext", async () => {
    const first = await encryptSavedChartDataWithKey(plaintext, "owner-a", key);
    const second = await encryptSavedChartDataWithKey(plaintext, "owner-a", key);

    for (const value of Object.values(first)) assert.equal(isEncryptedSavedChartValue(value), true);
    assert.notEqual(first.birth_date, second.birth_date);
    assert.deepEqual(await decryptSavedChartDataWithKey(first, "owner-a", key), plaintext);
  });

  it("continues to read a complete legacy plaintext row", async () => {
    assert.deepEqual(await decryptSavedChartDataWithKey(plaintext, "owner-a", ""), plaintext);
  });

  it("fails closed when a new write has no valid deployment key", async () => {
    await assert.rejects(
      () => encryptSavedChartDataWithKey(plaintext, "owner-a", ""),
      EncryptionConfigurationError,
    );
  });

  it("binds ciphertext to its owner and field", async () => {
    const encrypted = await encryptSavedChartDataWithKey(plaintext, "owner-a", key);
    await assert.rejects(
      () => decryptSavedChartDataWithKey(encrypted, "owner-b", key),
      EncryptionIntegrityError,
    );

    const swapped = { ...encrypted, birth_date: encrypted.birth_time };
    await assert.rejects(
      () => decryptSavedChartDataWithKey(swapped, "owner-a", key),
      EncryptionIntegrityError,
    );
  });

  it("rejects rows containing a mix of plaintext and enc:v1 fields", async () => {
    const encrypted = await encryptSavedChartDataWithKey(plaintext, "owner-a", key);
    const mixed = { ...encrypted, place: plaintext.place };
    await assert.rejects(
      () => decryptSavedChartDataWithKey(mixed, "owner-a", key),
      EncryptionIntegrityError,
    );
  });

  it("rejects reserved encryption prefixes from unknown versions", async () => {
    const unknownVersion = { ...plaintext, name: "enc:v2:not-supported" };
    await assert.rejects(
      () => decryptSavedChartDataWithKey(unknownVersion, "owner-a", key),
      EncryptionIntegrityError,
    );
  });
});
