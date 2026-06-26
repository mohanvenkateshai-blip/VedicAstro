# Vedic Prediction Engine — Yoga Detection Module Audit

**Date**: 23 June 2026
**Engine audited**: `vedic_engine/prediction/yoga.py` (530 lines)
**Source texts verified**:
1. Phaladeepika (Mantreswara) — Ch.6–7
2. Sarvartha Chintamani (Vyankatesh Sharma) — Ch.8, wealth sections
3. Hora Sara (Prithuyasas) — Ch.19 (Chandra Yogas)
4. Brihat Parasara Hora Shastra (Vol.1) — Ch.37 (Nabhasa), Ch.41 (Raja)
5. Jyotish Yoga Handbook 101 — reference catalogue
6. Muhurta Yogas (Ernst Wilhelm) — Vara/Tithi/Nakshatra tables
7. MuhurtaCosmos.jsx — Wilhelm yogas in the web UI

---

## Critical Structural Finding: Detection Gap

**The engine data structures define 34+ yogas, but `detect_yogas()` only detects 14.** The following are defined in constants but have **zero detection logic**:

| Category | Defined but NOT Detected |
|----------|--------------------------|
| Raja | Kendra-Kona, Mutual Kendra, Dharma-Karma Adhipati, 4-9 Connection, 5-9 Connection |
| Dhana | All 4 Dhana Yogas |
| Chandra | Adhi Yoga |
| Raja/Neecha | Neecha Bhanga Raja Yoga |

This means users receiving `detect_yogas()` output receive **no Raja Yoga (house-lord), no Dhana Yoga, no Adhi Yoga, and no Neechabhanga results**.

**Recommendation**: Either implement detection for the missing yogas or remove them from the data structures to avoid misleading users who see them in the definitions.

---

## A) Pancha Mahapurusha Yogas — PASS with minor notes

### Verification Table

| Yoga | Engine Planet | Own Signs | Exaltation | Kendra | Source |
|------|--------------|-----------|------------|--------|--------|
| Ruchaka | Mars | Aries, Scorpio | Capricorn | 1,4,7,10 | PD Ch.6 v.1 |
| Bhadra | Mercury | Gemini, Virgo | Virgo | 1,4,7,10 | PD Ch.6 v.1 |
| Hamsa | Jupiter | Sagittarius, Pisces | Cancer | 1,4,7,10 | PD Ch.6 v.1 |
| Malavya | Venus | Taurus, Libra | Pisces | 1,4,7,10 | PD Ch.6 v.1 |
| Sasa | Saturn | Capricorn, Aquarius | Libra | 1,4,7,10 | PD Ch.6 v.1 |

### Source Confirmation
Phaladeepika Ch.6 v.1 (pp.55-56):
> "If Mars occupies Aries or Scorpio (his own signs), or Capricorn (his sign of exaltation), identical with a kendra, the yoga so formed is known as Ruchaka."

Same pattern repeated verbatim for Mercury→Bhadra, Jupiter→Hamsa, Venus→Malavya, Saturn→Sasa.

### Engine Code
`yoga.py:362-378` — correct:
- Checks planet in KENDRA from Lagna
- Checks `PLANET_OWNERSHIP` or `EXALTATION`

### Findings

1. **Planet assignments**: PASS — exact match with PD, BPHS, Hora Sara
2. **Required placement**: PASS — Kendra (1,4,7,10) correctly defined
3. **Dignity**: PASS — own sign or exaltation correctly checked
4. **Effects**: PASS — descriptions align with PD Ch.6 vv.2-4
5. **Minor note**: Jataka Parijata adds Moolatrikona as qualifying dignity (not implemented). This is an accepted variant, not required for correctness.
6. **Confidence**: 1.0 — appropriate since exact match

**Verdict: CORRECT. No changes needed.**

---

## B) Chandra Yogas — PASS with 1 omission

### Verification Table

| Yoga | Engine Condition | Classical Definition | Match? |
|------|-----------------|---------------------|--------|
| Sunapha | Planet (not Sun) in 2nd from Moon | PD Ch.6 v.5, HS Ch.19 v.1 | PASS |
| Anapha | Planet (not Sun) in 12th from Moon | PD Ch.6 v.5, HS Ch.19 v.1 | PASS |
| Durudhara | Planets in BOTH 2nd and 12th from Moon | PD Ch.6 v.5, HS Ch.19 v.1 | PASS |
| Kemadruma | No planet in 2nd/12th AND no Kendra benefic from Lagna | HS Ch.19 v.8, PD Ch.6 v.5 notes | PASS |
| Adhi Yoga | Benefics in 6th, 7th, 8th from Moon | PD Ch.6 v.42, HS Ch.19 v.1 | **NOT DETECTED** |

