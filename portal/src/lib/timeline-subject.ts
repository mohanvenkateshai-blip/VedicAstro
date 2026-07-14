import "server-only";

import { bindTimelineSubject, timelineSubjectIsOwnedBy } from "./timeline-subject-binding";
import type { BirthInput } from "./types";

/** Stable, de-identified, owner-bound identity for an unsaved chart. Raw birth
 * fields remain request inputs but never become the persisted subject reference.
 * The HMAC prevents a caller from manufacturing another owner's subject id. */
export function timelineSubjectId(birth: BirthInput, owner: string): string {
  return bindTimelineSubject(birth, owner);
}

/** Constant-time owner-prefix check for write endpoints that do not carry birth
 * inputs. Exact chart identity is recomputed on query/detail endpoints. */
export function timelineSubjectBelongsToOwner(subjectId: string, owner: string): boolean {
  return timelineSubjectIsOwnedBy(subjectId, owner);
}
