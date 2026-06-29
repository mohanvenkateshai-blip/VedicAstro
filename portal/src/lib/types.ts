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
  transit_intelligence?: TransitIntelligence | null;
  transit_citations?: TransitCitation[];
  yoga_citations?: YogaCitation[];
  text_conflicts?: TextConflict[];
  god_node_insights?: GodNodeInsight[];
  panchanga_insights?: PanchangaInsight[];
  natal_insights?: PanchangaInsight[];
  muhurta_citations?: MuhurtaCitation[];
  graph_stats?: {
    nodes: number;
    links: number;
    hyperedges?: number;
    communities?: number;
    source_files?: number;
  };
}

export interface TransitIntelligence {
  date: string;
  janma_rashi?: string | null;
  overall_verdict: string;
  overall_score: number;
  day_summary: string;
  dasha_context?: string | null;
  moorthy_note?: string | null;
  tara_note?: string | null;
  planets: PlanetTransitAnalysis[];
  top_drivers: string[];
}

export interface PlanetTransitAnalysis {
  planet: string;
  rashi: string;
  nakshatra: string;
  house_from_janma?: number | null;
  retrograde: boolean;
  final_verdict: string;
  score: number;
  primary_driver: string;
  root_cause: string;
  aggravating: string[];
  mitigating: string[];
  positive_impact: string[];
  negative_impact: string[];
  factors: TransitFactor[];
  summary: string;
  classical_basis: string[];
}

export interface TransitFactor {
  role: string;
  weight: number;
  summary: string;
  source?: string;
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
  graph_matches?: GraphMatch[];
}

export interface GraphMatch {
  id: string;
  label: string;
  score: number;
  community: number;
  source_file?: string;
}

export interface MuhurtaCitation {
  name: string;
  nature: string;
  source?: string;
  detail?: string;
}

export interface DayWindows {
  rahu_kalam: { start: number; end: number };
  yamaganda: { start: number; end: number };
  gulika: { start: number; end: number };
  sunrise?: number;
  sunset?: number;
}

export interface DashaLadderRow {
  level: number;
  levelLabel: string;
  lord: string;
  lords: string[];
  start: string;
  end: string;
  durationYears: number;
}

/** One key transit shown inside a Dasha prediction panel. */
export interface KeyTransit {
  planet: string;
  rashi: string;
  house_from_moon: number | null;
  verdict: string;
  impact: string;
}

/**
 * Transit-fused prediction for one Maha–Antar period.
 * Produced by /dasha-predict; merged into DashaNode.prediction on the portal.
 */
export interface DashaPrediction {
  combined_verdict: "shubh" | "ashubh";
  combined_score: number;
  dasha_score: number;
  transit_score: number;
  snapshot_date: string;
  summary: string;
  key_transits: KeyTransit[];
  career: string[];
  wealth: string[];
  health: string[];
  family: string[];
  caution: string[];
}

export interface DashaPredictions {
  predictions: Record<string, DashaPrediction>;
}

/** A single fructification window — when dasha events actually manifest. */
export interface FructificationWindow {
  start: string;
  end: string;
  duration_months: number;
  ref_label: string;
  saturn: { house: number; sign: string };
  jupiter: { house: number; sign: string };
  sav_bindus: number | null;
  strength: "exceptional" | "strong" | "moderate" | "limited";
  domains: string[];
  narrative: string;
  score: number;
}

/** Full /fructification response. */
export interface FructificationResult {
  system: string;
  maha_lord: string;
  antar_lord: string;
  antar_start: string;
  antar_end: string;
  janma_rashi: string;
  natal_lagna: string;
  reference_points: { label: string; sign: string }[];
  progressed_lagna: {
    contributing_nak: number;
    contributing_nak_name: string;
    star_lord: string;
    cycle: number;
    progressed_lagna: string;
  } | null;
  windows: FructificationWindow[];
  total_windows: number;
  source: string;
}

/** One data point in the Dasha time-series chart. */
export interface DashaSeriesPoint {
  date: string;
  transit_score: number;
  combined_score: number;
  lagna_transit_score: number;
  lagna_combined_score: number;
  planet_scores: Record<string, number>;
  verdict: "shubh" | "ashubh";
  key_planet: string | null;
  key_note: string | null;
}

/** A slow-planet sign change that explains a peak or dip. */
export interface DashaSeriesEvent {
  date: string;
  planet: string;
  from_rashi: string;
  to_rashi: string;
  house_from_moon: number | null;
  transit_score_at_event: number;
  note: string;
}