### Source Confirmation
Hora Sara Ch.19 v.1:
> "Should the 2nd, 12th, and both 2nd, 12th from the Moon be occupied by planets excluding the Sun, the three resulting Yogas are known respectively as Sunapha, Anapha and Durudhura Yogas."

Hora Sara Ch.19 v.8 (Kemadruma):
> "The said yogas will not be put to effect if the Moon's or lagna's angles are not occupied. In such case, the Yoga arising is called Kemadruma which makes even a king beg."

Hora Sara Ch.19 v.1 (Adhi Yoga):
> "Should the 7th, 8th, and 6th from the Moon (or the Lagna) be occupied by benefic, free from the Sun's company, Adhiyoga results."

### Engine Code
- Sunapha/Anapha/Durudhara: `yoga.py:380-413` — logic correct, excludes Sun ✓
- Kemadruma: `yoga.py:414-428` — correct: checks absence in 2nd/12th then checks for Kendra benefic cancellation ✓
- Kemadruma cancellation: checks benefics in Kendra from Lagna. Classical texts also accept: Kendra from Moon, Moon angular to Lagna, aspect by Jupiter. **Missing** Moon-in-Kendra and Jupiter-aspect cancellation checks.

### Findings

1. **Sunapha/Anapha/Durudhara**: PASS — conditions correct. Sun correctly excluded.
2. **Kemadruma**: PASS on main condition. Partial on cancellation checks (only Lagna Kendra; missing Moon Kendra and Jupiter aspect).
3. **Adhi Yoga**: **BUG** — defined at line 108 in `CHANDRA_YOGAS` but has **zero detection code** in `detect_yogas()`. Also, if implemented, should check from both Moon AND Lagna (per HS), and should require benefics be "free from Sun's company" (HS v.1).
4. **Confidence**: Kemadruma shows 0.7 with note "PARTIAL: verify Kendra cancellation" — this is appropriate.

**Verdict: MOSTLY CORRECT. Add Adhi Yoga detection. Expand Kemadruma cancellation checks.**

---

## C) Raja Yogas — FAIL (no detection implemented)

### Verification Table

| Yoga | Engine Definition | Source | Detection? |
|------|------------------|--------|------------|
| Raja Yoga (Kendra-Kona) | Lord of Kendra with/aspected by lord of Kona | BPHS Ch.41, PD Ch.6 v.37 | **NONE** |
| Raja Yoga (Mutual Kendra) | Lords of Kendra in mutual exchange/conjunction | BPHS Ch.41 | **NONE** |
| Dharma-Karma Adhipati | Lord of 9th and 10th conjoined/mutual exchange | PD Ch.7 v.9, BPHS Ch.41 | **NONE** |
| Raja Yoga (4-9 Connection) | Lord of 4th and 9th conjunction/aspect | SC Ch.8 | **NONE** |
| Raja Yoga (5-9 Connection) | Lord of 5th and 9th conjoined or in Kendra | BPHS Ch.41 v.33-34 | **NONE** |
| Buddha-Aditya Yoga | Mercury and Sun conjoined | BPHS Ch.36 (classical) | **DETECTED** |
| Gaja-Kesari Yoga | Jupiter in Kendra from Moon | PD Ch.6 v.14 | **DETECTED** |
| Lakshmi Yoga | Venus and Jupiter conjunction/mutual aspect | PD Ch.7 v.20 | **DETECTED** |

### Source Details

**Dharma-Karma Adhipati** (PD Ch.7 v.9):
> "Should the lord of the 9th be in the 10th and vice versa, the person born becomes a king who is extolled by all."

**Kendra-Kona** (PD Ch.6 v.37):
> "If the lords of a Kendra and Trikona are similarly placed (that is, they occupy together an auspicious house), the Yoga so formed is called Shankha Yoga."

**5th-9th** (BPHS Ch.41 v.33-34):
> "The 9th Lord is akin to a minister and 5th Lord akin to the chief minister. If both have the mutual aspect... or if they are in conjunction... the native will certainly be a King."

### Engine Bugs Found

