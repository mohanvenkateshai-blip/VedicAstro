import { AlertTriangle, CheckCircle2, Clock3 } from "lucide-react";

import { MuhurtaContextForm } from "@/components/MuhurtaContextForm";
import { Card, CardLabel } from "@/components/ui/Card";
import { getMuhurta, type MuhurtaBundle } from "@/lib/cvce";
import { loadChartFromSearchParams } from "@/lib/load-chart";
import { isNativeMuhurtaResearchEnabled } from "@/lib/muhurta-feature";
import { formatMuhurtaWindowTime } from "@/lib/muhurta-time";
import {
  parseMuhurtaMoment,
  type MuhurtaMomentContext,
  type MuhurtaSearchParams,
} from "@/lib/muhurta-context";
import type { MuhurtaCitation, MuhurtaResult, Verdict } from "@/lib/types";

type NativeMuhurtaResult = MuhurtaResult;

function tone(value?: string): "support" | "block" | "neutral" {
  const normalized = (value ?? "").toLowerCase();
  if (/ashubh|inauspicious|unfavourable|unfavorable|weak|adverse|block/.test(normalized)) {
    return "block";
  }
  if (/shubh|auspicious|favourable|favorable|strong|support|good/.test(normalized)) {
    return "support";
  }
  return "neutral";
}

function verdictClass(value?: string) {
  const valueTone = tone(value);
  if (valueTone === "support") return "bg-success/10 text-success border-success/25";
  if (valueTone === "block") return "bg-danger/10 text-danger border-danger/25";
  return "bg-accent/10 text-accent border-accent/20";
}

function factors(result: NativeMuhurtaResult) {
  const candidates: { label: string; value: string; verdict?: Verdict | string }[] = [];
  const p = result.panchanga;
  if (p?.tithi) candidates.push({ label: "Tithi", value: p.tithi.name, verdict: p.tithi.verdict });
  if (p?.nakshatra) candidates.push({ label: "Nakshatra", value: p.nakshatra.name, verdict: p.nakshatra.verdict });
  if (p?.yoga) candidates.push({ label: "Nitya Yoga", value: p.yoga.name, verdict: p.yoga.verdict });
  if (p?.karana) candidates.push({ label: "Karana", value: p.karana.name, verdict: p.karana.verdict });
  if (result.gochar?.overall_verdict) {
    candidates.push({ label: "Personal Gochar", value: result.gochar.overall_verdict, verdict: result.gochar.overall_verdict });
  }
  if (result.gochar?.tara_balam?.name) {
    candidates.push({ label: "Tara Balam", value: result.gochar.tara_balam.name, verdict: result.gochar.tara_balam.verdict });
  }
  if (result.ashtakavarga?.moon_transit_verdict) {
    candidates.push({
      label: "Moon Ashtakavarga",
      value: `${result.ashtakavarga.moon_transit_bindus ?? "—"} bindus · ${result.ashtakavarga.moon_transit_verdict}`,
      verdict: result.ashtakavarga.moon_transit_verdict,
    });
  }
  for (const hit of result.muhurta_yogas?.active ?? []) {
    candidates.push({ label: hit.name ?? "Muhurta Yoga", value: hit.detail ?? hit.nature ?? "Active", verdict: hit.nature });
  }
  return {
    supporting: candidates.filter((item) => tone(item.verdict) === "support"),
    blocking: candidates.filter((item) => tone(item.verdict) === "block"),
    neutral: candidates.filter((item) => tone(item.verdict) === "neutral"),
  };
}

function yogaEvidenceSummary(result: NativeMuhurtaResult) {
  const active = result.muhurta_yogas?.active ?? [];
  if (!active.length) return result.summary;
  const names = active.map((hit) => hit.name ?? "Unnamed yoga");
  return `${active.length} cited general Muhūrta ${active.length === 1 ? "yoga supports" : "yogas support"} this moment: ${names.join(", ")}. Activity-specific and natal-transit checks are not yet included in this verdict.`;
}

function yogaWeightExplanation(result: NativeMuhurtaResult) {
  const weighted = (result.muhurta_yogas?.active ?? []).filter(
    (hit): hit is typeof hit & { strength: number } => Number.isFinite(hit.strength),
  );
  if (!weighted.length) return "No cited yoga weights contributed.";
  const terms = weighted.map((hit) => `${hit.strength > 0 ? "+" : ""}${hit.strength} ${hit.name ?? "yoga"}`);
  return `${terms.join(" · ")} = ${result.overall_score > 0 ? "+" : ""}${result.overall_score} total`;
}

