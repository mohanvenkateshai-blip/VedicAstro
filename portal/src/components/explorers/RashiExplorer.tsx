"use client";

import { useState, useMemo } from "react";
import { Filter, ChevronDown, ChevronUp } from "lucide-react";

interface RashiData {
  name: string;
  devanagari: string;
  glyph: string;
  element: string;
  modality: string;
  lord: string;
  bodyPart: string;
  qualities: string;
  exalted: Record<string, number>;
  debilitated: Record<string, number>;
  moolatrikona: Record<string, string>;
  own: Record<string, string>;
  keywords: string[];
}

const RASHIS: RashiData[] = [
  {
    name: "Aries",
    devanagari: "मेष",
    glyph: "♈",
    element: "Fire",
    modality: "Movable",
    lord: "Mars",
    bodyPart: "Head",
    qualities: "Courageous, pioneering, impulsive, competitive",
    exalted: { Sun: 10 },
    debilitated: { Saturn: 20 },
    moolatrikona: { Mars: "0°-12°" },
    own: { Mars: "0°-30°" },
    keywords: ["leader", "warrior", "initiator", "athlete"],
  },
  {
    name: "Taurus",
    devanagari: "वृषभ",
    glyph: "♉",
    element: "Earth",
    modality: "Fixed",
    lord: "Venus",
    bodyPart: "Face & Neck",
    qualities: "Stable, sensual, patient, stubborn",
    exalted: { Moon: 3 },
    debilitated: {},
    moolatrikona: { Moon: "3°-30°" },
    own: { Venus: "0°-30°" },
    keywords: ["builder", "artist", "banker", "loyal"],
  },
  {
    name: "Gemini",
    devanagari: "मिथुन",
    glyph: "♊",
    element: "Air",
    modality: "Dual",
    lord: "Mercury",
    bodyPart: "Arms & Lungs",
    qualities: "Curious, adaptable, witty, scattered",
    exalted: {},
    debilitated: {},
    moolatrikona: { Mercury: "15°-20°" },
    own: { Mercury: "0°-30°" },
    keywords: ["communicator", "writer", "trader", "networker"],
  },
  {
    name: "Cancer",
    devanagari: "कर्क",
    glyph: "♋",
    element: "Water",
    modality: "Movable",
    lord: "Moon",
    bodyPart: "Chest & Heart",
    qualities: "Nurturing, emotional, protective, moody",
    exalted: { Jupiter: 5 },
    debilitated: { Mars: 28 },
    moolatrikona: { Moon: "3°-30°" },
    own: { Moon: "0°-30°" },
    keywords: ["mother", "healer", "homemaker", "intuitive"],
  },
  {
    name: "Leo",
    devanagari: "सिंह",
    glyph: "♌",
    element: "Fire",
    modality: "Fixed",
    lord: "Sun",
    bodyPart: "Stomach & Spine",
    qualities: "Confident, generous, dramatic, proud",
    exalted: {},
    debilitated: {},
    moolatrikona: { Sun: "0°-20°" },
    own: { Sun: "0°-30°" },
    keywords: ["king", "performer", "leader", "creator"],
  },
  {
    name: "Virgo",
    devanagari: "कन्या",
    glyph: "♍",
    element: "Earth",
    modality: "Dual",
    lord: "Mercury",
    bodyPart: "Digestive System",
    qualities: "Analytical, precise, helpful, critical",
    exalted: { Mercury: 15 },
    debilitated: { Venus: 27 },
    moolatrikona: { Mercury: "15°-20°" },
    own: { Mercury: "0°-30°" },
    keywords: ["analyst", "healer", "craftsman", "editor"],
  },
  {
    name: "Libra",
    devanagari: "तुला",
    glyph: "♎",
    element: "Air",
    modality: "Movable",
    lord: "Venus",
    bodyPart: "Kidneys & Lower Back",
    qualities: "Diplomatic, fair, charming, indecisive",
    exalted: { Saturn: 20 },
    debilitated: { Sun: 10 },
    moolatrikona: { Venus: "0°-15°" },
    own: { Venus: "0°-30°" },
    keywords: ["diplomat", "artist", "judge", "partner"],
  },
  {
    name: "Scorpio",
    devanagari: "वृश्चिक",
    glyph: "♏",
    element: "Water",
    modality: "Fixed",
    lord: "Mars",
    bodyPart: "Reproductive Organs",
    qualities: "Intense, secretive, transformative, vengeful",
    exalted: {},
    debilitated: { Moon: 3 },
    moolatrikona: { Mars: "0°-12°", Ketu: "0°-30°" },
    own: { Mars: "0°-30°" },
    keywords: ["detective", "surgeon", "mystic", "psychologist"],
  },
  {
    name: "Sagittarius",
    devanagari: "धनु",
    glyph: "♐",
    element: "Fire",
    modality: "Dual",
    lord: "Jupiter",
    bodyPart: "Hips & Thighs",
    qualities: "Optimistic, philosophical, adventurous, blunt",
    exalted: {},
    debilitated: {},
    moolatrikona: { Jupiter: "0°-10°" },
    own: { Jupiter: "0°-30°" },
    keywords: ["guru", "explorer", "philosopher", "athlete"],
  },
  {
    name: "Capricorn",
    devanagari: "मकर",
    glyph: "♑",
    element: "Earth",
    modality: "Movable",
    lord: "Saturn",
    bodyPart: "Knees & Bones",
    qualities: "Ambitious, disciplined, practical, cold",
    exalted: { Mars: 28 },
    debilitated: { Jupiter: 5 },
    moolatrikona: { Saturn: "0°-20°" },
    own: { Saturn: "0°-30°" },
    keywords: ["CEO", "builder", "elder", "strategist"],
  },
  {
    name: "Aquarius",
    devanagari: "कुम्भ",
    glyph: "♒",
    element: "Air",
    modality: "Fixed",
    lord: "Saturn",
    bodyPart: "Ankles & Circulation",
    qualities: "Innovative, humanitarian, rebellious, detached",
    exalted: {},
    debilitated: {},
    moolatrikona: { Saturn: "0°-20°" },
    own: { Saturn: "0°-30°" },
    keywords: ["inventor", "rebel", "scientist", "humanitarian"],
  },
  {
    name: "Pisces",
    devanagari: "मीन",
    glyph: "♓",
    element: "Water",
    modality: "Dual",
    lord: "Jupiter",
    bodyPart: "Feet & Lymphatic System",
    qualities: "Compassionate, dreamy, artistic, escapist",
    exalted: { Venus: 27 },
    debilitated: { Mercury: 15 },
    moolatrikona: { Jupiter: "0°-5°", Venus: "0°-27°" },
    own: { Jupiter: "0°-30°" },
    keywords: ["mystic", "artist", "healer", "dreamer"],
  },
];

