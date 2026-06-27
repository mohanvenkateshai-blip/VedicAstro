/**
 * Browser-safe CVCE access via the portal's API proxy.
 * Never call Fly.io directly from client components — cold starts and
 * long-running dasha trees exceed browser patience.
 */

export class CvceClientError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "CvceClientError";
  }
}

const CLIENT_TIMEOUT_MS = 120_000;

export async function postCvce<T>(path: string, body: unknown): Promise<T> {
  const normalized = path.replace(/^\/+/, "");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CLIENT_TIMEOUT_MS);

  try {
    const res = await fetch(`/api/cvce/${normalized}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new CvceClientError(
        detail ? `Server returned ${res.status}` : `Server returned ${res.status}`,
        res.status,
      );
    }

    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof CvceClientError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new CvceClientError(
        "The calculation engine is taking too long — it may be waking from sleep. Please retry.",
      );
    }
    throw new CvceClientError(
      e instanceof Error ? e.message : "Failed to reach the calculation engine",
    );
  } finally {
    clearTimeout(timer);
  }
}
