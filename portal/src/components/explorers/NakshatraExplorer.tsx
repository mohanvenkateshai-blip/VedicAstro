"use client";

import { useState, useMemo } from "react";
import { Search, Filter, ChevronDown, ChevronUp } from "lucide-react";
import { clsx } from "clsx";

const NAKSHATRAS = [
  { name: "Ashwini", lord: "Ketu", deity: "Ashwini Kumaras", nature: "Light", gana: "Deva", yoni: "Horse", padas: [{ sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }], myth: "The divine twin physicians of the gods, born from the Sun and a mare. They represent healing and swift action." },
  { name: "Bharani", lord: "Venus", deity: "Yama", nature: "Fierce", gana: "Manushya", yoni: "Elephant", padas: [{ sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }], myth: "Presided over by Yama, the god of death and dharma. Represents restraint, morality, and the cycle of life." },
  { name: "Krittika", lord: "Sun", deity: "Agni", nature: "Mixed", gana: "Rakshasa", yoni: "Sheep", padas: [{ sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }, { sign: "Aries", lord: "Mars" }], myth: "Ruled by Agni, the fire god. Represents purification, sharpness, and the nurturing flame. Associated with the Pleiades star cluster." },
  { name: "Rohini", lord: "Moon", deity: "Brahma/Prajapati", nature: "Fixed", gana: "Manushya", yoni: "Serpent", padas: [{ sign: "Taurus", lord: "Venus" }, { sign: "Taurus", lord: "Venus" }, { sign: "Taurus", lord: "Venus" }, { sign: "Taurus", lord: "Venus" }], myth: "The red one, most beloved of the Moon. Represents growth, creativity, fertility, and the arts. Considered the most auspicious nakshatra for weddings." },
  { name: "Mrigashira", lord: "Mars", deity: "Soma", nature: "Soft", gana: "Deva", yoni: "Serpent", padas: [{ sign: "Taurus", lord: "Venus" }, { sign: "Taurus", lord: "Venus" }, { sign: "Gemini", lord: "Mercury" }, { sign: "Gemini", lord: "Mercury" }], myth: "The deer's head. Represents searching, seeking, and gentle exploration. Soma, the divine nectar, brings bliss and inspiration." },
  { name: "Ardra", lord: "Rahu", deity: "Rudra", nature: "Sharp", gana: "Manushya", yoni: "Dog", padas: [{ sign: "Gemini", lord: "Mercury" }, { sign: "Gemini", lord: "Mercury" }, { sign: "Gemini", lord: "Mercury" }, { sign: "Gemini", lord: "Mercury" }], myth: "The moist one, symbolized by a teardrop. Rudra (Shiva's fierce form) brings destruction that enables transformation. Represents storm and cleansing." },
  { name: "Punarvasu", lord: "Jupiter", deity: "Aditi", nature: "Movable", gana: "Deva", yoni: "Cat", padas: [{ sign: "Gemini", lord: "Mercury" }, { sign: "Gemini", lord: "Mercury" }, { sign: "Gemini", lord: "Mercury" }, { sign: "Cancer", lord: "Moon" }], myth: "The return of light. Aditi, the universal mother, represents abundance, renewal, and infinite possibilities. Associated with homecoming." },
  { name: "Pushya", lord: "Saturn", deity: "Brihaspati", nature: "Light", gana: "Deva", yoni: "Ram", padas: [{ sign: "Cancer", lord: "Moon" }, { sign: "Cancer", lord: "Moon" }, { sign: "Cancer", lord: "Moon" }, { sign: "Cancer", lord: "Moon" }], myth: "The nourisher. Priestly Brihaspati represents wisdom, teaching, and spiritual guidance. Considered the most auspicious nakshatra overall." },
  { name: "Ashlesha", lord: "Mercury", deity: "Naga/Serpent", nature: "Sharp", gana: "Rakshasa", yoni: "Cat", padas: [{ sign: "Cancer", lord: "Moon" }, { sign: "Cancer", lord: "Moon" }, { sign: "Cancer", lord: "Moon" }, { sign: "Cancer", lord: "Moon" }], myth: "The entwiner. Naga serpents represent kundalini energy, hidden knowledge, and psychological depth. Can be mystical or manipulative." },
  { name: "Magha", lord: "Ketu", deity: "Pitris (Ancestors)", nature: "Fierce", gana: "Rakshasa", yoni: "Rat", padas: [{ sign: "Leo", lord: "Sun" }, { sign: "Leo", lord: "Sun" }, { sign: "Leo", lord: "Sun" }, { sign: "Leo", lord: "Sun" }], myth: "The mighty ones. Ancestral spirits grant authority, lineage pride, and material power. Connected to the throne and royal succession." },
  { name: "Purva Phalguni", lord: "Venus", deity: "Bhaga", nature: "Fierce", gana: "Manushya", yoni: "Rat", padas: [{ sign: "Leo", lord: "Sun" }, { sign: "Leo", lord: "Sun" }, { sign: "Leo", lord: "Sun" }, { sign: "Leo", lord: "Sun" }], myth: "The former reddish one. Bhaga, god of marital bliss and prosperity, grants love, relaxation, and enjoyment. Associated with creative leisure." },
  { name: "Uttara Phalguni", lord: "Sun", deity: "Aryaman", nature: "Fixed", gana: "Manushya", yoni: "Cow", padas: [{ sign: "Leo", lord: "Sun" }, { sign: "Leo", lord: "Sun" }, { sign: "Virgo", lord: "Mercury" }, { sign: "Virgo", lord: "Mercury" }], myth: "The latter reddish one. Aryaman, god of contracts and unions, brings lasting partnerships, patronage, and formal agreements." },
  { name: "Hasta", lord: "Moon", deity: "Savitar", nature: "Light", gana: "Deva", yoni: "Buffalo", padas: [{ sign: "Virgo", lord: "Mercury" }, { sign: "Virgo", lord: "Mercury" }, { sign: "Virgo", lord: "Mercury" }, { sign: "Virgo", lord: "Mercury" }], myth: "The hand. Savitar, the solar deity of skill, grants craftsmanship, dexterity, and healing through hands." },
  { name: "Chitra", lord: "Mars", deity: "Vishwakarma", nature: "Soft", gana: "Rakshasa", yoni: "Tiger", padas: [{ sign: "Virgo", lord: "Mercury" }, { sign: "Virgo", lord: "Mercury" }, { sign: "Libra", lord: "Venus" }, { sign: "Libra", lord: "Venus" }], myth: "The brilliant one. Vishwakarma, divine architect, grants design, beauty, and creative genius. Associated with Spica, the bright star." },
  { name: "Swati", lord: "Rahu", deity: "Vayu", nature: "Movable", gana: "Deva", yoni: "Buffalo", padas: [{ sign: "Libra", lord: "Venus" }, { sign: "Libra", lord: "Venus" }, { sign: "Libra", lord: "Venus" }, { sign: "Libra", lord: "Venus" }], myth: "The independent one. Vayu, wind god, brings freedom, movement, and adaptability. Represented by a young sprout swaying in the wind." },
  { name: "Vishakha", lord: "Jupiter", deity: "Indra/Agni", nature: "Mixed", gana: "Rakshasa", yoni: "Tiger", padas: [{ sign: "Libra", lord: "Venus" }, { sign: "Libra", lord: "Venus" }, { sign: "Libra", lord: "Venus" }, { sign: "Scorpio", lord: "Mars" }], myth: "The forked one. Twin deities Indra-Agni bring ambition, determination, and the drive to achieve goals. Associated with branching paths." },
  { name: "Anuradha", lord: "Saturn", deity: "Mitra", nature: "Soft", gana: "Deva", yoni: "Hare", padas: [{ sign: "Scorpio", lord: "Mars" }, { sign: "Scorpio", lord: "Mars" }, { sign: "Scorpio", lord: "Mars" }, { sign: "Scorpio", lord: "Mars" }], myth: "Following success. Mitra, god of friendship and partnership, brings loyalty, devotion, and collaborative achievement." },
  { name: "Jyeshtha", lord: "Mercury", deity: "Indra", nature: "Sharp", gana: "Rakshasa", yoni: "Hare", padas: [{ sign: "Scorpio", lord: "Mars" }, { sign: "Scorpio", lord: "Mars" }, { sign: "Scorpio", lord: "Mars" }, { sign: "Sagittarius", lord: "Jupiter" }], myth: "The eldest. Indra, king of gods, grants authority, seniority, and protective power. Represents mature responsibility and leadership." },
  { name: "Mula", lord: "Ketu", deity: "Nirriti", nature: "Sharp", gana: "Rakshasa", yoni: "Dog", padas: [{ sign: "Sagittarius", lord: "Jupiter" }, { sign: "Sagittarius", lord: "Jupiter" }, { sign: "Sagittarius", lord: "Jupiter" }, { sign: "Sagittarius", lord: "Jupiter" }], myth: "The root. Nirriti, goddess of dissolution, represents deep inquiry, destruction of false roots, and spiritual liberation." },
  { name: "Purva Ashadha", lord: "Venus", deity: "Apah (Waters)", nature: "Fierce", gana: "Manushya", yoni: "Monkey", padas: [{ sign: "Sagittarius", lord: "Jupiter" }, { sign: "Sagittarius", lord: "Jupiter" }, { sign: "Sagittarius", lord: "Jupiter" }, { sign: "Sagittarius", lord: "Jupiter" }], myth: "The early victory. Water deities grant invigoration, purification, and the energy to persist. Represents the power of rejuvenation." },
  { name: "Uttara Ashadha", lord: "Sun", deity: "Vishwadevas", nature: "Fixed", gana: "Manushya", yoni: "Mongoose", padas: [{ sign: "Sagittarius", lord: "Jupiter" }, { sign: "Sagittarius", lord: "Jupiter" }, { sign: "Capricorn", lord: "Saturn" }, { sign: "Capricorn", lord: "Saturn" }], myth: "The later victory. The universal gods grant lasting achievement, enduring success, and the integrity to finish what was started." },
  { name: "Shravana", lord: "Moon", deity: "Vishnu", nature: "Movable", gana: "Deva", yoni: "Monkey", padas: [{ sign: "Capricorn", lord: "Saturn" }, { sign: "Capricorn", lord: "Saturn" }, { sign: "Capricorn", lord: "Saturn" }, { sign: "Capricorn", lord: "Saturn" }], myth: "The listener. Vishnu, the preserver, grants wisdom through listening, learning, and oral tradition. The three footsteps of Vamana avatar." },
  { name: "Dhanishta", lord: "Mars", deity: "Vasus (Eight Gods)", nature: "Movable", gana: "Rakshasa", yoni: "Lion", padas: [{ sign: "Capricorn", lord: "Saturn" }, { sign: "Capricorn", lord: "Saturn" }, { sign: "Aquarius", lord: "Saturn" }, { sign: "Aquarius", lord: "Saturn" }], myth: "The wealthiest. Eight Vasus (elemental gods) grant prosperity, music, rhythm, and communal celebration. Associated with drums and dance." },
  { name: "Shatabhisha", lord: "Rahu", deity: "Varuna", nature: "Movable", gana: "Rakshasa", yoni: "Horse", padas: [{ sign: "Aquarius", lord: "Saturn" }, { sign: "Aquarius", lord: "Saturn" }, { sign: "Aquarius", lord: "Saturn" }, { sign: "Aquarius", lord: "Saturn" }], myth: "Hundred physicians. Varuna, god of cosmic waters and divine law, grants healing, truth, and mystical insight. Represented by an empty circle." },
  { name: "Purva Bhadrapada", lord: "Jupiter", deity: "Aja Ekapada", nature: "Fierce", gana: "Manushya", yoni: "Lion", padas: [{ sign: "Aquarius", lord: "Saturn" }, { sign: "Aquarius", lord: "Saturn" }, { sign: "Aquarius", lord: "Saturn" }, { sign: "Pisces", lord: "Jupiter" }], myth: "The early blessed feet. The one-footed serpent (Rudra form) represents transformation through fire, tapasya (austerity), and spiritual burning." },
  { name: "Uttara Bhadrapada", lord: "Saturn", deity: "Ahirbudhnya", nature: "Fixed", gana: "Manushya", yoni: "Cow", padas: [{ sign: "Pisces", lord: "Jupiter" }, { sign: "Pisces", lord: "Jupiter" }, { sign: "Pisces", lord: "Jupiter" }, { sign: "Pisces", lord: "Jupiter" }], myth: "The later blessed feet. The serpent of the deep grants depth, stability, and protection. Represents the cosmic ocean and the kundalini at rest." },
  { name: "Revati", lord: "Mercury", deity: "Pushan", nature: "Soft", gana: "Deva", yoni: "Elephant", padas: [{ sign: "Pisces", lord: "Jupiter" }, { sign: "Pisces", lord: "Jupiter" }, { sign: "Pisces", lord: "Jupiter" }, { sign: "Pisces", lord: "Jupiter" }], myth: "The wealthy one. Pushan, the nourisher and guide of travelers, grants safe passage, abundance, and completion. The final nakshatra, representing closure." },
] as const;

