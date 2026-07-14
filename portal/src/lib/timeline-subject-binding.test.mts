import assert from "node:assert/strict";
import { describe, it } from "node:test";

// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { bindTimelineSubject, timelineSubjectIsOwnedBy } from "./timeline-subject-binding.ts";

const birth = {
  birth_datetime: "1975-04-22T19:15:00",
  birth_lat: 12.2958,
  birth_lon: 76.6394,
  birth_tz: 5.5,
  ayanamsa: "LAHIRI",
};

describe("timeline subject owner boundary", () => {
  it("is deterministic for the same chart and owner", () => {
    assert.equal(bindTimelineSubject(birth, "guest-a"), bindTimelineSubject(birth, "guest-a"));
  });

  it("separates identical birth data across owners", () => {
    const ownerA = bindTimelineSubject(birth, "guest-a");
    const ownerB = bindTimelineSubject(birth, "guest-b");
    assert.notEqual(ownerA, ownerB);
    assert.equal(timelineSubjectIsOwnedBy(ownerA, "guest-a"), true);
    assert.equal(timelineSubjectIsOwnedBy(ownerA, "guest-b"), false);
  });

  it("rejects caller-invented and malformed subject identifiers", () => {
    assert.equal(timelineSubjectIsOwnedBy("chart_public", "guest-a"), false);
    assert.equal(timelineSubjectIsOwnedBy(`chart_${"0".repeat(32)}_${"0".repeat(64)}`, "guest-a"), false);
  });
});
