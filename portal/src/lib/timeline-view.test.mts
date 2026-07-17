import assert from "node:assert/strict";
import { describe, it } from "node:test";

// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { ageAt, buildDigest, collapseSuperseded, eraOf, formatTick, packRows, panned, toneOf, viewportFor } from "./timeline-view.ts";

const DAY = 24 * 60 * 60 * 1000;
const NOW = Date.UTC(2026, 6, 15);

function milestone(overrides: Record<string, unknown>) {
  return {
    milestone_id: "m-default",
    direction: "mixed",
    origin: "engine_inference",
    supersedes_milestone_id: null,
    window: {
      start_at: new Date(NOW - 10 * DAY).toISOString(),
      peak_at: null,
      end_at: new Date(NOW + 10 * DAY).toISOString(),
    },
    ...overrides,
  } as never;
}

describe("valence tone", () => {
  it("maps every direction to a tone", () => {
    assert.equal(toneOf({ direction: "favourable" } as never), "good");
    assert.equal(toneOf({ direction: "unfavourable" } as never), "bad");
    assert.equal(toneOf({ direction: "mixed" } as never), "mixed");
    assert.equal(toneOf({ direction: "neutral" } as never), "neutral");
    assert.equal(toneOf({ direction: "not_applicable" } as never), "neutral");
  });
});

describe("viewport math", () => {
  const full = { start: NOW - 4000 * DAY, end: NOW + 4000 * DAY };

  it("centres a zoom span and clamps to the full range", () => {
    const year = viewportFor("year", NOW, full);
    assert.ok(Math.abs(year.end - year.start - 366 * DAY) < DAY);
    const clamped = viewportFor("year", full.start, full);
    assert.equal(clamped.start, full.start);
  });

  it("lifetime returns the full range", () => {
    assert.deepEqual(viewportFor("lifetime", NOW, full), full);
  });

  it("panning keeps the centre inside the full range", () => {
    const year = viewportFor("year", NOW, full);
    const centre = panned(year, 1000, full);
    assert.ok(centre <= full.end - (year.end - year.start) / 2);
  });
});

describe("row packing", () => {
  it("stacks overlapping intervals on separate rows and reuses free rows", () => {
    const items = [
      { id: "a", start: 0, end: 10 },
      { id: "b", start: 5, end: 15 },
      { id: "c", start: 11, end: 20 },
    ];
    const packed = packRows(items, (item) => item.start, (item) => item.end);
    const rowOf = (id: string) => packed.find((entry) => entry.item.id === id)?.row;
    assert.equal(rowOf("a"), 0);
    assert.equal(rowOf("b"), 1);
    assert.equal(rowOf("c"), 0);
  });
});

describe("supersession collapse", () => {
  it("hides corrected records and exposes their history chain", () => {
    const original = milestone({ milestone_id: "m-1" });
    const correction = milestone({ milestone_id: "m-2", supersedes_milestone_id: "m-1" });
    const { visible, historyOf } = collapseSuperseded([original, correction] as never[]);
    assert.deepEqual(visible.map((item: { milestone_id: string }) => item.milestone_id), ["m-2"]);
    assert.deepEqual(historyOf(correction).map((item: { milestone_id: string }) => item.milestone_id), ["m-1"]);
  });
});

describe("age and tick formatting", () => {
  const birth = "1975-04-22T19:15:00";

  it("ageAt returns null before birth and whole years after", () => {
    assert.equal(ageAt(Date.UTC(1970, 0, 1), birth), null);
    assert.equal(ageAt(Date.UTC(1975, 3, 23), birth), 0);
    assert.equal(ageAt(Date.UTC(2026, 6, 15), birth), 51);
  });

  it("formatTick renders in UTC at every zoom span", () => {
    // 2026-01-01T00:30Z formats as Jan 1 only when the formatter pins UTC;
    // a local-zone formatter west of UTC would say Dec 31.
    const instant = Date.UTC(2026, 0, 1, 0, 30);
    const yearSpan = { start: instant - 100 * DAY, end: instant + 100 * DAY };
    assert.match(formatTick(instant, yearSpan), /Jan 1, 2026/);
    const decadeSpan = { start: instant - 2000 * DAY, end: instant + 2000 * DAY };
    assert.match(formatTick(instant, decadeSpan), /Jan 2026/);
    const lifeSpan = { start: instant - 20000 * DAY, end: instant + 20000 * DAY };
    assert.equal(formatTick(instant, lifeSpan), "2026");
  });
});

describe("era digest", () => {
  it("splits records into behind, current and ahead around now", () => {
    const past = milestone({ milestone_id: "past", window: { start_at: new Date(NOW - 40 * DAY).toISOString(), peak_at: null, end_at: new Date(NOW - 20 * DAY).toISOString() } });
    const active = milestone({ milestone_id: "active" });
    const future = milestone({ milestone_id: "future", window: { start_at: new Date(NOW + 20 * DAY).toISOString(), peak_at: null, end_at: new Date(NOW + 40 * DAY).toISOString() } });
    assert.equal(eraOf(past, NOW), "behind");
    assert.equal(eraOf(active, NOW), "current");
    assert.equal(eraOf(future, NOW), "ahead");
    const digest = buildDigest([past, active, future] as never[], [], [], NOW);
    assert.deepEqual(digest.behind.map((entry) => entry.milestone.milestone_id), ["past"]);
    assert.deepEqual(digest.current.map((entry) => entry.milestone.milestone_id), ["active"]);
    assert.deepEqual(digest.ahead.map((entry) => entry.milestone.milestone_id), ["future"]);
  });
});
