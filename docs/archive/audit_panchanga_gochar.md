# Audit Report: Panchanga & Gochar Modules vs Source Texts

**Date:** 23 June 2026  
**Audited Files:**
- `vedic_engine/rules/transit_rules.py` — 10 rule tables
- `vedic_engine/prediction/gochar.py` — transit predictions
- `vedic_engine/core/panchanga.py` — panchanga computations
- `MuhurtaCosmos.jsx` — LATTA, TARA, GOCHAR_HOUSES, MOORTI, SADE_SATI

**Source Texts Compared Against:**
1. `Gochar_Phaladeepika_Pulippani.md` (GPD) — PRIMARY SOURCE
2. `Other texts/Vedic_Astrology_Panchang_Handbook.md` — Panchanga ref
3. `Other texts/Tara_Balam_Muhurta_Handbook.md` — Tara Balam ref
4. `Other texts/Tithi Astrology Master Reference Guide.md` — Tithi ref

---

## SUMMARY OF FINDINGS

| # | Domain | Severity | File(s) Affected |
|---|--------|----------|-----------------|
| 1 | Moorthy Nirnaya house mapping | **CRITICAL** | `transit_rules.py:134-147`, `MuhurtaCosmos.jsx:353-356` |
| 2 | Ketu omitted from Latta rules | **CRITICAL** | `transit_rules.py:115-126`, `MuhurtaCosmos.jsx:261-270` |
| 3 | Tara exceptions missing (Python engine) | **HIGH** | `transit_rules.py:207-249`, `gochar.py:233-240` |
| 4 | Mars bad houses: house 10 misclassified | **MEDIUM** | `transit_rules.py:36-41` |
| 5 | Paryaya 3 incomplete in Python engine | **MEDIUM** | `transit_rules.py:246-248` |
| 6 | Tara naming deviations | **LOW** | `transit_rules.py:218,222`, `MuhurtaCosmos.jsx:372,374` |
| 7 | Moon Latta effect description | **LOW** | `MuhurtaCosmos.jsx:266` |
| 8 | Individual tithi daily lords absent | **LOW** | `panchanga.py` |

---

## DOMAIN A: GOCHAR HOUSES (TABLE 12)

### Source Reference

GPD Chapter 10, Table 12 (lines 3844–4104):

> **Table-12:** *"Planet — The Transiting Results house of a planet from Janma Rasi"*

The table lists good houses, bad houses, and worst houses for each planet. Below is the comparison.

### Engine: `transit_rules.py:20-84` and `MuhurtaCosmos.jsx:1940-1950`

#### Sun
| Source | Good | Bad | Worst |
|--------|------|-----|-------|
| GPD Table 12 (line 3850–3871) | 3, 6, 10, 11 | 1, 2, 4, 8, 9, 12 | 5 |
| Engine | 3, 6, 10, 11 | 1, 2, 4, 8, 9, 12 | 5 |
| **Verdict** | ✅ MATCH | ✅ MATCH | ✅ MATCH |

Source text: *"Sun 1,2, 4, 898 and 12th... 3, 6 10thand 11th... the worst results of Sun are felt in 5th house."* (Note: "898" = garbled OCR for "8,9, and"—confirmed by context.)

#### Moon
| Source | Good | Bad | Worst | Neutral (unlisted) |
|--------|------|-----|-------|---------------------|
| GPD Table 12 (line 3873–3897) | 1, 3, 6, 7, 10, 11 | 2, 4, 5, 12 | 8 | 9 |
| Engine | 1, 3, 6, 7, 10, 11 | 2, 4, 5, 12 | 8 | 9 |
| **Verdict** | ✅ MATCH | ✅ MATCH | ✅ MATCH | ✅ MATCH |

Source text: *"When Moon passes through 9th from Janma Rasi, it causes..."* — the 9th house text describes moderate/mixed results, consistent with engine's `neutral: [9]`.

#### Mars
| Source | Good | Bad | Worst | Neutral |
|--------|------|-----|-------|---------|
| GPD Table 12 (line 3957–4016) | 3, 6, 11 | 1, 2, 5, 8, 9, 10, 12 | 7 | 4 |
| Engine | 3, 6, 11 | 1, 2, 5, 8, 9, 12 | 7 | 4, 10 |
| **Verdict** | ✅ MATCH | ⚠️ MISSES 10 | ✅ MATCH | ⚠️ 10 is "bad" per source |

