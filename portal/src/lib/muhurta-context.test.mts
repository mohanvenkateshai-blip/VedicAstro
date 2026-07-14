import assert from "node:assert/strict";
import { describe, it } from "node:test";

// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { parseMuhurtaMoment } from "./muhurta-context.ts";

describe("native Muhurta moment context", () => {
  it("derives the election offset from the IANA timezone at that instant", () => {
    const summer = parseMuhurtaMoment({
      m_date: "2026-07-14",
      m_time: "12:30",
      m_place: "Dublin, Ireland",
      m_lat: "53.3498",
      m_lon: "-6.2603",
      m_zone: "Europe/Dublin",
    });
    assert.equal(summer.error, null);
    assert.equal(summer.context?.effectiveInstant, "2026-07-14T12:30:00+01:00");
    assert.equal(summer.context?.utcOffsetHours, 1);

    const winter = parseMuhurtaMoment({
      m_date: "2026-01-14",
      m_time: "12:30",
      m_place: "Dublin, Ireland",
      m_lat: "53.3498",
      m_lon: "-6.2603",
      m_zone: "Europe/Dublin",
    });
    assert.equal(winter.context?.utcOffsetHours, 0);
  });

  it("keeps natal and election parameters separate", () => {
    const result = parseMuhurtaMoment({
      date: "1975-04-22",
      lat: "12.2958",
      lon: "76.6394",
      m_date: "2026-07-14",
      m_time: "09:15",
      m_place: "Dublin",
      m_lat: "53.3498",
      m_lon: "-6.2603",
      m_zone: "Europe/Dublin",
    });
    assert.equal(result.context?.date, "2026-07-14");
    assert.equal(result.context?.latitude, 53.3498);
    assert.equal("birth_lat" in (result.context ?? {}), false);
  });

  it("rejects a DST gap and incomplete context", () => {
    assert.match(
      parseMuhurtaMoment({
        m_date: "2026-03-29",
        m_time: "01:30",
        m_place: "Dublin",
        m_lat: "53.3498",
        m_lon: "-6.2603",
        m_zone: "Europe/Dublin",
      }).error ?? "",
      /does not exist/,
    );
    assert.match(parseMuhurtaMoment({ m_date: "2026-07-14" }).error ?? "", /time is required/);
  });

  it("never converts missing coordinates into zero coordinates", () => {
    const base = {
      m_date: "2026-07-14",
      m_time: "09:15",
      m_place: "Dublin",
      m_zone: "Europe/Dublin",
    };
    assert.match(parseMuhurtaMoment({ ...base, m_lon: "-6.2603" }).error ?? "", /latitude is required/);
    assert.match(parseMuhurtaMoment({ ...base, m_lat: "53.3498" }).error ?? "", /longitude is required/);
  });

  it("preserves an explicit DST-overlap occurrence", () => {
    const base = {
      m_date: "2026-10-25",
      m_time: "01:30",
      m_place: "Dublin",
      m_lat: "53.3498",
      m_lon: "-6.2603",
      m_zone: "Europe/Dublin",
    };
    assert.match(parseMuhurtaMoment(base).error ?? "", /occurs twice/);
    assert.equal(
      parseMuhurtaMoment({ ...base, m_disambiguation: "earlier" }).context?.effectiveInstant,
      "2026-10-25T01:30:00+01:00",
    );
    assert.equal(
      parseMuhurtaMoment({ ...base, m_disambiguation: "later" }).context?.effectiveInstant,
      "2026-10-25T01:30:00+00:00",
    );
  });
});