1. **Gaja-Kesari**: Correctly detected at `yoga.py:430-439`. PD Ch.6 v.14 says "the Moon is in a Kendra position to Jupiter." Engine checks "Jupiter in Kendra from Moon." These are mathematically equivalent (symmetric kendra relationship). PASS.

2. **Lakshmi Yoga**: Detected at `yoga.py:451-459`. Checks conjunction or mutual aspect. PD Ch.7 v.20 only says "If Venus is aspected by Jupiter" — the engine adds "in benefic signs" and "mutual aspect" which exceeds the PD definition but is within accepted interpretation. The category is listed as "Raja" in the source definition but detection puts it under "Dhana." Minor label inconsistency.

3. **Buddha-Aditya**: Detected by checking same-sign conjunction (`yoga.py:442-449`). Classical — PASS.

4. **ALL house-lord Raja Yogas**: NOT DETECTED. The engine stores them in `RAJA_YOGAS` (lines 120-178) but `detect_yogas()` never reads from `RAJA_YOGAS` (only uses the hardcoded checks). **This is a major implementation gap** — 5 out of 8 defined Raja Yogas produce no results.

**Verdict: PARTIALLY IMPLEMENTED. Implement detection for the 5 missing Raja Yogas.** Conditions and effects in the data structures are correct.

---

## D) Dhana Yogas — FAIL (no detection implemented)

### Verification

| Yoga | Engine Definition | Source | Detection? |
|------|------------------|--------|------------|
| 2nd lord + 11th lord | Association with lord of 11th (or Jupiter) | Standard classical | **NONE** |
| 2nd lord + 5th lord | 2nd in 5th or vice versa + benefic influence | PD Ch.7 | **NONE** |
| 2nd lord + 9th lord | Association of 2nd and 9th lords | PD Ch.7 v.25 | **NONE** |
| 5th lord in Kendra/Kona | 5th lord in Kendra/Kona + benefic aspect | PD Ch.7 | **NONE** |

### Source Confirmation
Phaladeepika Ch.7 v.25:
> "Should one out of the lords of the 11th, the 9th and the 2nd houses occupies a Kendra with reference to the Moon and should Jupiter own the 2nd, the 5th or the 11th house..."

Jyotish Yoga Handbook 101 lists Dhana Yogas as a standard category.

### Engine Status
All 4 Dhana Yogas are defined in `DHANA_YOGAS` (lines 184-209) but **`detect_yogas()` never references `DHANA_YOGAS`**. No detection code exists.

**Verdict: NOT IMPLEMENTED. Conditions appear correct when compared to classical sources. Needs detection logic.**

---

## E) Nabhasa Yogas — PARTIAL (subset implemented)

### Detected (3 of 32)
| Yoga | Engine Condition | BPHS Source | Accuracy |
|------|-----------------|-------------|----------|
| Rajju | All planets in movable signs (Aries, Cancer, Libra, Capricorn) | Ch.37 v.7 | PASS |
| Musala | All planets in fixed signs (Taurus, Leo, Scorpio, Aquarius) | Ch.37 v.7 | PASS |
| Nala | All planets in dual signs (Gemini, Virgo, Sagittarius, Pisces) | Ch.37 v.7 | PASS |

### Not Detected (29 of 32)
Gada, Shankha, Shakata, Maala, Sarpa, Sringataka, Vihaga, Hala, Vajra, Yava, Kamala, Vapi, Yupa, Sara, Shakti, Danda, Nauka, Koota, Chhatra, Chaapa, ArdhaChandra, Chakra, Samudra, Vallaki, Dama, Pasha, Kedara, Shula, Yuga, Gola.

### Source Confirmation
BPHS Ch.37 v.7:
> "If all the planets are situated in movable signs they cause Rajju Yoga, if they are in fixed signs they cause Musala Yoga and if they are in dual signs they cause Nala Yoga."

### Engine Bugs

1. **All-7-planet requirement**: The engine requires ALL planets to be in the same sign type. BPHS says "all the planets" — correct. But Garga's view (noted in BPHS commentary) allows partial occupancy. Current implementation is stricter than some classical interpretations but consistent with BPHS core.

2. **Gada Yoga**: Defined in engine (`yoga.py:234-239`) as "All planets in Kendra or all in Panaphara." BPHS Ch.37 v.9 says: "If all the planets occupy two successive angles, the yoga so formed is called Gada Yoga." **Engine definition is wrong** — it says Kendra OR Panaphara, not "two successive angles." Also, not detected.