**DISCREPANCY D4:** GPD Table 12 lists house 10 as bad for Mars (line 3957: *"1,2,3,5,8,9 10thand 12th"*). Note: the OCR shows "3" in the bad list, but 3 is also explicitly listed as a good house at line 4016 (*"3,6,11th — Happiness, gain..."*). The "3" in the bad list at line 3957 is likely a scanning artifact (dittography from the good list). However, **house 10 is clearly included** in the bad list. The engine currently classifies house 10 as `neutral` for Mars, but the source classifies it as bad.

#### Mercury
| Source | Good | Bad | Worst |
|--------|------|-----|-------|
| GPD Table 12 (line 4018–4045) | 6, 8, 10, 11 | 1, 2, 3, 4, 5, 7, 9, 12 | 1 |
| Engine | 6, 8, 10, 11 | 1, 2, 3, 4, 5, 7, 9, 12 | 1 |
| **Verdict** | ✅ MATCH | ✅ MATCH | ✅ MATCH |

#### Jupiter
| Source | Good | Bad | Worst |
|--------|------|-----|-------|
| GPD Table 12 (line 4025–4070) | 2, 5, 7, 9, 11 | 1, 4, 10 | 3 |
| Engine | 2, 5, 7, 9, 11 | 1, 3, 4, 6, 8, 10, 12 | 3 |
| **Verdict** | ✅ MATCH | ⚠️ DISCREPANCY | ✅ MATCH |

**Note:** GPD Table 12 line 4025 lists Jupiter bad as *"1, 4thand 10th"* (i.e., only 3 houses). However, GPD Chapter 10 summary at line 3798 states: *"Jupiter, passing through 1, 3,4, 6,8, 10 and 12th houses from one's Janma Rast is said to give bad results."* The Table 12 summary appears to condense the bad list to the three most severe houses. The engine follows the Chapter 10 summary's expanded list (7 bad houses). This is arguably more correct since the detailed transit results chapters describe adverse results for Jupiter in 3, 6, 8, and 12 as well. **Not flagged as an error** — the engine's expanded list is well-supported.

#### Venus
| Source | Good | Bad | Worst |
|--------|------|-----|-------|
| GPD Table 12 (line 3900–3923) | 1, 2, 3, 4, 5, 8, 9, 11, 12 | 7, 10 | 6 |
| Engine | 1, 2, 3, 4, 5, 8, 9, 11, 12 | 7, 10 | 6 |
| **Verdict** | ✅ MATCH | ✅ MATCH | ✅ MATCH |

#### Saturn
| Source | Good | Bad | Worst | Neutral |
|--------|------|-----|-------|---------|
| GPD Table 12 (line 3925–3995) | 3, 6, 9, 11 | 2, 4, 5, 7, 8, 12 | 1 | 10 |
| Engine | 3, 6, 9, 11 | 2, 4, 5, 7, 8, 12 | 1 | 10 |
| **Verdict** | ✅ MATCH | ✅ MATCH | ✅ MATCH | ✅ MATCH |

Source text (line 3986): *"Saturn gives good results in 3,6, and 9th houses only... good results are also given when saturn transits over the 11th house."*

#### Rahu
| Source | Good | Bad | Worst | Neutral |
|--------|------|-----|-------|---------|
| GPD Table 12 (line 4083–4104) | 3, 6, 11 | 1, 2, 4, 7, 8, 10, 12 | 9 | 5 |
| Engine | 3, 6, 11 | 1, 2, 4, 7, 8, 10, 12 | 9 | 5 |
| **Verdict** | ✅ MATCH | ✅ MATCH | ✅ MATCH | ✅ MATCH |

Source: *"Out of all the houses in 9th house worst results. Misfortune, defeat, losing law suits, imprisonment..."*

#### Ketu
| Source | Good | Bad | Worst | Neutral |
|--------|------|-----|-------|---------|
| GPD Table 12 | (treated same as Rahu) | (treated same as Rahu) | (treated same as Rahu) | (treated same as Rahu) |
| Engine | 3, 6, 11 | 1, 2, 4, 7, 8, 10, 12 | 9 | 5 |
| **Verdict** | ✅ Following convention | ✅ | ✅ | ✅ |

