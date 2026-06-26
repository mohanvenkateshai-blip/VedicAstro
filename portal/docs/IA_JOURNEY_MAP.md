# VedicAstro — Website Information Architecture & Journey Map

## User Personas

| Persona | Need | Frequency |
|---------|------|-----------|
| **Curious Visitor** | "What does my chart look like?" | Once |
| **Regular User** | "What's happening today for me?" | Daily |
| **Serious Student** | "Teach me the shastras behind this" | Weekly |
| **Professional Astrologer** | "I need accurate tools for clients" | Daily |
| **Couple** | "Are we compatible?" | Once |

## Navigation Architecture

```
PRIMARY NAV (top bar, always visible)
├── 🏠 Home
├── 📊 My Charts          ← saved charts + dashboard
├── 🔮 Cast Chart         ← main chart page (birth chart + all analysis)
├── ⏳ Muhurta             ← electional astrology (iframe standalone)
└── 📚 Learn               ← nakshatra/rashi explorers, classical references

SECONDARY NAV (left sidebar, visible on chart/analysis pages)
├── 📋 Chart Overview      ← birth chart, planet table, vargas
├── 🪐 Transits            ← gochar phala, animated transit, ephemeris
├── ⏱️ Dasha Timeline      ← vimshottari tree, multi-dasha view
├── ✨ Yogas & Strength    ← active yogas, shadbala, ashtakavarga
├── 💫 Special Points      ← bhrigu bindu, mandi, gulika, pushkar
├── ❤️ Compatibility       ← koota matching
├── 🌅 Varshaphala         ← solar return
├── 🔬 KP System           ← krishnamurti paddhati
├── 📜 Classical Sources   ← graph insights, citations
└── 📄 Export              ← PDF, share link

USER MENU (top right)
├── 👤 Profile
├── 📊 Dashboard
└── 🚪 Sign Out
```

## User Journeys → Page Map

### Journey 1: "Cast my birth chart"
```
Home → [Cast Chart] → BirthForm fills → Chart renders
     └── Sidebar loads with all analysis tabs
     └── "Save to My Charts" button
     └── Shareable URL generated
```

### Journey 2: "What's happening today?"
```
Dashboard → Click saved chart → Gochar Phala tab auto-loads
     └── Transit verdict card at top
     └── Planet-by-planet breakdown
     └── Animated transit timeline
     └── Year ephemeris view
     └── "Set alert for this transit" (future)
```

### Journey 3: "Are we compatible?"
```
Cast Chart → Sidebar: Compatibility → Enter Partner B details → Match button
     └── 36-point score card
     └── 8 koota breakdown bars
     └── Kuja Dosha status
     └── Nadi Dosha warning
     └── "Save both charts" option
```

### Journey 4: "When should I get married?"
```
Muhurta tab → Select activity "Marriage" → Date range → Finder runs
     └── Ranked windows with scores
     └── Panchanga breakdown per day
     └── Tara + Chandrabala overlay
     └── Best window highlighted
```

### Journey 5: "Teach me about Nakshatras"
```
Learn → Nakshatra Explorer
     └── 27-star grid with filters
     └── Click to expand: deity, lord, mythology, padas
     └── Related: which activities favor this star
     └── Related: classical verses mentioning this star
```

## Complete Page Inventory

| # | Route | Page | Primary Engine | Sidebar Tab |
|---|-------|------|---------------|-------------|
| 1 | `/` | **Home** — hero, feature cards, CTA | — | — |
| 2 | `/chart` | **Cast Chart** — birth form + full analysis | Janma Kundali | All tabs |
| 3 | `/chart/transits` | **Transit Analysis** — gochar + animated + ephemeris | Gochar Phala | Transits |
| 4 | `/chart/dasha` | **Dasha Timeline** — recursive tree + multi-system | Dasha Phala | Dasha |
| 5 | `/chart/yogas` | **Yogas & Strength** — active yogas + shadbala + SAV | Yoga Phala + Bala Nirnaya | Yogas |
| 6 | `/chart/special` | **Special Points** — bhrigu, mandi, gulika, pushkar | Special Points | Special |
| 7 | `/chart/kp` | **KP System** — placidus cusps + star/sub lords | KP Engine | KP |
| 8 | `/chart/varshaphala` | **Solar Return** — annual chart + muntha | Varshaphala | Varshaphala |
| 9 | `/chart/pdf` | **PDF Export** — formatted print layout | Rendering | Export |
| 10 | `/compatibility` | **Koota Matching** — two-chart input + score card | Koota Milan | Compatibility |
| 11 | `/muhurta` | **Muhurta Finder** — iframe standalone | Muhurta Nirnaya | — |
| 12 | `/learn/nakshatras` | **Nakshatra Explorer** — 27-star interactive grid | Shastra Pramana | — |
| 13 | `/learn/rashis` | **Rashi Explorer** — 12-sign profiles | Shastra Pramana | — |
| 14 | `/learn/yogas` | **Yoga Reference** — classical yoga catalog | Shastra Pramana | — |
| 15 | `/learn/dashas` | **Dasha Reference** — all dasha systems explained | Shastra Pramana | — |
| 16 | `/dashboard` | **My Charts** — saved charts + quick actions | Auth + DB | — |
| 17 | `/auth/signin` | **Sign In** — Google OAuth | Auth | — |

