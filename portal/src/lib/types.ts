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
  rules_source?: string;
  muhurta_yogas?: {
    overall?: string;
    score?: number;
    summary?: string;
    active?: Array<{
      name?: string;
      nature?: string;
      detail?: string;
      source?: string;
      strength?: number;
    }>;
  } | null;
  calculation_context?: {
    request_id: string;
    engine: string;
    backend: string;
    backend_version?: string;
    engine_version: string;
    ayanamsa: string;
    calculation_path: string;
    fallback_used: boolean;
  };
  election_context?: {
    instant: string;
    utc_instant: string;
    local_datetime: string;
    place: string;
    latitude: number;
    longitude: number;
    timezone: string;
    timezone_source: string;
    disambiguation: string;
    utc_offset_hours: number;
    jd: number;
  };
  natal_context?: {
    birth_datetime: string;
    birth_latitude: number;
    birth_longitude: number;
    birth_timezone_offset_hours: number;
    ayanamsa: string;
    jd: number;
    identity_verified: boolean;
  };
  windows?: DayWindows;
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

export interface DashaGraphCitation {
  id: string;
  label: string;
  description?: string;
  source_file?: string;
  source_location?: string;
}

export interface SignDashaPeriod {
  maha?: string | null;
  antara?: string | null;
  start?: string;
  end?: string;
  years?: number;
  isCurrent?: boolean;
}

export interface SignDashaBlock {
  status?: string;
  method?: string;
  maha?: string | null;
  antara?: string | null;
  mahaStart?: string | null;
  mahaEnd?: string | null;
  periods?: SignDashaPeriod[];
  graph_citations?: DashaGraphCitation[];
  ladder?: { levelLabel: string; lord?: string | null; start?: string | null; end?: string | null }[];
}

export interface KakshaTransit {
  planet: string;
  sign: string;
  degreeInSign: number;
  kakshaIndex: number;
  kakshaLord: string;
  binduActive: boolean;
  savBindus: number;
  verdict: string;
}

export interface KakshaBlock {
  status?: string;
  refinement?: string;
  summary?: string;
  transits?: KakshaTransit[];
  lagnaSign?: string | null;
  lagnaKakshas?: { index: number; lord: string; rangeDeg: string; binduActive: boolean }[];
}

export interface AlternateDashas {
  chara?: SignDashaBlock | null;
  kalachakra?: SignDashaBlock | null;
  kaksha?: KakshaBlock | null;
  yogini?: SignDashaBlock | null;
  ashtottari?: SignDashaBlock | null;
}

