import { Card } from "@/components/ui/Card";
import type {
  ReportFacts,
  AshtakavargaFacts,
  ForecastPeriod,
  TimingMerge,
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
                    {p.rashi} · H{p.house_from_janma}
                  </span>
                </div>
                {p.primary_driver ? (
                  <p className="text-[11px] text-text-muted leading-snug">{p.primary_driver}</p>
                ) : null}
                {p.positive_impact?.slice(0, 1).map((imp, i) => (
                  <p key={i} className="text-[11px] text-emerald-400/70 leading-snug">{imp}</p>
                ))}
              </div>
            ))}
          </div>
        )}

        {unfavorable.length > 0 && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 space-y-2">
            <p className="text-[10px] font-mono uppercase tracking-wider text-red-400">
              Caution ({unfavorable.length})
            </p>
            {unfavorable.slice(0, 4).map((p) => (
              <div key={p.planet} className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-red-400">{p.planet}</span>
                  <span className="text-[10px] font-mono text-text-muted">
                    {p.rashi} · H{p.house_from_janma}
                  </span>
                </div>
                {p.primary_driver ? (
                  <p className="text-[11px] text-text-muted leading-snug">{p.primary_driver}</p>
                ) : null}
                {p.mitigating?.slice(0, 1).map((m, i) => (
                  <p key={i} className="text-[11px] text-amber-400/70 leading-snug">↳ {m}</p>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Next favourable days */}
      {showLookAhead ? (
        <div className="pt-3 border-t border-hairline space-y-2">
          <p className="text-[10px] font-mono uppercase tracking-wider text-emerald-500">
            Next favourable days
          </p>
          {nextShubhDays!.map((day) => (
            <div
              key={day.date}
              className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-xs"
            >
              <span className="font-mono font-semibold text-emerald-400 tabular-nums shrink-0">
                {new Date(day.date + "T12:00:00").toLocaleDateString("en-IN", {
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                })}
              </span>
              <span className="text-text-muted leading-snug">{day.summary}</span>
              {day.top_drivers?.length ? (
                <span className="text-text-muted/60 font-mono shrink-0">
                  {day.top_drivers.join(" · ")}
                </span>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </Card>
  );
}

// ─── Vimshottari ladder ──────────────────────────────────────────────────────

function DashaLadderCard({ report }: { report: ReportFacts }) {
  return (
    <Card className="p-5 space-y-3">
      <SectionHeading>Vimshottari ladder (now)</SectionHeading>
      <div className="space-y-2">
        {report.dashas.currentLadder.map((row) => (
          <div
            key={row.level}
            className="flex flex-wrap gap-x-4 gap-y-1 text-sm border-b border-hairline/50 pb-2"
          >
            <span className="text-xs font-mono uppercase text-text-muted w-28">
              {row.levelLabel}
            </span>
            <span className="font-semibold text-accent">{row.lord}</span>
            <span className="text-xs font-mono text-text-muted tabular-nums">
              {row.start.slice(0, 10)} → {row.end.slice(0, 10)}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ─── Dasha forecast ──────────────────────────────────────────────────────────

function ForecastCard({ periods }: { periods: ForecastPeriod[] }) {
  if (!periods.length) return null;

  const verdictBg = (v: string) =>
    v === "shubh"
      ? "border-l-emerald-400"
      : v === "ashubh"
        ? "border-l-red-400"
        : "border-l-amber-400";

  return (
    <Card className="p-5 space-y-4">
      <SectionHeading>Dasha forecast — upcoming periods</SectionHeading>
      <div className="space-y-3">
        {periods.map((p, i) => (
          <div
            key={i}
            className={`border-l-2 pl-4 py-1 space-y-1 ${verdictBg(p.verdict)} ${p.isCurrent ? "opacity-100" : "opacity-80"}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold">
                {p.maha} / {p.antar}
              </span>
              {p.isCurrent && (
                <span className="text-xs bg-accent/10 text-accent px-1.5 py-0.5 rounded font-mono">
                  current
                </span>
              )}
              <VerdictBadge verdict={p.verdict} />
              <span className="text-xs font-mono text-text-muted tabular-nums">
                {p.start} → {p.end}
              </span>
            </div>
            <p className="text-xs text-text-muted">{p.summary}</p>
            {(p.profession[0] || p.wealth[0] || p.health[0]) && (
              <div className="text-xs font-mono text-text-muted space-y-0.5 pt-1">
                {p.profession[0] && <p>Profession: {p.profession[0]}</p>}
                {p.wealth[0] && <p>Wealth: {p.wealth[0]}</p>}
                {p.health[0] && <p>Health: {p.health[0]}</p>}
                {p.caution[0] && (
                  <p className="text-amber-700">Caution: {p.caution[0]}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

// ─── Yogas ───────────────────────────────────────────────────────────────────

function YogasCard({ yogas }: { yogas: NonNullable<ReportFacts["yogas"]> }) {
  const list = Object.entries(yogas.yogas || {});
  if (!list.length && !yogas.activeCount) return null;

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <SectionHeading>Active yogas</SectionHeading>
        {yogas.activeCount != null && (
          <span className="text-xs font-mono text-text-muted">
            {yogas.activeCount} active
            {yogas.totalChecked ? ` / ${yogas.totalChecked} checked` : ""}
          </span>
        )}
      </div>

      {list.length === 0 ? (
        <p className="text-sm text-text-muted">No yogas detected for this chart.</p>
      ) : (
        <div className="space-y-4">
          {list.slice(0, 20).map(([key, y]) => (
            <div key={key} className="space-y-1">
              <p className="text-sm font-semibold">{y.name || key}</p>
              {y.definition && (
                <p className="text-xs text-text-muted italic">{y.definition}</p>
              )}
              {y.prediction && (
                <p className="text-sm text-text-main">{y.prediction}</p>
              )}
            </div>
          ))}
          {list.length > 20 && (
            <p className="text-xs font-mono text-text-muted">
              + {list.length - 20} more yogas detected
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

// ─── Ashtakavarga ────────────────────────────────────────────────────────────

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
        <SectionHeading>Ashtakavarga (SAV)</SectionHeading>
        <span className="text-xs font-mono text-text-muted">
          post-shodhana total {akv.total}
        </span>
      </div>

      {/* SAV bar chart */}
      <div className="space-y-1.5">
        {akv.sav_annotated.map((row) => (
          <div key={row.sign} className="flex items-center gap-2 text-xs font-mono">
            <span className="w-14 text-text-muted shrink-0">{row.sign.slice(0, 3)}</span>
            <div className="flex-1 h-3 bg-hairline/40 rounded-sm overflow-hidden">
              <div
                className={`h-full rounded-sm transition-all ${BAND_COLORS[row.band] || "bg-amber-400"}`}
                style={{ width: `${(row.bindus / maxBindus) * 100}%` }}
              />
            </div>
            <span className="w-5 text-right tabular-nums">{row.bindus}</span>
            <span className={`w-16 ${row.band === "depleted" ? "text-red-600" : row.band === "excellent" ? "text-emerald-700" : "text-text-muted"}`}>
              {row.band}
            </span>
          </div>
        ))}
      </div>

      {/* Planet BAV totals */}
      <div>
        <h4 className="text-xs font-mono uppercase text-text-muted mb-2">Planet totals (BAV, post-shodhana)</h4>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs font-mono text-text-muted">
          {Object.entries(akv.planet_totals).map(([planet, total]) => (
            <span key={planet}>
              {planet.slice(0, 2)}: <span className="text-text-main">{total}</span>
            </span>
          ))}
        </div>
      </div>
      <p className="text-xs text-text-muted">
        Trikona + Ekadhipatya Shodhana applied per BPHS Ch.67. Shaded: depleted &lt;25, standard 25–27, good 28–29, excellent 30+.
      </p>
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
      <SectionHeading>Shadbala (planet strength)</SectionHeading>
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-left text-text-muted border-b border-hairline">
              <th className="py-2 pr-3">Planet</th>
              {SHADBALA_DISPLAY_KEYS.map((k) => (
                <th key={k} className="py-2 pr-3">
                  {SHADBALA_LABELS[k] || k}
                </th>
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
                  <td className={`py-1.5 pr-3 font-semibold ${isStrong ? "text-text-main" : "text-text-muted"}`}>
                    {planet.slice(0, 2)}
                  </td>
                  {SHADBALA_DISPLAY_KEYS.map((k) => {
                    const v = row[k];
                    return (
                      <td key={k} className={`py-1.5 pr-3 tabular-nums ${k === "total_rupa" ? "font-semibold" : ""}`}>
                        {v != null ? v.toFixed(2) : "—"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-text-muted">
        Strength ≥ 1.0 Rupa considered adequate. Source: BPHS Ch.27 (Shadbala).
      </p>
    </Card>
  );
}

// ─── Root component ──────────────────────────────────────────────────────────

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
    return (
      <Card className="p-6 border-danger/40">
        <p className="text-sm text-danger">{error}</p>
      </Card>
    );
  }
  if (!report) return null;

  const di = report.dasha_intelligence;
  const ti = report.transit_intelligence;
  const tm = report.timing_merge;

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-5 space-y-2">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Horoscope Report
        </h2>
        <p className="text-sm text-text-muted">
          {defaults.name} · born {defaults.date} {defaults.time} · {defaults.place}
        </p>
        <p className="text-xs font-mono text-text-muted">
          Judged for {report.meta.query_date} · {report.meta.ayanamsa} · {report.meta.engine}
        </p>
        {report.dashas.balanceAtBirth?.label ? (
          <p className="text-sm font-mono pt-1">
            Balance at birth:{" "}
            <span className="text-accent">{report.dashas.balanceAtBirth.label}</span>
          </p>
        ) : null}
      </Card>

      {/* Natal */}
      <NatalCard report={report} />

      {/* Timing merge hero */}
      {tm ? <TimingMergeCard tm={tm} /> : null}

      {/* Dasha intelligence */}
      {di ? <DashaIntelCard di={di} /> : null}

      {/* Transit intelligence */}
      {ti ? (
        <TransitIntelCard ti={ti} nextShubhDays={report.next_shubh_days} />
      ) : null}

      {/* Vimshottari ladder */}
      <DashaLadderCard report={report} />

      {/* Dasha forecast */}
      {report.forecast?.length ? <ForecastCard periods={report.forecast} /> : null}

      {/* Active yogas */}
      {report.yogas ? <YogasCard yogas={report.yogas} /> : null}

      {/* Ashtakavarga */}
      {report.ashtakavarga ? <AshtakavargaCard akv={report.ashtakavarga} /> : null}

      {/* Shadbala */}
      {report.shadbala ? <ShadbalaCard shadbala={report.shadbala} /> : null}

      {/* Optional LLM narration (CVCE_LLM_NARRATION=1) */}
      {report.narration?.prose ? (
        <Card className="p-5 space-y-2 border border-indigo-500/30">
          <SectionHeading>LLM Narrative Summary</SectionHeading>
          <p className="text-sm leading-relaxed text-text-main whitespace-pre-wrap">{report.narration.prose}</p>
          {report.narration.model && <div className="text-[10px] text-text-muted">Generated with {report.narration.model}</div>}
        </Card>
      ) : null}
    </div>
  );
}
