import assert from "node:assert/strict";
import { describe, it } from "node:test";

// Integration gap: these tests execute the validation, encryption, decoding,
// error mapping, owner-scoping, and cache-policy boundaries used by route.ts.
// They intentionally do not connect to a live Supabase project or exercise
// NextResponse cookies. A deployment smoke test is still required to verify the
// configured service-role client and guest-cookie behavior end to end.

// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { decodeSavedChartRows, parseSavedChartInput, prepareSavedChartInsert, SAVED_CHART_CACHE_CONTROL, savedChartPrivacyFailure, scopeSavedChartsToOwner } from "./boundary.ts";
// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { decryptSavedChartDataWithKey, encryptSavedChartDataWithKey, EncryptionConfigurationError, isEncryptedSavedChartValue } from "../../../lib/auth/saved-chart-crypto.ts";

const key = "0123456789abcdef0123456789abcdef";
const validInput = {
  name: "Leap chart",
  date: "2024-02-29",
  time: "23:59",
  place: "Dublin",
  lat: "53.3498",
  lon: "-6.2603",
  tz: "0",
};

describe("saved-chart route boundaries", () => {
  it("validates real calendar dates and 24-hour times", () => {
    assert.equal(parseSavedChartInput(validInput).success, true);
    assert.equal(parseSavedChartInput({ ...validInput, date: "2023-02-29" }).success, false);
    assert.equal(parseSavedChartInput({ ...validInput, date: "2024-04-31" }).success, false);
    assert.equal(parseSavedChartInput({ ...validInput, time: "99:99" }).success, false);
    assert.equal(parseSavedChartInput({ ...validInput, time: "24:00" }).success, false);
  });

  it("prepares an owner-scoped encrypted insert", async () => {
    const parsed = parseSavedChartInput(validInput);
    assert.equal(parsed.success, true);
    if (!parsed.success) return;

    const row = await prepareSavedChartInsert(
      parsed.data,
      "owner-a",
      7,
      (data, owner) => encryptSavedChartDataWithKey(data, owner, key),
    );
    assert.equal(row.guest_id, "owner-a");
    assert.equal(row.sort_order, 7);
    for (const field of ["name", "birth_date", "birth_time", "place", "lat", "lon", "tz"] as const) {
      assert.equal(isEncryptedSavedChartValue(row[field]), true);
    }
  });

  it("decodes both complete legacy and complete encrypted reads", async () => {
    const legacy = {
      id: "legacy",
      name: validInput.name,
      birth_date: validInput.date,
      birth_time: validInput.time,
      place: validInput.place,
      lat: validInput.lat,
      lon: validInput.lon,
      tz: validInput.tz,
    };
    const encryptedData = await encryptSavedChartDataWithKey(legacy, "owner-a", key);
    const encrypted = { id: "encrypted", ...encryptedData };
    const decoded = await decodeSavedChartRows(
      [legacy, encrypted],
      "owner-a",
      (data, owner) => decryptSavedChartDataWithKey(data, owner, key),
    );

    assert.deepEqual(decoded[0], legacy);
    assert.deepEqual(decoded[1], { ...legacy, id: "encrypted" });
  });

  it("maps a missing encryption key to a fail-closed 503", async () => {
    const parsed = parseSavedChartInput(validInput);
    assert.equal(parsed.success, true);
    if (!parsed.success) return;

    let caught: unknown;
    try {
      await prepareSavedChartInsert(
        parsed.data,
        "owner-a",
        0,
        (data, owner) => encryptSavedChartDataWithKey(data, owner, ""),
      );
    } catch (error) {
      caught = error;
    }
    assert.ok(caught instanceof EncryptionConfigurationError);
    assert.equal(savedChartPrivacyFailure(caught).status, 503);
  });

  it("rejects malformed payloads before persistence", () => {
    assert.equal(parseSavedChartInput(null).success, false);
    assert.equal(parseSavedChartInput({ ...validInput, unexpected: true }).success, false);
    assert.equal(parseSavedChartInput({ ...validInput, lat: "" }).success, false);
    assert.equal(parseSavedChartInput({ ...validInput, lon: "181" }).success, false);
  });

  it("centralizes owner scoping and private no-store responses", () => {
    const calls: Array<[string, string]> = [];
    const result = { order: true };
    const query = {
      eq(column: "guest_id", owner: string) {
        calls.push([column, owner]);
        return result;
      },
    };

    assert.equal(scopeSavedChartsToOwner(query, "owner-a"), result);
    assert.deepEqual(calls, [["guest_id", "owner-a"]]);
    assert.equal(SAVED_CHART_CACHE_CONTROL, "private, no-store");
  });
});