const PLANETS = [
  "Sun",
  "Moon",
  "Mars",
  "Mercury",
  "Jupiter",
  "Venus",
  "Saturn",
  "Rahu",
  "Ketu",
] as const;

const ELEMENTS = ["Fire", "Earth", "Air", "Water"] as const;
const MODALITIES = ["Movable", "Fixed", "Dual"] as const;

const ELEMENT_COLORS: Record<string, string> = {
  Fire: "text-warning bg-warning/10",
  Earth: "text-success bg-success/10",
  Air: "text-primary bg-primary/10",
  Water: "text-accent bg-accent/10",
};

type FilterKey = "element" | "modality" | "lord";

export default function RashiExplorer() {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [filters, setFilters] = useState<Record<FilterKey, string | null>>({
    element: null,
    modality: null,
    lord: null,
  });

  const lords = useMemo(
    () => [...new Set(RASHIS.map((r) => r.lord))].sort(),
    [],
  );

  const filtered = useMemo(() => {
    return RASHIS.filter((r) => {
      if (filters.element && r.element !== filters.element) return false;
      if (filters.modality && r.modality !== filters.modality) return false;
      if (filters.lord && r.lord !== filters.lord) return false;
      return true;
    });
  }, [filters.element, filters.modality, filters.lord]);

  const toggleFilter = (type: FilterKey, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [type]: prev[type] === value ? null : value,
    }));
  };

  const hasActiveFilters =
    filters.element !== null ||
    filters.modality !== null ||
    filters.lord !== null;

  const clearFilters = () => {
    setFilters({ element: null, modality: null, lord: null });
  };

  return (
    <div>
      <div className="flex flex-col gap-4 mb-8">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <Filter className="w-4 h-4" />
            <span className="font-medium">Filters</span>
          </div>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-[11px] text-text-muted hover:text-text-main transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-md px-2 py-1"
            >
              Clear all
            </button>
          )}
        </div>

        <FilterGroup
          label="Element"
          options={[...ELEMENTS]}
          active={filters.element}
          onToggle={(v) => toggleFilter("element", v)}
        />

        <FilterGroup
          label="Modality"
          options={[...MODALITIES]}
          active={filters.modality}
          onToggle={(v) => toggleFilter("modality", v)}
        />

        <FilterGroup
          label="Lord"
          options={lords}
          active={filters.lord}
          onToggle={(v) => toggleFilter("lord", v)}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {filtered.map((rashi) => {
          const originalIdx = RASHIS.indexOf(rashi);
          const isExpanded = expanded === originalIdx;

          return (
            <div
              key={rashi.name}
              className="rounded-xl border border-hairline bg-card overflow-hidden transition-shadow hover:shadow-sm"
            >
              <button
                onClick={() => setExpanded(isExpanded ? null : originalIdx)}
                className="w-full p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-t-xl"
                aria-expanded={isExpanded}
                aria-label={`${rashi.name} (${rashi.devanagari})`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className="text-3xl leading-none shrink-0"
                      aria-hidden="true"
                    >
                      {rashi.glyph}
                    </span>
                    <div className="min-w-0">
                      <h3 className="font-display text-lg font-semibold leading-tight truncate">
                        {rashi.name}
                      </h3>
                      <p className="text-sm text-text-muted font-sans">
                        {rashi.devanagari}
                      </p>
                    </div>
                  </div>
                  <div className="shrink-0 mt-0.5">
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-text-muted" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-text-muted" />
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 mt-3">
                  <span
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${ELEMENT_COLORS[rashi.element]}`}
                  >
                    {rashi.element}
                  </span>
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)] text-accent">
                    {rashi.modality}
                  </span>
                  <span className="text-[11px] text-text-muted">
                    Lord:{" "}
                    <span className="font-medium text-text-main">
                      {rashi.lord}
                    </span>
                  </span>
                </div>
              </button>

              {isExpanded && (
                <div className="border-t border-hairline p-4 space-y-4">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
                      Planetary Dignities
                    </span>
                    <div className="mt-2 overflow-x-auto rounded-lg border border-hairline">
                      <table className="w-full text-xs" aria-label="Planetary dignity table">
                        <thead>
                          <tr className="text-[10px] uppercase tracking-wider text-text-muted border-b border-hairline">
                            <th
                              scope="col"
                              className="px-2.5 py-1.5 text-left font-medium"
                            >
                              Planet
                            </th>
                            <th
                              scope="col"
                              className="px-2.5 py-1.5 text-left font-medium"
                            >
                              Exalted
                            </th>
                            <th
                              scope="col"
                              className="px-2.5 py-1.5 text-left font-medium"
                            >
                              Debil.
                            </th>
                            <th
                              scope="col"
                              className="px-2.5 py-1.5 text-left font-medium"
                            >
                              Moolatrikona
                            </th>
                            <th
                              scope="col"
                              className="px-2.5 py-1.5 text-left font-medium"
                            >
                              Own
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {PLANETS.map((planet) => {
                            const ex =
                              planet in rashi.exalted
                                ? rashi.exalted[planet as keyof typeof rashi.exalted]
                                : null;
                            const deb =
                              planet in rashi.debilitated
                                ? rashi.debilitated[planet as keyof typeof rashi.debilitated]
                                : null;
                            const mt =
                              planet in rashi.moolatrikona
                                ? rashi.moolatrikona[planet as keyof typeof rashi.moolatrikona]
                                : null;
                            const own =
                              planet in rashi.own
                                ? rashi.own[planet as keyof typeof rashi.own]
                                : null;
                            const hasAny = ex !== null || deb !== null || mt !== null || own !== null;

                            return (
                              <tr
                                key={planet}
                                className={`border-b border-hairline/60 last:border-0 ${
                                  hasAny
                                    ? "hover:bg-[color-mix(in_srgb,var(--color-accent)_5%,transparent)]"
                                    : ""
                                }`}
                              >
                                <td
                                  className={`px-2.5 py-1.5 ${
                                    hasAny ? "font-medium text-accent" : "text-text-muted"
                                  }`}
                                >
                                  {planet}
                                </td>
                                <td className="px-2.5 py-1.5 font-mono text-[10px]">
                                  {ex !== null ? `${ex}°` : "—"}
                                </td>
                                <td className="px-2.5 py-1.5 font-mono text-[10px]">
                                  {deb !== null ? `${deb}°` : "—"}
                                </td>
                                <td className="px-2.5 py-1.5 font-mono text-[10px]">
                                  {mt ?? "—"}
                                </td>
                                <td className="px-2.5 py-1.5 font-mono text-[10px]">
                                  {own ?? "—"}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
                      Body Part Ruled
                    </span>
                    <p className="mt-1 text-sm font-medium">{rashi.bodyPart}</p>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
                      Qualities
                    </span>
                    <p className="mt-1 text-sm text-text-main leading-relaxed">
                      {rashi.qualities}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
                      Associated Archetypes
                    </span>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {rashi.keywords.map((kw) => (
                        <span
                          key={kw}
                          className="text-[11px] px-2 py-0.5 rounded-full border border-hairline text-text-muted bg-[color-mix(in_srgb,var(--color-accent)_4%,transparent)]"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="rounded-2xl border border-hairline bg-card p-10 text-center">
          <p className="text-sm text-text-muted">
            No Rashis match the selected filters.
          </p>
          <button
            onClick={clearFilters}
            className="mt-3 text-xs text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-md px-2 py-1"
          >
            Clear all filters
          </button>
        </div>
      )}
    </div>
  );
}

function FilterGroup({
  label,
  options,
  active,
  onToggle,
}: {
  label: string;
  options: readonly string[];
  active: string | null;
  onToggle: (value: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] uppercase tracking-wider text-text-muted mr-1 min-w-[56px]">
        {label}
      </span>
      <div className="inline-flex rounded-lg border border-hairline p-0.5 flex-wrap">
        {options.map((opt) => (
          <button
            key={opt}
            onClick={() => onToggle(opt)}
            className={`px-2.5 py-1.5 min-h-[44px] rounded-md text-[11px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ${
              active === opt
                ? "bg-accent text-accent-fg"
                : "text-text-muted hover:text-text-main"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