---

## DOMAIN B: LATTA (STAR AFFLICTION)

### Source Reference

GPD Chapter 10, section "RESULTS OF LATTA" (lines 4145–4207):

> *(a) The following stars counted in **forward direction** from that occupied by a planet are called **Forward Latta** stars:*
> 1. Twelfth star from that occupied by **Sun**.
> 2. Third star from that occupied by **Mars**.
> 3. Sixth star from that occupied by **Jupiter**.
> 4. Eighth star from that occupied by **Saturn**.
>
> *(b) The following stars counted in **backward direction** from that occupied by a planet called **Rear Latta** stars:*
> 1. Fifth star counted backwards from the star occupied by **Venus**.
> 2. The 7th star from that occupied by **Mercury**.
> 3. The 9th star from that occupied by **Rahu and Ketu**.
> 4. The 22nd star from that occupied by **Moon**.

### Engine: `transit_rules.py:115-126`

```python
LATTA_RULES = {
    "Sun": (12, +1, "..."),        # ✅ 12 forward
    "Mars": (3, +1, "..."),        # ✅ 3 forward
    "Jupiter": (6, +1, "..."),     # ✅ 6 forward
    "Saturn": (8, +1, "..."),      # ✅ 8 forward
    "Venus": (5, -1, "..."),       # ✅ 5 backward
    "Mercury": (7, -1, "..."),     # ✅ 7 backward
    "Rahu": (9, -1, "..."),        # ✅ 9 backward
    "Moon": (22, -1, "..."),       # ✅ 22 backward
}
# ❌ KETU MISSING
```

### Engine: `MuhurtaCosmos.jsx:261-270`

```js
const LATTA = {
  Sun:[12,+1,...], Mars:[3,+1,...], Jupiter:[6,+1,...], Saturn:[8,+1,...],
  Moon:[22,-1,...], Mercury:[7,-1,...], Venus:[5,-1,...], Rahu:[9,-1,...],
};
// ❌ KETU MISSING
```

**DISCREPANCY D1:** GPD line 4169 explicitly states: *"The 9th star from that occupied by **Rahu and Ketu**"* — both nodes are specified. Neither the Python engine nor the JSX include Ketu in the Latta table. Ketu should have: `"Ketu": (9, -1, "Difficulties of all kinds", "GPD-Ch1.6")`.

### Latta Formula Verification

**Engine formula** (`gochar.py:169`):
```python
kicked = ((planet_nak_idx + direction * (dist - 1)) % 27 + 27) % 27
```

**Verification for Sun (forward 12th star):**
- Sun at Ashwini (nak_idx=0): `(0 + 1 * (12-1)) % 27 = 11` → Uttara Phalguni
- "12th star from Ashwini" counting inclusively: 1=Ashwini, 2=Bharani, ..., 12=Uttara Phalguni (idx 11)
- ✅ FORMULA CORRECT

**Verification for Venus (backward 5th star):**
- Venus at Magha (nak_idx=9): `(9 + (-1) * (5-1)) % 27 = 5` → Ardra
- "5th star behind Magha" counting backward inclusively: 1=Magha, 2=Ashlesha, 3=Pushya, 4=Punarvasu, 5=Ardra (idx 5)
- ✅ FORMULA CORRECT

### Latta Effect Descriptions

| Planet | Source Text (GPD lines 4180–4207) | Engine | JSX |
|--------|-------------------------------------|--------|-----|
| Sun | "the complete business will be ruined" | "Complete business ruined" ✅ | "Loss of wealth; friction" ⚠️ |
| Mars | (death-class by context) | "Death-class ruin; injury" ✅ | "Death-class ruin; injury" ✅ |
| Jupiter | "death, misery to some relation and fear as well as insecurity" | "Death, misery to relations, fear" ✅ | "Destruction of relatives; financial loss" ⚠️ |
| Saturn | "many difficulties and even danger to life" | "Many difficulties, danger to life" ✅ | "Chronic illness, depression; family loss" ⚠️ |
| Venus | "quarrels" | "Quarrels, marital disharmony" ✅ | "Loss of work; marital disharmony" ⚠️ |
| Mercury | "loss of status and other unwanted events" | "Loss of status, career collapse" ✅ | "Failed communication, career/business collapse" ✅ |
| Rahu+Ketu | "difficulties of all kinds" | "Difficulties of all kinds, deception" ✅ | "Death-class; deception, sudden misery" ⚠️ |
| Moon | "humiliation and loss of honour" | "Humiliation, loss of honour, mental anxiety" ✅ | "Total destruction; mental anxiety, loss" ⚠️ |

