"use client";

import { useState } from "react";
import { Heart, Loader, AlertTriangle } from "lucide-react";
import { postCvce } from "@/lib/cvce-client";

interface PartnerInput {
  name: string;
  birth_datetime: string;
  birth_lat: string;
  birth_lon: string;
  birth_tz: string;
}

interface KootaItem {
  name: string;
  score: number;
  max: number;
}

interface KujaDoshaStatus {
  has_dosha: boolean;
  cancellation?: string | null;
}

interface KootaResult {
  total_score: number;
  verdict: string;
  kootas: KootaItem[];
  kuja_dosha_a: KujaDoshaStatus;
  kuja_dosha_b: KujaDoshaStatus;
  ke_version?: string;
}

const KOOTA_LABELS: Record<string, string> = {
  Varna: "Varna (caste / spiritual compatibility)",
  Vashya: "Vashya (mutual control & influence)",
  Tara: "Tara (birth star / longevity)",
  Yoni: "Yoni (sexual & instinctual nature)",
  Graha: "Graha Maitri (planetary friendship)",
  Gana: "Gana (temperament — deva/manushya/rakshasa)",
  Bhakoot: "Bhakoot (lunar sign relationship)",
  Nadi: "Nadi (prakriti / health of progeny)",
};

const KOOTA_ORDER = [
  "Varna",
  "Vashya",
  "Tara",
  "Yoni",
  "Graha",
  "Gana",
  "Bhakoot",
  "Nadi",
];

const KOOTA_API_KEYS: Record<string, string> = {
  Varna: "varna",
  Vashya: "vashya",
  Tara: "tara",
  Yoni: "yoni",
  Graha: "grahaMaitri",
  Gana: "gana",
  Bhakoot: "bhakoot",
  Nadi: "nadi",
};

interface KootaApiResponse {
  totalScore: number;
  verdict: string;
  breakdown: Record<string, { score: number; max: number; name?: string }>;
  kujaDosha?: {
    bride: boolean;
    groom: boolean;
    note?: string;
  };
  ke_version?: string;
}

function mapKootaResponse(raw: KootaApiResponse): KootaResult {
  const breakdown = raw.breakdown ?? {};
  return {
    total_score: raw.totalScore,
    verdict: raw.verdict,
    kootas: KOOTA_ORDER.map((name) => {
      const item = breakdown[KOOTA_API_KEYS[name]];
      return { name, score: item?.score ?? 0, max: item?.max ?? 0 };
    }),
    kuja_dosha_a: {
      has_dosha: raw.kujaDosha?.bride ?? false,
      cancellation:
        raw.kujaDosha?.bride && raw.kujaDosha?.groom
          ? raw.kujaDosha.note ?? "Both partners Manglik — dosha cancelled"
          : null,
    },
    kuja_dosha_b: {
      has_dosha: raw.kujaDosha?.groom ?? false,
      cancellation:
        raw.kujaDosha?.bride && raw.kujaDosha?.groom
          ? raw.kujaDosha.note ?? "Both partners Manglik — dosha cancelled"
          : null,
    },
    ke_version: raw.ke_version,
  };
}

const DEFAULT_PARTNER_A: PartnerInput = {
  name: "Mohan",
  birth_datetime: "1975-04-22T19:15:00",
  birth_lat: "12.2958",
  birth_lon: "76.6394",
  birth_tz: "5.5",
};

const EMPTY_PARTNER: PartnerInput = {
  name: "",
  birth_datetime: "",
  birth_lat: "",
  birth_lon: "",
  birth_tz: "",
};

const field =
  "w-full rounded-lg border border-hairline bg-card px-3 py-2 text-sm outline-none focus:border-accent transition-colors";
const label = "block text-xs font-medium text-text-muted mb-1.5";

