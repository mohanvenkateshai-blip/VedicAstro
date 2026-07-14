import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";

// @ts-expect-error -- Node's built-in TypeScript test runner requires an explicit .ts extension.
import { consumeCvceQuota, resetCvceQuotaForTests } from "./cvce-rate-limit.ts";

describe("guest CVCE proxy quota", () => {
  beforeEach(() => resetCvceQuotaForTests());

  it("allows a bounded burst and then returns a retry interval", () => {
    assert.equal(consumeCvceQuota("post:guest-a", 2, 60_000, 1_000).allowed, true);
    assert.equal(consumeCvceQuota("post:guest-a", 2, 60_000, 1_001).allowed, true);
    assert.deepEqual(consumeCvceQuota("post:guest-a", 2, 60_000, 1_002), {
      allowed: false,
      retryAfterSeconds: 60,
      remaining: 0,
    });
  });

  it("isolates clients and resets after the window", () => {
    assert.equal(consumeCvceQuota("get:guest-a", 1, 1_000, 10_000).allowed, true);
    assert.equal(consumeCvceQuota("get:guest-a", 1, 1_000, 10_500).allowed, false);
    assert.equal(consumeCvceQuota("get:guest-b", 1, 1_000, 10_500).allowed, true);
    assert.equal(consumeCvceQuota("get:guest-a", 1, 1_000, 11_000).allowed, true);
  });
});
