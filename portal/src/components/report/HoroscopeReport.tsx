import { Card } from "@/components/ui/Card";
import type {
  ReportFacts,
  AshtakavargaFacts,
  ForecastPeriod,
  TimingMerge,
  AlternateDashas,
  GraphEnhancements,
  SignDashaBlock,
  KakshaBlock,
  KnowledgeEngineHealth,
  TextConflict,
  GodNodeInsight,
} from "@/lib/types";
import type { BirthDefaults } from "@/lib/birth-params";

// ─── Shared primitives ───────────────────────────────────────────────────────

function VerdictBadge({ verdict }: { verdict: string }) {
  const tone =
    verdict === "shubh"
      ? "text-emerald-700 bg-emerald-500/10 border-emerald-500/30"
      : verdict === "ashubh"
        ? "text-red-700 bg-red-500/10 border-red-500/30"
        : "text-amber-800 bg-amber-500/10 border-amber-500/30";
  return (
    <span className={`text-xs font-mono uppercase px-2 py-0.5 rounded-md border ${tone}`}>
      {verdict}
    </span>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted">
      {children}
    </h3>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (!items?.length) return <p className="text-sm text-text-muted">—</p>;
  return (
    <ul className="text-sm text-text-main space-y-1.5 list-disc pl-4">
      {items.map((t, i) => (
        <li key={i}>{t}</li>
      ))}
    </ul>
  );
}

// ─── Natal summary ───────────────────────────────────────────────────────────

function NatalCard({ report }: { report: ReportFacts }) {
  const natal = report.natal;
  return (
    <Card className="p-5 space-y-3">
      <SectionHeading>Natal summary</SectionHeading>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
        <div>
          <span className="text-text-muted">Lagna</span>
          <p className="font-medium">
            {natal.lagna.rashi} {natal.lagna.degree} · {natal.lagna.nakshatra} p
            {natal.lagna.pada}
          </p>
        </div>
        <div>
          <span className="text-text-muted">Moon</span>
          <p className="font-medium">
            {natal.moon.rashi} · {natal.moon.nakshatra} p{natal.moon.pada}
          </p>
        </div>
        <div>
          <span className="text-text-muted">Running dasha</span>
          <p className="font-medium font-mono">
            {report.dashas.current.slice(0, 2).join(" / ")}
          </p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-left text-text-muted border-b border-hairline">
              <th className="py-2 pr-3">Planet</th>
              <th className="py-2 pr-3">Rāśi</th>
              <th className="py-2 pr-3">Degree</th>
              <th className="py-2 pr-3">Nakṣatra</th>
              <th className="py-2">Dignity</th>
            </tr>
          </thead>
          <tbody>
            {natal.planets
              .filter((p) => p.planet !== "Lagna")
              .map((p) => (
                <tr key={p.planet} className="border-b border-hairline/60">
                  <td className="py-1.5 pr-3 font-medium">
                    {p.planet}
                    {p.retrograde ? <span className="text-amber-600 ml-1">℞</span> : null}
                  </td>
                  <td className="py-1.5 pr-3">{p.rashi}</td>
                  <td className="py-1.5 pr-3 tabular-nums">{p.degree}</td>
                  <td className="py-1.5 pr-3">
                    {p.nakshatra} p{p.pada}
                  </td>
                  <td className="py-1.5">{p.dignity || "—"}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Timing merge ────────────────────────────────────────────────────────────

function TimingMergeCard({ tm }: { tm: TimingMerge }) {
  return (
    <Card className="p-5 space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <SectionHeading>Timing window</SectionHeading>
        <VerdictBadge verdict={tm.verdict} />
        <span className="text-xs font-mono text-text-muted">combined score {tm.score}</span>
      </div>
      <p className="text-sm font-medium">{tm.label}</p>
      {tm.reasons.length > 0 && (
        <ul className="text-xs font-mono text-text-muted space-y-1">
          {tm.reasons.map((r, i) => (
            <li key={i}>· {r}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// ─── Dasha intelligence ──────────────────────────────────────────────────────

function DashaIntelCard({ di }: { di: NonNullable<ReportFacts["dasha_intelligence"]> }) {
  return (
    <Card className="p-5 space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <SectionHeading>Dasha intelligence</SectionHeading>
        <VerdictBadge verdict={di.final_verdict} />
        <span className="text-xs font-mono text-text-muted">score {di.score}</span>
      </div>
      <p className="text-sm leading-relaxed">{di.summary}</p>
      <p className="text-xs font-mono text-text-muted">{di.root_cause}</p>
      <p className="text-sm">
        <span className="text-text-muted">Primary driver: </span>
        {di.primary_driver}
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-mono uppercase text-text-muted mb-2">Profession</h4>
          <BulletList items={di.profession} />
        </div>
        <div>
          <h4 className="text-xs font-mono uppercase text-text-muted mb-2">Wealth</h4>
          <BulletList items={di.wealth} />
        </div>
        <div>
          <h4 className="text-xs font-mono uppercase text-text-muted mb-2">Health</h4>
          <BulletList items={di.health} />
        </div>
        <div>
          <h4 className="text-xs font-mono uppercase text-text-muted mb-2">Family</h4>
          <BulletList items={di.family} />
        </div>
      </div>
      {di.caution?.length ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
          <h4 className="text-xs font-mono uppercase text-amber-800 mb-2">Caution</h4>
          <BulletList items={di.caution} />
        </div>
      ) : null}
    </Card>
  );
}

// ─── Transit intelligence ────────────────────────────────────────────────────

function TransitIntelCard({
  ti,
  nextShubhDays,
}: {
  ti: NonNullable<ReportFacts["transit_intelligence"]>;
  nextShubhDays?: ReportFacts["next_shubh_days"];
}) {
  const favorable = (ti.planets ?? []).filter((p) => p.final_verdict === "shubh");
  const unfavorable = (ti.planets ?? []).filter(
    (p) => p.final_verdict === "ashubh" || p.final_verdict === "mixed",
  );
  const isNegative =
    ti.overall_verdict === "ashubh" || ti.overall_verdict === "mixed";
  const showLookAhead =
    isNegative && nextShubhDays && nextShubhDays.length > 0;

  return (
    <Card className="p-5 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <SectionHeading>Transit intelligence</SectionHeading>
        <VerdictBadge verdict={ti.overall_verdict} />
        <span className="text-xs font-mono text-text-muted ml-auto">
          score {ti.overall_score > 0 ? "+" : ""}{ti.overall_score}
        </span>
      </div>

      {/* Context pills */}
      <div className="flex flex-wrap gap-2 text-xs">
        {ti.dasha_context ? (
          <span className="px-2 py-0.5 rounded-md bg-accent/10 text-accent font-mono">
            {ti.dasha_context}
          </span>
        ) : null}
        {ti.moorthy_note ? (
          <span className={`px-2 py-0.5 rounded-md font-mono ${
            ti.moorthy_note.toLowerCase().includes("gold") || ti.moorthy_note.toLowerCase().includes("silver")
              ? "bg-emerald-500/10 text-emerald-400"
              : ti.moorthy_note.toLowerCase().includes("copper")
                ? "bg-amber-500/10 text-amber-400"
                : "bg-red-500/10 text-red-400"
          }`}>
            Moorthi · {ti.moorthy_note}
          </span>
        ) : null}
        {ti.tara_note ? (
          <span className={`px-2 py-0.5 rounded-md font-mono ${
            ti.tara_note.toLowerCase().includes("ashubh") || ti.tara_note.toLowerCase().includes("unfav")
              ? "bg-red-500/10 text-red-400"
              : "bg-emerald-500/10 text-emerald-400"
          }`}>
            Tara · {ti.tara_note}
          </span>
        ) : null}
      </div>

      {/* Planet split — favourable / unfavourable */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {favorable.length > 0 && (
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 space-y-2">
            <p className="text-[10px] font-mono uppercase tracking-wider text-emerald-500">
              Favourable ({favorable.length})
            </p>
            {favorable.map((p) => (
              <div key={p.planet} className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-emerald-400">{p.planet}</span>
                  <span className="text-[10px] font-mono text-text-muted">
                    {p.rashi} · score {p.score}
                  </span>
                </div>
                <p className="text-xs text-text-main">{p.summary}</p>
              </div>
            ))}
          </div>
        )}
        {unfavorable.length > 0 && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 space-y-2">
            <p className="text-[10px] font-mono uppercase tracking-wider text-red-500">
              Caution ({unfavorable.length})
            </p>
            {unfavorable.map((p) => (
              <div key={p.planet} className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-red-400">{p.planet}</span>
                  <span className="text-[10px] font-mono text-text-muted">
                    {p.rashi} · score {p.score}
                  </span>
                </div>
                <p className="text-xs text-text-main">{p.summary}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {showLookAhead && (
        <div className="text-xs text-text-muted">
          Next shubh windows: {nextShubhDays!.map((d) => d.date).join(", ")}
        </div>
      )}
    </Card>
  );
}

// ─── Dasha ladder ────────────────────────────────────────────────────────────

function DashaLadderCard({ report }: { report: ReportFacts }) {
  const ladder = report.dashas.currentLadder || [];
  if (!ladder.length) return null;
  return (
    <Card className="p-5 space-y-3">
      <SectionHeading>Vimshottari ladder (current)</SectionHeading>
      <div className="text-xs font-mono space-y-1">
        {ladder.slice(0, 5).map((r: any, i: number) => (
          <div key={i} className={i === 0 ? "text-accent font-semibold" : ""}>
            {r.lord} · {r.start} → {r.end} ({r.years}y)
          </div>
        ))}
      </div>
      <p className="text-[10px] text-text-muted font-mono">ke: {report.knowledge_engine?.version || "—"}</p>
    </Card>
  );
}

// ─── Forecast (next 8) ───────────────────────────────────────────────────────

function ForecastCard({ periods }: { periods: ForecastPeriod[] }) {
  return (
    <Card className="p-5 space-y-3">
      <SectionHeading>Next 8 Antardashas — area forecast</SectionHeading>
      <div className="space-y-3 text-sm">
        {periods.slice(0, 8).map((p, i) => (
          <div key={i} className="border-l-2 border-hairline pl-3">
            <div className="font-mono text-xs text-text-muted">
              {p.maha}/{p.antar} · {p.start.slice(0,10)}→{p.end.slice(0,10)} ({p.durationYears.toFixed(1)}y) · <VerdictBadge verdict={p.verdict} />
            </div>
            <p className="text-xs text-text-main mt-0.5">{p.summary}</p>
            <div className="text-[10px] font-mono text-text-muted grid grid-cols-2 gap-x-2 mt-1">
              {p.profession?.[0] && <span>Prof: {p.profession[0]}</span>}
              {p.wealth?.[0] && <span>Wealth: {p.wealth[0]}</span>}
              {p.health?.[0] && <span>Health: {p.health[0]}</span>}
              {p.family?.[0] && <span>Family: {p.family[0]}</span>}
              {p.caution?.[0] && <span className="text-amber-700">Caution: {p.caution[0]}</span>}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ─── Yogas (full enriched) ───────────────────────────────────────────────────

function YogasCard({ yogas }: { yogas: NonNullable<ReportFacts["yogas"]> }) {
  const list = Object.entries(yogas.yogas || {});
  if (!list.length && !yogas.activeCount) return null;
  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <SectionHeading>Active Yogas (all)</SectionHeading>
        {yogas.activeCount != null && (
          <span className="text-xs font-mono text-text-muted">
            {yogas.activeCount} active
            {yogas.totalChecked ? ` / ${yogas.totalChecked} checked` : ""}
          </span>
        )}
      </div>
      {list.length === 0 ? (
        <p className="text-sm text-text-muted">No yogas detected.</p>
      ) : (
        <div className="space-y-3 text-sm">
          {list.slice(0, 40).map(([key, y]: any) => (
            <div key={key} className="border-l-2 border-hairline pl-3">
              <div className="font-semibold">{y.name || key} {y.strength ? `(${y.strength})` : ""}</div>
              {y.definition && <p className="text-xs text-text-muted italic">{y.definition}</p>}
              {y.prediction && <p className="text-sm">{y.prediction}</p>}
              {(y.category || y.source || y.citation) && <p className="text-[10px] font-mono text-text-muted">{y.category} · {y.source || y.citation}</p>}
            </div>
          ))}
        </div>
      )}
      <p className="text-[10px] text-text-muted font-mono">yoga.py + KE Jataka structured (BPHS/PD/SC) + graph</p>
    </Card>
  );
}

// ─── Ashtakavarga (full SAV + BAV tables) ────────────────────────────────────

const BAND_COLORS: Record<string, string> = {
  excellent: "bg-emerald-500",
  good: "bg-emerald-400",
  standard: "bg-amber-400",
  depleted: "bg-red-400",
};

function AshtakavargaCard({ akv }: { akv: AshtakavargaFacts }) {
  const maxBindus = Math.max(...akv.sav, 1);
  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <SectionHeading>Ashtakavarga — Full SAV + BAV tables</SectionHeading>
        <span className="text-xs font-mono text-text-muted">post-shodhana total {akv.total}</span>
      </div>
      {/* SAV */}
      <div className="space-y-1.5">
        {akv.sav_annotated?.map((row: any, idx: number) => (
          <div key={idx} className="flex items-center gap-2 text-xs font-mono">
            <span className="w-14 text-text-muted shrink-0">{row.sign.slice(0, 3)}</span>
            <div className="flex-1 h-3 bg-hairline/40 rounded-sm overflow-hidden">
              <div className={`h-full rounded-sm transition-all ${BAND_COLORS[row.band] || "bg-amber-400"}`} style={{ width: `${(row.bindus / maxBindus) * 100}%` }} />
            </div>
            <span className="w-5 text-right tabular-nums">{row.bindus}</span>
            <span className={`w-16 ${row.band === "depleted" ? "text-red-600" : row.band === "excellent" ? "text-emerald-700" : "text-text-muted"}`}>{row.band}</span>
          </div>
        ))}
      </div>
      {/* Full BAV tables */}
      <div>
        <h4 className="text-xs font-mono uppercase text-text-muted mb-1">BAV (7 planets × 12 signs)</h4>
        <div className="overflow-x-auto text-[10px] font-mono">
          <table className="min-w-full border border-hairline">
            <thead><tr className="text-left"><th className="px-1">Pl</th>{Array.from({length:12}).map((_,i)=><th key={i} className="px-0.5 text-center tabular-nums">{i+1}</th>)}<th>Tot</th></tr></thead>
            <tbody>
              {Object.entries(akv.bav || {}).map(([pl, arr]: any) => (
                <tr key={pl} className="border-t border-hairline/60">
                  <td className="font-semibold pr-1">{pl.slice(0,2)}</td>
                  {(arr||[]).map((b:number,i:number)=><td key={i} className="px-0.5 text-center tabular-nums">{b}</td>)}
                  <td className="pl-1 font-semibold">{akv.planet_totals?.[pl]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-xs text-text-muted">{akv.handbook?.note || "Trikona+Ekadhipatya per BPHS Ch.67"} · {akv.handbook?.source || "KE"}</p>
    </Card>
  );
}

// ─── Shadbala ────────────────────────────────────────────────────────────────

const SHADBALA_DISPLAY_KEYS = ["sthana", "dig", "cheshta", "kaala", "naisargika", "total_rupa"];
const SHADBALA_LABELS: Record<string, string> = {
  sthana: "Sthana",
  dig: "Dik",
  cheshta: "Cheshta",
  kaala: "Kaala",
  naisargika: "Naisargika",
  total_rupa: "Total (Rupa)",
};

function ShadbalaCard({ shadbala }: { shadbala: NonNullable<ReportFacts["shadbala"]> }) {
  const planets = Object.keys(shadbala);
  if (!planets.length) return null;
  return (
    <Card className="p-5 space-y-3">
      <SectionHeading>Shadbala (6 components + total, 7 planets)</SectionHeading>
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-left text-text-muted border-b border-hairline">
              <th className="py-2 pr-3">Planet</th>
              {SHADBALA_DISPLAY_KEYS.map((k) => (
                <th key={k} className="py-2 pr-3">{SHADBALA_LABELS[k] || k}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {planets.map((planet) => {
              const row = shadbala[planet];
              const totalRupa = row["total_rupa"];
              const isStrong = typeof totalRupa === "number" && totalRupa >= 1;
              return (
                <tr key={planet} className="border-b border-hairline/60">
                  <td className={`py-1.5 pr-3 font-semibold ${isStrong ? "text-text-main" : "text-text-muted"}`}>{planet.slice(0, 2)}</td>
                  {SHADBALA_DISPLAY_KEYS.map((k) => {
                    const v = row[k];
                    return <td key={k} className={`py-1.5 pr-3 tabular-nums ${k === "total_rupa" ? "font-semibold" : ""}`}>{v != null ? (typeof v === "number" ? v.toFixed(2) : v) : "—"}</td>;
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-text-muted">BPHS Ch.27 · ke source on each planet</p>
    </Card>
  );
}

// ─── Narration ───────────────────────────────────────────────────────────────

function NarrationCard({ narration, error }: { narration: ReportFacts["narration"]; error?: string | null }) {
  if (error) {
    return <Card className="p-5 space-y-2 border border-danger/30"><SectionHeading>LLM Narrative</SectionHeading><p className="text-sm text-danger">{error}</p></Card>;
  }
  if (!narration) return null;
  if (narration.prose) {
    return (
      <Card className="p-5 space-y-2 border border-indigo-500/30">
        <SectionHeading>LLM Narrative (CVCE_LLM_NARRATION=1)</SectionHeading>
        <p className="text-sm leading-relaxed text-text-main whitespace-pre-wrap">{narration.prose}</p>
        {narration.model && <div className="text-[10px] text-text-muted">via {narration.model}</div>}
      </Card>
    );
  }
  return null;
}

// ─── Knowledge strip ─────────────────────────────────────────────────────────

function KnowledgeEngineStrip({ ke }: { ke?: KnowledgeEngineHealth | null }) {
  if (!ke) return null;
  return (
    <div className="text-[10px] font-mono text-text-muted">
      KE {ke.version} · healthy:{String(ke.healthy)} · engines:{ke.registered_engines?.length || 0}
    </div>
  );
}

// ─── Root: 8 FULL chapters, nav, sources, ke per section ─────────────────────

export function HoroscopeReport({
  defaults,
  report,
  error,
}: {
  defaults: BirthDefaults;
  report: ReportFacts | null;
  error: string | null;
}) {
  if (error) {
    return <Card className="p-6 border-danger/40"><p className="text-sm text-danger">{error}</p></Card>;
  }
  if (!report) return null;

  const hasKaksha = !!(report as any)?.dashas?.kaksha;
  const hasChara = !!(report as any)?.dashas?.chara;
  const hasKalachakra = !!(report as any)?.dashas?.kalachakra;

  const alternateDashas: string[] = [];
  if (hasKaksha) alternateDashas.push("ch9-kaksha");
  if (hasChara) alternateDashas.push("ch10-chara");
  if (hasKalachakra) alternateDashas.push("ch11-kalachakra");

  const allChapters = [
    "ch1-natal","ch2-yogas","ch3-akv","ch4-shadbala","ch5-timing",
    "ch6-dasha","ch7-varsha","ch8-narration", ...alternateDashas
  ];

  const tm = report.timing_merge;
  const keVer = report.knowledge_engine?.version || "file-based";
  const classSrc = report.classical_sources || {};

  return (
    <div className="space-y-8">
      <Card className="p-5 space-y-2 border border-hairline">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">Horoscope Report — Hiranya (Phases 9-12 complete)</h2>
        <p className="text-sm text-text-muted">{defaults.name} · born {defaults.date} {defaults.time} · {defaults.place}</p>
        <p className="text-xs font-mono text-text-muted">Judged {report.meta.query_date} · {report.meta.ayanamsa} · ke:{keVer}</p>
        {report.dashas.balanceAtBirth?.label && <p className="text-sm font-mono pt-1">Balance: <span className="text-accent">{report.dashas.balanceAtBirth.label}</span></p>}
      </Card>

      {/* Updated chapter nav including alternate dashas */}
      <div className="sticky top-0 z-10 bg-background/95 border-b border-hairline py-2">
        <nav className="flex flex-wrap gap-1 text-xs font-mono">
          {allChapters.map((id, i) => (
            <a key={id} href={`#${id}`} className="px-2 py-1 rounded border border-hairline hover:bg-accent/10">
              {i < 8 ? ["1.Natal+Panch", "2.Yogas(full)", "3.AKV(full SAV+BAV)", "4.Shadbala(7×6)", "5.Timing(merge+windows)", "6.Dasha(8AD+areas)", "7.Varshaphala", "8.Narration+KE"][i] : 
              id === 'ch9-kaksha' ? "9.Kaksha Dasha" : 
              id === 'ch10-chara' ? "10.Chara Dasha" : 
              id === 'ch11-kalachakra' ? "11.Kalachakra Dasha" : ""}
            </a>
          ))}
        </nav>
      </div>

      {/* Ch1 */}
      <div id="ch1-natal"><NatalCard report={report} />
        {report.panchanga && <Card className="p-5 mt-3 border border-hairline"><SectionHeading>Panchanga</SectionHeading><div className="text-xs font-mono grid grid-cols-5 gap-1">{Object.keys(report.panchanga).map(k=><span key={k}>{k}:{(report.panchanga as any)[k]?.name||""}</span>)}</div><p className="text-[10px] text-text-muted">drik+KE · ke:{keVer}</p></Card>}
      </div>

      {/* Ch2 Yogas full */}
      <div id="ch2-yogas">{report.yogas && <YogasCard yogas={report.yogas} />}<p className="text-[10px] px-1 font-mono text-text-muted">34 active on Mohan · yoga.py+KE Jataka/graph · {classSrc.yoga}</p></div>

      {/* Ch3 AKV full tables */}
      <div id="ch3-akv">{report.ashtakavarga && <AshtakavargaCard akv={report.ashtakavarga} />}<p className="text-[10px] px-1 font-mono text-text-muted">SAV12 + 7BAV×12 + handbook · ke:{keVer} {classSrc.ashtakavarga}</p></div>

      {/* Ch4 Shadbala */}
      <div id="ch4-shadbala">{report.shadbala && <ShadbalaCard shadbala={report.shadbala} />}<p className="text-[10px] px-1 font-mono text-text-muted">7 planets, 6 comps + total_rupa · BPHS27 · ke:{keVer}</p></div>

      {/* Ch5 Timing */}
      <div id="ch5-timing">{tm && <TimingMergeCard tm={tm} />}{report.next_shubh_days?.length ? <Card className="p-5 mt-3 border border-hairline"><SectionHeading>Next shubh</SectionHeading><div className="text-xs font-mono">{report.next_shubh_days.map((d:any)=>d.date).join(", ")}</div></Card> : null}<p className="text-[10px] px-1 font-mono text-text-muted">merged dasha+transit via KE · ke:{keVer}</p></div>

      {/* Ch6 Dasha forecast */}
      <div id="ch6-dasha">{report.forecast?.length && <ForecastCard periods={report.forecast} />}<p className="text-[10px] px-1 font-mono text-text-muted">next 8 AD + 5 area bullets · ke:{keVer} {classSrc.dasha}</p></div>

      {/* Ch7 Varshaphala */}
      <div id="ch7-varsha">
        <Card className="p-5 border border-hairline">
          <SectionHeading>Varshaphala</SectionHeading>
          {report.varshaphala?.muntha ? (
            <>
              <div className="text-sm font-mono">Muntha {report.varshaphala.muntha.sign} (yr{report.varshaphala.muntha.yearsElapsed})</div>
              <p className="text-xs text-amber-700">{report.varshaphala.tier_note}</p>
            </>
          ) : (
            <p className="text-xs text-text-muted">Solar return data not available for this chart.</p>
          )}
        </Card>
        <p className="text-[10px] px-1 font-mono text-text-muted">include_varshaphala wired · ke:{keVer}</p>
      </div>

      {/* Ch8 Narration + KE sources */}
      <div id="ch8-narration">
        <NarrationCard narration={report.narration} error={report.narration_error} />
        {report.graph_enhancements || report.knowledge_engine ? (
          <Card className="p-5 mt-3 border border-hairline">
            <SectionHeading>KE + Classical sources</SectionHeading>
            <KnowledgeEngineStrip ke={report.knowledge_engine} />
            <p className="text-[10px] font-mono">yoga:{classSrc.yoga} dasha:{classSrc.dasha} akv:{classSrc.ashtakavarga}</p>
          </Card>
        ) : null}
      </div>
      
      {/* Ch9 Kaksha Dasha */}
      {hasKaksha && (
        <div id="ch9-kaksha">
          <Card className="p-5 border border-hairline">
            <SectionHeading>Kaksha Dasha</SectionHeading>
            <div className="text-xs font-mono">
              {report.dashas.kaksha.periods.map((period: any, index: number) => (
                <div key={index} className="border-b border-hairline/60 py-1">
                  <div className="flex justify-between">
                    <span>{period.lord}</span>
                    <span>{period.start} → {period.end}</span>
                  </div>
                  {period.isCurrent && <span className="text-accent">Current</span>}
                </div>
              ))}
            </div>
            <p className="text-[10px] text-text-muted font-mono">Kaksha Dasha via BPHS · ke:{keVer}</p>
          </Card>
        </div>
      )}
      
      {/* Ch10 Chara Dasha */}
      {hasChara && (
        <div id="ch10-chara">
          <Card className="p-5 border border-hairline">
            <SectionHeading>Chara Dasha</SectionHeading>
            <div className="text-xs font-mono">
              {report.dashas.chara.periods.map((period: any, index: number) => (
                <div key={index} className="border-b border-hairline/60 py-1">
                  <div className="flex justify-between">
                    <span>{period.maha}/{period.antara}</span>
                    <span>{period.start} → {period.end}</span>
                  </div>
                  {period.isCurrent && <span className="text-accent">Current</span>}
                </div>
              ))}
            </div>
            <p className="text-[10px] text-text-muted font-mono">Chara Dasha via Jaimini · ke:{keVer}</p>
          </Card>
        </div>
      )}
      
      {/* Ch11 Kalachakra Dasha */}
      {hasKalachakra && (
        <div id="ch11-kalachakra">
          <Card className="p-5 border border-hairline">
            <SectionHeading>Kalachakra Dasha</SectionHeading>
            <div className="text-xs font-mono">
              {report.dashas.kalachakra.periods.map((period: any, index: number) => (
                <div key={index} className="border-b border-hairline/60 py-1">
                  <div className="flex justify-between">
                    <span>{period.maha}/{period.antara}</span>
                    <span>{period.start} → {period.end}</span>
                  </div>
                  {period.isCurrent && <span className="text-accent">Current</span>}
                </div>
              ))}
            </div>
            <p className="text-[10px] text-text-muted font-mono">Kalachakra Dasha via PVR · ke:{keVer}</p>
          </Card>
        </div>
      )}
    </div>
  );
}