function ResultView({ bundle, context }: { bundle: MuhurtaBundle; context: MuhurtaMomentContext }) {
  const result = bundle.prediction as NativeMuhurtaResult;
  const evidence = factors(result);
  const limbs = [
    ["Tithi", result.panchanga?.tithi?.name, result.panchanga?.tithi?.verdict, result.panchanga?.tithi?.paksha],
    ["Vara", result.panchanga?.vaar, undefined, "Weekday"],
    ["Nakshatra", result.panchanga?.nakshatra?.name, result.panchanga?.nakshatra?.verdict, result.panchanga?.nakshatra?.pada ? `Pada ${result.panchanga.nakshatra.pada}` : undefined],
    ["Yoga", result.panchanga?.yoga?.name, result.panchanga?.yoga?.verdict, "Daily Panchānga yoga"],
    ["Karana", result.panchanga?.karana?.name, result.panchanga?.karana?.verdict, "Half-tithi division"],
  ] as const;
  const citations: MuhurtaCitation[] = result.graph_enhancements?.muhurta_citations ?? [];
  const windows = bundle.windows;

  return (
    <div className="space-y-6">
      <Card className="p-5 md:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><CardLabel>Canonical Muhūrta research preview</CardLabel><h2 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold">{tone(result.overall_verdict) === "support" ? "Generally supportive at the Panchānga level" : result.overall_verdict}</h2><p className="mt-2 max-w-3xl text-sm leading-relaxed text-text-muted">{yogaEvidenceSummary(result)}</p></div>
          <div className={`max-w-sm rounded-xl border px-4 py-3 ${verdictClass(result.overall_verdict)}`}><p className="font-mono text-[10px] uppercase tracking-widest">Cited yoga evidence</p><p className="mt-1 text-lg font-semibold">{evidence.supporting.length} supporting · {evidence.blocking.length} caution</p><p className="mt-1 text-xs leading-relaxed">{yogaWeightExplanation(result)}</p><p className="mt-1 text-[10px] leading-relaxed opacity-80">Additive classical-rule weights—not a score out of a maximum, percentage, or probability.</p></div>
        </div>
        <dl className="mt-5 grid gap-3 border-t border-hairline pt-4 text-xs md:grid-cols-3">
          <div><dt className="text-text-muted">Effective instant</dt><dd className="mt-1 font-mono">{context.effectiveInstant}</dd></div>
          <div><dt className="text-text-muted">Election place</dt><dd className="mt-1">{context.place} · {context.latitude.toFixed(4)}, {context.longitude.toFixed(4)}</dd></div>
          <div><dt className="text-text-muted">Calculation method</dt><dd className="mt-1 font-mono">{result.calculation_context ? `${result.calculation_context.engine} / ${result.calculation_context.backend} · ${result.calculation_context.ayanamsa}` : "Method unavailable"}</dd></div>
        </dl>
      </Card>

      <section><div className="mb-3"><CardLabel>Five-limb Panchānga</CardLabel><h3 className="mt-1 text-lg font-semibold">Conditions at the selected instant</h3><p className="mt-1 max-w-3xl text-xs leading-relaxed text-text-muted">These values describe the moment and are inputs to the combination rules. A value marked “Context only” does not independently raise or lower the verdict.</p></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{limbs.map(([name, value, verdict, detail]) => <Card key={name} className="p-4"><p className="font-mono text-[10px] uppercase tracking-widest text-text-muted">{name}</p><p className="mt-2 font-semibold">{value ?? "Unavailable"}</p><p className="mt-1 text-xs text-text-muted">{detail ?? "—"}</p>{verdict ? <span className={`mt-3 inline-flex rounded-full border px-2 py-0.5 text-[10px] font-mono ${verdictClass(verdict)}`}>{tone(verdict) === "neutral" ? "Context only" : verdict}</span> : null}</Card>)}</div></section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5"><div className="flex items-center gap-2 text-success"><CheckCircle2 size={17} /><h3 className="font-semibold">Supporting factors</h3></div><ul className="mt-4 space-y-3 text-sm">{evidence.supporting.length ? evidence.supporting.map((item) => <li key={`${item.label}-${item.value}`}><span className="font-medium">{item.label}:</span> <span className="text-text-muted">{item.value}</span></li>) : <li className="text-text-muted">No explicitly supportive factor was returned.</li>}</ul></Card>
        <Card className="p-5"><div className="flex items-center gap-2 text-danger"><AlertTriangle size={17} /><h3 className="font-semibold">Blocking and caution factors</h3></div><ul className="mt-4 space-y-3 text-sm">{evidence.blocking.map((item) => <li key={`${item.label}-${item.value}`}><span className="font-medium">{item.label}:</span> <span className="text-text-muted">{item.value}</span></li>)}{result.warnings.map((warning) => <li key={warning} className="text-text-muted">{warning}</li>)}{!evidence.blocking.length && !result.warnings.length ? <li className="text-text-muted">No explicit blocker was returned; neutral or untested factors still remain.</li> : null}</ul></Card>
      </div>

      <Card className="p-5"><div className="flex items-center gap-2"><Clock3 size={17} className="text-accent" /><h3 className="font-semibold">Daily avoid windows</h3></div><div className="mt-4 grid gap-3 text-sm sm:grid-cols-3"><p><span className="text-text-muted">Rahu Kalam</span><br /><span className="font-mono">{formatMuhurtaWindowTime(windows.rahu_kalam.start)}–{formatMuhurtaWindowTime(windows.rahu_kalam.end)}</span></p><p><span className="text-text-muted">Yamaganda</span><br /><span className="font-mono">{formatMuhurtaWindowTime(windows.yamaganda.start)}–{formatMuhurtaWindowTime(windows.yamaganda.end)}</span></p><p><span className="text-text-muted">Gulika</span><br /><span className="font-mono">{formatMuhurtaWindowTime(windows.gulika.start)}–{formatMuhurtaWindowTime(windows.gulika.end)}</span></p></div></Card>

      <Card className="p-5"><h3 className="font-semibold">Why this moment received this verdict</h3><ul className="mt-4 space-y-3 text-sm">{(result.muhurta_yogas?.active ?? []).map((hit) => <li key={`${hit.name}-${hit.detail}`}><span className="font-medium">{hit.name ?? "Muhūrta yoga"}</span>{hit.detail ? <span className="text-text-muted"> — {hit.detail}</span> : null}</li>)}{citations.map((citation) => <li key={`${citation.name}-${citation.detail}`}><span className="font-medium">{citation.name}</span><span className="text-text-muted"> — {citation.detail ?? citation.nature}</span></li>)}{!(result.muhurta_yogas?.active ?? []).length && !citations.length ? <li className="text-text-muted">No named supportive or cautionary combination was active.</li> : null}</ul></Card>
      <p className="text-xs leading-relaxed text-text-muted">This research preview evaluates one candidate start moment and verifies the natal-chart identity used by the request. Activity-specific and personalized transit rules remain visibly unvalidated; the score is not a probability or guarantee.</p>
    </div>
  );
}

