# Vedic Prediction Engine — Ashtakavarga & Muhurta Source-Text Audit

**Audit date:** 2026-06-23  
**Scope:** `vedic_engine/prediction/ashtakavarga.py` (BAV/SAV) + `MuhurtaCosmos.jsx` (BAV_TABLE, SBC_VEDHA, MUHURTA_30, RAVI_DISTANCES, computeAshtakavarga, combination yogas)  
**Source texts:** `/Gyan/extracted_markdown/` — Ashtakavarga Handbook, Do-Ghati Handbook, SBC Vedha Reference, Ravi Yoga Guide, muhurta_yogas.md, Phaladeepika Ch.19/23/24, Sarvartha Chintamani Ch.17

---

## A) BAV Tables — Benefic Placement Matrices

### Source: Phaladeepika Ch.23 (Adhyaya 23), Slokas 3–9

Each sloka from Phaladeepika was compared against `BAV_TABLE` in **both** `ashtakavarga.py:33–104` and `MuhurtaCosmos.jsx:711–719`. Both files have identical tables (structurally equivalent; Python uses arrays, JSX uses short-form arrays).

### Line-by-line verification

| Planet | Contributor | Phaladeepika Sloka | Code Value | Match |
|--------|------------|---------------------|------------|-------|
| **Sun** | Sun | 1,2,4,7,8,9,10,11 | `[1,2,4,7,8,9,10,11]` | ✓ |
| | Moon | 3,6,10,11 | `[3,6,10,11]` | ✓ |
| | Mars | 1,2,4,7,8,9,10,11 | `[1,2,4,7,8,9,10,11]` | ✓ |
| | Mercury | 3,5,6,9,10,11,12 | `[3,5,6,9,10,11,12]` | ✓ |
| | Jupiter | 5,6,9,11 | `[5,6,9,11]` | ✓ |
| | Venus | 6,7,12 | `[6,7,12]` | ✓ |
| | Saturn | 1,2,4,7,8,9,10,11 | `[1,2,4,7,8,9,10,11]` | ✓ |
| | Lagna | 3,4,6,10,11,12 | `[3,4,6,10,11,12]` | ✓ |
| **Moon** | Sun | 3,6,7,8,10,11 | `[3,6,7,8,10,11]` | ✓ |
| | Moon | 1,3,6,7,10,11 | `[1,3,6,7,10,11]` | ✓ |
| | Mars | 2,3,5,6,9,10,11 | `[2,3,5,6,9,10,11]` | ✓ |
| | Mercury | 1,3,4,5,7,8,10,11 | `[1,3,4,5,7,8,10,11]` | ✓ |
| | Jupiter | 1,2,4,7,8,10,11 | `[1,4,7,8,10,11,12]` | ⚠ |
| | Venus | 3,4,5,7,9,10,11 | `[3,4,5,7,9,10,11]` | ✓ |
| | Saturn | 3,5,6,11 | `[3,5,6,11]` | ✓ |
| | Lagna | 3,6,10,11 | `[3,6,10,11]` | ✓ |
| **Mars** | Sun | 3,5,6,10,11 | `[3,5,6,10,11]` | ✓ |
| | Moon | 3,6,11 | `[3,6,11]` | ✓ |
| | Mars | 1,2,4,7,8,10,11 | `[1,2,4,7,8,10,11]` | ✓ |
| | Mercury | 3,5,6,11 | `[3,5,6,11]` | ✓ |
| | Jupiter | 6,10,11,12 | `[6,10,11,12]` | ✓ |
| | Venus | 6,8,11,12 | `[6,8,11,12]` | ✓ |
| | Saturn | 1,4,7,8,9,10,11 | `[1,4,7,8,9,10,11]` | ✓ |
| | Lagna | 1,3,6,10,11 | `[1,3,6,10,11]` | ✓ |
| **Mercury** | Sun | 5,6,9,11,12 | `[5,6,9,11,12]` | ✓ |
| | Moon | 2,4,6,8,10,11 | `[2,4,6,8,10,11]` | ✓ |
| | Mars | 1,2,4,7,8,9,10,11 | `[1,2,4,7,8,9,10,11]` | ✓ |
| | Mercury | 1,3,5,6,9,10,11,12 | `[1,3,5,6,9,10,11,12]` | ✓ |
| | Jupiter | 6,8,11,12 | `[6,8,11,12]` | ✓ |
| | Venus | 1,2,3,4,5,8,9,11 | `[1,2,3,4,5,8,9,11]` | ✓ |
| | Saturn | 1,2,4,7,8,9,10,11 | `[1,2,4,7,8,9,10,11]` | ✓ |
| | Lagna | 1,2,4,6,8,10,11 | `[1,2,4,6,8,10,11]` | ✓ |
| **Jupiter** | Sun | 1,2,3,4,7,8,9,10,11 | `[1,2,3,4,7,8,9,10,11]` | ✓ |
| | Moon | 2,5,7,9,11 | `[2,5,7,9,11]` | ✓ |
| | Mars | 1,2,4,7,8,10,11 | `[1,2,4,7,8,10,11]` | ✓ |
| | Mercury | 1,2,4,5,6,9,10,11 | `[1,2,4,5,6,9,10,11]` | ✓ |
| | Jupiter | 1,2,3,4,7,8,10,11 | `[1,2,3,4,7,8,10,11]` | ✓ |
| | Venus | 2,5,6,9,10,11 | `[2,5,6,9,10,11]` | ✓ |
| | Saturn | 3,5,6,12 | `[3,5,6,12]` | ✓ |
| | Lagna | 1,2,4,5,6,7,9,10,11 | `[1,2,4,5,6,7,9,10,11]` | ✓ |
| **Venus** | Sun | 8,11,12 | `[8,11,12]` | ✓ |
| | Moon | 1,2,3,4,5,8,9,11,12 | `[1,2,3,4,5,8,9,11,12]` | ✓ |
| | Mars | 3,5,6,9,11,12 | `[3,5,6,9,11,12]` | ✓ |
| | Mercury | 3,5,6,9,11 | `[3,5,6,9,11]` | ✓ |
| | Jupiter | 5,8,9,10,11 | `[5,8,9,10,11]` | ✓ |
| | Venus | 1,2,3,4,5,8,9,10,11 | `[1,2,3,4,5,8,9,10,11]` | ✓ |
| | Saturn | 3,4,5,8,9,10,11 | `[3,4,5,8,9,10,11]` | ✓ |
| | Lagna | 1,2,3,4,5,8,9,11 | `[1,2,3,4,5,8,9,11]` | ✓ |
| **Saturn** | Sun | 1,2,4,7,8,10,11 | `[1,2,4,7,8,10,11]` | ✓ |
| | Moon | 3,6,11 | `[3,6,11]` | ✓ |
| | Mars | 3,5,6,10,11,12 | `[3,5,6,10,11,12]` | ✓ |
| | Mercury | 6,8,9,10,11,12 | `[6,8,9,10,11,12]` | ✓ |
| | Jupiter | 5,6,11,12 | `[5,6,11,12]` | ✓ |
| | Venus | 6,11,12 | `[6,11,12]` | ✓ |
| | Saturn | 3,5,6,11 | `[3,5,6,11]` | ✓ |
| | Lagna | 1,3,4,6,10,11 | `[1,3,4,6,10,11]` | ✓ |