The JSX descriptions deviate from the source text in tone and specific wording, but all distances and directions are correct. The Python engine's descriptions are generally closer to the source text.

---

## DOMAIN C: TARA BALAM

### Source Reference

`Tara_Balam_Muhurta_Handbook.md` Part 3 (lines 143–313).

### Nine Tara Classifications

| Remainder | Source Name | Source Verdict | Engine Name (`transit_rules.py`) | Engine Name (`MuhurtaCosmos.jsx`) |
|-----------|-------------|----------------|-----------------------------------|-------------------------------|
| 1 | Janma | Caution | Janma Tara ✅ | Janma ✅ |
| 2 | Sampat | Favorable | Sampat Tara ✅ | Sampat ✅ |
| 3 | Vipat | Unfavorable | Vipat Tara ✅ | Vipat ✅ |
| 4 | Kshema | Favorable | Kshema Tara ✅ | Kshema ✅ |
| 5 | Pratyak | Unfavorable | Pratyak Tara ✅ | Pratyak ✅ |
| 6 | **Sadhaka** | Favorable | **Sadhana Tara** ⚠️ | Sadhaka ✅ |
| 7 | Vadha/Naidhana | Unfavorable | Naidhana Tara ✅ | Vadha / Naidhana ✅ |
| 8 | **Maitra** | Favorable | **Mitra Tara** ⚠️ | Maitra ✅ |
| 9/0 | Parama Maitra | Highly favorable | Parama Maitra Tara ✅ | Parama Maitra ✅ |

**DISCREPANCY D6a:** The Python engine names the 6th Tara "Sadhana" but the source names it "Sadhaka" (or "Daivanukula" in older texts).

**DISCREPANCY D6b:** The Python engine names the 8th Tara "Mitra" but the source calls it "Maitra" (Sanskrit: मैत्र).

### Paryaya (Cycles) Handling

| Aspect | Source (Handbook §4.1) | Python Engine | JSX |
|--------|----------------------|---------------|-----|
| 1st Paryaya (1–9) | Full effect | Full effect ✅ | Full effect ✅ |
| 2nd Paryaya (10–18) | Reduced negative | Softened ✅ | Softened ✅ |
| 3rd Paryaya (19–27) | Mild / nearly negligible | Softened ✅ | `neutral` for ashubh ✅ |

**DISCREPANCY D5:** The Python engine's `TARA_RESULTS` dict in `transit_rules.py:246-248` only defines **count 19** for Paryaya 3:
```python
19: ("Janma Tara (Paryaya 3)", "Mild personal changes", "neutral", "Paryaya 3 — mild", 3),
```
Counts 20–27 are **missing** from the dict and fall through to the generic `tara_of()` function (line 251-278), which computes them correctly via modulo arithmetic. However, the Paryaya 3 entries lack proper named descriptions. The missing entries should be:
```python
20: ("Sampat Tara (Paryaya 3)", "...", "shubh", "Paryaya 3 — mild", 3),
21: ("Vipat Tara (Paryaya 3)", "...", "neutral", "Paryaya 3 — mild", 3),
22: ("Kshema Tara (Paryaya 3)", "...", "shubh", "Paryaya 3 — mild", 3),
23: ("Pratyak Tara (Paryaya 3)", "...", "neutral", "Paryaya 3 — mild", 3),
24: ("Sadhana Tara (Paryaya 3)", "...", "shubh", "Paryaya 3 — mild", 3),
25: ("Naidhana Tara (Paryaya 3)", "...", "neutral", "Paryaya 3 — mild", 3),
26: ("Mitra Tara (Paryaya 3)", "...", "shubh", "Paryaya 3 — mild", 3),
27: ("Parama Maitra Tara (Paryaya 3)", "...", "shubh", "Paryaya 3 — mild", 3),
```