export default async function NativeMuhurtaPage({ searchParams }: { searchParams: Promise<MuhurtaSearchParams> }) {
  const params = await searchParams;
  if (!isNativeMuhurtaResearchEnabled()) {
    return (
      <div role="status"><Card className="border-accent/30 p-6">
        <CardLabel>Validation hold</CardLabel>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-xl font-semibold">Native Muhūrta research is disabled</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-text-muted">
          This route is fail-closed while canonical Swiss/PyJHora calculations, timezone and chart-identity checks, rule provenance, and user-comprehension tests are being validated. No Muhūrta calculation has been run. The top-level legacy viewer is not used as a calculation fallback here.
        </p>
      </Card></div>
    );
  }

  const one = (value: string | string[] | undefined) => Array.isArray(value) ? value[0] : value;
  const natalParams = Object.entries(params).flatMap(([name, raw]) => {
    if (name.startsWith("m_") || raw === undefined) return [];
    return (Array.isArray(raw) ? raw : [raw]).map((value) => [name, value] as [string, string]);
  });
  const { chart, birth, error: chartError } = await loadChartFromSearchParams(params);
  const parsed = parseMuhurtaMoment(params);
  let bundle: MuhurtaBundle | null = null;
  let engineError: string | null = null;
  if (chart && parsed.context) {
    try {
      bundle = await getMuhurta({ ...birth, ayanamsa: chart.ayanamsa }, {
        instant: parsed.context.effectiveInstant,
        place: parsed.context.place,
        lat: parsed.context.latitude,
        lon: parsed.context.longitude,
        timezone: parsed.context.timezone,
        disambiguation: parsed.context.disambiguation ?? "exact",
      }, chart);
    } catch (caught) {
      engineError = caught instanceof Error ? caught.message : "Muhūrta calculation is unavailable.";
    }
  }
  return (
    <div className="space-y-6">
      <Card className="p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="font-[family-name:var(--font-display)] text-xl font-semibold">Native Muhūrta research</h1><p className="mt-1 text-sm text-text-muted">Assess one precise election moment through the canonical CVCE calculation path.</p></div><a href="https://muhurtha.uvwx.me" target="_blank" rel="noopener noreferrer" className="text-xs font-medium text-accent hover:underline">Open legacy viewer in a new tab ↗</a></div></Card>
      {chartError ? <div role="alert"><Card className="border-danger/40 p-5 text-sm text-danger">{chartError}</Card></div> : null}
      {!chart && !chartError ? <Card className="p-6 text-sm text-text-muted">Enter birth details above before assessing a Muhūrta.</Card> : null}
      {chart ? <MuhurtaContextForm natalParams={natalParams} initial={{ date: one(params.m_date) ?? "", time: one(params.m_time) ?? "", place: one(params.m_place) ?? "", latitude: one(params.m_lat) ?? "", longitude: one(params.m_lon) ?? "", timezone: one(params.m_zone) ?? "", disambiguation: one(params.m_disambiguation) ?? "" }} /> : null}
      {parsed.error ? <div role="alert"><Card className="border-danger/40 p-5 text-sm text-danger">{parsed.error}</Card></div> : null}
      {engineError ? <div role="alert"><Card className="border-danger/40 p-5 text-sm text-danger">{engineError}</Card></div> : null}
      {bundle && parsed.context ? <ResultView bundle={bundle} context={parsed.context} /> : null}
    </div>
  );
}