/** Full series response from /dasha-series. */
export interface DashaSeriesData {
  maha_lord: string;
  antar_lord: string;
  dasha_score: number;
  series: DashaSeriesPoint[];
  events: DashaSeriesEvent[];
  stats: {
    shubh_months: number;
    ashubh_months: number;
    total_months: number;
    peak: { date: string; score: number };
    trough: { date: string; score: number };
    lagna_peak: { date: string; score: number };
    lagna_trough: { date: string; score: number };
  };
}

export interface DashaNode {
  level: number;
  lord: string;
  start: string;
  end?: string;
  durationYears: number;
  subPeriods: DashaNode[];
  verdict?: "shubh" | "ashubh" | "mixed" | null;
  score?: number | null;
  prediction?: DashaPrediction | null;
}

export interface DashaDeepData {
  current: string[];
  currentLadder?: DashaLadderRow[];
  balanceAtBirth?: { lord: string; years: number; months: number; days: number; label: string };
  antardashaTable?: { maha: string; antara: string; start: string; durationYears: number }[];
  dashaTree: DashaNode[];
}

export interface DashaIntelligence {
  maha_lord: string;
  antar_lord: string;
  pratyantar_lord?: string | null;
  maha_start: string;
  maha_end: string;
  antar_start: string;
  antar_end: string;
  lagna?: string | null;
  janma_rashi?: string | null;
  final_verdict: string;
  score: number;
  primary_driver: string;
  root_cause: string;
  maha_houses: number[];
  antar_houses: number[];
  aggravating: string[];
  mitigating: string[];
  profession: string[];
  wealth: string[];
  health: string[];
  family: string[];
  caution: string[];
  factors: { role: string; weight: number; summary: string }[];
  summary: string;
  classical_basis: string[];
}

export interface SavAnnotated {
  sign: string;
  bindus: number;
  band: "excellent" | "good" | "standard" | "depleted";
}

export interface AshtakavargaFacts {
  bav: Record<string, number[]>;
  sav: number[];
  sav_annotated: SavAnnotated[];
  planet_totals: Record<string, number>;
  total: number;
}

export interface ForecastPeriod {
  maha: string;
  antar: string;
  start: string;
  end: string;
  durationYears: number;
  isCurrent: boolean;
  verdict: "shubh" | "ashubh" | "mixed";
  score: number;
  summary: string;
  profession: string[];
  wealth: string[];
  health: string[];
  family: string[];
  caution: string[];
}

export interface TimingMerge {
  verdict: "shubh" | "ashubh" | "mixed";
  label: string;
  score: number;
  dasha_score: number;
  transit_verdict: string;
  reasons: string[];
}

export interface ShubhDay {
  date: string;
  summary: string;
  score: number;
  top_drivers: string[];
}

export interface ReportFacts {
  schemaVersion: string;
  meta: {
    name?: string | null;
    birth_datetime: string;
    query_date: string;
    ayanamsa: string;
    engine: string;
  };
  natal: {
    lagna: { rashi?: string; degree?: string; nakshatra?: string; pada?: number };
    moon: { rashi?: string; nakshatra?: string; pada?: number };
    planets: {
      planet: string;
      rashi?: string;
      degree?: string;
      nakshatra?: string;
      pada?: number;
      dignity?: string;
      retrograde?: boolean;
    }[];
  };
  dashas: {
    balanceAtBirth: { lord: string; label: string };
    current: string[];
    currentLadder: DashaLadderRow[];
    antardashaTable: { maha: string; antara: string; start: string; durationYears: number }[];
  };
  dasha_intelligence?: DashaIntelligence | null;
  transit_intelligence?: TransitIntelligence | null;
  next_shubh_days?: ShubhDay[] | null;
  timing_merge?: TimingMerge | null;
  forecast?: ForecastPeriod[] | null;
  yogas?: {
    activeCount?: number;
    totalChecked?: number | null;
    yogas?: Record<string, { name?: string; definition?: string; prediction?: string }>;
  } | null;
  ashtakavarga?: AshtakavargaFacts | null;
  shadbala?: Record<string, Record<string, number | null>> | null;
  panchanga?: Record<string, unknown> | null;
  narration?: {
    prose?: string;
    model?: string;
    generated?: boolean;
    status?: string;
    reason?: string;
  } | null;
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