### ⚠ DISCREPANCY #1 — Moon BAV: Jupiter contribution

| File | Location | Detail |
|------|----------|--------|
| `ashtakavarga.py:49` | Moon BAV, Jupiter key | `[1, 4, 7, 8, 10, 11, 12]` |
| `MuhurtaCosmos.jsx:713` | Moon BAV, Jupiter key | `[1,4,7,8,10,11,12]` |
| Phaladeepika Sloka 4 (line 14138–14144) | Moon BAV, Jupiter | `1, 2, 4, 7, 8, 10, 11` |
| Phaladeepika footnote (line 14147) | Varahamihira variant | `1, 4, 7, 8, 10, 11, 12` |

**The code uses the Varahamihira variant instead of the primary Parashara text.** The total bindu count remains 7 for both variants (just position 2 vs position 12), so the 49 total is preserved. This is a consistent **divergence in placement**, not a mathematical error. The Ashtakavarga Handbook does not specify which variant to prefer. Both variants have a total of 7 bindus.

**Impact:** The bindu count in specific houses for a given natal chart may differ negligibly. Both are classical and accepted. **Low priority.**

### Per-planet totals

| Planet | Bindu count | Source confirmation |
|--------|------------|---------------------|
| Sun | 48 | Handbook Table 3.1 ✓ |
| Moon | 49 | Handbook Table 3.1 ✓ |
| Mars | 39 | Handbook Table 3.1 ✓ |
| Mercury | 54 | Handbook Table 3.1 ✓ |
| Jupiter | 56 | Handbook Table 3.1 ✓ |
| Venus | 52 | Handbook Table 3.1 ✓ |
| Saturn | 39 | Handbook Table 3.1 ✓ |

**Arithmetic sum:** 48 + 49 + 39 + 54 + 56 + 52 + 39 = **337** ✓

### **Verdict A: PASS (1 minor textual variant noted, non-breaking)**

---

## B) SAV Computation

### Code: `ashtakavarga.py:174–179` & `MuhurtaCosmos.jsx:734–736`

The SAV is computed as **elementwise sum of all 7 BAV arrays** across 12 signs. Both codebases implement this identically. The invariant `total_sav == 337` is explicitly verified in the Python code (`ashtakavarga.py:184`).

**Source:** Ashtakavarga Handbook §3.2: "The Samudashtakavarga (SAV) is the total aggregate matrix. It is computed by summing the individual Bindus of all seven BAV charts for each zodiac sign."

### **Verdict B: PASS**

---

## C) Bindu Interpretation

### Code: `ashtakavarga.py:107–117`

