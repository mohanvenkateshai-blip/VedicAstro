import "server-only";

import { getChart, CvceError } from "./cvce";
import { birthInputSchema } from "./validate";
import {
  defaultsToBirthInput,
  parseBirthDefaults,
  type BirthDefaults,
  type SearchParams,
} from "./birth-params";
import type { BirthInput, ChartData } from "./types";

export type ChartLoadResult = {
  defaults: BirthDefaults;
  birth: BirthInput;
  chart: ChartData | null;
  error: string | null;
};

export async function loadChartFromSearchParams(
  sp: SearchParams,
): Promise<ChartLoadResult> {
  const defaults = parseBirthDefaults(sp);
  const birth = defaultsToBirthInput(defaults);

  if (
    Number.isNaN(birth.birth_lat) ||
    Number.isNaN(birth.birth_lon) ||
    Number.isNaN(birth.birth_tz)
  ) {
    return {
      defaults,
      birth,
      chart: null,
      error: "Invalid coordinates — check latitude, longitude, and timezone.",
    };
  }

  try {
    birthInputSchema.parse(birth);
    const chart = await getChart(birth);
    return { defaults, birth, chart, error: null };
  } catch (e) {
    const message =
      e instanceof CvceError
        ? e.message
        : e instanceof Error
          ? e.message
          : "Could not load chart";
    return { defaults, birth, chart: null, error: message };
  }
}