3. **Shankha Yoga**: Engine defines as "All planets in Panaphara and Apoklima." BPHS doesn't list this as a Nabhasa Yoga — Shankha is a Sankhya/Dala type in BPHS. PD Ch.6 v.37 uses "Shankha" for Kendra+Trikona lords conjunction (completely different). The engine's definition conflates two different Shankha yogas.

4. **Confidence**: 0.8 — appropriate since only 7-planet body considered.

**Verdict: CORRECT for the 3 Ashraya yogas implemented. Gada and Shankha definitions are incorrect. 29 of 32 Nabhasa yogas missing from detection.**

---

## F) Viparita Raja Yoga — PASS with interpretation notes

### Engine Condition
> "Lord of 6th, 8th, or 12th in a Dusthana (6,8,12) or with another Dusthana lord" — requires ≥2 such lords.

### Source Comparison
Uttarakalamrit (cited in PD Ch.6 notes, pp.70-71):
> "If the lord of the 8th is in the 12th or 6th, if the lord of the 6th is in the 8th or 12th, if the lord of the 12th is in the 8th or 6th, the three lords may be in the signs of each other or be aspected by each other and if they are not associated with or aspected by the lords of any other houses..."

Jyotish Yoga Handbook 101:
> "6th, 8th, or 12th lords placed exclusively in 6th, 8th, or 12th."

### Findings

1. **PASS**: The engine's requirement of dusthana lords in dusthanas is correct per all sources.
2. **PASS**: The ≥2 requirement is a reasonable compromise between Uttarakalamrit's strict formulation and modern practice.
3. **Missing**: The engine doesn't check for "not associated with lords of other houses" (the Uttarakalamrit constraint). The most conservative interpretation requires the dusthana lords to be EXCLUSIVELY involved with each other.
4. **Confidence**: 1.0 — but should be 0.7-0.8 with a note about the exclusivity check missing.

**Verdict: SUBSTANTIALLY CORRECT. Consider lowering confidence and adding the exclusivity check.**

---

## G) Neecha Bhanga Raja Yoga — FAIL (no detection)

### Engine Definition
`yoga.py:260-264` defines 2 conditions:
1. "lord of debilitation sign in Kendra from Moon/Lagna"
2. "exalted lord aspects debilitated planet"