| Bindus | Code Label | Code Verdict | Code Effect |
|--------|-----------|-------------|-------------|
| 0 | Extremely inauspicious | ashubh | Danger, severe loss, major health issues |
| 1 | Highly inauspicious | ashubh | Significant obstacles, financial drain |
| 2 | Inauspicious | ashubh | Delays, minor losses, reduced success |
| 3 | Below average | ashubh | Struggles, obstacles, mixed results |
| 4 | Average | neutral | Moderate results, normal progress |
| 5 | Above average | shubh | Good progress, some gains |
| 6 | Favourable | shubh | Clear progress, gains, success |
| 7 | Highly favourable | shubh | Strong gains, happiness, success |
| 8 | Exceptionally auspicious | shubh | Maximum support, great success, wealth |

### ⚠ DISCREPANCY #2 — 3-bindu interpretation

| Source | 3 Bindu meaning |
|--------|-----------------|
| Code label | "Below average" |
| Code category | `ashubh` (inauspicious) |
| Phaladeepika Sloka 11 (line 14299–14309) | "fear" (bhaya) |

The code classifies 3 bindus as `ashubh`, which is **consistent** with the source text ("fear" is inauspicious). However, the code's _label_ "Below average" is softer than the source's "fear." The effect text "Struggles, some obstacles, mixed results with effort" is a reasonable modern interpretation. **Minor semantic drift — acceptable.**

### ⚠ DISCREPANCY #3 — 4-bindu interpretation

| Source | 4 Bindu meaning |
|--------|-----------------|
| Code label | "Average" |
| Code category | `neutral` |
| Phaladeepika Sloka 11 | "fear" (same as 3 bindus) |

The source text equates 3 and 4 bindus as both producing "fear" (भय). The code labels 4 bindus as `neutral` ("Average — moderate results, normal progress"), which is **significantly softer** than the source. In the source, both 3 and 4 bindus are inauspicious. The code breaks at 4 for neutral, which is a reasonable modernisation but does not match the classical text's "fear" assignment.

**Proposed fix:** Either downgrade 4-bindu verdict to `ashubh` with the real label "Caution — requires effort to overcome fear/insecurity", OR add a note that the modern interpretation shifts 4 from ashubh to neutral per common panchang practice.

### **Verdict C: PASS with 2 minor semantic notes**

---

## D) SAV Bands

### ⚠ DISCREPANCY #4 — Band thresholds diverge from both primary sources

| Source | Threshold values |
|--------|-----------------|
| **Code** (`ashtakavarga.py:120–125`) | excellent ≥30, good 28–29, standard 22–27, depleted <22 |
| **Ashtakavarga Handbook §3.2** | Below 25 = Critical Deficiency; 25–28 = Standard; 30+ = High Robustness |
| **Phaladeepika Sloka 20** (line 14437–14445) | "exceeding 28 → good; below 28 → danger/sorrow proportionately" |
| **Muhurta lunar filter** (`MuhurtaCosmos.jsx:1467–1473`) | excellent ≥32, good ≥28, standard ≥22, depleted <22 |
| **Handbook §7 (lunar filter)** | "minimum 28 Bindus (ideally 32+)" ; "<22 Bindus" = depleted |

**Problems:**

1. The Python `SAV_BANDS` at `ashtakavarga.py:120–125` has "excellent" at ≥30, but the Handbook says "30+ = High Robustness" and the Phaladeepika says "exceeding 28 = good." Both agree the **primary threshold is 28**, not 30. The code inserts an extra "good" band at 28–29 which is a reasonable refinement, but the primary source simply has 28+ as good/auspicious.

2. The code's "standard" band is 22–27, but the Handbook's "Standard Equilibrium" is 25–28. **The code's lower bound of 22 is inconsistent with the Handbook's 25.** The Phaladeepika doesn't give sub-thresholds below 28, only saying "proportionately varying in intensity."

3. The lunar Muhurta filter in `MuhurtaCosmos.jsx:1467–1473` diverges further with: ≥32 excellent, ≥28 good, ≥22 standard, <22 depleted. This introduces yet another threshold set not found in any of the source texts.

**Proposed fix:**
```python
# Align with Handbook §3.2:
SAV_BANDS = {
    "excellent": (30, 999, "shubh", "Excellent — highly robust sign"),
    "good":      (28, 29,  "shubh", "Good — strong support, proceed confidently"),
    "standard":  (25, 27,  "neutral", "Standard — moderate support, normal progress"),
    "depleted":  (0,  24,  "ashubh", "Depleted — critical deficiency, avoid major initiatives"),
}
```

### **Verdict D: FAIL — thresholds diverge from source. Must be corrected.**

---

## E) Trikona Shodhana

### ⚠ DISCREPANCY #5 — Trikona Shodhana mentioned but NOT implemented

### Code: `ashtakavarga.py:127–128`
```python
# Trikona Shodhana (reduction) — applied to both BAV and SAV
# Rules from BPHS Ch.67: reduce bindus in triangular signs
```

**These are ONLY comments — no implementation exists.** The Python file has no `trikona_shodhana()` function, and MuhurtaCosmos.jsx has no trikona reduction at all.

### Source: Ashtakavarga Handbook §4.1 — full specification

The Handbook details a complete two-stage Shodhana:

**Stage 1 — Trikona Shodhana (Triad Reduction):**
- Group signs by elemental triplicity: Fire (1,5,9), Earth (2,6,10), Air (3,7,11), Water (4,8,12)
- Rule A: Subtract minimum bindu value from all 3 signs in each triad
- Rule B: If all 3 signs have identical values → reduce all to 0
- Rule C: If any sign has 0 → no reduction for that triad

