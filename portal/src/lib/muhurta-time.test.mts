import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error -- Node's built-in TypeScript test runner requires the extension.
import { formatMuhurtaWindowTime } from "./muhurta-time.ts";

test("formats canonical CVCE window strings without producing NaN", () => {
  assert.equal(formatMuhurtaWindowTime("17:41:53"), "17:41");
  assert.equal(formatMuhurtaWindowTime("09:32:40"), "09:32");
  assert.equal(formatMuhurtaWindowTime("13:37:16"), "13:37");
});

test("continues to format legacy decimal-hour values", () => {
  assert.equal(formatMuhurtaWindowTime(17.7), "17:42");
});

test("renders invalid values safely", () => {
  assert.equal(formatMuhurtaWindowTime("not-a-time"), "Unavailable");
  assert.equal(formatMuhurtaWindowTime(Number.NaN), "Unavailable");
});
