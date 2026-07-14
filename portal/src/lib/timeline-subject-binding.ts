import { createHmac, timingSafeEqual } from "node:crypto";
import type { BirthInput } from "./types";

function subjectSecret(): string {
  const configured = process.env.TIMELINE_SUBJECT_SECRET ?? process.env.AUTH_SECRET;
  if (configured) return configured;
  if (process.env.NODE_ENV !== "production") return "vedicastro-local-timeline-subject-v1";
  throw new Error("Timeline owner binding is not configured");
}

function ownerTag(owner: string): string {
  return createHmac("sha256", subjectSecret()).update(`owner\0${owner}`).digest("hex").slice(0, 32);
}

export function bindTimelineSubject(birth: BirthInput, owner: string): string {
  const canonical = JSON.stringify({
    ayanamsa: birth.ayanamsa ?? "LAHIRI",
    birth_datetime: birth.birth_datetime,
    birth_lat: birth.birth_lat,
    birth_lon: birth.birth_lon,
    birth_tz: birth.birth_tz,
  });
  const digest = createHmac("sha256", subjectSecret())
    .update(`chart\0${owner}\0${canonical}`)
    .digest("hex");
  return `chart_${ownerTag(owner)}_${digest}`;
}

export function timelineSubjectIsOwnedBy(subjectId: string, owner: string): boolean {
  const expected = Buffer.from(ownerTag(owner), "utf8");
  const actualTag = subjectId.match(/^chart_([0-9a-f]{32})_[0-9a-f]{64}$/)?.[1];
  if (!actualTag) return false;
  const actual = Buffer.from(actualTag, "utf8");
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}