export interface DayWindows {
  rahu_kalam: { start: number | string; end: number | string };
  yamaganda: { start: number | string; end: number | string };
  gulika: { start: number | string; end: number | string };
  sunrise?: number | string;
  sunset?: number | string;
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

// ── Kalachakra Dasha (86y nakshatra-pada wheel; BPHS Vol.2 Ch.46/49) ────────

export interface KalachakraLeapStrength {
  sign: string;
  bindus: number;
  band: "strong" | "good" | "neutral" | "weak";
  verdict: "positive_potential" | "mixed" | "challenging";
}

export interface KalachakraTravelDirection {
  favorable: string[];
  unfavorable: string[];
  citation: string;
}

export interface KalachakraLeapInfo {
  isLeap: true;
  type: "frog_leap" | "lions_leap" | "monkey_leap";
  label: string;
  direction: "forward" | "backward";
  step: number;
  /** false when this Gati's Frog/Lion/Monkey label isn't classically verified
   * for the dhasa_method that produced it (e.g. Raghavacharya's navamsa
   * method) — the geometric detection still applies, but BPHS Vol.2 Ch.46's
   * naming is only established for the PVR/book method. */
  verified?: boolean;
  /** Ashtakavarga (SAV)-based positive-potential-vs-challenging verdict for
   * the leaping sign, per the handbook's modulating-factors table. */
  strength?: KalachakraLeapStrength;
  /** Favorable/unfavorable travel directions for this exact sign transition —
   * only present for the 6 (from,to) pairs PVR Rao's tutorial documents
   * (p.12); omitted (not guessed) for all other transitions. */
  travelDirection?: KalachakraTravelDirection | null;
}

export interface KalachakraArgala {
  givers: string[];
  obstructors: string[];
  occupants: string[];
  ownLordPresent: boolean;
  maleficOccupant: string[];
  verdict: "boosted" | "obstructed" | "neutral";
  citation: string;
}

export interface KalachakraSignInterpretation {
  signIndex: number;
  sign: string;
  argala: KalachakraArgala;
  yogakaraka: string | null;
  karakas: string[];
  isLagnaLordSign: boolean;
}

export interface KalachakraLagnaLordAffliction {
  planet: string | null;
  afflicted: boolean;
  reasons: string[];
}

export interface KalachakraMoonNavamsaPoint {
  signIndex: number | null;
  sign: string | null;
}

export interface KalachakraBirthNakshatra {
  moonLongitude: number;
  nakshatra: string;
  nakshatraIndex: number;
  pada: number;
  padaIndex: number;
  remainderDeg: number;
  kcIndex: number;
  kcGroupName: string;
  direction: string;
  isSavya: boolean;
}

export interface KalachakraCycleSign {
  index: number;
  sign: string;
  signIndex: number;
  years: number;
  leapFromPrevious: KalachakraLeapInfo | null;
}

export interface KalachakraCycle {
  kcIndex: number;
  padaIndex: number;
  signs: KalachakraCycleSign[];
  totalYears: number;
  dehaRasi: string;
  jeevaRasi: string;
  hasActiveLeap: boolean;
}

export interface KalachakraLadderRow {
  level: number;
  levelLabel: string;
  sign: string;
  signIndex: number;
  signs: string[];
  start: string;
  end: string;
}

export interface KalachakraNode {
  level: number;
  sign: string;
  signIndex: number;
  start: string;
  end?: string;
  durationYears: number;
  leapFromPrevious: KalachakraLeapInfo | null;
  subPeriods: KalachakraNode[];
}

export interface KalachakraTimelineEntry {
  level: number;
  sign: string;
  start: string;
  end: string;
  leap: KalachakraLeapInfo;
  when: "past" | "current" | "future";
  /** Index-chain path (e.g. "0-3-1") into dashaTree — jump target for quick-nav. */
  path: string;
}

export interface KalachakraAlternateMethod {
  method: string;
  methodLabel: string;
  gatisVerified: boolean;
  currentLadder: KalachakraLadderRow[];
  activeLeap: KalachakraLeapInfo | null;
  dashaTree: KalachakraNode[];
  leapTimeline: KalachakraTimelineEntry[];
}

export interface KalachakraDeepData {
  status: string;
  system: string;
  method: string;
  error?: string;
  birthNakshatra?: KalachakraBirthNakshatra;
  cycle?: KalachakraCycle;
  balanceOfFirstDasha?: { actual: number | null; simplifiedEstimate: number | null };
  /** Natal Sarvashtakavarga (12-sign bindu board) — the strength source for
   * each leap's positive-potential-vs-challenging verdict. */
  sav?: number[];
  /** Argala/Yogakaraka/karaka verdict per sign (12 entries) — computed once
   * per chart since it depends only on the natal chart, not on dates. Look
   * up by a node's signIndex for its interpretation. */
  signInterpretations?: KalachakraSignInterpretation[] | null;
  lagnaLordAffliction?: KalachakraLagnaLordAffliction | null;
  moonNavamsaPoint?: KalachakraMoonNavamsaPoint | null;
  currentLadder?: KalachakraLadderRow[];
  activeLeap?: KalachakraLeapInfo | null;
  dashaTree?: KalachakraNode[];
  leapTimeline?: KalachakraTimelineEntry[];
  /** Raghavacharya (navamsa-based) method, computed alongside the primary
   * PVR/book method for side-by-side comparison. */
  alternateMethod?: KalachakraAlternateMethod | null;
  ke_version?: string | null;
  source_notes?: DashaGraphCitation[];
  graph_citations?: DashaGraphCitation[];
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
  handbook?: { source?: string; note?: string };
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

export interface KnowledgeEngineHealth {
  version?: string | null;
  healthy?: boolean;
  invalidated_count?: number;
  invalidated_nodes?: string[];
  registered_engines?: string[];
  last_revived?: string | null;
}

/** One planet's Mahadasha window relevant to a priority prediction. */
export interface PredictionTimingWindow {
  planet: string;
  start: string;
  end: string;
  when: "past" | "current" | "future";
}

/** Practical remedy theme attached to a priority prediction — present only
 * when a genuine affliction (debilitated/combust planet) or negative
 * classical text warrants one; positive yogas carry no remedy by design. */
export interface PredictionRemedy {
  theme: string;
  label: string;
  remedies: string[];
}

/** A chart-scored, dasha-timed prediction — the report's headline content
 * (backend: report_facts.py:_priority_predictions). */
export interface PriorityPrediction {
  yoga_key: string;
  name: string;
  score: number;
  planets_involved: string[];
  timing_windows: PredictionTimingWindow[];
  manifestation_text: string;
  remedy: PredictionRemedy | null;
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
    kaksha?: any;
    chara?: any;
    kalachakra?: any;
  };
  dasha_intelligence?: DashaIntelligence | null;
  transit_intelligence?: TransitIntelligence | null;
  next_shubh_days?: ShubhDay[] | null;
  timing_merge?: TimingMerge | null;
  forecast?: ForecastPeriod[] | null;
  priority_predictions?: PriorityPrediction[] | null;
  yogas?: {
    activeCount?: number;
    totalChecked?: number | null;
    yogas?: Record<string, { name?: string; definition?: string; prediction?: string; strength?: string; category?: string; source?: string; citation?: string; planets?: string[] }>;
  } | null;
  ashtakavarga?: AshtakavargaFacts | null;
  shadbala?: Record<string, Record<string, number | null>> | null;
  panchanga?: Record<string, unknown> | null;
  alternate_dashas?: AlternateDashas | null;
  graph_enhancements?: GraphEnhancements | null;
  narration?: {
    prose?: string;
    model?: string;
    generated?: boolean;
    status?: string;
    reason?: string;
    sources_used?: string[];
    sources_blocked?: string[];
  } | null;
  narration_error?: string | null;
  knowledge_engine?: KnowledgeEngineHealth | null;
  varshaphala?: {
    year?: number;
    lagna?: string;
    muntha?: { sign?: string; yearsElapsed?: number } | null;
    planets?: any[];
    yogas?: any[];
  } | null;
  classical_sources?: Record<string, string> | null;
  timing?: {
    rahu_kalam: { start: number; end: number };
    yamaganda: { start: number; end: number };
    gulika: { start: number; end: number };
    sunrise?: number;
    sunset?: number;
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

// Minimal stubs to unblock build for new dasha components (will be replaced with real shapes later)
export interface CharaDashaData {
  charaDashas: Array<{ name: string; duration: string }>;
}

export interface KakshaData {
  kakshas: Array<{ name: string; duration: string }>;
}

export interface KalachakraDashaData {
  kalachakraDashas: Array<{ name: string; duration: string }>;
}

// Additive v2 forecast contracts. These intentionally do not expose the
// internal traditional_strength_index as a user-facing probability.
export type ForecastV2Mode = "forecast";
export type ForecastV2Polarity =
  | "favourable"
  | "unfavourable"
  | "mixed"
  | "indeterminate";
export type ForecastV2ProbabilityStatus =
  | "unavailable"
  | "uncalibrated_signal"
  | "calibrated";

export interface ForecastV2Input {
  contract_version?: string;
  claim_id: string;
  forecast_id: string;
  release_id: string;
  locale: string;
  mode: ForecastV2Mode;
  event_code: string;
  event_domain: string;
  subject?: "native";
  observable_outcome: string;
  timing: {
    start_on: string;
    end_on: string;
    resolution_due_on: string;
    timezone: string;
    granularity: "day" | "week" | "month" | "quarter";
    horizon_days: number;
  };
  polarity: ForecastV2Polarity;
  traditional_strength_index: number;
  forecast_probability?: number | null;
  probability_status: ForecastV2ProbabilityStatus;
  calibration_release_id?: string | null;
  base_rate?: number | null;
  base_rate_source?: string | null;
  supporting_evidence_ids?: string[];
  opposing_evidence_ids?: string[];
  rule_ids?: string[];
  citation_ids?: string[];
  provenance: Record<string, unknown>;
  uncertainty: Record<string, unknown>;
  prerequisites?: string[];
  alternate_manifestations?: string[];
  disconfirmers?: string[];
  what_to_expect?: string[];
  safe_next_steps?: string[];
  avoidance_advice?: string[];
  decision_scope: string;
  limitations?: string[];
  certainty_tier: string;
  abstention: {
    abstained: boolean;
    code: string;
    reason?: string | null;
    retryable?: boolean;
  };
  high_stakes?: boolean;
  review_required?: boolean;
}

export interface GroundedForecastText {
  text: string;
  source_paths: string[];
}

export interface ForecastV2Brief {
  claim_id: string;
  concise_sentence: string;
  paragraphs: string[];
  content_plan: {
    claim_id: string;
    event: GroundedForecastText;
    timing: GroundedForecastText;
    implication: GroundedForecastText;
    expectations: GroundedForecastText[];
    prerequisites: GroundedForecastText[];
    evidence: Array<{
      direction: "supporting" | "opposing";
      evidence_ids: string[];
      statement: GroundedForecastText;
    }>;
    safe_actions: GroundedForecastText[];
    limitations: GroundedForecastText[];
    probability: GroundedForecastText;
    birth_time_stability: GroundedForecastText;
    abstention: GroundedForecastText | null;
  };
}

export interface ForecastV2ReleaseMetadata {
  api_version: string;
  contract_version: string;
  release_id: string;
  engine_version: string;
  policy_version: string;
  verbalizer_version: string;
  probability_status: ForecastV2ProbabilityStatus;
  ledger_write_enabled: boolean;
  ledger_written: boolean;
}

export interface ForecastV2ReleasedResponse {
  status: "released";
  metadata: ForecastV2ReleaseMetadata;
  claim: {
    event_code: string;
    timing: ForecastV2Input["timing"];
    polarity: ForecastV2Polarity;
    probability_status: ForecastV2ProbabilityStatus;
    forecast_probability: number | null;
    base_rate: number | null;
    base_rate_source: string | null;
    birth_time_sensitivity: "stable" | "moderate" | "high" | "unknown";
    supporting_evidence_ids: string[];
    opposing_evidence_ids: string[];
  };
  brief: ForecastV2Brief;
}

export interface ForecastV2ShadowResponse {
  status: "shadow";
  accepted: true;
  verbalization_computed: boolean;
  safety_status: "passed" | "filtered";
  blocked_category_count: number;
  metadata: ForecastV2ReleaseMetadata;
}

export type ForecastV2Response = ForecastV2ReleasedResponse | ForecastV2ShadowResponse;

// Canonical Person Timeline HTTP projection. These names intentionally match
// the backend contract; the portal does not maintain a lossy duplicate model.
export type TimelineOrigin = "prospective_prediction" | "observed_event" | "retrospective_hypothesis" | "imported_history" | "engine_inference";
export type TimelineDirection = "favourable" | "unfavourable" | "mixed" | "neutral" | "not_applicable";
export type TimelineOutcomeStatus = "hit" | "partial_hit" | "miss" | "false_alarm" | "unresolved" | "ambiguous";
export type TimelineZoom = "lifetime" | "decade" | "year" | "month" | "week" | "day";

export interface TimelineTolerance {
  before_seconds: number;
  after_seconds: number;
  native_label: string;
}

export interface TimelineWindow {
  start_at: string;
  peak_at: string | null;
  end_at: string;
  native_resolution: string;
  native_resolution_label: string;
  tolerance: TimelineTolerance;
}

export interface TimelineMilestone {
  milestone_id: string;
  timeline_id: string;
  subject_reference_id: string;
  origin: TimelineOrigin;
  origin_record_id: string;
  origin_identity_hash: string;
  canonical_event_id: string;
  original_label: string;
  title: string;
  description: string | null;
  direction: TimelineDirection;
  magnitude: unknown;
  window: TimelineWindow;
  created_at: string;
  sealed_at: string | null;
  knowledge_cutoff_at: string | null;
  known_event_milestone_id: string | null;
  supersedes_milestone_id: string | null;
  native_score_refs: string[];
  provenance: {
    actor_id: string;
    engine_version: string | null;
    run_id: string | null;
    release_id: string | null;
    input_snapshot_hash: string | null;
    calculation_hash: string | null;
    rule_pack_versions: Record<string, string>;
    source_ids: string[];
    citation_ids: string[];
    artifact_refs: string[];
  };
  visibility: string;
}

export interface TimelineTimingPeriod {
  system: string;
  level: string;
  ruler: string;
  parentRuler?: string;
  startAt: string;
  endAt: string;
  deepLink: string;
}

export interface PersonTimelineRecord {
  timeline_id: string;
  subject: { reference_id: string; protection: "deidentified" | "encrypted"; key_id: string | null };
  created_at: string;
  prediction_release_versions: string[];
  outcome_ledger_version: string | null;
}

export interface PersonTimeline {
  timeline: PersonTimelineRecord;
  generatedAt: string;
  scientificIdentity: { legacyCandidates: "engine_inference"; prospectivePredictionCount: number; notice: string };
  milestones: TimelineMilestone[];
  timingPeriods: TimelineTimingPeriod[];
  outcomes: TimelineOutcomeProjection[];
  calculation: Record<string, unknown>;
}

export interface TimelineOutcomeProjection {
  resolutionId: string;
  predictionMilestoneId: string;
  observedMilestoneId: string | null;
  status: TimelineOutcomeStatus;
  actualWindow: TimelineWindow | null;
  certainty: string;
  resolvedAt: string;
  supersedesResolutionId: string | null;
}

export interface TimelineDashaPeriod {
  level: string;
  ruler: string;
  start_at: string;
  end_at: string;
  node_id: string | null;
  deep_link: string | null;
}

export interface TimelineEvidenceProjection {
  role: string;
  statement: string;
  nativeScoreRef: string | null;
  ruleIds: string[];
  artifactRef: string;
}

export interface PersonTimelineDetailResponse {
  milestone: TimelineMilestone;
  humanStatement: string;
  direction: TimelineDirection;
  scientificIdentity: { origin: TimelineOrigin; prospective: boolean; notice: string };
  temporalPrecision: { interval: TimelineWindow; statement?: string };
  timingLadders: Array<{ system: string; periods: TimelineDashaPeriod[] }>;
  dashaDeepLink: string;
  supportingEvidence: TimelineEvidenceProjection[];
  opposingEvidence: TimelineEvidenceProjection[];
  evidenceSummary?: string;
  oppositionNotice: string;
  calculationTrace: Record<string, unknown>;
}
