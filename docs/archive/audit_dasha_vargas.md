# Audit: Vedic Prediction Engine — Dasha & Varga Modules

**Date:** 2026-06-23  
**Audited against:** BPHS Ch.6, Ch.48; Jaimini Sutras; Predicting Through Jaimini Astrology; Predict Effectively Through Yogini Dasha (V.P. Goel)  
**Engine files:** `vedic_engine/prediction/dasha.py`, `MuhurtaCosmos.jsx`

---

## A) Vimshottari Mahadasha Periods

| Planet | Engine (dasha.py line 27–30) | Engine (MuhurtaCosmos.jsx line 842) | BPHS Standard |
|--------|------|------|------|
| Sun    | 6    | 6    | 6    |
| Moon   | 10   | 10   | 10   |
| Mars   | 7    | 7    | 7    |
| Rahu   | 18   | 18   | 18   |
| Jupiter| 16   | 16   | 16   |
| Saturn | 19   | 19   | 19   |
| Mercury| 17   | 17   | 17   |
| Ketu   | 7    | 7    | 7    |
| Venus  | 20   | 20   | 20   |
| **Sum**| **120** | **120** | **120** |

**Verdict: PASS** — All 9 periods correct, summing exactly to 120. BPHS confirms the full human lifespan is 120 years (BPHS Ch.45 sloka 54, p.603: "in Deerghaya 120").

---

## B) Dasha Sequence

**Engine (dasha.py line 33):** `Ketu → Venus → Sun → Moon → Mars → Rahu → Jupiter → Saturn → Mercury`  
**Engine (MuhurtaCosmos.jsx line 841):** Same.  
**BPHS:** The standard Vimshottari sequence follows the nakshatra-lord order repeating every 9 nakshatras, beginning from Ashwini (Ketu).

**Verdict: PASS** — Sequence is exactly correct.

---

## C) Nakshatra-to-Dasha Mapping

### Engine (dasha.py lines 36–46):

| Lord   | Nakshatras |
|--------|-----------|
| Ketu   | Ashwini, Magha, Mula |
| Venus  | Bharani, Purva Phalguni, Purva Ashadha |
| Sun    | Krittika, Uttara Phalguni, Uttara Ashadha |
| Moon   | Rohini, Hasta, Shravana |
| Mars   | Mrigashira, Chitra, Dhanishtha |
| Rahu   | Ardra, Swati, Shatabhisha |
| Jupiter| Punarvasu, Vishakha, Purva Bhadrapada |
| Saturn | Pushya, Anuradha, Uttara Bhadrapada |
| Mercury| Ashlesha, Jyeshtha, Revati |

### MuhurtaCosmos.jsx (line 844):
```js
const NAK_VIM_LORD = (nakIdx0)=> VIM_ORDER[nakIdx0 % 9];
```
This uses the NAKSHATRAS array (line 41) in the standard order from Ashwini to Revati, mapping every 9th nakshatra to the same lord. This produces the exact same grouping as dasha.py.

**Verdict: PASS** — Both implementations correctly map all 27 nakshatras per the classical Vimshottari scheme (3 nakshatras per lord, repeating every 9).

---

## D) Balance of Dasha at Birth

### Engine (dasha.py lines 204–216):
```python
nak_span = 360 / 27  # 13.333...°
elapsed_fraction = ((birth_moon_lon % 360) - nak_start) / nak_span
balance = total_period * (1 - elapsed_fraction)
```

### Engine (MuhurtaCosmos.jsx lines 850–856):
```js
const fracTraversed = (norm360(moonLonSidereal) % NAK_SPAN) / NAK_SPAN;
const firstBalanceYears = VIM_YEARS[startLord] * (1 - fracTraversed);
```

### BPHS:
BPHS Ch.4 (slokas 5–6) defines Bhayaata (traversed portion of nakshatra) and Bhabhoga (total span of nakshatra). The balance-of-dasha formula is:

> balance = (remaining arc / total nakshatra span) × lord's full period

where remaining arc = nakshatra span − traversed arc.

**Verdict: PASS** — Formula matches. Nakshatra span of 13°20′ (= 360/27) is correct. The elapsed fraction is correctly subtracted from 1 to get the remaining fraction. The `birth_moon_lon` percent-wrap and boundary handling in dasha.py are sound.

