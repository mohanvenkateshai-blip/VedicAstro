"use client";

import { useState, useEffect } from "react";
import { Loader, AlertTriangle, Info } from "lucide-react";
import type { ChartData } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PlanetTransit {
  planet: string;
  rashi: string;
  nakshatra: string;
  retrograde: boolean;
  house_from_janma: number | null;
  house_from_lagna: number | null;
  verdict: "shubh" | "ashubh" | "neutral";
  house_quality: string;
  score: number;
  lagna_score: number;
  effects: string[];
  vedha_active: boolean;
  vedha_by: string | null;
  vipareetha_vedha_active: boolean;
}

interface GocharData {
  date: string;
  janma_rashi: string | null;
  janma_nakshatra: string | null;
  lagna_rashi: string | null;
  overall_score: number;
  overall_verdict: string;
  lagna_overall_score: number;
  synthesis: string;
  moorthy: { house: number; name: string; verdict: string; description: string } | null;
  sade_sati: { phase: string; effect: string } | null;
  ashtama_shani: { house: number; effect: string } | null;
  kantaka_shani: { house: number; effect: string } | null;
  tara_balam: { name: string; verdict: string; paryaya: number; description: string } | null;
  planets: PlanetTransit[];
}

// ── Colour tokens ─────────────────────────────────────────────────────────────

const SHUBH  = "#10b981";
const ASHUBH = "#ef4444";
const NEUTRAL = "#94a3b8";
const MOON_C  = "#60a5fa";
const LAGNA_C = "#f59e0b";

const PLANET_COLOR: Record<string, string> = {
  Sun:     "#f97316",
  Moon:    "#94a3b8",
  Mars:    "#ef4444",
  Mercury: "#22c55e",
  Jupiter: "#facc15",
  Venus:   "#ec4899",
  Saturn:  "#7c3aed",
  Rahu:    "#64748b",
  Ketu:    "#a78bfa",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function verdictColor(v: string): string {
  if (v === "shubh") return SHUBH;
  if (v === "ashubh") return ASHUBH;
  return NEUTRAL;
}

function scoreLabel(s: number): string {
  return `${s > 0 ? "+" : ""}${s}`;
}

function ordinal(n: number): string {
  const suffixes = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (suffixes[(v - 20) % 10] ?? suffixes[v] ?? suffixes[0]);
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric", month: "long", year: "numeric",
  });
}

// ── Score orb ─────────────────────────────────────────────────────────────────

function ScoreOrb({ score, label, color }: { score: number; label: string; color: string }) {
  const isPositive = score > 0;
  const verdict = score >= 10 ? "Favorable" : score >= 0 ? "Mixed" : score >= -15 ? "Challenging" : "Very Challenging";

  return (
    <div className="flex flex-col items-center gap-1.5 px-4 py-3 rounded-xl border"
      style={{ borderColor: `${color}33`, backgroundColor: `${color}08` }}>
      <span className="text-[9px] font-mono uppercase tracking-widest" style={{ color: `${color}99` }}>
        {label}
      </span>
      <span className="text-2xl font-semibold font-mono tabular-nums" style={{ color }}>
        {scoreLabel(score)}
      </span>
      <span className="text-[10px] font-mono" style={{ color: isPositive ? SHUBH : score === 0 ? NEUTRAL : ASHUBH }}>
        {verdict}
      </span>
    </div>
  );
}

// ── Alert banner ──────────────────────────────────────────────────────────────

function AlertBanner({ icon, title, body }: { icon: "warn" | "info"; title: string; body: string }) {
  const isWarn = icon === "warn";
  const c = isWarn ? ASHUBH : "#f59e0b";
  return (
    <div className="flex gap-2.5 rounded-xl border p-3" style={{ borderColor: `${c}33`, backgroundColor: `${c}08` }}>
      {isWarn
        ? <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: c }} />
        : <Info className="w-4 h-4 shrink-0 mt-0.5" style={{ color: c }} />
      }
      <div>
        <p className="text-[11px] font-semibold font-mono" style={{ color: c }}>{title}</p>
        <p className="text-[11px] text-text-muted mt-0.5 leading-snug">{body}</p>
      </div>
    </div>
  );
}

// ── Planet impact table ───────────────────────────────────────────────────────