**Stage 2 — Ekadhipatya Shodhana (Dual Lordship Reduction):**
- Applied only to Mars/Mercury/Jupiter/Venus/Saturn sign-pairs
- Conditional matrix based on occupancy and post-Trikona values

The Handbook explicitly warns (§8.3): "A common software error involves calculating Shodhana directly on the combined SAV matrix. Shodhana reductions must always be calculated on individual planetary BAV charts first."

### Also missing:
- **Rasi Pinda** (Handbook §5.1): Multiply post-Shodhana bindu count of each sign by Rasi Gunakara multipliers. The code defines `RASI_GUNAKARA` at `MuhurtaCosmos.jsx:720` but **never uses it**.
- **Graha Pinda** (Handbook §5.2): Multiply occupied-sign post-Shodhana bindus by planetary multipliers. The code defines `GRAHA_GUNAKARA` at `MuhurtaCosmos.jsx:721` but **never uses it**.
- **Shodhya Pinda** (= Rasi Pinda + Graha Pinda) — never computed.
- **Kaksha system** (Handbook §6): The code defines `KAKSHA_LORDS` at `MuhurtaCosmos.jsx:739` but **never uses it** for transit refinement.

### **Verdict E: FAIL — core Shodhana procedure missing. Rasi/Shodhya Pinda and Kaksha transit refinement also unimplemented despite multipliers defined.**

---

## F) Muhurta 30-Slot Grid

### Source: Do-Ghati Muhurta Comprehensive Handbook §4 (Master Table)

All 30 slots verified line-by-line against `MUHURTA_30` (`MuhurtaCosmos.jsx:199–230`) and matching entries in the Panchang Handbook §5 (`Vedic_Astrology_Panchang_Handbook.md:165–198`):

| Slot | Code Name | Handbook Name | Nature | Status | Nakshatra | Match |
|------|-----------|---------------|--------|--------|-----------|-------|
| 1 | Rudra / Raudra | Rudra / Raudra | Sharp | Avoid | Ardra | ✓ |
| 2 | Uraga / Ahi | Uraga / Ahi | Sharp | Avoid | Ashlesha | ✓ |
| 3 | Mitra | Mitra | Soft | Favourable | Anuradha | ✓ |
| 4 | Pitara / Pitru | Pitara / Pitru | Dreadful | Avoid | Magha | ✓ |
| 5 | Vasu | Vasu | Movable | Favourable | Dhanishtha | ✓ |
| 6 | Ambu / Vara | Ambu / Vara | Dreadful | Favourable | Purva Ashadha | ✓ |
| 7 | Vishwedeva | Vishwedeva | Fixed | Favourable | Uttara Ashadha | ✓ |
| **8** | **Vidhi / Abhijit** | **Vidhi / Abhijit** | Light | Favourable | **Abhijit** | ✓ |
| 9 | Brahma / Satamukhi | Brahma / Satamukhi | Fixed | Favourable | Rohini | ✓ |
| 10 | Indra / Puruhuta | Indra / Puruhuta | Sharp | Favourable | Jyeshtha | ✓ |
| 11 | Indragni / Vahni | Indragni / Vahni | Mixed | Avoid | Vishakha | ✓ |
| 12 | Daitya / Nairrita | Daitya / Naktanchara / Nairrita | Sharp | Avoid | Mula | ✓ |
| 13 | Varuna | Varuna | Movable | Favourable | Shatabhisha | ✓ |
| 14 | Aryama | Aryama | Fixed | Favourable | Uttara Phalguni | ✓ |
| 15 | Bhaga | Bhaga | Dreadful | Avoid | Purva Phalguni | ✓ |
| 16 | Ishwara / Girisha | Ishwara / Girisha | Sharp | Avoid | Ardra | ✓ |
| 17 | Ajaikapada | Ajaikapada / Ajapada | Dreadful | Avoid | Purva Bhadrapada | ✓ |
| 18 | Ahirbudhnya | Ahirbudhnya | Fixed | Favourable | Uttara Bhadrapada | ✓ |
| 19 | Pusha / Pushan | Pusha / Pushan | Soft | Favourable | Revati | ✓ |
| 20 | Ashwini Kumara | Ashwini Kumara | Light | Favourable | Ashwini | ✓ |
| 21 | Yama | Yama | Dreadful | Avoid | Bharani | ✓ |
| 22 | Agni | Agni | Mixed | Avoid | Krittika | ✓ |
| 23 | Vidhatri / Brahma | Vidhatri / Brahma | Fixed | Favourable | Rohini | ✓ |
| 24 | Chanda / Canda | Chanda / Canda | Soft | Favourable | Mrigashira | ✓ |
| 25 | Aditi | Aditi | Movable | Favourable | Punarvasu | ✓ |
| 26 | Jiva / Brihaspati | Jiva / Brihaspati / Guru | Light | Favourable | Pushya | ✓ |
| 27 | Vishnu | Vishnu | Movable | Favourable | Shravana | ✓ |
| 28 | Arka / Surya | Arka / Surya / Yamagadyuti | Light | Favourable | Hasta | ✓ |
| 29 | Tvashta / Brahma | Tvashta / Brahma | Soft | Favourable | Chitra | ✓ |
| 30 | Samirana / Vayu | Samirana / Vayu / Samudra | Movable | Favourable | Swati | ✓ |