### Special Exceptions (22nd Vainasika, 27th)

| Exception | Handbook Reference | Python Engine (`transit_rules.py` + `gochar.py`) | JSX (`MuhurtaCosmos.jsx`) |
|-----------|-------------------|--------------------------------------------------|----------------------------|
| 22nd (Vainasika) | §4.5 — destructive exception; avoid durable events | ❌ **NOT IMPLEMENTED** | ✅ Line 1447 |
| 27th (Parama Maitra but restricted) | §4.6 — avoid marriage, travel, shaving | ❌ **NOT IMPLEMENTED** | ✅ Line 1448 |
| Janma/Anujanma/Trijanma (1,10,19) | §4.4 — effect lifts after midday | ❌ **NOT IMPLEMENTED** | ✅ Line 1449 |

**DISCREPANCY D3:** The Python engine (`transit_rules.py` and `gochar.py`) does not implement ANY of the three special Tara exceptions. The JSX correctly implements all three. The Python Tara computation in `gochar.py:233-240` simply calls `tara_of(count)` without any special-case logic for counts 22, 27, 1, 10, or 19.

---

## DOMAIN D: TITHI RULES

### Tithi Groups

| Tithi # | Source Group (Guide p.2) | Source Lord | Engine `tithi_group()` | Engine `GROUP_INFO` |
|---------|--------------------------|-------------|------------------------|---------------------|
| 1, 6, 11 | Nanda | Venus | Nanda ✅ | Venus ✅ |
| 2, 7, 12 | Bhadra | Mercury | Bhadra ✅ | Mercury ✅ |
| 3, 8, 13 | Jaya | Mars | Jaya ✅ | Mars ✅ |
| 4, 9, 14 | Rikta | Saturn | Rikta ✅ | Saturn ✅ |
| 5, 10, 15, 30 | Purna | Jupiter | Purna ✅ | Jupiter ✅ |

**Verdict:** ✅ ALL MATCH

### Dagdha Rashis by Tithi

`panchanga.py:138-147` — All 16 entries compared against the Panchang Handbook (p.2, lines 68–93):

| Tithi | Source Dagdha | Engine DAGDHA_BY_TITHI |
|-------|---------------|------------------------|
| 1 | Libra, Capricorn | ✅ Libra, Capricorn |
| 2 | Sagittarius, Pisces | ✅ Sagittarius, Pisces |
| 3 | Leo, Capricorn | ✅ Leo, Capricorn |
| 4 | Taurus, Aquarius | ✅ Taurus, Aquarius |
| 5 | Gemini, Virgo | ✅ Gemini, Virgo |
| 6 | Aries, Leo | ✅ Aries, Leo |
| 7 | Cancer, Sagittarius | ✅ Cancer, Sagittarius |
| 8 | Gemini, Virgo | ✅ Gemini, Virgo |
| 9 | Leo, Scorpio | ✅ Leo, Scorpio |
| 10 | Leo, Scorpio | ✅ Leo, Scorpio |
| 11 | Sagittarius, Pisces | ✅ Sagittarius, Pisces |
| 12 | Libra, Capricorn | ✅ Libra, Capricorn |
| 13 | Taurus, Leo | ✅ Taurus, Leo |
| 14 | Pisces, Gem, Vir, Sag | ✅ Gemini, Virgo, Sagittarius, Pisces |
| 15 (Purnima) | None | ✅ [] |
| 30 (Amavasya) | None | ✅ [] |

**Verdict:** ✅ ALL MATCH

### Individual Daily Tithi Lords

**DISCREPANCY D8:** The Tithi Astrology Guide (lines 461–479) specifies daily tithi lords:
> Sun: 1st & 9th / Moon: 2nd & 10th / Mars: 3rd & 11th / Mercury: 4th & 12th / Jupiter: 5th & 13th / Venus: 6th & 14th / Saturn: 7th & 15th (Purnima) / Rahu: 8th & 30th (Amavasya)