### Phaladeepika Ch.7 vv.26-30 — Five Types
| # | Condition | Engine Coverage |
|---|-----------|----------------|
| 1 | Lord of depression sign OR planet exalted in that sign in Kendra from Lagna/Moon | Partial (only lord of depression sign covered) |
| 2 | Lord of depression sign AND lord of exaltation sign mutually in Kendra | **NOT COVERED** |
| 3 | Debilitated planet aspected by lord of its sign | Covered (#2 above) |
| 4 | Lord of depression sign OR lord of exaltation sign in Kendra from Lagna/Moon | Covered (#1 above) |
| 5 | Debilitated planet itself in Kendra from Lagna/Moon | **NOT COVERED** |

### Engine Status
**Not detected.** `Neecha Bhanga Raja Yoga` is defined in `SC_YOGAS` (line 260-264) but has **zero detection code** in `detect_yogas()`.

### Jyotish Yoga Handbook 101 (pp.405-415) Additional Conditions
- Dispositor in Kendra from Ascendant/Moon
- Planet exalted in that sign in Kendra
- Lord of exaltation sign in Kendra
- Debilitated planet aspected by sign dispositor
- Highly exalted in Navamsha (Vargottama)

**Verdict: NOT IMPLEMENTED. Definition captures only 2 of 5 PD conditions. Add detection and expand to all 5 types.**

---

## H) Wilhelm Vara/Tithi/Nakshatra Yogas — MOSTLY CORRECT with 1 drift

### Data Tables Verified

#### Vara/Tithi (VT_*) — ALL PASS
| Table | Entries | Wilhelm Source Match |
|-------|---------|---------------------|
| VT_SIDDHA | 5 non-empty | 100% (tithi groups match vars) |
| VT_AMRITA | 7 non-empty | 100% |
| VT_DAGDHA | 7 non-empty | 100% (incl. Mercury dual) |
| VT_VISHA | 7 non-empty | 100% |
| VT_HUTASANA | 7 non-empty | 100% |
| VT_KRAKACHA | 7 non-empty | 100% (descending order) |
| VT_SAMVARTAKA | 2 non-empty | 100% |

#### Vara/Nakshatra (VN_*) — 7 of 8 PASS, 1 DRIFT
| Table | Entries | Wilhelm Source Match |
|-------|---------|---------------------|
| VN_SARVARTHA | 7 non-empty | **100%** — every nakshatra verified |
| VN_AMRITA | 6 non-empty | **100%** |
| VN_SRI | 1 non-empty | **100%** |
| VN_DAGDHA | 7 non-empty | **100%** |
| VN_YAMAGHANTA | 7 non-empty | **100%** |
| VN_UTPATA | 7 non-empty | **DRIFT** — uses Muhurta Chintamani seed+1 system |
| VN_MRITYU | 6+Abhijit | **DRIFT** — same seed+n system |
| VN_KANA | 7 non-empty | **DRIFT** — same seed+n system |
| VN_SIDDHI | 7 non-empty | **DRIFT** — same seed+n system |

#### Utpata/Mrityu/Kana/Siddhi Drift Detail

The engine comment acknowledges this explicitly:
> "Utpāta–Mṛtyu–Kāṇa–Siddhi catuṣṭaya (Muhūrta Cintāmaṇi). From each weekday's SEED nakshatra, the NEXT FOUR nakshatras (28-scheme incl. Abhijit) are Utpāta, Mṛtyu, Kāṇa, Siddhi."

Wilhelm's tables list the SEED nakshatras as the yogas. The engine offsets by +1 (Utpata = seed+1, Mrityu = seed+2, Kana = seed+3, Siddhi = seed+4):

| Day | Seed (Wilhelm) | Engine Utpata | Engine Mrityu | Engine Kana | Engine Siddhi |
|-----|---------------|---------------|---------------|-------------|---------------|
| Sun | Vishakha (16) | Anuradha (17) | Jyestha (18) | Mula (19) | P.Ashadha (20) |
| Mon | P.Ashadha (20) | U.Ashadha (21) | Abhijit/Sravana | Sravana (22) | Dhanishta (23) |
| Tue | Dhanishta (23) | Satabhisha (24) | P.Bhadrapada (25) | U.Bhadrapada (26) | Revati (27) |
| Wed | Revati (27) | Ashvini (1) | Bharani (2) | Krittika (3) | Rohini (4) |
| Thu | Rohini (4) | Mrigasira (5) | Ardra (6) | Punarvasu (7) | Pushya (8) |
| Fri | Pushya (8) | Ashlesha (9) | Magha (10) | P.Phalguni (11) | U.Phalguni (12) |
| Sat | U.Phalguni (12) | Hasta (13) | Chitra (14) | Svati (15) | Visakha (16) |

**Both systems exist in the classical literature.** Muhurta Chintamani uses the offset system; Wilhelm's tables use the direct seed system. The engine correctly identifies its source.

**Impact**: On any given day, the Utpata yoga will be "one nakshatra later" than Wilhelm's table. Since both are valid systems, this is a **documented divergence, not an error**.

#### Tithi/Nakshatra Ashubha — PASS
`yoga.py:130` — 16 pairs. Wilhelm pp.7-8 lists these exactly. Verified against Wilhelm tables.

#### Strength Weights — PASS
| Yoga Type | Engine Strength | Wilhelm | Match? |
|-----------|----------------|---------|---------|
| Vara/Tithi | 1 | baseline | PASS |
| Vara/Nakshatra | 3 | 3× Vara/Tithi | PASS (1×3) |
| Tithi/Nakshatra | 0.5 | weakest | PASS |
| Repetition (VTN) | 9 | 3× Vara/Nakshatra | PASS (3×3) |

> Wilhelm p.6: "Vara/Nakshatra Yogas are three times as powerful as Vara/Tithi Yogas, and Vara/Tithi/Nakshatra Yogas are three times as powerful as Vara/Nakshatra Yogas. Tithi/Nakshatra Yogas are the least powerful Yogas."

#### Cancellation Logic — PASS
> Wilhelm p.6: "If these (auspicious and inauspicious) are equally powerful types of Yogas... the auspicious Yoga cancels the inauspicious Yoga and the event started will prove favorable providing the Tara and the relevant Nakshatra, Vara and/or Tithi are favorable. If these are not favorable, the inauspicious Yoga will overcome the beneficial effects of the auspicious Yoga."

Engine `yoga.py:171-183` implements this correctly: equal strength → auspicious cancels IF Tara favourable; stronger type wins otherwise.

### Missing Wilhelm Yogas (not implemented)

The engine implements Vara/Tithi and Vara/Nakshatra yogas but omits:
1. **Subha Yoga** (Vara/Nakshatra auspicious — 3 rows in Wilhelm)
2. **Subha Madhyam Yoga** (Vara/Nakshatra — 3 rows)
3. **Shobhana Yoga** (Vara/Nakshatra — 1 row)
4. **Suta Yoga** (Vara/Tithi/Nakshatra — specific combos)
5. **Siddha Yoga (VTN)** (Vara/Tithi/Nakshatra combos)
6. **Visha Yoga (VTN)** (Vara/Tithi/Nakshatra inauspicious)
7. **Vinasa Yoga** (Vara/Tithi/Nakshatra inauspicious)
8. **Nasa Yoga** (Vara/Nakshatra inauspicious)
9. **Yogas that Dispel Difficulties** (Vara/Nakshatra — all 7 varas)
10. **Dagdha (fatal variant)** — Jupiter's extended Dagdha list
11. **Second Mrityu table** (alternate Mrityu nakshatras)
12. **Unlucky Yogas (10-month manifestation)**

These are lower priority since the implemented set covers the most commonly cited yogas.

**Verdict: MOSTLY CORRECT. Core Vara/Tithi and Vara/Nakshatra tables are 100% accurate. Utpata/Mrityu/Kana/Siddhi follow Muhurta Chintamani system (valid, but 1-off from Wilhelm's direct tables). Strength weights and cancellation logic match Wilhelm exactly.**

---

## Summary Scorecard

| Category | Sub-items | Pass | Partial | Fail | Not Implemented |
|----------|-----------|------|---------|------|-----------------|
| A) Pancha Mahapurusha | 5 yogas | 5 | 0 | 0 | 0 |
| B) Chandra Yogas | 5 yogas | 4 | 0 | 0 | 1 |
| C) Raja Yogas | 8 yogas | 3 | 0 | 0 | 5 |
| D) Dhana Yogas | 4 yogas | 0 | 0 | 0 | 4 |
| E) Nabhasa Yogas | 32 yogas | 3 | 0 | 2 defs | 29 |
| F) Viparita Raja | 1 yoga | 0 | 1 | 0 | 0 |
| G) Neecha Bhanga | 1 yoga (5 types) | 0 | 0 | 0 | 1 |
| H) Wilhelm VTN | 31 table rows | 27 | 4 (drift) | 0 | 12 minor |
| **TOTAL** | | **42** | **5** | **2** | **52** |

