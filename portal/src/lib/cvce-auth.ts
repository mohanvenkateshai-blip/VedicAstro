import "server-only";

const SERVICE_TOKEN_HEADER = "x-cvce-service-token";

/**
 * Headers for a protected portal-to-CVCE request.
 *
 * `null` means production is missing its required server-only token. Local
 * development may deliberately run without auth against a local CVCE.
 */
export function cvceServiceHeaders(json = false): Record<string, string> | null {
  const token = process.env.CVCE_SERVICE_TOKEN?.trim();
  if (!token && process.env.NODE_ENV === "production") return null;
  return {
    ...(json ? { "content-type": "application/json" } : {}),
    ...(token ? { [SERVICE_TOKEN_HEADER]: token } : {}),
  };
}