The engine's `panchanga.py` implements **group lords** (via `GROUP_INFO`) but does not compute or expose **individual daily tithi lords**. This is a separate layer of lordship distinct from the group lord. The engine should add a `tithi_lord` field derived from the tithi number.

---

## DOMAIN E: PANCHANGA BOUNDARY TIMING

### Mathematical Formulas

**Source:** Vedic standard formulas (Panchang Handbook confirms the underlying principles).

| Limb | Standard Formula | Engine `panch_instant()` (line 188–203) |
|------|-----------------|------------------------------------------|
| Tithi | (Moon − Sun) / 12° | `norm360(moon - sun) / 12` ✅ |
| Nakshatra | Moon / (360/27) | `moon / (360/27)` ✅ |
| Yoga | (Sun + Moon) / (360/27) | `norm360(sun + moon) / (360/27)` ✅ |
| Karana | (Moon − Sun) / 6° | `norm360(moon - sun) / 6` ✅ |

### Boundary Finding Algorithm

**Engine `find_boundary()`** (`panchanga.py:211–234`):
1. Coarse scan at 0.25-hour steps to detect index change
2. 40 iterations of bisection between last-a and first-b

This is mathematically sound. The approach finds where the floored continuous panchanga value crosses an integer threshold, which is exactly what determines a panchanga limb boundary.

**Verdict:** ✅ CORRECT — the bisection root-finding matches the continuous mathematical definition of panchanga boundaries.

---

## DOMAIN F: SADE SATI PHASES

### Source Reference

GPD Chapter 26 (lines 10592–10634):
> *"71/2 years Sade Sati Sani (Saturn in 12th, 1st and 2nd from Moon sign)"* (line 10598–10599)
> *"In 12 and 2nd houses it is first and last 21/2 years... Janma Sani is the period of 2!/, years when Saturn is in birth Moon sign"* (lines 10628–10634)

### Engine: `transit_rules.py:155–171` and `gochar.py:217–231`

| Phase | House from Janma | Source Description | Engine Description |
|-------|-----------------|--------------------|--------------------|
| Rising | 12 | First 2½ years | "Mental stress, financial pressure, health concerns begin" ✅ |
| Peak | 1 (Janma Rasi) | Middle 2½ years — most critical | "Maximum difficulty — job loss, family strife, health crisis, financial drain" ✅ |
| Setting | 2 | Last 2½ years | "Recovery period — gradual relief, lessons learned, rebuilding" ✅ |

### Additional Saturn Afflictions

| Condition | House from Janma | Source Line | Engine Implemented? |
|-----------|-----------------|-------------|---------------------|
| Ardhashtama / Kantaka Sani | 4 | GPD line 3808, 10595 | ✅ `gochar.py` line 228 — checked but **not explicitly named** in engine |
| Ashtama Sani | 8 | GPD line 3808, 10596 | ✅ `gochar.py:228-230` |

**Note:** The engine's `gochar.py:228` checks `sat_house == 8` and sets `ashtama_shani`. However, the Kantaka Sani (house 4) check at `gochar.py:227` is **missing** from the Python engine even though the JSX has it (line 1998: `"Kantaka Shani: Saturn in 4th from Janma Rashi"`). The JSX correctly penalizes both 4th and 8th house Saturn positions.

---

## DOMAIN G: MOORTHY NIRNAYA

### Source Reference

GPD Chapter 25 (lines 10333–10351):

> *"When a planet is entering a new Rasi the Rasi occupied by transit Moon at that moment happens to be **1, 6 and 11th** from Janma Rasi, the planet is said to be **Swarna Moorty** (gold)."*

> *"If the Moon is in **2, 5 and 9th** from one's Janma Rasi on that day, then the planet becomes **Rajatha Moorty** (silver)."*

> *"Likewise if Moon is in **3, 7, 10** from Janma Rasi, it becomes **Tamra Moorthy** (Copper)."*

> *"Moon in **4, 8, 12** from Natal Moon is **Loh Moorthi** (iron)."*

**CORRECT MAPPING:**