function QualityDot({ quality }: { quality: string }) {
  const color =
    quality === "good" ? SHUBH :
    quality === "bad" ? ASHUBH :
    quality === "worst" ? "#dc2626" :
    NEUTRAL;
  const label = quality === "good" ? "✓" : quality === "bad" ? "✗" : quality === "worst" ? "✗✗" : "~";
  return (
    <span className="text-[11px] font-semibold" style={{ color }}>{label}</span>
  );
}

function PlanetRow({ p, showLagna }: { p: PlanetTransit; showLagna: boolean }) {
  const [open, setOpen] = useState(false);
  const color = PLANET_COLOR[p.planet] ?? NEUTRAL;

  return (
    <>
      <tr
        className="border-b border-hairline cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => p.effects.length > 0 && setOpen((s) => !s)}
      >
        {/* Planet */}
        <td className="py-2 pl-3 pr-2">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium" style={{ color }}>{p.planet}</span>
            {p.retrograde && <span className="text-[9px] font-mono" style={{ color: `${color}77` }}>℞</span>}
          </div>
          <div className="text-[10px] text-text-muted font-mono">{p.rashi}</div>
        </td>

        {/* House from Moon */}
        <td className="py-2 px-2 text-center">
          {p.house_from_janma != null ? (
            <div>
              <span className="text-sm font-mono tabular-nums" style={{ color: verdictColor(p.verdict) }}>
                {ordinal(p.house_from_janma)}
              </span>
              <div className="flex justify-center mt-0.5">
                <QualityDot quality={p.house_quality} />
              </div>
            </div>
          ) : <span className="text-text-muted text-xs">—</span>}
        </td>

        {/* House from Lagna */}
        {showLagna && (
          <td className="py-2 px-2 text-center">
            {p.house_from_lagna != null ? (
              <span className="text-sm font-mono tabular-nums text-text-muted">
                {ordinal(p.house_from_lagna)}
              </span>
            ) : <span className="text-text-muted text-xs">—</span>}
          </td>
        )}

        {/* Moon score */}
        <td className="py-2 px-2 text-right">
          <span className="text-sm font-mono tabular-nums font-semibold"
            style={{ color: p.score > 0 ? SHUBH : p.score < 0 ? ASHUBH : NEUTRAL }}>
            {scoreLabel(p.score)}
          </span>
        </td>

        {/* Lagna score */}
        {showLagna && (
          <td className="py-2 pr-3 pl-2 text-right">
            <span className="text-sm font-mono tabular-nums"
              style={{ color: p.lagna_score > 0 ? SHUBH : p.lagna_score < 0 ? ASHUBH : NEUTRAL }}>
              {scoreLabel(p.lagna_score)}
            </span>
          </td>
        )}

        {/* Key note */}
        <td className="py-2 px-2 max-w-[200px]">
          <div className="flex items-center gap-1.5">
            {p.vedha_active && (
              <span className="text-[9px] font-mono px-1 py-0.5 rounded" style={{ backgroundColor: "#94a3b810", color: NEUTRAL }}>
                Vedha
              </span>
            )}
            {p.effects[0] && (
              <span className="text-[11px] text-text-muted truncate">{p.effects[0]}</span>
            )}
          </div>
        </td>
      </tr>

      {/* Expanded effects row */}
      {open && p.effects.length > 0 && (
        <tr className="border-b border-hairline">
          <td colSpan={showLagna ? 6 : 4} className="pb-2 pt-0 px-3">
            <ul className="space-y-0.5 pl-3">
              {p.effects.map((e, i) => (
                <li key={i} className="text-[11px] text-text-muted list-disc">{e}</li>
              ))}
            </ul>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function GocharPanel({ chart }: { chart: ChartData }) {
  const [data, setData] = useState<GocharData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    postCvce<GocharData>("gochar", {
      birth_datetime: chart.meta?.birth_datetime,
      birth_lat: chart.meta?.birth_lat,
      birth_lon: chart.meta?.birth_lon,
      birth_tz: chart.meta?.birth_tz,
    })
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch((e) => { if (!cancelled) { setError(e.message); setLoading(false); } });

    return () => { cancelled = true; };
  }, [chart]);

  if (loading) {
    return (
      <div className="flex items-center gap-3 py-12 text-text-muted text-sm font-mono">
        <Loader className="w-4 h-4 animate-spin" style={{ color: "#7c3aed" }} />
        Computing transit assessment…
      </div>
    );
  }

  if (error || !data) {
    return (
      <p className="text-sm font-mono text-text-muted py-6">
        Could not load transit data. {error}
      </p>
    );
  }

  const showLagna = data.lagna_rashi != null;
  const alerts: { icon: "warn" | "info"; title: string; body: string }[] = [];

  if (data.sade_sati) {
    alerts.push({
      icon: "warn",
      title: `Sade Sati — ${data.sade_sati.phase.charAt(0).toUpperCase() + data.sade_sati.phase.slice(1)} Phase`,
      body: data.sade_sati.effect,
    });
  }
  if (data.ashtama_shani) {
    alerts.push({ icon: "warn", title: "Ashtama Shani", body: data.ashtama_shani.effect });
  }
  if (data.kantaka_shani) {
    alerts.push({ icon: "warn", title: "Kantaka Shani", body: data.kantaka_shani.effect });
  }
  if (data.tara_balam) {
    alerts.push({
      icon: data.tara_balam.verdict === "ashubh" ? "warn" : "info",
      title: `Tara Balam: ${data.tara_balam.name} (Paryaya ${data.tara_balam.paryaya})`,
      body: data.tara_balam.description ?? "",
    });
  }
  if (data.moorthy) {
    alerts.push({
      icon: data.moorthy.verdict === "ashubh" ? "warn" : "info",
      title: `Moorthy Nirnaya: ${data.moorthy.name}`,
      body: data.moorthy.description,
    });
  }

  return (
    <div className="space-y-4">

      {/* ── Reference context ──────────────────────────────────────────────── */}
      <div className="text-[11px] font-mono text-text-muted">
        Transit scores as of{" "}
        <span className="text-text-main">{fmtDate(data.date)}</span>
        {data.janma_rashi && (
          <> · Janma Rashi <span style={{ color: MOON_C }}>{data.janma_rashi}</span>{" "}
            {data.janma_nakshatra && <span className="text-text-muted">({data.janma_nakshatra})</span>}
          </>
        )}
        {data.lagna_rashi && (
          <> · Lagna <span style={{ color: LAGNA_C }}>{data.lagna_rashi}</span></>
        )}
      </div>

      {/* ── Score cards ────────────────────────────────────────────────────── */}
      <div className="flex gap-3">
        <ScoreOrb score={data.overall_score} label="From Moon (Janma Rashi)" color={MOON_C} />
        {showLagna && (
          <ScoreOrb score={data.lagna_overall_score} label="From Lagna (Ascendant)" color={LAGNA_C} />
        )}
      </div>

      {/* ── Alerts ─────────────────────────────────────────────────────────── */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((a, i) => <AlertBanner key={i} {...a} />)}
        </div>
      )}

      {/* ── Planet impact table ─────────────────────────────────────────────── */}
      <div className="rounded-xl border border-hairline overflow-hidden">
        <div className="px-3 py-2 border-b border-hairline bg-card/50">
          <p className="text-[9px] font-mono uppercase tracking-widest text-text-muted">
            Planet-by-planet impact · click a row to expand effects
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-hairline">
                <th className="text-left text-[9px] font-mono uppercase tracking-wider text-text-muted py-2 pl-3 pr-2">Planet</th>
                <th className="text-center text-[9px] font-mono uppercase tracking-wider text-text-muted py-2 px-2">
                  <span style={{ color: MOON_C }}>H☽</span>
                </th>
                {showLagna && (
                  <th className="text-center text-[9px] font-mono uppercase tracking-wider text-text-muted py-2 px-2">
                    <span style={{ color: LAGNA_C }}>H↑</span>
                  </th>
                )}
                <th className="text-right text-[9px] font-mono uppercase tracking-wider py-2 px-2">
                  <span style={{ color: MOON_C }}>Score☽</span>
                </th>
                {showLagna && (
                  <th className="text-right text-[9px] font-mono uppercase tracking-wider py-2 pr-3 pl-2">
                    <span style={{ color: LAGNA_C }}>Score↑</span>
                  </th>
                )}
                <th className="text-left text-[9px] font-mono uppercase tracking-wider text-text-muted py-2 px-2">Effect</th>
              </tr>
            </thead>
            <tbody>
              {data.planets.map((p) => (
                <PlanetRow key={p.planet} p={p} showLagna={showLagna} />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Synthesis note ─────────────────────────────────────────────────── */}
      {data.synthesis && data.synthesis !== "No natal chart — transit-only analysis" && (
        <p className="text-[11px] text-text-muted leading-relaxed font-mono border-l-2 pl-3"
          style={{ borderColor: "#7c3aed44" }}>
          {data.synthesis}
        </p>
      )}
    </div>
  );
}