**Note:** dasha.py falls back to assuming 50% traversed (elapsed_fraction = 0.5) when `birth_moon_lon` is `None` — this is a reasonable default but should be documented as a lossy approximation.

---

## E) Antardasha (Bhukti) Calculation

### Engine (dasha.py lines 270–273):
```python
ant_years = (maha_total * VIMSHOTTARI_PERIODS[ant_lord]) / 120
```

### Engine (MuhurtaCosmos.jsx lines 871–874):
```js
const alen = mahaLen * (VIM_YEARS[al] / 120);
```

### BPHS Standard:
The antardasha within a mahadasha is proportional:
> Antar_years = (Maha_lord_years × Antar_lord_years) / 120

The antardasha sequence begins with the mahadasha lord and proceeds in Vimshottari order (same as mahadasha order), cycling through all 9 lords.

**Verdict: PASS** — Both implementations follow the standard formula. The sequence correctly starts from the maha lord `(start_idx + i) % 9` / `(mIdx + j) % 9`.

---

## F) Yogini Dasha

### F1. Yogini Names, Periods, and Lords

**Engine (dasha.py lines 49–85):**

| Yogini   | Years | Lord   | Engine |
|----------|-------|--------|--------|
| Mangala  | 1     | Moon   | ✓      |
| Pingala  | 2     | Sun    | ✓      |
| Dhanya   | 3     | Jupiter| ✓      |
| Bhramari | 4     | Mars   | ✓      |
| Bhadrika | 5     | Mercury| ✓      |
| Ulka     | 6     | Saturn | ✓      |
| Siddha   | 7     | Venus  | ✓      |
| Sankata  | 8     | Rahu   | ✓      |
| **Sum**  | **36**|        | ✓      |

**Source (Goel, p.12, Table I):** "Dasha periods from one year to eight years to make total of thirty-six years" — Mangla→Moon, Pingla→Sun, Dhanya→Jupiter, BhraMari→Mars, Bhadrika→Mercury, Ulka→Saturn, Siddha→Venus, Sankata→Rahu.

**Verdict for F1: PASS** — Names, periods (1–8), lords, and order all match the source text exactly. The 36-year cycle total is correct.

### F2. Yogini Dasha Sequence

**Engine (dasha.py line 54):** Mangala → Pingala → Dhanya → Bhramari → Bhadrika → Ulka → Siddha → Sankata  
**Source:** Same order (Goel, p.8 Table I + worked example p.12: "Dasha at birth is Dhanya and the order is Dhanya, BhraMari, Bhadrika, Ulka, Siddha, Sankata, Mangla, Pingla").

**Verdict: PASS** — Order matches the source.

### F3. Yogini Nakshatra Mapping — CRITICAL FAILURE

**Source formula (Goel, p.12):**
> "Nakshatra number is counted from Ashwini, which is taken as one. Add three to the Nakshatra number. Divide the sum by eight. The remainder represents the Yogini dasha operating. If remainder is zero, it means 8."

Worked example: Pushya = nakshatra #8. 8+3=11. 11÷8 = remainder 3 → Dhanya.

**Engine mapping (dasha.py lines 56–66):**
Direct hardcoded map of 27 nakshatras → 8 Yoginis in 8 groups (first 5 Yoginis each cover 3 nakshatras; last 3 Yoginis each cover 4 nakshatras).