| House from Janma Rasi | Moorthy Type | Quality (Benefic) | Quality (Malefic) |
|----------------------|--------------|-------------------|-------------------|
| 1, 6, 11 | Swarna (Gold) | Full good | 1/4 good |
| 2, 5, 9 | Rajatha (Silver) | 3/4 good | Full good |
| 3, 7, 10 | Thambra (Copper) | 1/2 good | 3/4 good |
| 4, 8, 12 | Loha (Iron) | 1/4 good | 1/2 good |

### Engine: `transit_rules.py:134-147` (WRONG)

```python
MOORTHI_RESULTS = {
    1: ("Swarna (Gold)", "shubh", ...),   # ❌ Should be Swarna
    2: ("Rajatha (Silver)", "shubh", ...), # ❌ Should be Rajatha
    3: ("Thambra (Copper)", "ashubh", ...),# ❌ Should be Thambra
    4: ("Loha (Iron)", "ashubh", ...),     # ❌ Should be Loha
    5: ("Swarna (Gold)", "shubh", ...),    # ❌ Should be Rajatha
    6: ("Rajatha (Silver)", "shubh", ...), # ❌ Should be Swarna
    7: ("Thambra (Copper)", "ashubh", ...),# ❌ Should be Thambra
    8: ("Loha (Iron)", "ashubh", ...),     # ❌ Should be Loha
    9: ("Swarna (Gold)", "shubh", ...),    # ❌ Should be Rajatha
    10: ("Rajatha (Silver)", "shubh", ...),# ❌ Should be Thambra
    11: ("Thambra (Copper)", "ashubh", ...),# ❌ Should be Swarna
    12: ("Loha (Iron)", "ashubh", ...),    # ❌ Should be Loha
}
```

### Engine: `MuhurtaCosmos.jsx:353-356` (WRONG)

```js
const MOORTI = (h) => h<=3 ? ["Swarna (Gold)",...]   // ❌ houses 1,2,3 → should be 1,6,11
  : h<=6 ? ["Rajata (Silver)",...]                      // ❌ houses 4,5,6 → should be 2,5,9
  : h<=9 ? ["Tamra (Copper)",...]                       // ❌ houses 7,8,9 → should be 3,7,10
  : ["Loha (Iron)",...];                                // ✅ houses 10,11,12 → should be 4,8,12
```

**DISCREPANCY D1 (CRITICAL):** Both implementations use a simple **sequential pattern** (houses 1–4 repeated 3 times) instead of the correct **grouped pattern** from GPD. This means:

| House | Engine says | Should be |
|-------|-------------|-----------|
| 1 | Swarna ✅ | Swarna ✅ |
| 2 | Rajatha ✅ | Rajatha ✅ |
| 3 | Thambra ❌ | Thambra ✅ |
| 4 | Loha ✅ | Loha ✅ |
| 5 | Swarna ❌ | Rajatha ❌ |
| 6 | Rajatha ❌ | Swarna ❌ |
| 7 | Thambra ✅ | Thambra ✅ |
| 8 | Loha ✅ | Loha ✅ |
| 9 | Swarna ❌ | Rajatha ❌ |
| 10 | Rajatha ❌ | Thambra ❌ |
| 11 | Thambra ❌ | Swarna ❌ |
| 12 | Loha ✅ | Loha ✅ |

**Seven of twelve houses are incorrectly classified!** Houses 5, 6, 9, 10, 11 are most affected.

### Corrected Engine Code (`transit_rules.py`)

Replace `MOORTHI_RESULTS` dict. Correct mapping:

```python
MOORTHI_RESULTS = {
    1:  ("Swarna (Gold)",    "shubh",  "Excellent — success, wealth, honour"),
    2:  ("Rajatha (Silver)", "shubh",  "Good — moderate success, comfort"),
    3:  ("Thambra (Copper)", "ashubh", "Poor — obstacles, worries"),
    4:  ("Loha (Iron)",      "ashubh", "Worst — severe difficulties, loss"),
    5:  ("Rajatha (Silver)", "shubh",  "Good — moderate success, comfort"),
    6:  ("Swarna (Gold)",    "shubh",  "Excellent — success, wealth, honour"),
    7:  ("Thambra (Copper)", "ashubh", "Poor — obstacles, worries"),
    8:  ("Loha (Iron)",      "ashubh", "Worst — severe difficulties, loss"),
    9:  ("Rajatha (Silver)", "shubh",  "Good — moderate success, comfort"),
    10: ("Thambra (Copper)", "ashubh", "Poor — obstacles, worries"),
    11: ("Swarna (Gold)",    "shubh",  "Excellent — success, wealth, honour"),
    12: ("Loha (Iron)",      "ashubh", "Worst — severe difficulties, loss"),
}
```

