import "server-only";

/** Missing or malformed configuration intentionally keeps research disabled. */
export function isNativeMuhurtaResearchEnabled(): boolean {
  return ["1", "true", "yes", "on"].includes(
    process.env.NATIVE_MUHURTA_RESEARCH_ENABLED?.trim().toLowerCase() ?? "",
  );
}