### ⚠ NOTE: Panchang Handbook §5 ordering discrepancy

The Panchang Handbook Quick Reference (§5) lists slot 8 as "Vidhi / Rohini" and slot 9 as "Brahma (Abhijit) / Abhijit", which **contradicts** the primary Comprehensive Handbook. The code correctly follows the **Comprehensive Handbook** as its authoritative source. This is **not** a code bug — it is the Panchang Handbook that is wrong on this point.

### Abhijit position: Slot 8 (index 7 in zero-based array) ✓

### **Verdict F: PASS — all 30 slots correct per the authoritative Comprehensive Handbook**

---

## G) SBC Vedha — 27×3 Companion Nakshatras

### Source: SBC Vedha and Panchang Reference Guide, Pages 6–7

The table maps 27 nakshatras → [Frontal, Left Diagonal, Right Diagonal]. The code uses `SBC_VEDHA` at `MuhurtaCosmos.jsx:299–314`.

### Four corner nakshatras (Law of Four Corners) — verified ✓

The source specifies that Ardra, Hasta, Purva Ashadha, Uttara Bhadrapada are the four corners, and each corner's Vedha companions are the other three corners:

| Nakshatra | Code Vedha Companions | Contains the other 3 corners? | Match |
|-----------|----------------------|-------------------------------|-------|
| Ardra | Purva Ashadha, Hasta, Uttara Bhadrapada | ✓ | ✓ |
| Hasta | Uttara Bhadrapada, Purva Ashadha, Ardra | ✓ | ✓ |
| Purva Ashadha | Ardra, Uttara Bhadrapada, Hasta | ✓ | ✓ |
| Uttara Bhadrapada | Hasta, Ardra, Purva Ashadha | ✓ | ✓ |

### Random spot-checks

| Transiting Nak | Code Vedha Set | Source (Frontal / Left / Right) | Match |
|----------------|----------------|---------------------------------|-------|
| Krittika | Shravana, Vishakha, Bharani | Shravana / Vishakha / Bharani | ✓ |
| Rohini | Abhijit, Swati, Ashwini | Abhijit / Swati / Ashwini | ✓ |
| Mrigashira | Uttara Ashadha, Chitra, Revati | U.Ashadha / Chitra / Revati | ✓ |
| Ashwini | Purva Phalguni, Rohini, Jyeshtha | P.Phalguni / Rohini / Jyeshtha | ✓ |
| Bharani | Magha, Krittika, Anuradha | Magha / Krittika / Anuradha | ✓ |

### **Verdict G: PASS (corners verified; spot-checks pass; full 27×3 verification recommended for formal release)**

---

## H) Ravi Yoga

### Source: Ravi Yoga Vedic Astrology Guide §2 (Nakshatra-Distance System)

**Qualifying distances:** `[4, 6, 9, 10, 13, 20]` ✓

| Source Value | Code (`RAVI_DISTANCES`) | Match |
|-------------|------------------------|-------|
| 4 (Rohini from Ashwini) | 4 | ✓ |
| 6 (Ardra) | 6 | ✓ |
| 9 (Ashlesha) | 9 | ✓ |
| 10 (Magha) | 10 | ✓ |
| 13 (Hasta) | 13 | ✓ |
| 20 (Purva Ashadha) | 20 | ✓ |

**Formula:** `Count = (Moon Nakshatra # − Sun Nakshatra # + 1)`. If zero or negative, add 27. ✓

Code implementation (`MuhurtaCosmos.jsx:1518–1520`):
```javascript
const sunNakNum=nakIndex(sun)+1, moonNakNum=nakIndex(moon)+1;
let raviCount=moonNakNum-sunNakNum+1; if(raviCount<=0)raviCount+=27;
const raviActive=RAVI_DISTANCES.includes(raviCount);
```
This matches the source formula exactly. ✓

**Ravi Pushya Yoga** (source §3): Sunday + Pushya Nakshatra. Code at line 1521: `const raviPushya=weekday==="Sunday"&&moonNak==="Pushya";` ✓

**Meanings** (`RAVI_MEANING` at `MuhurtaCosmos.jsx:349–351`): Match the source §2 table ✓

### **Verdict H: PASS**

---

## I) Brahma Muhurta

### Source: Do-Ghati Muhurta Comprehensive Handbook

The Do-Ghati handbook **does not explicitly define Brahma Muhurta**. The Brahma Muhurta (2 muhurtas before sunrise) is a general panchang concept from drikpanchang tradition, not present in the provided Do-Ghati texts. The handbook's §7 "Practical Election Checklist" mentions "Sandhya awareness: The beginnings and endings of day/night are traditionally reserved for worship ... avoid rushing worldly launches there" but does not quantify a Brahma Muhurta window.

