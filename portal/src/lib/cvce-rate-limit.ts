/**
 * Best-effort per-process protection for the guest-access CVCE proxy.
 *
 * This deliberately preserves unsigned chart exploration. It limits accidental
 * and low-volume abuse before a request receives the server-only CVCE token.
 * Serverless instances do not share this map, so production should retain the
 * CVCE service's own limiter and may add a distributed edge/WAF limit later.
 */

interface Bucket {
  startedAt: number;
  count: number;
}

export interface QuotaResult {
  allowed: boolean;
  retryAfterSeconds: number;
  remaining: number;
}

const buckets = new Map<string, Bucket>();
const MAX_BUCKETS = 10_000;

export function consumeCvceQuota(
  key: string,
  limit: number,
  windowMs: number,
  now = Date.now(),
): QuotaResult {
  let bucket = buckets.get(key);
  if (!bucket || now - bucket.startedAt >= windowMs) {
    if (!bucket && buckets.size >= MAX_BUCKETS) {
      const oldest = [...buckets.entries()].sort(
        (left, right) => left[1].startedAt - right[1].startedAt,
      );
      const pruneCount = Math.max(1, Math.ceil(MAX_BUCKETS / 10));
      for (const [staleKey] of oldest.slice(0, pruneCount)) buckets.delete(staleKey);
    }
    bucket = { startedAt: now, count: 0 };
    buckets.set(key, bucket);
  }

  const elapsed = Math.max(0, now - bucket.startedAt);
  const retryAfterSeconds = Math.max(1, Math.ceil((windowMs - elapsed) / 1000));
  if (bucket.count >= limit) {
    return { allowed: false, retryAfterSeconds, remaining: 0 };
  }

  bucket.count += 1;
  return {
    allowed: true,
    retryAfterSeconds,
    remaining: Math.max(0, limit - bucket.count),
  };
}

export function resetCvceQuotaForTests(): void {
  buckets.clear();
}