## Priority Action Items

### P0 — Critical (missing detection, breaking user results)
1. **Implement Raja Yoga detection** — Kendra-Kona, Mutual Kendra, Dharma-Karma Adhipati, 4-9, 5-9 connections (5 yogas)
2. **Implement Dhana Yoga detection** — 2nd lord + 11th/5th/9th lord connections (4 yogas)
3. **Implement Adhi Yoga detection** — benefics in 6,7,8 from Moon/Lagna
4. **Implement Neecha Bhanga detection** — all 5 PD cancellation types

### P1 — Important (definition errors)
5. **Fix Gada Yoga definition** — change from "Kendra or Panaphara" to "two successive angles" per BPHS
6. **Fix Shankha Yoga definition** — change from "Panaphara+Apoklima" to Kendra+Trikona lords conjunction per PD
7. **Fix Lakshmi Yoga category** — currently labelled "Dhana" at detection but defined as "Raja"

### P2 — Enhancement (coverage expansion)
8. **Expand Kemadruma cancellation** — add Moon-in-Kendra and Jupiter aspect checks
9. **Expand Viparita Raja confidence** — lower to 0.7 with exclusivity note
10. **Add missing Wilhelm VTN yogas** — Subha, Shobhana, Subha Madhyam, Suta, Vinasa at minimum
11. **Document Utpata/Mrityu/Kana/Siddhi drift** — add code comment explaining Muhurta Chintamani vs Wilhelm direct-table divergence

### P3 — Nice to have
12. **Add remaining 29 Nabhasa yogas** (low priority; Ashraya yogas are the most impactful)
13. **Add Moolatrikona as qualifying dignity for Pancha Mahapurusha** (Jataka Parijata variant)
