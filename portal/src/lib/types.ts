/**
 * TypeScript mirror of the canonical chart_data contract
 * (VedicAstro/docs/chart_data.schema.json). Keep in lockstep with the schema.
 */

export type SignIndex = number; // 0..11 (Aries..Pisces)

export type Dignity = "exalted" | "debilitated" | "own" | "neutral" | null;

export interface Body {
  planet: string;
  longitude: number;
  signIndex: SignIndex;
  rashi: string;
  degInSign?: number;
  degLabel?: string;
  nakIndex?: number;
  nakshatra: string;
  pada: number;
  retro?: boolean;
  dignity?: Dignity;
  combust?: boolean;
}

export interface Lagna {
  rashi: string;
  signIndex: SignIndex;
  nakshatra: string;
  pada: number;
  degInSign?: number;
  degLabel?: string;
}

export interface Varga {
  name: string;
  signs: Record<string, SignIndex>; // planet | "Lagna" -> sign index
}

export interface Ashtakavarga {
  sav: number[]; // 12 entries, totals 337
  bav: Record<string, number[]>; // contributor -> 12 bindus
  lagnaSignIdx: SignIndex;
}

export interface DashaPeriod {
  maha: string;
  antara: string | null;
  start: string;
  durationYears: number;
}

export interface ChartData {
  schemaVersion: string;
  meta?: {
    name?: string | null;
    birth_datetime?: string;
    birth_lat?: number;
    birth_lon?: number;
    birth_tz?: number;
    engine?: string;
  };
  ayanamsa: string;
  jd: number;
  ascendant: Body;
  lagna: Lagna;
  planets: Body[];
  natalSign: Record<string, SignIndex>;
  vargas: Record<string, Varga>;
  ashtakavarga: Ashtakavarga;
  dashas?: { current?: unknown[] | null; periods?: DashaPeriod[] } | null;
  shadbala?: Record<string, Record<string, number | null>> | null;
  yogas?: { activeCount?: number; totalChecked?: number | null; yogas?: Record<string, unknown> } | null;
  panchanga?: Record<string, unknown> | null;
  errors?: Record<string, string>;
}

export interface BirthInput {
  birth_datetime: string; // local civil ISO 8601, e.g. 1975-04-22T19:15:00
  birth_lat: number;
  birth_lon: number;
  birth_tz: number; // hours offset from UTC
  name?: string;
  ayanamsa?: string;
}

// ── Muhurta / prediction (engine /predict) ──────────────────────────────────
export type Verdict = "shubh" | "ashubh" | "neutral" | string;

export interface Limb {
  name: string;
  verdict?: Verdict;
  [k: string]: unknown;
}

export interface TaraBalam {
  name: string;
  description?: string;
  verdict?: Verdict;
  paryaya?: string;
}

export interface MuhurtaPanchanga {
  tithi: Limb & { paksha?: string; num?: number; group?: string };
  vaar: string;
  nakshatra: Limb & { nature?: string; lord?: string };
  yoga: Limb & { nature?: string };
  karana: Limb;
  sunrise?: number;
  sunset?: number;
}

export interface MuhurtaResult {
  date: string;
  time: string;
  overall_verdict: string;
  overall_score: number;
  summary: string;
  panchanga: MuhurtaPanchanga | null;
  gochar: {
    overall_verdict?: string;
    synthesis?: string;
    sade_sati?: unknown;
    tara_balam?: TaraBalam | null;
  } | null;
  dasha: {
    mahadasha?: { planet: string; start?: string; end?: string } | null;
    antardasha?: { planet: string; start?: string; end?: string } | null;
    summary?: string;
  } | null;
  ashtakavarga: {
    moon_transit_bindus?: number;
    moon_transit_verdict?: Verdict;
    moon_transit_band?: string;
  } | null;
  warnings: string[];
  transit_summary?: string;
  graph_enhancements?: GraphEnhancements | null;
}

export interface GraphEnhancements {
  transit_citations?: TransitCitation[];
  yoga_citations?: YogaCitation[];
  text_conflicts?: TextConflict[];
  god_node_insights?: GodNodeInsight[];
  panchanga_insights?: PanchangaInsight[];
  graph_stats?: { nodes: number; links: number; hyperedges: number; communities: number };
}

export interface TransitCitation {
  planet: string;
  rashi: string;
  house_from_janma?: number | null;
  verdict?: string;
  vedha_pairs?: string;
  vedha_source?: string;
  classical_effects?: { description?: string; effect?: string; source?: string; confidence?: number; relation?: string }[];
}

export interface YogaCitation {
  yoga: string;
  label?: string;
  source_file?: string;
  required_planets?: string[];
  hyperedge_groups?: { label: string; members: string[]; confidence: string }[];
  descriptions?: string[];
}

export interface TextConflict {
  source: string;
  target: string;
  source_file?: string;
}

export interface GodNodeInsight {
  god_node: string;
  degree: number;
  community?: number;
  connected_concepts?: string[];
}

export interface PanchangaInsight {
  type: string;
  value: string;
  graph_matches?: { id: string; label: string; score: number; community: number }[];
}

export interface DayWindows {
  rahu_kalam: { start: number; end: number };
  yamaganda: { start: number; end: number };
  gulika: { start: number; end: number };
  sunrise?: number;
  sunset?: number;
}

export const RASHIS = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
] as const;

export const RASHI_SHORT = [
  "Ar", "Ta", "Ge", "Ca", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi",
] as const;

/** Short glyph-ish planet codes for chart cells. */
export const PLANET_SHORT: Record<string, string> = {
  Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju",
  Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke", Lagna: "La", Ascendant: "As",
};