function PartnerForm({
  title,
  value,
  onChange,
}: {
  title: string;
  value: PartnerInput;
  onChange: (p: PartnerInput) => void;
}) {
  return (
    <div className="flex-1 min-w-0">
      <h3 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">
        {title}
      </h3>
      <div className="flex flex-col gap-3">
        <div>
          <label className={label}>Name</label>
          <input
            className={field}
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
            placeholder="Name"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={label}>Birth date</label>
            <input
              className={field}
              type="date"
              value={value.birth_datetime.slice(0, 10)}
              onChange={(e) => {
                const time = value.birth_datetime.slice(11, 16) || "12:00";
                onChange({
                  ...value,
                  birth_datetime: e.target.value
                    ? `${e.target.value}T${time}:00`
                    : "",
                });
              }}
            />
          </div>
          <div>
            <label className={label}>Birth time</label>
            <input
              className={field}
              type="time"
              value={value.birth_datetime.slice(11, 16)}
              onChange={(e) => {
                const date = value.birth_datetime.slice(0, 10) || "2000-01-01";
                onChange({
                  ...value,
                  birth_datetime: e.target.value
                    ? `${date}T${e.target.value}:00`
                    : "",
                });
              }}
            />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={label}>Lat</label>
            <input
              className={field}
              inputMode="decimal"
              value={value.birth_lat}
              onChange={(e) =>
                onChange({ ...value, birth_lat: e.target.value })
              }
              placeholder="12.30"
            />
          </div>
          <div>
            <label className={label}>Lon</label>
            <input
              className={field}
              inputMode="decimal"
              value={value.birth_lon}
              onChange={(e) =>
                onChange({ ...value, birth_lon: e.target.value })
              }
              placeholder="76.65"
            />
          </div>
          <div>
            <label className={label}>TZ</label>
            <input
              className={field}
              inputMode="decimal"
              value={value.birth_tz}
              onChange={(e) =>
                onChange({ ...value, birth_tz: e.target.value })
              }
              placeholder="5.5"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function KootaBar({ item }: { item: KootaItem }) {
  const pct = item.max > 0 ? (item.score / item.max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-muted w-24 shrink-0 truncate">
        {item.name}
      </span>
      <div className="flex-1 h-2 rounded-full bg-[color-mix(in_srgb,var(--color-accent)_10%,transparent)] overflow-hidden">
        <div
          className="h-full rounded-full bg-accent transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-text-muted w-10 text-right tabular-nums">
        {item.score}/{item.max}
      </span>
    </div>
  );
}

export function KootaMatcher() {
  const [partnerA, setPartnerA] = useState<PartnerInput>(DEFAULT_PARTNER_A);
  const [partnerB, setPartnerB] = useState<PartnerInput>(EMPTY_PARTNER);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<KootaResult | null>(null);

  async function handleMatch() {
    if (!partnerA.birth_datetime || !partnerB.birth_datetime) {
      setError("Both partners need a birth date and time.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const raw = await postCvce<KootaApiResponse>("koota-match", {
        bride: {
          birth_datetime: partnerA.birth_datetime,
          birth_lat: parseFloat(partnerA.birth_lat) || 0,
          birth_lon: parseFloat(partnerA.birth_lon) || 0,
          birth_tz: parseFloat(partnerA.birth_tz) || 0,
        },
        groom: {
          birth_datetime: partnerB.birth_datetime,
          birth_lat: parseFloat(partnerB.birth_lat) || 0,
          birth_lon: parseFloat(partnerB.birth_lon) || 0,
          birth_tz: parseFloat(partnerB.birth_tz) || 0,
        },
      });
      setResult(mapKootaResponse(raw));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Matching failed.");
    } finally {
      setLoading(false);
    }
  }

  function scoreColor(score: number) {
    if (score >= 28) return "text-success";
    if (score >= 21) return "text-[#c5a46e]";
    if (score >= 18) return "text-warning";
    return "text-danger";
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-6 flex-col sm:flex-row">
        <PartnerForm
          title="Partner A"
          value={partnerA}
          onChange={setPartnerA}
        />
        <div className="hidden sm:flex items-center pt-7">
          <Heart className="h-5 w-5 text-accent/40" />
        </div>
        <PartnerForm
          title="Partner B"
          value={partnerB}
          onChange={setPartnerB}
        />
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-danger bg-danger/10 rounded-xl px-4 py-3">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <button
        onClick={handleMatch}
        disabled={loading}
        className="inline-flex items-center justify-center gap-2 font-medium rounded-xl transition-all duration-200 active:scale-[0.985] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:opacity-50 disabled:pointer-events-none bg-accent text-accent-fg hover:bg-accent-strong px-6 py-3 min-h-[44px] shadow-sm w-full sm:w-auto"
      >
        {loading ? (
          <>
            <Loader className="h-4 w-4 animate-spin" />
            Matching…
          </>
        ) : (
          <>
            <Heart className="h-4 w-4" />
            Match
          </>
        )}
      </button>

      {result && (
        <div className="rounded-2xl border border-hairline bg-card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs text-text-muted font-mono uppercase tracking-wider">
                Guna Milan Score
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span
                  className={`text-3xl font-display tabular-nums ${scoreColor(result.total_score)}`}
                >
                  {result.total_score}
                </span>
                <span className="text-lg text-text-muted font-mono">
                  / 36
                </span>
              </div>
            </div>
            <span
              className={`text-sm font-medium px-3 py-1.5 rounded-full ${scoreColor(result.total_score)} bg-[color-mix(in_srgb,currentColor_12%,transparent)]`}
            >
              {result.verdict}
            </span>
          </div>

          <div className="space-y-2">
            {KOOTA_ORDER.map((name) => {
              const item = result.kootas.find((k) => k.name === name);
              if (!item) return null;
              return <KootaBar key={name} item={item} />;
            })}
          </div>

          <div className="border-t border-hairline pt-4 space-y-3">
            <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider">
              Kuja Dosha (Manglik)
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-hairline p-3">
                <p className="text-xs text-text-muted mb-1">Partner A</p>
                <span
                  className={`text-sm font-medium ${result.kuja_dosha_a.has_dosha ? "text-danger" : "text-success"}`}
                >
                  {result.kuja_dosha_a.has_dosha
                    ? "Manglik"
                    : "Not Manglik"}
                </span>
                {result.kuja_dosha_a.cancellation && (
                  <p className="mt-1 text-[11px] text-text-muted">
                    Cancellation: {result.kuja_dosha_a.cancellation}
                  </p>
                )}
              </div>
              <div className="rounded-xl border border-hairline p-3">
                <p className="text-xs text-text-muted mb-1">Partner B</p>
                <span
                  className={`text-sm font-medium ${result.kuja_dosha_b.has_dosha ? "text-danger" : "text-success"}`}
                >
                  {result.kuja_dosha_b.has_dosha
                    ? "Manglik"
                    : "Not Manglik"}
                </span>
                {result.kuja_dosha_b.cancellation && (
                  <p className="mt-1 text-[11px] text-text-muted">
                    Cancellation: {result.kuja_dosha_b.cancellation}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {result?.ke_version && (
        <div className="text-[10px] text-text-muted font-mono">
          Knowledge source: traditional koota tables (static) • ke: {result.ke_version}
        </div>
      )}
    </div>
  );
}
