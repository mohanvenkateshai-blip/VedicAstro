/**
 * Classical Navagraha (planet) and elemental (bhuta) color associations,
 * used consistently wherever a planet or sign needs to carry visual meaning
 * beyond the app's single neutral accent — kundali charts, dasha timelines,
 * yoga panels, ephemeris plots.
 *
 * Planet hues follow the traditional associations (Sun=copper-red,
 * Moon=pearl, Mars=blood-red, Mercury=emerald, Jupiter=gold, Venus=diamond/
 * rose-white, Saturn=indigo-black, Rahu=smoke, Ketu=maroon-grey), tuned for
 * legible contrast on a dark chart surface rather than literal pigment.
 */

export const PLANET_COLORS: Record<string, string> = {
  Sun: "#f97316", // copper-orange
  Moon: "#cbd5f5", // pearl / silvery blue-white
  Mars: "#ef4444", // blood-red
  Mercury: "#22c55e", // emerald
  Jupiter: "#eab308", // gold
  Venus: "#f9a8d4", // diamond / rose-white
  Saturn: "#818cf8", // indigo
  Rahu: "#94a3b8", // smoke-grey
  Ketu: "#c2410c", // maroon-brown
};

export function planetColor(planet: string): string {
  return PLANET_COLORS[planet] ?? "var(--color-text-muted)";
}

/** Fire / Earth / Air / Water, by sign index 0=Aries..11=Pisces. */
export const SIGN_ELEMENTS = [
  "fire", "earth", "air", "water", "fire", "earth",
  "air", "water", "fire", "earth", "air", "water",
] as const;

export type Element = (typeof SIGN_ELEMENTS)[number];

export const ELEMENT_COLORS: Record<Element, string> = {
  fire: "#f97316", // warm orange-red
  earth: "#b45309", // olive-brown
  air: "#38bdf8", // sky
  water: "#2563eb", // deep blue
};

export function elementOf(signIndex: number): Element {
  return SIGN_ELEMENTS[signIndex % 12];
}

export function elementColor(signIndex: number): string {
  return ELEMENT_COLORS[elementOf(signIndex)];
}
