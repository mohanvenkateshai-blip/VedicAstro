import assert from "node:assert/strict";
import { describe, it } from "node:test";

// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { buildTransitObservationRequest, resolveZonedLocalInstants, zonedLocalToOffsetIso } from "./transit-context.ts";

describe("transit observation instant", () => {
  it("uses Ireland summer and winter offsets from the named timezone", () => {
    assert.equal(
      zonedLocalToOffsetIso("2026-07-14", "12:30", "Europe/Dublin"),
      "2026-07-14T12:30:00+01:00",
    );
    assert.equal(
      zonedLocalToOffsetIso("2026-01-14", "12:30", "Europe/Dublin"),
      "2026-01-14T12:30:00+00:00",
    );
  });

  it("rejects Ireland's nonexistent spring-forward civil time", () => {
    assert.throws(
      () => zonedLocalToOffsetIso("2026-03-29", "01:30", "Europe/Dublin"),
      /does not exist/,
    );
  });

  it("requires an explicit occurrence for Ireland's repeated fall-back civil time", () => {
    const candidates = resolveZonedLocalInstants("2026-10-25", "01:30", "Europe/Dublin");

    assert.deepEqual(candidates, [
      {
        instant: "2026-10-25T01:30:00+01:00",
        utcInstant: "2026-10-25T00:30:00.000Z",
        offset: "+01:00",
        disambiguation: "earlier",
      },
      {
        instant: "2026-10-25T01:30:00+00:00",
        utcInstant: "2026-10-25T01:30:00.000Z",
        offset: "+00:00",
        disambiguation: "later",
      },
    ]);
    assert.throws(
      () => zonedLocalToOffsetIso("2026-10-25", "01:30", "Europe/Dublin"),
      /occurs twice/,
    );
    assert.equal(
      zonedLocalToOffsetIso("2026-10-25", "01:30", "Europe/Dublin", "earlier"),
      "2026-10-25T01:30:00+01:00",
    );
    assert.equal(
      zonedLocalToOffsetIso("2026-10-25", "01:30", "Europe/Dublin", "later"),
      "2026-10-25T01:30:00+00:00",
    );
  });

  it("builds transit fields without copying Mysuru natal coordinates", () => {
    const request = buildTransitObservationRequest({
      date: "2026-07-14",
      time: "12:30",
      place: "Dublin, Ireland",
      latitude: 53.3498,
      longitude: -6.2603,
      timezone: "Europe/Dublin",
    });

    assert.deepEqual(request, {
      transit_instant: "2026-07-14T12:30:00+01:00",
      transit_place: "Dublin, Ireland",
      transit_lat: 53.3498,
      transit_lon: -6.2603,
      transit_timezone: "Europe/Dublin",
      transit_disambiguation: "exact",
    });
    assert.equal("birth_lat" in request, false);
    assert.equal("birth_lon" in request, false);
  });
});