const LORD_DETAILS: Record<string, string> = {
  Ketu: "South Node — detachment, liberation, past-life karma, spiritual insight, and the moksha path.",
  Venus: "Shukra — love, beauty, arts, luxury, relationships, creativity, and refined pleasure.",
  Sun: "Surya — the soul, authority, vitality, leadership, self-expression, and royal power.",
  Moon: "Chandra — the mind, emotions, nourishment, intuition, motherhood, and public life.",
  Mars: "Mangala — courage, action, energy, aggression, initiative, and competitive drive.",
  Rahu: "North Node — obsession, ambition, materialism, unconventional paths, and worldly desire.",
  Jupiter: "Guru — wisdom, expansion, fortune, teaching, divine grace, and spiritual guidance.",
  Saturn: "Shani — discipline, delay, structure, endurance, karmic lessons, and slow mastery.",
  Mercury: "Budha — intellect, communication, commerce, adaptability, wit, and analytical skill.",
};

const GANA_STYLES: Record<string, string> = {
  Deva: "bg-success/10 text-success border-success/25",
  Manushya: "bg-warning/10 text-warning border-warning/25",
  Rakshasa: "bg-danger/10 text-danger border-danger/25",
};

const LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"];
const NATURES = ["Fixed", "Soft", "Light", "Sharp", "Movable", "Fierce", "Mixed"];
const GANAS = ["Deva", "Manushya", "Rakshasa"];