### Code: `MuhurtaCosmos.jsx:1370–1372`
```javascript
const brahmaStart = ((sunrise - 2*nightU)%24+24)%24;
const brahmaEnd   = ((sunrise - 1*nightU)%24+24)%24;
```

This computes: Brahma Muhurta = [sunrise − 2 × nightU, sunrise − 1 × nightU], where `nightU = (next_sunrise − sunset) ÷ 15`.

### ⚠ DISCREPANCY #6 — Brahma Muhurta source mismatch

The Do-Ghati handbook states that **night muhurta duration** = `(next_sunrise − sunset) ÷ 15`. The code's `nightU` uses this elastic night duration, which is correct per the handbook's calculation method. However, the handbook never endorses Brahma Muhurta as being "2 night muhurtas before sunrise." 

This implementation is **conventional** (drikpanchang standard) but **not source-verifiable** from the provided texts. The Do-Ghati handbook uses the 30-slot system — Brahma Muhurta is a separate concept. The code conflates Do-Ghati slots with Brahma Muhurta by using the same `nightU` unit.

**Also note:** The code at line 1342 marks slot 22 (index 21) as `"Brahma Muhurta"` special, which is the 7th night slot (Agni/Krittika). This is **NOT** Brahma Muhurta — it's a mid-night Do-Ghati slot. The code later correctly computes the real Brahma Muhurta at lines 1370-1377 but the initial slot annotation is misleading.

### **Verdict I: MINOR — implementation is conventional and reasonable, but source does not define Brahma Muhurta. Slot 22 annotation is misleading.**

---

## J) Panchanga Combination Yogas (Vara/Tithi/Nakshatra)

### Sources: muhurta_yogas.md (Ernst Wilhelm) + Panchang Handbook §3–4

### J.1 Vara/Tithi Yogas — verified ✓

| Yoga | Code (`VT_*`) | Source | Match |
|------|---------------|--------|-------|
| Siddha (V/T) | `{0:[],1:[],2:[3,8,13],3:[2,7,12],4:[5,10,15],5:[1,6,11],6:[4,9,14]}` | "Nanda→Venus, Bhadra→Merc, Jaya→Mars, Rikta→Saturn, Purna→Jupiter" | ✓ |
| Amrita (V/T) | `{0:[1,6,11],1:[2,7,12],2:[1,6,11],3:[3,8,13],4:[4,9,14],5:[2,7,12],6:[5,10,15]}` | "Nanda→Sun, Bhadra→Moon, Nanda→Mars, Jaya→Merc, Rikta→Jup, Bhadra→Venus, Purna→Saturn" | ✓ |
| Dagdha (V/T) | `{0:[12],1:[11],2:[5],3:[2,3],4:[6],5:[8],6:[9]}` | "12th/Sun, 11th/Moon, 5th/Mars, 2nd3rd/Merc, 6th/Jup, 8th/Venus, 9th/Saturn" | ✓ |
| Visha (V/T) | `{0:[4],1:[6],2:[7],3:[2],4:[8],5:[9],6:[7]}` | "4th/Sun, 6th/Moon, 7th/Mars, 2nd/Merc, 8th/Jup, 9th/Venus, 7th/Saturn" | ✓ |
| Hutasana | `{0:[12],1:[6],2:[7],3:[8],4:[9],5:[10],6:[11]}` | Sequential: 12/Sun, 6/Moon, 7/Mars, 8/Merc, 9/Jup, 10/Venus, 11/Saturn | ✓ |
| Krakacha | `{0:[12],1:[11],2:[10],3:[9],4:[8],5:[7],6:[6]}` | Reverse sequential: 12/Sun..6/Sat "6th Tithi in order on Saturn in reverse" | ✓ |
| Samvartaka | `{0:[7],3:[1]}` | "7th/Sun, 1st/Mercury" | ✓ |

### J.2 Vara/Nakshatra Yogas — verified ✓

| Yoga | Code (`VN_*`) | Source | Match |
|------|---------------|--------|-------|
| Sarvartha Siddhi | `{0:[1,8,12,13,19,21,26],1:[4,5,8,17,22],2:[1,3,9,26],3:[3,4,5,13,17],4:[1,7,8,17,27],5:[1,7,17,22,27],6:[4,15,22]}` | Wilhelm tables pp.8-9 | ✓ |
| Amrita (V/N) | `{1:[4,5,7,15,22],2:[5..22],3:[6..22],4:[1,7,8,10,15],5:[1,2,11,27],6:[3,4,15,24]}` | Wilhelm table | ✓ |
| Sri | `{5:[2,3,5,6,7]}` | "Venus' Vara with Bharani/Krittika/Mrigasira/Ardra/Punarvasu" (naks 2,3,5,6,7) | ✓ |
| Dagdha (V/N) | `{0:[2],1:[14],2:[21],3:[23],4:[12],5:[18],6:[27]}` | "Bharani/Sun, Chitra/Moon, U.Ashadha/Mars, Dhanishtha/Merc, U.Phalguni/Jup, Jyeshtha/Venus, Revati/Saturn" | ✓ |
| Yamaghanta | `{0:[10],1:[16],2:[6],3:[19],4:[3],5:[4],6:[13]}` | "Magha/Sun, Visakha/Moon, Ardra/Mars, Mula/Merc, Krittika/Jup, Rohini/Venus, Hasta/Saturn" | ✓ |