## Page Layout Template

```
┌─────────────────────────────────────────────────────────────┐
│ PRIMARY NAV: Home | My Charts | Cast Chart | Muhurta | Learn │
├──────────┬──────────────────────────────────────────────────┤
│ SIDEBAR  │                                                  │
│          │              PAGE CONTENT                        │
│ Chart ▸  │                                                  │
│ Transits │   ┌──────────────────────────────────────┐      │
│ Dasha    │   │                                      │      │
│ Yogas    │   │     Engine-powered component         │      │
│ Special  │   │     (chart / table / explorer)       │      │
│ KP       │   │                                      │      │
│ Compat.  │   └──────────────────────────────────────┘      │
│ Varsha.  │                                                  │
│ Sources  │   ┌──────────────────────────────────────┐      │
│ Export   │   │     Classical Citation Card           │      │
│          │   │     "BPHS Ch.36, v.12"               │      │
│          │   └──────────────────────────────────────┘      │
│          │                                                  │
├──────────┴──────────────────────────────────────────────────┤
│ FOOTER: Sources · Swiss Ephemeris · Lahiri · v3.0            │
└─────────────────────────────────────────────────────────────┘
```

## Information Architecture: How Features Map to Pages

```
                    ┌──────────────────┐
                    │   / (HOME PAGE)   │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
    │ /chart   │      │ /muhurta    │     │  /learn/*   │
    │ (MAIN)   │      │ (STANDALONE)│     │ (REFERENCE) │
    └────┬─────┘      └─────────────┘     └──────┬──────┘
         │                                       │
    ┌────▼────────────────────────────┐    ┌─────▼──────────┐
    │ SIDEBAR TABS (in-page anchors)  │    │ /learn/nak      │
    │                                 │    │ /learn/rashi    │
    │ #overview  → Chart + Planet     │    │ /learn/yogas    │
    │ #transits  → Gochar Engine      │    │ /learn/dashas   │
    │ #dasha     → Dasha Engine       │    └─────────────────┘
    │ #yogas     → Yoga + Bala Engine │
    │ #special   → Special Points     │    ┌──────┬──────┐
    │ #kp        → KP Engine          │    │/comp  │/dash │
    │ #varshaph  → Varshaphala Engine │    │atibil.│board │
    │ #compat    → Koota Engine       │    │       │      │
    │ #sources   → GraphRAG Citations │    └───────┴──────┘
    │ #export    → PDF/SVG Export     │
    └─────────────────────────────────┘
```

## Current page.tsx → Future Architecture

**Current:** One massive `vedicastro/page.tsx` (152 lines) with ALL 12+ components stacked vertically.

**Future:** Layout-based architecture:

```
src/app/
├── layout.tsx                    ← Root layout (nav + sidebar)
├── (main)/
│   ├── layout.tsx                ← Main layout with sidebar
│   ├── chart/
│   │   ├── page.tsx              ← /chart → Chart Overview tab active
│   │   ├── transits/page.tsx     ← /chart/transits → Transits tab
│   │   ├── dasha/page.tsx        ← /chart/dasha → Dasha tab
│   │   └── ...                   ← Each tab = separate route
│   ├── compatibility/page.tsx    ← /compatibility
│   ├── muhurta/page.tsx          ← /muhurta (existing iframe)
│   ├── learn/
│   │   ├── nakshatras/page.tsx   ← /learn/nakshatras
│   │   ├── rashis/page.tsx       ← /learn/rashis
│   │   └── yogas/page.tsx        ← /learn/yogas
│   └── dashboard/page.tsx        ← /dashboard (existing)
```

Each page calls EXACTLY ONE engine endpoint. No more monolithic fetch-all.