| Nakshatra (#) | Source Formula | Engine |
|---------------|----------------|--------|
| Ashwini (1)   | (1+3)%8=4 → Bhramari | Mangala |
| Bharani (2)   | (2+3)%8=5 → Bhadrika | Pingala |
| Krittika (3)  | (3+3)%8=6 → Ulka     | Dhanya |
| Rohini (4)    | (4+3)%8=7 → Siddha   | Bhramari |
| Mrigashira (5)| (5+3)%8=0 → Sankata | Bhadrika |
| Ardra (6)     | (6+3)%8=1 → Mangala  | Ulka |
| Punarvasu (7) | (7+3)%8=2 → Pingala  | Siddha |
| Pushya (8)    | (8+3)%8=3 → Dhanya   | **Sankata** |
| Chitra (14)   | (14+3)%8=1 → Mangala | **Ulka** |

**The engine's mapping does NOT use the classical (n+3)%8 formula.** It uses a mechanical 3-nakshatra-per-yogini grouping that does not match any known classical source. The source text itself uses the (n+3)%8 formula in its worked examples (p.12) and in the progression scheme (pp.15–16).

**Verdict: FAIL** — The Yogini nakshatra mapping is incorrect. The engine must implement the formula `(nakshatra_number + 3) % 8` (using 1-indexed nakshatra count from Ashwini, with remainder 0 interpreted as 8/Sankata).

### F4. Yogini Antardasha (Sub-periods)

**Source (Goel, p.12):**
> "Sub period = Dasha years of Q × Dasha period of P × 10 are the number of days of sub period."

Example: Siddha in Ulka major: 6 × 7 × 10 = 420 days.

**Engine (dasha.py):** The engine does NOT compute antardasha (sub-periods) for Yogini. It only computes the mahadasha sequence (`compute_yogini` function, lines 318–351).

**Verdict: FAIL** — Yogini antardasha is not implemented. The source provides a simple formula (`years_Q × years_P × 10 = days`) that should be added.

### F5. Balance of Yogini Dasha

**Source (Goel, p.12):**
> "Full Dasha period of a yogini spans one Nakshatra. The degrees remaining to be traversed by Moon in the Nakshatra occupied is the proportional balance of Dasha at birth/epoch."

Example: Pushya spans 3°20′ to 16°40′. Moon at 12°40′ has 4°0′ remaining. Balance = 4° × 3 years / 13°20′ = 0y 10m 24d.

**Engine (dasha.py):** The engine does NOT compute balance of Yogini dasha. All Yogini dashas start from the exact birth date without any balance calculation (line 335: `current = birth_date`).

**Verdict: FAIL** — Balance of Yogini dasha at birth is not computed. The first Yogini dasha should be proportionally reduced based on how much of the nakshatra the Moon has already traversed, exactly like the Vimshottari balance calculation.

---

## G) Vargas (Divisional Charts)

### G1. General

**Engine (MuhurtaCosmos.jsx lines 926–946):** Computes D1, D2, D4, D7, D9, D10, D24 sign placements for all 9 planets + Lagna.  
**BPHS Ch.6:** Lists 16 Vargas (slokas 2–4). The engine implements 6 of them.

### G2. D2 (Hora) — Wealth

**BPHS (slokas 5–6):** Odd signs 0–15° = Sun's Hora, 15–30° = Moon's Hora. Even signs reversed.

**Engine:**
```js
v.D2[name] = si%2===0 ? (degInSign<15 ? 4 : 3) : (degInSign<15 ? 3 : 4);
```
Where index 4 = Leo (Sun's sign), 3 = Cancer (Moon's sign). With 0-based sign indices, `si%2===0` correctly selects odd signs (Aries, Gemini, Leo, Libra, Sagittarius, Aquarius).

| Condition | Engine Output | BPHS |
|-----------|--------------|------|
| Odd sign, 0–15° | 4 (Leo) | Sun's hora → Leo ✓ |
| Odd sign, 15–30° | 3 (Cancer) | Moon's hora → Cancer ✓ |
| Even sign, 0–15° | 3 (Cancer) | Moon's hora → Cancer ✓ |
| Even sign, 15–30° | 4 (Leo) | Sun's hora → Leo ✓ |

**Verdict: PASS** — Division count (2), part size (15°), and starting sign rules all correct.

### G3. D4 (Chaturthamsha) — Home/Property

**BPHS (sloka 9):** 4 parts of 7°30′ each. Ruled by lords of 1st, 4th, 7th, 10th from the sign.

**Engine:**
```js
v.D4[name] = (si + Math.floor(degInSign/7.5) * 3) % 12;
```
Part 0 → sign itself (+0), Part 1 → 4th sign (+3), Part 2 → 7th (+6), Part 3 → 10th (+9). This is equivalent to `Part N = sign + N×3`.

**Verdict: PASS** — Correct. Division count (4), part size (7°30′), and progression all match BPHS.

### G4. D7 (Saptamsha) — Children

**BPHS (slokas 10–11):** 7 parts of 4°17′8.57″ each. Odd signs: starts from same sign. Even signs: starts from 7th sign.

**Engine:**
```js
v.D7[name] = si%2===0 ? (si+p)%12 : (si+6+p)%12;
```
p = Math.floor(degInSign / (30/7)).

**Verdict: PASS** — Correct. Division count (7), part size (≈4°17′), and starting rules match BPHS.

### G5. D9 (Navamsha) — Marriage/Spouse

**BPHS (sloka 12):** 9 parts of 3°20′ each. Movable: from same sign. Fixed: from 9th. Dual: from 5th.

**Engine:**
```js
const s = {0:0,4:0,8:0, 1:9,5:9,9:9, 2:6,6:6,10:6, 3:3,7:3,11:3};
v.D9[name] = (s[si] + p) % 12;
```
The lookup `s` maps each sign to its starting count sign based on the movable/fixed/dual classification. Verification of each sign against BPHS rules:

| Sign | Index | Type | Engine(start) | BPHS rule | Match |
|------|-------|------|---------------|-----------|-------|
| Aries | 0 | Movable | 0 (Aries) | same sign | ✓ |
| Taurus | 1 | Fixed | 9 (Capricorn) | 9th = Cap | ✓ |
| Gemini | 2 | Dual | 6 (Libra) | 5th = Lib | ✓ |
| Cancer | 3 | Movable | 3 (Cancer) | same sign | ✓ |
| Leo | 4 | Fixed | 0 (Aries) | 9th = Ari | ✓ |
| Virgo | 5 | Dual | 9 (Capricorn) | 5th = Cap | ✓ |
| Libra | 6 | Movable | 6 (Libra) | same sign | ✓ |
| Scorpio | 7 | Fixed | 3 (Cancer) | 9th = Can | ✓ |
| Sagittarius | 8 | Dual | 0 (Aries) | 5th = Ari | ✓ |
| Capricorn | 9 | Movable | 9 (Capricorn) | same sign | ✓ |
| Aquarius | 10 | Fixed | 6 (Libra) | 9th = Lib | ✓ |
| Pisces | 11 | Dual | 3 (Cancer) | 5th = Can | ✓ |

**Verdict: PASS** — All 12 signs' starting rules verified correct. Division count (9), part size (3°20′).

### G6. D10 (Dashamsha) — Career

**BPHS (slokas 13–14):** 10 parts of 3° each. Odd signs: from same sign. Even signs: from 9th sign.

**Engine:**
```js
v.D10[name] = si%2===0 ? (si+p)%12 : (si+8+p)%12;
```

**Verdict: PASS** — Correct. Division count (10), part size (3°), and starting rules match BPHS. Note: `si+8` = 9th sign (since `si+9-1` due to 0-indexing, or equivalently `(si+8)%12` gives the 9th sign from the original).

### G7. D24 (Siddhamsha / Chaturvimsamsha) — Education

**BPHS (slokas 22–23):** 24 parts of 1°15′ each. Odd signs: from Leo. Even signs: from Cancer.

**Engine:**
```js
v.D24[name] = si%2===0 ? (4+p)%12 : (3+p)%12;
```
Index 4 = Leo, 3 = Cancer.

**Verdict: PASS** — Correct. Division count (24), part size (1°15′), and starting sign rules (Leo for odd, Cancer for even) match BPHS.

---

## H) Jaimini Chara Karakas

**Engine (dasha.py):** No Chara Karaka computation exists.  
**Engine (MuhurtaCosmos.jsx):** No Chara Karaka computation. The only Karaka references are hardcoded labels (AK, DK, etc.) in the static MOHAN chart data (lines 952–964). The `buildNatal()` function (line 882) computes planet positions but does NOT sort by longitude to determine Chara Karakas.

**Jaimini Sutras (Adhyaya 1, Pada 1, Sutra 11):**
> "Of the seven planets from the Sun to Saturn, whichever gets the highest number of degrees becomes the Atmakaraka."

Sutra 13: Next in degrees → Amatyakaraka.  
Sutra 14: Next → Bhratrukaraka.  
Sutra 15: Next → Matrukaraka.  
Subsequent: Putrakaraka, Gnatikaraka, Darakaraka (7 karakas, descending in longitude).  
Rahu/Ketu fill gaps when planets tie.

| Karaka | Definition | 
|--------|-----------|
| AK (Atmakaraka) | Planet with highest longitude (degrees-minutes-seconds within sign) |
| AmK (Amatyakaraka) | 2nd highest |
| BK (Bhratrukaraka) | 3rd highest |
| MK (Matrukaraka) | 4th highest |
| PK (Putrakaraka) | 5th highest |
| GK (Gnatikaraka) | 6th highest |
| DK (Darakaraka) | 7th highest (lowest) |

**Verdict: FAIL** — Chara Karaka computation is completely absent from the engine. This is a significant gap given that the engine is titled "Vedic Prediction Engine" and both Jaimini and BPHS (Ch.34 "Planetary Karakatwas") define these as essential predictive tools. The algorithm is straightforward: sort planets by within-sign longitude, assign AK→DK in descending order.

---

## I) Vimshottari Year Length: 360 Savana vs 365.25

### Engine (dasha.py line 162–167):
```python
def _add_years(date_str, years):
    total_days = years * 365.25  # ← tropical/solar year
    dt = datetime(y, m, d) + timedelta(days=total_days)
```

### Engine (MuhurtaCosmos.jsx line 845):
```js
const VIM_DAY = 365.2425;  // ← precise tropical year
```

### BPHS Text:
BPHS Ch.4 defines **Savanesta** (Savan/Savana time) as the time from sunrise used in dasha calculations. The text mentions "Savana" (solar/civil day count) as the basis for time reckoning.

The Vedic dasha system conventionally uses a **360-day Savana year** (12 months × 30 days) because dashas are measured in "years of 360 savana days each" — consistent with the Vedic time unit where 1 year = 360 savana (solar) days.

However, there is scholarly debate:
- **Traditional view:** 360-day savana years (all major classical software like Jagannatha Hora uses this)
- **Modern view:** Some argue for 365.25 solar years for calendar date conversion

The engine uses 365.25 (Python) / 365.2425 (JS), which is the **solar/tropical year**. This diverges from the traditional 360-day savana convention used in most classical implementations.

**Verdict: PARTIAL FAIL** — The engine should default to 360-day savana years for Vimshottari date computation (matching Jagannatha Hora, Kala, and other standard software). The 365.25 value produces end dates that are ~1.5% later than classical convention. Optionally, a toggle between 360 and 365.25 should be offered for users who prefer the modern approach.

The Yogini dasha in dasha.py also inherits the same `_add_years()` function, so the same issue applies there.

---

## Summary of Findings

| Item | Topic | Verdict |
|------|-------|---------|
| A | Vimshottari periods (120-year sum) | ✅ PASS |
| B | Dasha sequence (Ketu→...→Mercury) | ✅ PASS |
| C | Nakshatra-to-lord mapping (27 nakshatras) | ✅ PASS |
| D | Balance of dasha formula | ✅ PASS |
| E | Antardasha (proportional formula) | ✅ PASS |
| F1 | Yogini names, periods, lords, order | ✅ PASS |
| F2 | Yogini sequence | ✅ PASS |
| F3 | Yogini nakshatra mapping | ❌ **FAIL** — Uses wrong formula |
| F4 | Yogini antardasha computation | ❌ **FAIL** — Not implemented |
| F5 | Yogini balance of dasha at birth | ❌ **FAIL** — Not computed |
| G | Vargas D2/D4/D7/D9/D10/D24 | ✅ ALL PASS |
| H | Jaimini Chara Karakas (AK→DK) | ❌ **FAIL** — Not implemented |
| I | Vimshottari year length (360 vs 365.25) | ⚠️ PARTIAL FAIL — Should use 360 |

### Action Items (Priority Order)

1. **CRITICAL:** Fix Yogini nakshatra mapping to use `(nakshatra_number + 3) % 8` formula per the classical text. Replace the hardcoded `YOGINI_NAKSHATRA_MAP` dict.

2. **CRITICAL:** Implement Yogini balance-of-dasha calculation (proportional to remaining nakshatra arc traversed by Moon).

3. **HIGH:** Implement Chara Karaka computation (sort 7 planets by within-sign longitude, assign AK→DK descending). This is core Jaimini and required by both `dasha.py` and `MuhurtaCosmos.jsx`.

4. **MEDIUM:** Implement Yogini antardasha using the source formula `years_Q × years_P × 10 = days`.

5. **LOW:** Add a year-type toggle (360 savana vs 365.25 solar) for Vimshottari date conversion, defaulting to 360-day savana years per classical convention.