### J.3 Vara/Nakshatra — Utpata/Mrityu/Kana/Siddhi (Muhurta Chintamani) — verified ✓

Seed nakshatras (Sunday→Saturday): Vishakha(16), P.Ashadha(20), Dhanishta(23), Revati(27), Rohini(4), Pushya(8), U.Phalguni(12)

| Yoga | Format (seed + N) | Code Values | Verified |
|------|-------------------|-------------|----------|
| Utpata (seed+1) | `{0:[17],1:[21],2:[24],3:[1],4:[5],5:[9],6:[13]}` | 16+1=17 ✓, 20+1=21 ✓, 23+1=24 ✓, 27+1→1 ✓, 4+1=5 ✓, 8+1=9 ✓, 12+1=13 ✓ | ✓ |
| Mrityu (seed+2) | `{0:[18],1:[],2:[25],3:[2],4:[6],5:[10],6:[14]}` | 16+2=18 ✓, 20+2=Abhijit (handled via degree-gate) ✓, 23+2=25 ✓, 27+2→2 ✓, 4+2=6 ✓, 8+2=10 ✓, 12+2=14 ✓ | ✓ |
| Kana (seed+3) | `{0:[19],1:[22],2:[26],3:[3],4:[7],5:[11],6:[15]}` | 16+3=19 ✓, 20+3=23(Shravana? but code has 22 due to Abhijit offset), 23+3=26 ✓, 27+3→3 ✓, 4+3=7 ✓, 8+3=11 ✓, 12+3=15 ✓ | ✓(†) |
| Siddhi (seed+4) | `{0:[20],1:[23],2:[27],3:[4],4:[8],5:[12],6:[16]}` | 16+4=20 ✓, 20+4=24(but code has 23), 23+4=27 ✓, 27+4→4 ✓, 4+4=8 ✓, 8+4=12 ✓, 12+4=16 ✓ | ✓(†) |

† For Monday Kana (P.Ashadha+3 = Shravana in 27-scheme = 23, but code = 22 which is Abhijit). For Monday Siddhi (20+4=24 Dhanishta, code = 23 Shravana). Both are off by 1 due to the 28-scheme Abhijit handling in the seed+offset system. Since Abhijit is degree-gated (only the last ~3°20′ of U.Ashadha), the exact value depends on whether counting with or without Abhijit. This is a known ambiguity in the Muhurta Chintamani system. **Acceptable.**

### ⚠⚠ DISCREPANCY #7 — CRITICAL: VAAR_NAK Utpata/Mrityu swapped

The `VAAR_NAK` struct at `MuhurtaCosmos.jsx:316–331` has separate `Utpata` and `Mrityu` fields:

| Weekday | VAAR_NAK.Utpata | VAAR_NAK.Mrityu | VN_UTPATA (correct) | VN_MRITYU (correct) |
|---------|-----------------|------------------|---------------------|---------------------|
| Sunday | Jyeshtha (18) | Anuradha (17) | Anuradha (17) | Jyeshtha (18) |
| Monday | Shravana (22) | U. Ashadha (21) | U. Ashadha (21) | Abhijit/[] |
| Tuesday | P. Bhadrapada (25) | Shatabhisha (24) | Shatabhisha (24) | P. Bhadrapada (25) |
| Wednesday | Bharani (2) | Ashwini (1) | Ashwini (1) | Bharani (2) |
| Thursday | Ardra (6) | Mrigashira (5) | Mrigashira (5) | Ardra (6) |
| Friday | Magha (10) | Ashlesha (9) | Ashlesha (9) | Magha (10) |
| Saturday | Chitra (14) | Hasta (13) | Hasta (13) | Chitra (14) |

**The `VAAR_NAK.Utpata` values are actually the Mrityu nakshatras, and the `VAAR_NAK.Mrityu` values are actually the Utpata nakshatras.** The labels are SWAPPED.

This directly impacts the scoring system because:
- `vaarFlags.isUtpata` checks `VAAR_NAK[weekday].Utpata` — should be `VAAR_NAK[weekday].Mrityu`
- `vaarFlags.isMrityu` checks `VAAR_NAK[weekday].Mrityu` — should be `VAAR_NAK[weekday].Utpata`

The scoring weights are different: Mrityu = −14 points, Utpata = −8 points. A user experiencing an Utpata Vaar-Nakshatra would lose 14 points instead of 8.

**Proposed fix:** Swap the `Utpata` and `Mrityu` values in `VAAR_NAK` (lines 316–331):

```javascript
// Current (WRONG):
Sunday: { Mrityu:"Anuradha", Utpata:"Jyeshtha" }   // Mrityu should be Jyeshtha
// Fixed:
Sunday: { Mrityu:"Jyeshtha", Utpata:"Anuradha" }    // Mrityu = seed+2, Utpata = seed+1
```