const selectClass =
  "rounded-lg border border-hairline bg-card px-3 py-2 text-xs outline-none focus:border-accent transition-colors text-text-main appearance-none cursor-pointer";

const labelClass = "font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted";

export default function NakshatraExplorer() {
  const [expandedName, setExpandedName] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterLord, setFilterLord] = useState("");
  const [filterNature, setFilterNature] = useState("");
  const [filterGana, setFilterGana] = useState("");

  const filtered = useMemo(() => {
    return NAKSHATRAS.filter((n) => {
      if (filterLord && n.lord !== filterLord) return false;
      if (filterNature && n.nature !== filterNature) return false;
      if (filterGana && n.gana !== filterGana) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (
          !n.name.toLowerCase().includes(q) &&
          !n.deity.toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [filterLord, filterNature, filterGana, searchQuery]);

  const toggleExpand = (name: string) => {
    setExpandedName(expandedName === name ? null : name);
  };

  const hasActiveFilters = filterLord || filterNature || filterGana || searchQuery;

  return (
    <section className="w-full max-w-7xl mx-auto py-10">
      <div className="mb-8">
        <h2 className="font-display text-3xl text-text-main mb-1">27 Nakshatras</h2>
        <p className="text-sm text-text-muted">
          The lunar mansions of Vedic astrology — each spanning 13°20' of the zodiac.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-8">
        <div className="relative flex-1 min-w-[200px] max-w-[340px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Search nakshatra or deity…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={clsx(selectClass, "pl-9 w-full cursor-text appearance-auto")}
          />
        </div>

        <div className="flex items-center gap-1.5 text-text-muted">
          <Filter className="w-3.5 h-3.5" />
          <span className={labelClass}>Filters</span>
        </div>

        <select
          value={filterLord}
          onChange={(e) => setFilterLord(e.target.value)}
          className={clsx(selectClass, "min-w-[130px]")}
        >
          <option value="">All lords</option>
          {LORDS.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>

        <select
          value={filterNature}
          onChange={(e) => setFilterNature(e.target.value)}
          className={clsx(selectClass, "min-w-[130px]")}
        >
          <option value="">All natures</option>
          {NATURES.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>

        <select
          value={filterGana}
          onChange={(e) => setFilterGana(e.target.value)}
          className={clsx(selectClass, "min-w-[130px]")}
        >
          <option value="">All ganas</option>
          {GANAS.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>

        {hasActiveFilters && (
          <button
            onClick={() => {
              setSearchQuery("");
              setFilterLord("");
              setFilterNature("");
              setFilterGana("");
            }}
            className="text-xs text-accent hover:underline ml-1"
          >
            Clear
          </button>
        )}
      </div>

      <p className={clsx(labelClass, "mb-5")}>
        Showing {filtered.length} of {NAKSHATRAS.length} nakshatras
      </p>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-text-muted text-sm">
          No nakshatras match the current filters.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((n) => {
          const isExpanded = expandedName === n.name;

          return (
            <div
              key={n.name}
              className={clsx(
                "rounded-2xl border border-hairline bg-card text-card-fg transition-all duration-200",
                isExpanded
                  ? "ring-1 ring-accent/40"
                  : "hover:border-accent/30 cursor-pointer",
              )}
            >
              <button
                type="button"
                className="w-full text-left p-5"
                onClick={() => toggleExpand(n.name)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="font-display text-lg text-text-main truncate">
                      {n.name}
                    </h3>
                    <p className="text-xs text-text-muted mt-0.5">{n.deity}</p>
                  </div>
                  <div className="shrink-0 flex flex-col items-end gap-1.5">
                    <span className="text-xs font-medium text-accent tabular-nums">
                      {n.lord}
                    </span>
                    <span
                      className={clsx(
                        "inline-block text-[10px] font-medium px-2 py-0.5 rounded-full border",
                        GANA_STYLES[n.gana],
                      )}
                    >
                      {n.gana}
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3">
                  <span className={clsx(labelClass, "text-[10px]")}>
                    {n.nature}
                  </span>
                  <span className="text-xs text-text-muted">·</span>
                  <span className="text-xs text-text-muted capitalize">
                    {n.yoni} yoni
                  </span>
                </div>

                <div className="flex items-center justify-center mt-3">
                  <ChevronDown
                    className={clsx(
                      "w-4 h-4 text-text-muted transition-transform duration-200",
                      isExpanded && "rotate-180",
                    )}
                  />
                </div>
              </button>

              {isExpanded && (
                <div className="border-t border-hairline p-5 pt-4 space-y-4">
                  <div>
                    <div className={clsx(labelClass, "mb-1.5")}>
                      Ruling planet
                    </div>
                    <p className="text-xs text-text-muted leading-relaxed">
                      <span className="text-text-main font-medium">{n.lord}</span>
                      {" — "}{LORD_DETAILS[n.lord]}
                    </p>
                  </div>

                  <div>
                    <div className={clsx(labelClass, "mb-2")}>Padas</div>
                    <div className="grid grid-cols-4 rounded-lg border border-hairline overflow-hidden">
                      {n.padas.map((p, pi) => (
                        <div
                          key={pi}
                          className={clsx(
                            "bg-card px-2 py-2.5 text-center",
                            pi < 3 && "border-r border-hairline",
                          )}
                        >
                          <div className={clsx(labelClass, "mb-1")}>
                            Pada {pi + 1}
                          </div>
                          <div className="text-xs text-text-main font-medium">
                            {p.sign}
                          </div>
                          <div className="text-[10px] text-text-muted">
                            {p.lord}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className={clsx(labelClass, "mb-1.5")}>Mythology</div>
                    <p className="text-xs text-text-muted leading-relaxed">
                      {n.myth}
                    </p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
