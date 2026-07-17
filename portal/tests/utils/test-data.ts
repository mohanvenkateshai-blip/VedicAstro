/**
 * Canonical test data and selectors for the VedicAstro portal E2E suite.
 *
 * Selectors mirror what the components actually render (accessible names
 * first, stable markup second). The chart pages parse `date` + `time`
 * query params (see src/lib/birth-params.ts) — never `dob`.
 */

export const MOHAN_BIRTH_DATA = {
  name: 'Mohan',
  date: '1975-04-22',
  time: '19:15',
  place: 'Mysore',
  lat: 12.2958,
  lon: 76.6394,
  tz: '5.5',
};

export type BirthData = typeof MOHAN_BIRTH_DATA;

export function birthParams(birthData: BirthData = MOHAN_BIRTH_DATA, extraParams: Record<string, string> = {}) {
  return new URLSearchParams({
    date: birthData.date,
    time: birthData.time,
    place: birthData.place,
    lat: String(birthData.lat),
    lon: String(birthData.lon),
    tz: birthData.tz,
    ...extraParams,
  }).toString();
}

export function buildChartUrl(birthData: BirthData = MOHAN_BIRTH_DATA, extraParams: Record<string, string> = {}) {
  return `/chart?${birthParams(birthData, extraParams)}`;
}

export function buildTimelineUrl(birthData: BirthData = MOHAN_BIRTH_DATA) {
  return `/chart/timeline?${birthParams(birthData)}`;
}

export function buildTransitsUrl(birthData: BirthData = MOHAN_BIRTH_DATA) {
  return `/chart/transits?${birthParams(birthData)}`;
}

export const TIMEOUTS = {
  /** First navigation may compile the route in dev and warm the CVCE engine. */
  pageLoad: 60000,
  chartLoad: 30000,
  apiCall: 15000,
  animation: 300,
};

export const SELECTORS = {
  birthForm: {
    name: 'input[name="name"]',
    date: 'input[name="date"]',
    time: 'input[name="time"]',
    place: 'input[name="place"]',
    lat: 'input[name="lat"]',
    lon: 'input[name="lon"]',
    tz: 'input[name="tz"]',
    submit: 'form button[type="submit"]',
  },
  chart: {
    /** Kundali SVGs declare role="img" with a "…kundali…" label. */
    kundaliSvg: 'svg[role="img"][aria-label*="kundali" i]',
    planetsTable: 'table[aria-label="Planetary positions"]',
  },
  timeline: {
    addEventButton: 'button:has-text("Add event")',
    eventDialog: '[role="dialog"][aria-labelledby="add-event-title"]',
    detailSheet: '[role="dialog"][aria-labelledby="milestone-title"]',
    minimap: '[role="slider"][aria-label*="Lifetime overview"]',
    canvas: '[role="group"][aria-label*="Person timeline canvas"]',
    viewToggle: '[role="group"][aria-label="Timeline view"]',
    zoomGroup: '[role="group"][aria-label="Timeline zoom"]',
    travelGroup: '[role="group"][aria-label="Move through time"]',
    valenceGroup: '[role="group"][aria-label="Filter by valence"]',
  },
  theme: {
    /** ThemeToggle persists to localStorage key "va-theme". */
    storageKey: 'va-theme',
  },
};