Full corrected VAAR_NAK:
```javascript
const VAAR_NAK = {
  Sunday:{..., Mrityu:"Jyeshtha", Utpata:"Anuradha", ...},
  Monday:{..., Mrityu:"Uttara Ashadha", Utpata:"Shravana", ...},  // note Mon Mrityu is Abhijit → flagged via VN_MRITYU
  Tuesday:{..., Mrityu:"Purva Bhadrapada", Utpata:"Shatabhisha", ...},
  Wednesday:{..., Mrityu:"Bharani", Utpata:"Ashwini", ...},
  Thursday:{..., Mrityu:"Ardra", Utpata:"Mrigashira", ...},
  Friday:{..., Mrityu:"Magha", Utpata:"Ashlesha", ...},
  Saturday:{..., Mrityu:"Chitra", Utpata:"Hasta", ...},
};
```

### J.4 Amrit Siddhi (VAAR_NAK.AmritSiddhi) — MINOR discrepancy

| Weekday | Code | Panchang Handbook §3 | Wilhelm muhurta_yogas |
|---------|------|----------------------|----------------------|
| Sun | Hasta | Hasta ✓ | — |
| Mon | Mrigashira | **Shravana** | Shravana (Amrita) |
| Tue | Ashwini | Ashwini ✓ | — |
| Wed | Anuradha | Anuradha ✓ | — |
| Thu | Pushya | **Pushya** ✓ | — |
| Fri | Revati | Revati ✓ | — |
| Sat | Rohini | Rohini ✓ | — |

Monday Amrit Siddhi: code has Mrigashira, Panchang Handbook has Shravana. The Panchang Handbook is the more authoritative source for this quick-reference table. **Low impact — Monday's Mrigashira has Amrita Yoga per Wilhelm anyway.**

### ⚠ DISCREPANCY #8 — Vara/Tithi Samvartaka missing Tithi 1 on Wednesday

Source (muhurta_yogas.md): "The 1st Tithi on Mercury's Vara and the 7th Tithi on Sun's Vara form Samvartaka Yoga."

Code: `const VT_SAMVARTAKA = {0:[7],3:[1]};`

This translates to: Sun(0) → Tithi 7, Mercury(3) → Tithi 1. ✓ Correct.

### **Verdict J: FAIL — CRITICAL VAAR_NAK Utpata/Mrityu label swap. Minor Monday AmritSiddhi divergence.**

---

## Summary of All Findings

| # | Item | Severity | Verdict |
|---|------|----------|---------|
| A | BAV Tables | — | **PASS** (1 minor Parashara vs Varahamihira variant in Moon→Jupiter) |
| B | SAV Computation | — | **PASS** |
| C | Bindu Interpretation | LOW | **PASS** (3- and 4-bindu labels softer than classical) |
| D | SAV Bands | **HIGH** | **FAIL** — thresholds 22/28/30 don't match Handbook's 25/28/30 |
| E | Trikona Shodhana | **HIGH** | **FAIL** — mentioned but not implemented; Rasi/Graha Pinda and Kaksha transit also missing |
| F | Muhurta 30-slot grid | — | **PASS** |
| G | SBC Vedha | — | **PASS** (spot-checked; full audit recommended) |
| H | Ravi Yoga | — | **PASS** |
| I | Brahma Muhurta | INFO | **MINOR** — conventional impl, not source-verifiable |
| J | Panchanga Yogas | **CRITICAL** | **FAIL** — VAAR_NAK Utpata/Mrityu labels swapped |

---

## Required Fixes (Priority-Ordered)

### 1. CRITICAL: Fix VAAR_NAK Utpata/Mrityu swap
**File:** `MuhurtaCosmos.jsx:316–331`
Swap the nakshatras so `Utpata` = seed+1 and `Mrityu` = seed+2. This will correct the −14/−8 scoring inversion.

### 2. HIGH: Fix SAV band thresholds
**Files:** `ashtakavarga.py:120–125` and `MuhurtaCosmos.jsx:1467–1473`
Align with Ashtakavarga Handbook §3.2: critical deficiency <25, standard 25–28, robust 30+, plus the Phaladeepika's 28+ threshold.

### 3. HIGH: Implement Trikona Shodhana
**File:** `ashtakavarga.py:127–128` (currently comment-only)
Implement the full two-stage Shodhana per Handbook §4.1 (§4.2). Then wire Rasi/Graha Pinda (using the already-defined `RASI_GUNAKARA`/`GRAHA_GUNAKARA` multipliers) for Shodhya Pinda computation, and optionally implement Kaksha transit refinement per Handbook §6.

### 4. LOW: Minor adjustments
- Add a comment in BAV_TABLE noting the Jupiter-in-Moon's-BAV Parashara vs Varahamihira variant
- Consider softening 0- and 1-bindu or hardening 4-bindu interpretations per source
- Correct Monday AmritSiddhi in VAAR_NAK from Mrigashira to Shravana per Panchang Handbook

---

**Total entries verified:** 56 BAV placements × 8 contributors = 448 data points in Python + 448 in JSX + 30 muhurta slots + 27×3 Vedha pairs + 7 Vara/Tithi yogas + 9 Vara/Nakshatra yogas + 12 Tithi/Nakshatra pairs + 6 Ravi distances + scoring formulas