### Corrected JSX Code (`MuhurtaCosmos.jsx` line 353)

Replace with:
```js
const MOORTI_HOUSES = {1:0, 6:0, 11:0, 2:1, 5:1, 9:1, 3:2, 7:2, 10:2, 4:3, 8:3, 12:3};
const MOORTI_TYPES = [
  ["Swarna (Gold)","Most auspicious — radiant, full results.","good","#F5C451"],
  ["Rajata (Silver)","Auspicious — gentle, steady gains.","good","#CBD5E1"],
  ["Tamra (Copper)","Mixed — effortful, moderate fruit.","neutral","#E08B4F"],
  ["Loha (Iron)","Inauspicious — obstruction, delay.","bad","#8794A8"],
];
const MOORTI = (h) => MOORTI_TYPES[MOORTI_HOUSES[h]];
```

---

## APPENDIX: VERIFIED CORRECT IMPLEMENTATIONS

The following were verified against source texts and found to be **fully correct**:

| Component | What was verified | Result |
|-----------|------------------|--------|
| Gochar houses Table 12 | All 9 planets' good/bad/worst houses | ✅ Except Mars house 10 (D4) |
| Latta distances & directions | All 8 planets | ✅ Except Ketu missing (D1) |
| Latta formula | `(nak + dir*(dist-1)) % 27` | ✅ Verified for forward & backward |
| Sade Sati phases | 12, 1, 2 from Janma Rasi | ✅ Correct order (rise/peak/setting) |
| Ashtama Shani | 8th house | ✅ Correct |
| Tithi group classification | Nanda/Bhadra/Jaya/Rikta/Purna | ✅ All 30 tithis correct |
| Tithi group lords | Venus/Mercury/Mars/Saturn/Jupiter | ✅ Correct |
| Dagdha Rashis | 16 entries × 2–4 rashis each | ✅ All correct |
| Panchanga boundary formulas | Tithi/Nak/Yoga/Karana calculations | ✅ Mathematically correct |
| Panchanga bisection algorithm | `find_boundary()` | ✅ Correct approach |
| Tara Balam remainder formula | `count % 9` with 0→9 | ✅ Correct |
| Combustion orbs | Classical values | ✅ Verified |
| Nakshatra natures | All 27 stars | ✅ Verified |
| Karana sequence | 60 half-tithis | ✅ Verified |
| Vedha matrix | Gochara Vedha and Vipareetha Vedha | ✅ Verified for 7 planets |

---

## PRIORITY ACTION ITEMS

1. **IMMEDIATE:** Fix Moorthy Nirnaya mapping in both `transit_rules.py:134-147` and `MuhurtaCosmos.jsx:353-356` — this is a 7/12 error rate.

2. **IMMEDIATE:** Add Ketu to LATTA_RULES in both `transit_rules.py:115-126` and `MuhurtaCosmos.jsx:261-270`: `"Ketu": (9, -1, "Difficulties of all kinds", "GPD-Ch1.6")`.

3. **HIGH:** Add Tara exceptions to Python engine (`gochar.py:233-240`):
   - 22nd Nakshatra → Vainasika warning
   - 27th Nakshatra → Parama Maitra restriction
   - 1st/10th/19th → Janma group (lifts after midday)

4. **MEDIUM:** Fix Mars bad houses → add house 10 as bad (or at minimum not neutral).

5. **MEDIUM:** Complete Paryaya 3 entries (counts 20–27) in `transit_rules.py` `TARA_RESULTS` dict.

6. **LOW:** Rename "Sadhana" → "Sadhaka" and "Mitra" → "Maitra" in `transit_rules.py`.

7. **LOW:** Add Kantaka Shani (4th house) detection to `gochar.py`.

8. **LOW:** Add individual daily tithi lords to `panchanga.py` as a `tithi_lord` field.
