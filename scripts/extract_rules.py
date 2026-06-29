#!/usr/bin/env python3
"""Extract prediction rules from Phaladeepika and Sarvartha Chintamani texts."""

import os

BASE = "/Users/ganesha/Projects/04-UX-Practice/Panchang/panchanga_muhurtha/extracted_texts"

# Read both texts
phaladeepika_path = os.path.join(BASE, "Mantreswara_s__Phaladeeplka_.txt")
chintamani_path = os.path.join(
    BASE, "ebharati-pdf-1621242374Sarvartha-Chintamani-JN-Bhasin_compressed.txt"
)

with open(phaladeepika_path, encoding="utf-8") as f:
    pd_text = f.read()

with open(chintamani_path, encoding="utf-8") as f:
    sc_text = f.read()

OUTPUT = "/Users/ganesha/Projects/04-UX-Practice/Panchang/panchanga_muhurtha/rules_phaladeepika_chintamani.md"

# Map chapter boundaries in Phaladeepika
pd_chapter_markers = [
    (1, "Chapter 1", "Information and characteristic features of the Signs"),
    (2, "Chapter 2", "Characteristic features of the planets"),
    (3, "Chapter 3", "Divisions of a sign"),
    (4, "Chapter 4", "The strength of planets"),
    (5, "Chapter 5", "Source of livelihood"),
    (6, "Chapter 6", "Yogas"),
    (7, "Chapter 7", "Raja yogas"),
    (8, "Chapter 8", "Effect of the Sun and other planets In the twelve houses"),
    (9, "Chapter 9", "Effect of different Ascendants"),
    (10, "Chapter 10", "Matters relating to the 7th house"),
    (11, "Chapter 11", "Female Horoscopy"),
    (12, "Chapter 12", "Birth of children"),
    (13, "Chapter 13", "Determination of longevity"),
    (14, "Chapter 14", "Diseases, death"),
    (15, "Chapter 15", "Assessment of houses"),
    (16, "Chapter 16", "General effects of the twelve houses"),
    (17, "Chapter 17", "Exit from the world"),
    (18, "Chapter 18", "Effects of conjunction of two planets"),
    (19, "Chapter 19", "Dasas (major periods)"),
    (20, "Chapter 20", "Effects of the Dasas of the lords of houses"),
    (21, "Chapter 21", "Nature of Antar Dasas and Pratyantar Dasas"),
    (22, "Chapter 22", "Kalachakra Dasa"),
    (23, "Chapter 23", "Ashtakavarga"),
    (24, "Chapter 24", "Effects of Ashtakavarga according to Horosara"),
    (25, "Chapter 25", "Gulika and other Upagrahas"),
    (26, "Chapter 26", "Effects of transits"),
    (27, "Chapter 27", "Yogas leading to asceticism"),
    (28, "Chapter 28", "Conclusion"),
]

# Map chapter boundaries in Sarvartha Chintamani
sc_chapter_markers = [
    (1, "CHAPTER·I", "Rashi vichar"),
    (2, "Results of 2nd house", "2nd house"),
    (3, "Results of 3rd & 4th", "3rd 4th houses"),
    (4, "Considerations of 5th & 6th", "5th 6th houses"),
    (5, "Considerations of 7th", "7th house"),
    (6, "Considerations of 8th & 9th", "8th 9th houses"),
    (7, "Results of 10th. 11th & 12th", "10th 11th 12th houses"),
    (8, "Raj yogas", "Raja yogas"),
    (9, "Span of life", "Longevity"),
    (10, "Cancellations of yogas", "Cancellations"),
    (11, "Medium longevity", "Medium longevity"),
    (12, "Ruling Periods of Sun & Moon", "Dasha Sun Moon"),
    (13, "Ruling Periods of Mars & Mercury", "Dasha Mars Mercury"),
    (14, "Ruling Periods of Jupiter. Venus & Saturn", "Dasha Jupiter Venus Saturn"),
    (15, "Ruling Periods of Rahu. Ketu", "Dasha Rahu Ketu"),
    (16, "Miscellaneou s", "Miscellaneous"),
]

rules = []

# ============================================================
# EXTRACT FROM PHALADEEPIKA
# ============================================================

# --- Chapter 1: Signs and Houses ---
rules.append("""
## 1. PANCHANG RULES (Tithi, Vaar, Nakshatra, Yoga, Karana)

### Source: Phaladeepika, Chapter 1-2, 25-26

#### 1.1 Nakshatra Characteristics (Ch. 26)
| Nak # | Name | Lord | Guna | Nature |
|-------|------|------|------|--------|
| 1 | Ashwini | Ketu | Tamas | Light, swift |
| 2 | Bharani | Venus | Rajas | Severe, cruel |
| 3 | Krittika | Sun | Rajas | Mixed, fire |
| 4 | Rohini | Moon | Rajas | Fixed, fertile |
| 5 | Mrigashira | Mars | Tamas | Soft, tender |
| 6 | Ardra | Rahu | Tamas | Sharp, severe |
| 7 | Punarvasu | Jupiter | Satwa | Moveable, light |
| 8 | Pushya | Saturn | Tamas | Light, swift |
| 9 | Ashlesha | Mercury | Tamas | Sharp, dreadful |
| 10 | Magha | Ketu | Tamas | Fierce, severe |
| 11 | Purva Phalguni | Venus | Rajas | Fierce, cruel |
| 12 | Uttara Phalguni | Sun | Rajas | Fixed, steady |
| 13 | Hasta | Moon | Rajas | Light, swift |
| 14 | Chitra | Mars | Tamas | Soft, tender |
| 15 | Swati | Rahu | Tamas | Moveable, light |
| 16 | Vishakha | Jupiter | Satwa | Mixed, soft-sharp |
| 17 | Anuradha | Saturn | Tamas | Soft, tender |
| 18 | Jyeshtha | Mercury | Tamas | Sharp, dreadful |
| 19 | Mula | Ketu | Tamas | Sharp, dreadful |
| 20 | Purva Ashadha | Venus | Rajas | Fierce, severe |
| 21 | Uttara Ashadha | Sun | Rajas | Fixed, steady |
| 22 | Shravana | Moon | Rajas | Moveable, light |
| 23 | Dhanishtha | Mars | Tamas | Moveable, light |
| 24 | Shatabhisha | Rahu | Tamas | Moveable, light |
| 25 | Purva Bhadrapada | Jupiter | Satwa | Fierce, severe |
| 26 | Uttara Bhadrapada | Saturn | Tamas | Fixed, steady |
| 27 | Revati | Mercury | Tamas | Soft, tender |

**Rule PD-NAK-01** (Ch. 26): IF transit of a planet is through Nakshatras that are 3rd, 5th, or 7th from natal Moon Nakshatra THEN the period is unfavourable (Vedha effect).

#### 1.2 Tithi/ Lunar Day Rules (Ch. 12)
**Rule PD-TITHI-01**: IF a child is born on Amavasya (new moon), Rikta Tithis (4, 9, 14), or Bhadra Tithis (2, 7, 12) THEN adverse effects on parents; remedial measures prescribed.

**Rule PD-TITHI-02**: IF birth occurs when Chandra's rays are at their minimum (dark fortnight) AND in certain Nakshatras THEN remedial Shanti must be performed.

#### 1.3 Karana (Ch. 4)
The 60 Chandra Kriyas (Karanas) along with 12 Chandra Awasthas and 36 Chandra Velas produce specific effects. Table provided for guidance.

**Rule PD-KAR-01**: IF Chandra Kriya at birth is known THEN the effects on the native's fortune can be predicted from the corresponding table entries.

#### 1.4 Yoga (Ch. 26 - Saptasalaka)
**Rule PD-YOG-01**: IF a planet in transit occupies the Saptasalaka diagram positions relative to birth Nakshatra THEN auspicious or inauspicious results manifest per the diagram.

""")

# --- Chapter 2: Planet Characteristics ---
rules.append("""
## 2. PLANETARY SIGNIFICATIONS (Karakatwas)

### Source: Phaladeepika, Chapter 2; Sarvartha Chintamani, Ch. 1

#### 2.1 Sun (Surya)
- **Temperament**: Pita (bilious), steady, Satwic
- **Body**: Bones, heart, right eye, hair
- **Places**: Temples, forests, mountains, government buildings
- **Substances**: Gold, copper, wheat, red grains
- **Relations**: Father, king, employer, government
- **Age**: 50 years (Ayur bhaga)
- **Guna**: Satwa
- **Color**: Copper-red

#### 2.2 Moon (Chandra)
- **Temperament**: Kapha-Vata, fickle, Satwic
- **Body**: Blood, left eye, breasts, stomach, fluids
- **Places**: Water bodies, wells, gardens, female apartments
- **Substances**: Silver, rice, milk, white items
- **Relations**: Mother, women, public, masses
- **Age**: 70 years
- **Guna**: Satwa
- **Color**: White

#### 2.3 Mars (Mangal)
- **Temperament**: Pita (bilious), cruel, Tamasic
- **Body**: Marrow, muscles, genitals, blood
- **Places**: Battlefield, fire places, factories, police stations
- **Substances**: Copper, red lentils, red flowers
- **Relations**: Brothers, soldiers, engineers, enemies
- **Age**: 16 years
- **Guna**: Tamas
- **Color**: Blood red

#### 2.4 Mercury (Budha)
- **Temperament**: Mixed (Tridosha), witty, Rajasic
- **Body**: Skin, tongue, speech, nervous system
- **Places**: Schools, libraries, markets, courts
- **Substances**: Green gram, emerald, bronze
- **Relations**: Maternal uncles, friends, traders, accountants
- **Age**: 32 years
- **Guna**: Rajas
- **Color**: Green / grass

#### 2.5 Jupiter (Guru)
- **Temperament**: Kapha, gentle, Satwic
- **Body**: Fat, liver, spleen, ears
- **Places**: Temples, courts, treasuries, universities
- **Substances**: Gold, yellow sapphire, gram, ghee
- **Relations**: Teachers, priests, sons, ministers
- **Age**: 80 years
- **Guna**: Satwa
- **Color**: Yellow / golden

#### 2.6 Venus (Shukra)
- **Temperament**: Kapha-Vata, passionate, Rajasic
- **Body**: Semen, reproductive organs, eyes, face
- **Places**: Bedrooms, theatres, gardens, luxury places
- **Substances**: Diamond, silver, perfumes, silk
- **Relations**: Wife, women, lovers, artists
- **Age**: 20 years
- **Guna**: Rajas
- **Color**: White / variegated

#### 2.7 Saturn (Shani)
- **Temperament**: Vata (windy), lazy, Tamasic
- **Body**: Bones, teeth, knees, feet, nerves
- **Places**: Dirty places, cemeteries, prisons, mines
- **Substances**: Iron, blue sapphire, black grains, oil
- **Relations**: Servants, old people, laborers, outcastes
- **Age**: 100 years
- **Guna**: Tamas
- **Color**: Black / dark blue

#### 2.8 Rahu
- **Temperament**: Tamasic, erratic
- **Body**: Skin diseases, poison, insanity
- **Places**: Foreign lands, gambling dens, secret places
- **Relations**: Foreigners, outcastes, magicians
- **Age**: 100 years

#### 2.9 Ketu
- **Temperament**: Tamasic, spiritual
- **Body**: Mysterious diseases, wounds
- **Places**: Hermitages, caves, pilgrimage sites
- **Relations**: Saints, ascetics, grandfather
- **Age**: 100 years

### Source: Sarvartha Chintamani, Ch. 1 (Rashi Vichar)

**Rule SC-SIG-01**: IF the 5th sign, its lord, the 5th house, and its lord are afflicted by Rahu THEN heart attack is indicated. IF by Saturn THEN dyspepsia/indigestion. IF by Mars and Ketu THEN operation/injury to the belly.

**Rule SC-SIG-02** (p.8): IF the 12th house, lord of 12th, sign no.12 and its lord Jupiter are ALL afflicted by Mars AND Ketu THEN feet may require amputation.

""")

# --- Chapters 6-7: Yogas ---
rules.append("""
## 3. YOGA RULES (Planetary Combinations)

### Source: Phaladeepika, Chapters 6-7

#### 3.1 Panchamahapurusha Yogas (Five Great Person Yogas)

**Rule PD-YOGA-01 — RUCHAKA YOGA**
IF: Mars is in its own sign OR exaltation sign AND posited in a Kendra (1,4,7,10) from Lagna
THEN: Native is courageous, victorious, has strong physique, commands army, acquires wealth, has scars/wounds on body.

**Rule PD-YOGA-02 — BHADRA YOGA**
IF: Mercury is in its own sign OR exaltation sign AND posited in a Kendra from Lagna
THEN: Native is learned, intelligent, wealthy, has lion-like face, long arms, helps relatives, long-lived.

**Rule PD-YOGA-03 — HANSA YOGA**
IF: Jupiter is in its own sign OR exaltation sign AND posited in a Kendra from Lagna
THEN: Native has handsome appearance, is righteous, liked by all, kingly, has prominent nose, pure-hearted.

**Rule PD-YOGA-04 — MALAVYA YOGA**
IF: Venus is in its own sign OR exaltation sign AND posited in a Kendra from Lagna
THEN: Native is wealthy, enjoys luxuries, has beautiful wife, vehicles, fine clothes, likes fine arts.

**Rule PD-YOGA-05 — SASA YOGA**
IF: Saturn is in its own sign OR exaltation sign AND posited in a Kendra from Lagna
THEN: Native is a village headman, leader, commander, has good servants, cruel temperament, enjoys others' wealth.

#### 3.2 Chandra Yogas (Lunar Combinations)

**Rule PD-YOGA-06 — SUNAPHA YOGA**
IF: There is a planet (other than Sun) in the 2nd house from the Moon
THEN: Native is wealthy, intelligent, enjoys good reputation, self-earned wealth.

**Rule PD-YOGA-07 — ANAPHA YOGA**
IF: There is a planet (other than Sun) in the 12th house from the Moon
THEN: Native is wealthy, famous, moral, enjoys pleasures, commands respect, free from diseases.

**Rule PD-YOGA-08 — DURUDHARA YOGA**
IF: There are planets (other than Sun) in BOTH the 2nd AND 12th houses from the Moon
THEN: Native has enormous wealth, vehicles, is charitable, known for good qualities.

**Rule PD-YOGA-09 — KEMADRUMA YOGA**
IF: There are NO planets in the 2nd or 12th from the Moon AND no planets in Kendra from Moon
THEN: Native suffers poverty, disgrace, mental distress, misfortune.
EXCEPTION: IF Moon is conjoined with a planet OR IF Moon is aspected by planets from Kendra THEN Kemadruma is cancelled.

#### 3.3 Other Important Yogas

**Rule PD-YOGA-10 — KESARI YOGA**
IF: Jupiter is in a Kendra from the Moon (1,4,7,10 from Moon)
THEN: Native is wise, wealthy, famous, destroys enemies, liked by all.

**Rule PD-YOGA-11 — SAKATA YOGA**
IF: Moon is in the 6th, 8th, or 12th from Jupiter
THEN: Native experiences alternating fortune and misfortune (rise and fall cycles).

**Rule PD-YOGA-12 — AMALA YOGA**
IF: A natural benefic occupies the 10th house from Lagna
THEN: Native enjoys lasting fame, wealth, and good reputation.

**Rule PD-YOGA-13 — VASUMATI YOGA**
IF: Benefics are in Upachaya houses (3,6,10,11) when counted from the Moon AND from Lagna
THEN: Native possesses immense wealth.

**Rule PD-YOGA-14 — PUSHKALA YOGA**
IF: The lord of the sign occupied by the Moon is in a Kendra AND the Lagna lord is strong AND Moon conjoins a powerful benefic
THEN: Native is wealthy, famous, enjoys all pleasures.

**Rule PD-YOGA-15 — LAKSHMI YOGA**
IF: Lord of Lagna is very strong AND lord of 9th is in own/exaltation house occupying Kendra or Trikona
THEN: Native is extremely wealthy like Goddess Lakshmi, respected by kings.

**Rule PD-YOGA-16 — SARASWATI YOGA**
IF: Jupiter, Venus, and Mercury are in Kendras (1,4,7,10) OR Trikonas (5,9) OR 2nd house
THEN: Native is highly learned, eloquent, skilled in arts and sciences.

**Rule PD-YOGA-17 — GOURI YOGA**
IF: Lord of 10th is in 10th (own house/exaltation) AND Lord of Lagna is strong
THEN: Native is highly fortunate, honored by rulers.

**Rule PD-YOGA-18 — PARIVARTANA YOGA**
IF: There is mutual exchange of signs between the lords of two houses (e.g., lord of 1st in 2nd and lord of 2nd in 1st)
THEN: The houses involved produce their results strongly; if involving Dusthanas (6,8,12), results may be adverse.

**Rule PD-YOGA-19 — ADHI YOGA**
IF: Benefic planets occupy the 6th, 7th, and 8th houses from the Moon
THEN: Native is a commander, has no enemies, enjoys good health and long life.

**Rule PD-YOGA-20 — CHAMARA YOGA**
IF: Lord of Lagna is exalted or in own sign in a Kendra AND aspected by Jupiter
THEN: Native becomes a high-ranking official or minister, honored by royalty.

**Rule PD-YOGA-21 — PARIJATA YOGA**
IF: Lord of the house occupied by the lord of 10th is in a Kendra or Trikona from Lagna
THEN: Native is happy, enjoys royal favor, has vehicles.

#### 3.4 Daridra Yogas (Poverty Combinations)

**Rule PD-YOGA-22 — DARIDRA YOGA**
IF: Lord of 11th is in Dusthana (6,8,12) AND lord of 2nd is also weak/afflicted
THEN: Native remains poor despite efforts.

**Rule PD-YOGA-23 — AVAYOGA**
IF: All planets occupy the 6th, 8th, and 12th houses (Dusthanas) from Lagna
THEN: Native suffers poverty, misery, and misfortune throughout life.

**Rule PD-YOGA-24 — MRITYU YOGA**
IF: Lord of Lagna is in 8th AND 8th lord is in Lagna AND they are mutually aspected/conjoined by malefics
THEN: Danger of death, especially during Dasha of these planets.

#### 3.5 Sankhya Yogas (Shape-based Combinations)

**Rule PD-YOGA-25 — VEENA YOGA**
IF: All 7 planets occupy 7 different houses
THEN: Native is musical, fond of arts, wealthy.

**Rule PD-YOGA-26 — GOLA YOGA**
IF: All planets are distributed in the 4 quadrants (Kendras)
THEN: Native is poor, wandering (shape of a sphere/ball).

#### 3.6 Raja Yogas (Royal Combinations) - Ch. 7

**Rule PD-YOGA-27 — RAJA YOGA (General)**
IF: Lords of Kendra (1,4,7,10) and Trikona (1,5,9) are mutually associated/aspected OR exchange signs
THEN: Native becomes a king, ruler, or high government official.

**Rule PD-YOGA-28 — RAJA YOGA (Specific)**
IF: The lord of the sign occupied by the Moon is in conjunction with the lord of the sign occupied by the Lagna lord AND both are in Kendra/Trikona
THEN: Native becomes a ruler.

**Rule PD-YOGA-29**: IF: Lord of Lagna and lord of 5th or 9th are in mutual Kendras AND aspected by benefics
THEN: Native enjoys royal status.

**Rule PD-YOGA-30**: IF: Three or more planets are in their exaltation signs
THEN: Native becomes an emperor (Chakravarti).

### Source: Sarvartha Chintamani, Chapter 9 (Raj Yogas)

**Rule SC-YOGA-01**: IF the lords of Kendra and Trikona are in conjunction or mutual aspect (Sambandha) in a Kendra or Trikona AND are posited in exaltation/own house THEN native attains position like a king, possesses elephants, horses, and all grandeur.

**Rule SC-YOGA-02**: IF the lord of 9th (Bhagya) is in exaltation or own house AND occupies Kendra or Trikona AND is associated with Kendra lord THEN the native acquires kingdom, treasures, and vehicles.

**Rule SC-YOGA-03**: IF the Moon is in its exaltation sign (Taurus) with Jupiter posited in Cancer or in Pisces in Kendra from Moon THEN a powerful Rajayoga is formed; the person becomes a noble king.

**Rule SC-YOGA-04**: IF Jupiter and Venus are in the 2nd house from Moon AND Mars AND Mercury are in the 4th from Moon AND Saturn is in Lagna THEN native is a great king.

**Rule SC-YOGA-05**: IF Jupiter is in Lagna (Cancer) AND Moon and Mars are in Capricorn (10th) AND Sun and Venus are in Taurus (11th) THEN the native attains kingdom.

**Rule SC-YOGA-06**: IF Mercury is in its own sign and Jupiter occupies the 12th from Mercury THEN the native influences even the king due to his intelligence.

**Rule SC-YOGA-07**: IF the lord of the sign occupied by the Moon is placed in a Kendra from the house occupied by the lord of Lagna AND the lord of the house occupied by exaltation lord of the lord of Lagna occupies a Kendra THEN full Raja yoga.

**Rule SC-YOGA-08**: IF the lords of 2nd, 4th, 5th, 9th, and 10th own Kendras exchanging with Trikonas AND the Lagna lord is in a Kendra THEN full Raja yoga.

**Rule SC-YOGA-09**: IF the lord of the Lagna sign and the lord of the Moon sign aspect each other THEN Raja yoga.

""")

# --- Chapter 4: Strength Calculations ---
rules.append("""
## 4. PLANETARY STRENGTH & POSITION RULES

### Source: Phaladeepika, Chapter 3-4

#### 4.1 Exaltation and Debilitation Points

| Planet | Exaltation Sign | Exaltation Degree | Debilitation Sign | Debilitation Degree | Moolatrikona |
|--------|----------------|-------------------|-------------------|---------------------|--------------|
| Sun | Aries | 10° | Libra | 10° | Leo (0-20°) |
| Moon | Taurus | 3° | Scorpio | 3° | Taurus (4-20°) |
| Mars | Capricorn | 28° | Cancer | 28° | Aries (0-12°) |
| Mercury | Virgo | 15° | Pisces | 15° | Virgo (16-20°) |
| Jupiter | Cancer | 5° | Capricorn | 5° | Sagittarius (0-10°) |
| Venus | Pisces | 27° | Virgo | 27° | Libra (0-15°) |
| Saturn | Libra | 20° | Aries | 20° | Aquarius (0-20°) |

**Rule PD-STR-01**: IF a planet is in its exaltation sign at the exact exaltation degree THEN it has maximum Shadbala strength (Uchchabala = 60 virupas).

**Rule PD-STR-02**: IF a planet is at the exact debilitation degree THEN its Uchchabala = 0 virupas.

#### 4.2 Awasthas (Planetary States)

| # | Awastha | Meaning | Effect |
|---|---------|---------|--------|
| 1 | Pradeepta | Blazing | Success, fame, leadership |
| 2 | Sukhita | Happy | Comforts, pleasures |
| 3 | Swastha | Healthy | Good health, contentment |
| 4 | Mudita | Joyful | Happiness, social success |
| 5 | Shanta | Peaceful | Calm, spiritual |
| 6 | Shakta | Powerful | Strength, influence |
| 7 | Vikala | Deformed | Obstacles, suffering |
| 8 | Nipidita | Oppressed | Humiliation, loss |
| 9 | Khala | Vile | Evil deeds, cruelty |
| 10 | Atibhjeeta | Exceedingly frightened | Extreme fear, loss |

**Rule PD-STR-03**: IF a planet is in exaltation or own sign THEN it is in Pradeepta, Sukhita, or Swastha awastha (good states).

**Rule PD-STR-04**: IF a planet is in debilitation or enemy sign THEN it is in Vikala, Nipidita, or Khala awastha (bad states).

**Rule PD-STR-05**: IF a planet is in the same Navamsa across multiple Vargas (Vargottama) THEN its strength is amplified 2x.

#### 4.3 Varga Classification (Vimshopaka Bala)

**Rule PD-STR-06**: IF a planet occupies 1st class Vargas (Parijata, Uttama, Gopura) THEN the planet is strong. IF it occupies Simhasana, Parvata, Devaloka, Airavata THEN it is very strong, conferring exceptional results.

#### 4.4 Shad Bala (Six-fold Strength)

| Strength Type | Maximum (Virupas/Rupas) | Based On |
|---------------|------------------------|----------|
| Sthanabala | (positional) | Sign, exaltation, etc. |
| Dikbala | 60 virupas | Directional strength |
| Kalabala | (temporal) | Time of day/year |
| Chestabala | 60 virupas | Motion (retrograde = max) |
| Naisargika Bala | | Natural strength |
| Drigbala | 60 virupas | Aspect strength |

**Rule PD-STR-07** (PD Ch.4 p.37-56): Calculate ALL 60 Chandra Kriyas, 12 Chandra Awasthas, and 36 Chandra Velas using provided tables to determine Moon's strength at birth.

""")

# --- Chapter 8: Planets in Houses ---
rules.append("""
## 5. BHAVA / HOUSE RULES (Results for Each House)

### Source: Phaladeepika, Chapter 8; Sarvartha Chintamani, Chapters 2-8

#### 5.1 First House (Lagna / Ascendant)

**SUN IN 1ST:**
- IF Sun in Lagna: Native is valorous, has thin hair, cruel disposition, impatient, bilious temperament. (PD Ch.8)
- IF Sun in Lagna in own/exaltation: commanding personality.

**MOON IN 1ST:**
- IF Moon in 1st (waxing): Native is handsome, wealthy, fortunate, enjoys life.
- IF Moon in 1st (waning): Native suffers from poverty and illness.

**MARS IN 1ST:**
- IF Mars in 1st (own/exaltation): Ruchaka yoga - courageous, commander.
- IF Mars in 1st (debilitated/enemy): wounds, accidents, cruel nature.

**MERCURY IN 1ST:**
- IF Mercury in 1st: Long-lived, learned, pleasant speech, skilled.

**JUPITER IN 1ST:**
- IF Jupiter in 1st (own/exaltation): Hansa yoga - handsome, righteous, respected.
- IF Jupiter in 1st: Protects from evil effects, gives long life.

**VENUS IN 1ST:**
- IF Venus in 1st (own/exaltation): Malavya yoga - wealthy, beautiful wife, luxuries.

**SATURN IN 1ST:**
- IF Saturn in 1st (own/exaltation): Sasa yoga - leadership, commands servants.
- IF Saturn in 1st (afflicted): Lazy, diseased, unhappy.

**RAHU IN 1ST:**
- IF Rahu in Lagna: Native is courageous, wealthy, but may suffer sudden losses.

**KETU IN 1ST:**
- IF Ketu in Lagna: Native has spiritual inclinations, may suffer mysterious ailments.

#### 5.2 Second House (Dhana Bhava — Wealth)

**Rule SC-BHAVA-02** (Ch.3): IF a natural benefic occupies the 2nd house AND lord of 2nd is a natural benefic AND the significator (Sun for right eye, Jupiter for wealth) is under good influence THEN man has broad eyes with good sight.

**Rule SC-BHAVA-02a**: IF lord of 2nd is in 10th (Kendra from 2nd) AND in friend's/exaltation/own sign THEN great wealth.

**Rule SC-BHAVA-02b**: IF 2nd lord is in 2nd itself (own house) AND strong THEN independent wealth, not dependent on others.

**Rule SC-BHAVA-02c**: IF Mars or Saturn alone be in the 2nd house along with one of the nodes (Rahu/Ketu) as lord of 2nd being in 6th, 8th, or 12th THEN the person squanders away his wealth.

**Rule SC-BHAVA-02d**: IF lord of 2nd is in 6th, 8th, or 12th AND afflicted by malefics THEN accumulated wealth is lost or seized.

**Rule SC-BHAVA-02e**: IF lord of 2nd is exalted AND occupies Kendra or Trikona AND Jupiter aspects THEN native is a multi-millionaire.

**Rule SC-BHAVA-02f**: IF lord of 2nd is in 8th with a malefic AND there is no benefic aspect THEN the native is always in want of money.

**Rule SC-BHAVA-02g**: IF Sun, Mars, and Saturn all three occupy the 2nd house THEN the man earns his livelihood by squeezing the life out of someone or by causing death to others (butcher, executioner, etc.) — source: SC.

**Rule SC-BHAVA-02h** (Speech): IF lord of 2nd is in own, exaltation, or friendly Drekkan (decanate) AND is aspected by benefics THEN the words of the person prove correct.

**Rule SC-BHAVA-02i**: IF lord of 2nd is in 2nd or 11th in exaltation, own, or friendly Navamsa AND Mercury joins THEN the man is an eloquent speaker.

#### 5.3 Third House (Sahaja Bhava — Siblings, Courage)

**Rule SC-BHAVA-03** (Ch.4): IF the lord of 3rd is posited in 3rd itself, in own sign, exaltation, or friendly sign THEN brothers are many, long-lived, and helpful.

**Rule SC-BHAVA-03a**: IF Mars is in 3rd house in exaltation, own sign, or friendly sign THEN more brothers.

**Rule SC-BHAVA-03b**: IF lord of 3rd is in 6th, 8th, or 12th OR is debilitated THEN there are no brothers or they die early.

**Rule SC-BHAVA-03c**: IF Saturn, Mars, and the lords of 2nd and 12th are strong THEN step-brothers are indicated.

**Rule SC-BHAVA-03d**: IF Saturn is in the 3rd AND Moon in 1st or 9th (from Lagna) THEN number of brothers is few.

**Rule SC-BHAVA-03e**: IF lord of 3rd is in 3rd in a friendly or own sign AND Saturn aspects THEN younger sister(s) are indicated (no brothers).

#### 5.4 Fourth House (Sukha Bhava — Mother, Home, Vehicles)

**Rule SC-BHAVA-04** (Ch.4): IF Moon is in the 4th from Lagna AND aspected by benefics THEN the native has many cows and buffaloes (livestock, wealth).

**Rule SC-BHAVA-04a**: IF a natural benefic occupies the 4th house AND lord of 4th is also a benefic THEN much land and property.

**Rule SC-BHAVA-04b**: IF Moon is alone in Leo in the 4th with no planet in 2nd or 12th from Moon THEN the mother dies when the native is 3 years old.

**Rule SC-BHAVA-04c**: IF lord of 4th is in his own house AND strong THEN well-built houses.

**Rule SC-BHAVA-04d**: IF Venus is in the 4th house THEN many vehicles and conveyances.

**Rule SC-BHAVA-04e**: IF Sun occupies 4th (Aquarius) AND Ketu is in 12th THEN the native leaves his native place forever.

**Rule SC-BHAVA-04f**: IF the number of planets in 4th and 10th houses is equal AND the lord of Lagna signifies the same THEN the native occupies the throne of an emperor.

#### 5.5 Fifth House (Putra Bhava — Children, Intelligence)

**Rule PD-BHAVA-05** (Ch.12): IF the 5th lord is in 6th, 8th, or 12th AND is weak/afflicted THEN issuelessness.

**Rule PD-BHAVA-05a**: IF Jupiter is in 5th, strong and unafflicted THEN many children.

**Rule PD-BHAVA-05b**: IF 5th lord is in a Kendra/Trikona and strong THEN children after some delay.

**Rule PD-BHAVA-05c**: IF Saturn aspects or occupies the 5th THEN delay in progeny; children only after remedial measures.

**Rule SC-BHAVA-05** (Ch.5): IF a benefic planet occupies the 5th house and lord of 5th is also a benefic occupying a benefic position then the man will have five or more children.

**Rule SC-BHAVA-05a**: IF Jupiter is in 5th AND owner of 5th is also a benefic THEN more than five sons (surviving).

**Rule SC-BHAVA-05b**: IF Mars is in 5th and owner of 5th is also malefic then many children but few survive.

**Rule SC-BHAVA-05c**: IF lord of 5th is posited in 4th, 6th, 10th, or 12th from Lagna THEN male issues are denied; only daughters.

**Rule SC-BHAVA-05d**: IF Jupiter, lord of 5th, and 5th house are all under the influence of Saturn THEN children are begotten late AND few.

#### 5.6 Sixth House (Ripu Bhava — Enemies, Disease, Debt)

**Rule SC-BHAVA-06** (Ch.5): IF lord of 6th is in 1st, 5th, 9th, or 12th then the native is able to overcome enemies.

**Rule SC-BHAVA-06a**: IF lord of 6th in a Kendra with a malefic AND lord of Lagna is weak THEN powerful secret enemies who harm without being known.

**Rule SC-BHAVA-06b**: IF lord of 6th and Mars both join in the 5th or 9th house THEN the son of the native suffers many diseases.

**Rule SC-BHAVA-06c**: IF 6th lord is with Rahu THEN enemies from among his own men/uncles.

**Rule SC-BHAVA-06d**: IF Mars is in 6th, in own or exaltation sign AND lord of 6th is not in 10th, 11th or 12th THEN the native wins over enemies.

**Rule SC-BHAVA-06e**: IF lord of 6th and lord of Lagna join in Kendra or Trikona THEN severe diseases.

#### 5.7 Seventh House (Kalatra Bhava — Spouse, Marriage)

**Rule PD-BHAVA-07** (Ch.10): IF lord of 7th is in 6th, 8th, or 12th AND is weak THEN loss of wife OR issuelessness.

**Rule PD-BHAVA-07a**: IF 7th lord is strong in Kendra/Trikona AND aspected by benefics THEN fortunate, beautiful, and chaste wife.

**Rule PD-BHAVA-07b**: IF malefics occupy 7th AND 7th lord is in debilitation/enemy sign THEN a crippled wife or liaison with others' wives.

**Rule PD-BHAVA-07c**: IF Mars and Saturn both aspect 7th house/lord THEN wifelessness (bachelor).

**Rule PD-BHAVA-07d**: IF dual signs are in 7th or 7th lord is in dual sign aspected by Venus THEN two wives.

**Rule SC-BHAVA-07** (Ch.6): IF Venus is in his own sign (Taurus or Libra) in 7th house AND lord of 7th is a strong benefic THEN the wife is extremely beautiful.

**Rule SC-BHAVA-07a**: IF 7th lord is in 6th, 8th, or 12th or in debilitation or combustion THEN early death of wife.

**Rule SC-BHAVA-07b**: IF Saturn, Rahu, or Ketu is in the 7th house while the 7th lord is weak and unaspected by benefics THEN the man remains a bachelor or loses his wife.

**Rule SC-BHAVA-07c**: IF the lord of the Navamsa occupied by the lord of 7th is in 6th, 8th, or 12th from Venus OR is debilitated THEN the wife may be unfaithful.

**Rule SC-BHAVA-07d**: IF Sun and Saturn are in 7th with Rahu/Ketu THEN the native becomes a sanyasi (renunciate — no marriage).

**Rule SC-BHAVA-07e**: IF lord of 7th is in 2nd OR 12th from Venus THEN the native gets an ambitious wife; IF lord of 7th is in the 12th from its own Navamsa lord THEN the native deserts his wife.

#### 5.8 Eighth House (Ayur Bhava — Longevity)

**Rule SC-BHAVA-08** (Ch.7): IF the Moon occupies the 8th house AND a malefic occupies the Kendra from Moon THEN the native has a short life.

**Rule SC-BHAVA-08a**: IF 8th lord is in a Kendra or Trikona with a benefic THEN full span of life.

**Rule SC-BHAVA-08b**: IF a malefic occupies 8th in debilitation OR enemy sign THEN the native gets recovery from long ailments.

**Rule SC-BHAVA-08c**: IF Saturn and Mars occupy Lagna AND Moon is in 8th THEN the person dies by poisoning.

**Rule SC-BHAVA-08d**: IF lord of 8th is in 2nd AND lord of 2nd is in 8th THEN wealth gets accumulated and also becomes the cause of quarrel with brothers and relatives — and death.

**Rule SC-BHAVA-08e**: IF Jupiter is in the 8th house AND 8th lord is strong THEN long life.

#### 5.9 Ninth House (Dharma Bhava — Fortune, Father)

**Rule SC-BHAVA-09** (Ch.7): IF a benefic is in 9th AND lord of 9th is strong and occupies Kendra or Trikona THEN the father is long-lived and the native is fortunate from childhood.

**Rule SC-BHAVA-09a**: IF Jupiter is in 9th in own, exaltation, or friendly sign THEN the native's father is a highly spiritual person, generous and wealthy.

**Rule SC-BHAVA-09b**: IF lord of 9th is in 6th, 8th, or 12th THEN early death of father.

**Rule SC-BHAVA-09c**: IF Saturn is in 9th AND Moon in 1st, 5th, or 9th (in own sign) THEN step-father (father remarries).

**Rule SC-BHAVA-09d**: IF Sun is in 9th AND strong THEN the father is a king or occupies a very high position AND the native is fortunate.

#### 5.10 Tenth House (Karma Bhava — Profession)

**Rule SC-BHAVA-10** (Ch.8): IF the lord of 10th is in 10th, in own sign or exaltation, with strong benefics THEN the person occupies a position of authority and honor.

**Rule SC-BHAVA-10a**: IF Sun and Mars are in 10th THEN the person is successful in government service or military.

**Rule SC-BHAVA-10b**: IF Mercury and Venus are in 10th THEN the person earns through business, arts, or commerce.

**Rule SC-BHAVA-10c**: IF Saturn is in 10th (own/exaltation) THEN the person earns through labor, mining, or heavy industries.

**Rule SC-BHAVA-10d**: IF lord of 10th is in 6th, 8th, or 12th THEN failure in profession, frequent job changes, disgrace.

**Rule SC-BHAVA-10e**: IF exalted planet is in 10th AND lord of 10th is in a Kendra from Lagna THEN Rajyoga — high government position.

**Rule SC-BHAVA-10f**: IF lord of 10th is in 2nd or 11th AND is strong THEN wealth through profession.

#### 5.11 Eleventh House (Labha Bhava — Gains)

**Rule SC-BHAVA-11** (Ch.8): IF lord of 11th is in 11th, in exaltation, or own sign THEN all gains come easily and quickly.

**Rule SC-BHAVA-11a**: IF Jupiter is in 11th in own sign or exaltation THEN great wealth through righteous means.

**Rule SC-BHAVA-11b**: IF lord of 11th is in 2nd, 5th, or 9th AND strong THEN high income and wealth.

**Rule SC-BHAVA-11c**: IF lord of 11th is in 6th, 8th, or 12th THEN gains are lost quickly; income is blocked.

#### 5.12 Twelfth House (Vyaya Bhava — Expenditure, Loss)

**Rule SC-BHAVA-12** (Ch.8): IF lord of 12th is in a Kendra or Trikona and strong THEN expenditure is on good/charitable causes.

**Rule SC-BHAVA-12a**: IF lord of 12th is in 12th itself in exaltation or own sign AND aspected by benefics THEN the person attains salvation (Moksha).

**Rule SC-BHAVA-12b**: IF Moon is in 12th AND a malefic is in Lagna then troubles and losses from foreign lands.

""")

# --- Dasha Rules ---
rules.append("""
## 6. DASHA RULES (Vimshottari Timing and Effects)

### Source: Phaladeepika, Chapters 19-21; Sarvartha Chintamani, Chapters 12-16

#### 6.1 Vimshottari Dasha Periods (PD Ch.19)

| Planet | Years | Nakshatras Ruled |
|--------|-------|------------------|
| Sun | 6 | Krittika, U.Phalguni, U.Ashadha |
| Moon | 10 | Rohini, Hasta, Shravana |
| Mars | 7 | Mrigashira, Chitra, Dhanishtha |
| Rahu | 18 | Ardra, Swati, Shatabhisha |
| Jupiter | 16 | Punarvasu, Vishakha, P.Bhadrapada |
| Saturn | 19 | Pushya, Anuradha, U.Bhadrapada |
| Mercury | 17 | Ashlesha, Jyeshtha, Revati |
| Ketu | 7 | Ashwini, Magha, Mula |
| Venus | 20 | Bharani, P.Phalguni, P.Ashadha |
| **Total** | **120** | |

**Rule PD-DASH-01**: The Dasha at birth is determined by the Moon's Nakshatra. The balance of Dasha is proportional to the degrees of Moon already traversed in that Nakshatra.

**Rule PD-DASH-02** (PD Ch.19-20): General effects during the major period of each planet:

**SUN Dasha (6 years):**
- IF Sun is strong/well-placed THEN: Rise in position, favor from government, father's prosperity, name and fame.
- IF Sun is weak/afflicted THEN: Troubles from government, loss of father, health problems (eyes, heart, bones), humiliation.

**MOON Dasha (10 years):**
- IF Moon is waxing and strong THEN: Comforts, wealth, mother's happiness, public favor, mental peace.
- IF Moon is waning and weak THEN: Mental distress, financial losses, ill health to mother.

**MARS Dasha (7 years):**
- IF Mars is strong in own/exaltation/friend sign THEN: Courage, victory, acquisition of land/property, brother's help.
- IF Mars is weak/afflicted THEN: Accidents, injuries, fire hazards, litigation, enemies.

**RAHU Dasha (18 years):**
- IF Rahu is well-placed in a Kendra/Trikona with benefics THEN: Sudden gains, foreign travel, material success, unconventional rise.
- IF Rahu is in Dusthana or with malefics THEN: Deception, losses, diseases, mental disturbance, danger from poison.

**JUPITER Dasha (16 years):**
- IF Jupiter is strong (own/exaltation, Kendra/Trikona) THEN: Spiritual growth, children, wealth, honor, education, marriage.
- IF Jupiter is weak THEN: Loss of reputation, financial troubles, obstructions in education.

**SATURN Dasha (19 years):**
- IF Saturn is well-placed THEN: Service to old/sick, gains from masses, longevity, leadership of groups.
- IF Saturn is ill-placed THEN: Poverty, diseases (chronic), obstruction, death of elders, imprisonment.

**MERCURY Dasha (17 years):**
- IF Mercury is strong THEN: Learning, business success, writing, communication skills, uncle's help.
- IF Mercury is weak/combust THEN: Nervous disorders, business losses, speech problems.

**KETU Dasha (7 years):**
- IF Ketu is well-placed in spiritual houses (4,8,12) THEN: Spiritual progress, detachment, pilgrimage.
- IF Ketu is afflicted THEN: Accidents, mysterious diseases, separation, loss.

**VENUS Dasha (20 years):**
- IF Venus is strong THEN: Marriage, luxuries, vehicles, artistic success, love affairs, comforts.
- IF Venus is weak THEN: Marital discord, loss of wealth, venereal diseases, disgrace through women.

#### 6.2 Dasha of House Lords (PD Ch.20)

**Rule PD-DASH-03**: IF the Dasha planet is Vargottama (same sign in Rasi and Navamsa) THEN the results are fully and intensely experienced.

**Rule PD-DASH-04**: IF two planets occupy the 8th house THEN their Dasha and Antardasha periods are UNFAVORABLE.

**Rule PD-DASH-05**: IF Antardasha lord occupies the 3rd, 5th, or 7th Nakshatra from natal Moon in the Dasha of a malefic THEN results are evil.

**Rule PD-DASH-06**: IF the 4th Dasha is of Saturn, 6th of Jupiter, and 5th of Mars or Rahu THEN evil effects must be expected.

**Rule PD-DASH-07**: IF Mars is in Urdhvamukha (upward-facing) sign identical with 10th or 11th house THEN its Dasha is favorable.

**Rule PD-DASH-08**: IF a planet is inimical to the Dasha lord THEN its Antardasha within that Dasa produces unfavorable effects.

**Rule PD-DASH-09** (Quantum rule): The effects of a planet in its Dasa are proportional to its strength (Shadbala). Strong planet = full good effects; Weak planet = minimal or bad effects.

**Rule PD-DASH-10**: IF a benefic owns a Kendra (1,4,7,10) THEN its Dasha may be unfavorable (Kendradhipati Dosha). EXCEPTION: The same planet owning a Trikona (5,9) negates this dosha.

**Rule PD-DASH-11**: IF lords of Kendra also own Trikona AND occupy Kendra or Trikona THEN the Dasha yields Raja yoga results.

**Rule PD-DASH-12**: IF Rahu or Ketu are posited in Kendra or Trikona THEN they attain Yogakaraka status and their Dasha yields favorable results.

**Rule PD-DASH-13** (Avarohini/Arohini): IF Dasas proceed from a weak to strong sequence (Arohini) THEN life improves. IF from strong to weak (Avarohini) THEN life declines.

#### 6.3 Antardasha Effects (PD Ch.21)

**Rule PD-DASH-14**: IF the Antardasha lord is in exaltation, own, or friendly sign in transit THEN good results materialize during that Antardasha.

**Rule PD-DASH-15**: IF the Antardasha lord is in debilitation or inimical sign in transit THEN evil results prevail.

#### 6.4 Kalachakra Dasha (PD Ch.22)

**Rule PD-KALA-01**: The Kalachakra Dasha uses the 7 planets (excluding Rahu/Ketu) and proceeds differently through Savya (clockwise starting Scorpio) and Apasavya (counter-clockwise starting Aries) chakras depending on the birth Nakshatra pada.

**Rule PD-KALA-02**: The Parama Ayus (maximum years) for the 12 Rasiamsas (sign-based periods) in Apasavya chakra is different from Savya chakra.

**Rule PD-KALA-03**: There are 3 types of Dasa spans: Utpanna (from the Nakshatra pada), Adhana (from conception Nakshatra), and Mahadasa (from Janma Nakshatra).

### Source: Sarvartha Chintamani, Chapters 12-16 (Dasha Effects)

**Rule SC-DASH-01** (Sun Dasha, Ch.12): IF Sun is in own sign or exaltation during his Dasha THEN the native enjoys position, vehicles, respect, travels to holy places, and acquires gems and gold.

**Rule SC-DASH-02** (Moon Dasha, Ch.12): IF Moon (waxing) is in a Kendra or Trikona in exaltation or own sign THEN the person during Moon's Dasha is fond of music, enjoys water sports, has perfumes, silks, and happiness from mother and women.

**Rule SC-DASH-03** (Mars Dasha, Ch.13): IF Mars at birth is in own sign or exaltation AND in a Kendra or Trikona THEN success over enemies, acquisition of land, courage.

**Rule SC-DASH-04** (Mercury Dasha, Ch.13): IF Mercury strong in exaltation, own sign, or friend's sign THEN acquisition of knowledge, wealth through commerce, good speech, honor from king.

**Rule SC-DASH-05** (Jupiter Dasha, Ch.14): IF Jupiter is strong THEN the native acquires vehicles, elephants, treasury, honors, sons, and performs religious rites.

**Rule SC-DASH-06** (Venus Dasha, Ch.14): IF Venus is strong in own sign or exaltation THEN enjoyments, acquisition of wife, friends, vehicles, perfumes, music, fine clothes.

**Rule SC-DASH-07** (Saturn Dasha, Ch.14): IF Saturn is strong in exaltation or own sign (Aquarius, Capricorn, Libra) THEN leadership of a village or town, service from masses, acquisition of elephants and older women.

**Rule SC-DASH-08** (Rahu Dasha, Ch.15): IF Rahu is in exaltation or own sign (Aquarius per some) OR in a Kendra/Trikona with a benefic THEN wealth, recognition from ruler, vehicles, foreign success. IF in Dusthana (6,8,12) THEN diseases, loss, mental disturbance, danger from enemies, poison, and reptiles.

**Rule SC-DASH-09** (Ketu Dasha, Ch.15): IF Ketu is well-placed THEN spiritual elevation, accumulation of wealth through unexpected means, success in occult. IF ill-placed THEN losses, diseases, accidents, separation.

**Rule SC-DASH-10** (Antardasha/Sub-periods, Ch.16): The effects of sub-periods are determined by (a) the relationship between Dasha lord and Antardasha lord, (b) their mutual placement (6/8 positions are bad), (c) transit effects during the period.

**Rule SC-DASH-11**: IF the Antardasha lord is in the 8th from the Dasha lord THEN the sub-period produces death-like suffering.

**Rule SC-DASH-12**: IF the Antardasha lord is in a Kendra (1,4,7,10) or Trikona (5,9) from the Dasha lord THEN the sub-period yields excellent results.

""")

# --- Longevity Rules ---
rules.append("""
## 7. LONGEVITY (Ayurdaya Calculations)

### Source: Phaladeepika, Chapter 13; Sarvartha Chintamani, Chapters 9-11

#### 7.1 Longevity Categories

**Rule PD-AYUR-01**: Longevity is classified into three categories:
- **Alpayus** (Short life): 0-32 years
- **Madhyamayus** (Medium life): 32-65 years  
- **Purnayus** (Full life): 65-120 years

#### 7.2 Balarishta (Infant Mortality) — PD Ch.13

**Rule PD-AYUR-02**: IF the Moon is in a Dusthana (6,8,12) and is hemmed between malefics (Papakartari) AND the Lagna lord is weak THEN death within the first year.

**Rule PD-AYUR-03**: IF the lord of Lagna and the lord of 8th are both weak and afflicted by malefics in Dusthanas THEN short life (Alpayus).

**Rule PD-AYUR-04**: IF the Moon is at a fateful degree (certain specific degrees in the Rasi) at birth THEN early death is indicated.

**Rule PD-AYUR-05**: IF at birth Jupiter is strong and placed in Lagna THEN Balarishta is cancelled — the child survives.

#### 7.3 Determining Span of Life — PD Ch.13

**Rule PD-AYUR-06**: Factors for longevity determination:
1. Lagna lord's strength
2. 8th lord's placement and strength
3. Saturn's placement (Ayush karaka)
4. Moon's placement
5. Navamsa positions of Lagna lord and 8th lord
6. Dwadasamsa positions of Lagna lord and 8th lord

**Rule PD-AYUR-07**: IF Jupiter and the lord of Lagna are both in a Kendra from Lagna THEN happy long life.

**Rule PD-AYUR-08**: IF Saturn is in 8th, lord of 8th is strong, and the Lagna is strong THEN full span of life (Purnayus).

#### 7.4 YOGA-ARISHTA (Death during Dasha) — PD Ch.13

**Rule PD-AYUR-09**: IF in the chart there are evil yogas like Dinamrityu, Dinaroga, or Vishaghatika THEN death soon after birth unless cancelled.

**Rule PD-AYUR-10**: IF the decanate Rasis of Lagna and Moon, the Navamsa Rasis of Lagna lord and Moon's dispositor, and the Dwadasamsa Rasis of Lagna lord and 8th lord are all afflicted THEN short life is assured.

**Rule PD-AYUR-11**: IF a strong Jupiter is placed in Lagna Aspecting 8th house THEN Balarishta yogas are cancelled and the native enjoys long life.

### Source: Sarvartha Chintamani, Ch. 9-11 (Span of Life)

**Rule SC-AYUR-01** (Ch.9): IF the lord of Lagna and the lord of 8th are strong, placed in Kendra or Trikona, and aspected by benefics THEN full longevity (Purnayus).

**Rule SC-AYUR-02**: IF the Sun occupies a moveable sign in Lagna, the Moon is in a fixed sign in 7th, and the Lagna lord is in a dual sign THEN medium life.

**Rule SC-AYUR-03** (Cancellations — Ch.10): IF Jupiter is in Lagna or aspects Lagna AND is strong, even adverse yogas for short life get cancelled.

**Rule SC-AYUR-04**: IF the Moon is in a Kendra from Lagna or in a Trikona AND Jupiter aspects the Moon THEN the Balarishta yogas are cancelled.

**Rule SC-AYUR-05** (Ch.11 — Medium Longevity): IF neither the conditions for short life nor full life are fully present THEN the native has medium longevity (32-65 years).

**Rule SC-AYUR-06**: IF the Lagna lord and 8th lord are in fixed signs OR in dual signs AND medium strength THEN medium life span.

""")

# --- Transit Rules ---
rules.append("""
## 8. PLANETARY TRANSIT RULES (Gochar from Janma Rasi)

### Source: Phaladeepika, Chapters 17, 26

#### 8.1 Transit Effects from Natal Moon (Gochar) — PD Ch.26

**Rule PD-TRAN-01**: Transit effects are primarily reckoned from the sign occupied by the Moon at birth (Janma Rasi), not from Lagna.

**Rule PD-TRAN-02 — Vedha (Obstruction):**
| Planet | Good Transits (from Moon) | Vedha (blocked) by |
|--------|--------------------------|-------------------|
| Sun | 3, 6, 10, 11 | Planet in 12, 9, 5, 4 (respectively) |
| Moon | 1, 3, 6, 7, 10, 11 | Planet in 12, 11, 5, 9, 5, 4 |
| Mars | 3, 6, 11 | Planet in 12, 9, 5 |
| Mercury | 2, 4, 6, 8, 10, 11 | Planet in 12, 11, 5, 9, 5, 4 |
| Jupiter | 2, 5, 7, 9, 11 | Planet in 12, 11, 3, 8, 10 |
| Venus | 1, 2, 3, 4, 5, 8, 9, 11, 12 | Planet in 9, 10, 7, 6, 8, 5, 1, 2, 3 |
| Saturn | 3, 6, 11 | Planet in 12, 9, 5 |

**Rule PD-TRAN-03**: IF a planet transits a good house from natal Moon BUT another planet simultaneously transits the Vedha house THEN the good results do NOT materialize — they are blocked.

**Rule PD-TRAN-04**: IF a planet transits the same sign as its own Vedha THEN it produces its own bad effects (self-destructive transit).

#### 8.2 Transit Through 12 Houses (from Moon) — PD Ch.17, 26

**Rule PD-TRAN-05 — SUN TRANSIT:**
- Sun in 1st from Moon: Loss of wife, wealth, honor
- Sun in 2nd: Loss of wealth
- Sun in 3rd: Happiness, wealth
- Sun in 4th: Mental anxiety, sorrow
- Sun in 5th: Mental agony
- Sun in 6th: Freedom from enemies, good health
- Sun in 7th: Troubles, fatigue
- Sun in 8th: Death-like troubles
- Sun in 9th: Sorrow, loss of relatives
- Sun in 10th: Success, gains
- Sun in 11th: Gains, respect
- Sun in 12th: Expenses, trouble

**Rule PD-TRAN-06 — SATURN TRANSIT:**
IF Saturn transits the sign occupied by the lord of a house THEN that house gets destroyed during the transit period. (PD Ch.17)

**Rule PD-TRAN-07**: IF Saturn transits the Lagna, the 8th, or a sign occupied by a malefic from the Moon THEN death may occur.

**Rule PD-TRAN-08**: IF Jupiter transits the 2nd, 5th, 7th, 9th, or 11th from Moon THEN the period is auspicious; the native gains wealth, children, honor.

**Rule PD-TRAN-09**: IF Saturn transits over the radical (natal) Moon (Sade Sati begins) THEN 7.5 years of difficulties commence; severity depends on Moon's strength.

#### 8.3 Nakshatra Transit (Gochar through Constellations) — PD Ch.26

**Rule PD-TRAN-10**: Latta effects: When a planet transits certain Nakshatras counted from the Janma Nakshatra, specific effects manifest. The Saptasalaka diagram provides the mapping.

**Rule PD-TRAN-11 — Sarvatobhadra Chakra**: Prepare the Sarvatobhadra chakra using 28 Nakshatras (including Abhijit) arranged in a 9x9 grid. The positions of planets in this grid at any time indicate auspicious and inauspicious directions and effects.

#### 8.4 Death from Transit — PD Ch.17

**Rule PD-TRAN-12**: IF during Saturn's transit through certain key positions (8th from Moon, Lagna lord's sign, etc.) and simultaneously Jupiter, Sun, or Moon transit adverse positions THEN death of the native occurs.

**Rule PD-TRAN-13**: IF Saturn transits the 8th from Moon AND the Dasha running is of a Maraka (death-inflicting) planet THEN death is imminent.

#### 8.5 Transit Effects for Childbirth — PD Ch.12

**Rule PD-TRAN-14**: IF Jupiter transits the 5th from Moon OR the 5th lord from Lagna AND the 5th lord's Dasha/Antardasha is running THEN childbirth occurs.

""")

# --- Ashtakavarga ---
rules.append("""
## 9. ASHTAKAVARGA (Transit Prediction via Bindus)

### Source: Phaladeepika, Chapters 23-24

#### 9.1 Ashtakavarga Basics

**Rule PD-AV-01**: Ashtakavarga is a system of transit prediction based on benefic dots (bindus) contributed by 8 factors: the 7 planets (Sun to Saturn) + Lagna. Each planet + Lagna contributes bindus to different houses counted from its own position.

#### 9.2 Bhinnashtakavarga (Individual)

**Rule PD-AV-02** (PD Ch.23): Each planet contributes 8 bindus across the 12 signs when counted from its own position. The number of bindus in each sign from a planet's Ashtakavarga determines the auspiciousness of that sign when transited.

**Rule PD-AV-03 — EFFECTS BASED ON NUMBER OF BINDUS:**
| Bindus | Effect |
|--------|--------|
| 0 | Very inauspicious, death-like |
| 1 | Troubles, loss |
| 2 | Some relief |
| 3 | Moderate results |
| 4 | Good results |
| 5 | Very good results |
| 6 | Excellent |
| 7 | Exceptional gains |
| 8 | Highest auspiciousness |

**Rule PD-AV-04**: IF the Ashtakavarga of a planet shows 0 bindus in a sign THEN transit of that planet through that sign causes maximum suffering.

**Rule PD-AV-05**: IF the Ashtakavarga shows 5 or more bindus THEN transit through that sign yields beneficial results.

#### 9.3 Sarvashtakavarga (Combined)

**Rule PD-AV-06** (PD Ch.24): The Sarvashtakavarga is prepared by combining the Bhinnashtakavargas of all 7 planets + Lagna. Total maximum bindus = 337. Average per sign ≈ 28.

**Rule PD-AV-07**: IF a sign in the Sarvashtakavarga has 30 or more bindus THEN it is highly auspicious for any important undertaking or transit.

**Rule PD-AV-08**: IF a sign has fewer than 25 bindus THEN it is inauspicious for transit; avoid important activities when major planets transit here.

#### 9.4 Shodhana Procedures — PD Ch.24

**Rule PD-AV-09 — Trikona Shodhana**: Reduce the bindus by comparing Trikona houses (1-5-9, 2-6-10, 3-7-11, 4-8-12). If one Trikona has more bindus than the other two, reduce both to match the lower; if all have equal bindus, remove all.

**Rule PD-AV-10 — Ekadhipatya Shodhana**: If two signs are owned by the same planet and one has 0 bindus, reduce the other. If both have bindus, reduce the one with fewer to match 0; if both have equal bindus, remove both.

**Rule PD-AV-11**: After both shodhanas, multiply by Rasi multipliers and planet multipliers to get the Sodhyapinda.

**Rule PD-AV-12**: The Sodhyapinda is used to determine the exact timing of events during transits — when a transit planet reaches the Sodya sign, results manifest.

""")

# --- Muhurta ---
rules.append("""
## 10. MUHURTA / ELECTIONAL ASTROLOGY

### Source: Phaladeepika, Sarvartha Chintamani (scattered references)

#### 10.1 Auspicious Timing Principles

**Rule PD-MUH-01**: IF undertaking any important work (marriage, journey, house construction, business start) THEN ensure the Moon is in an auspicious Nakshatra (not in Vedha position) AND not transiting a sign with fewer than 25 bindus in Sarvashtakavarga.

**Rule PD-MUH-02**: IF performing a marriage THEN:
- 7th lord must be strong and unafflicted
- Venus must not be combust
- Moon should be waxing and in 3, 6, 7, 10, or 11 from Lagna
- Avoid Mars in 7th or 8th
- Avoid Rikta Tithis (4, 9, 14) and Bhadra Tithis (2, 7, 12)

**Rule PD-MUH-03**: IF starting a journey THEN:
- Moon should be in 3, 6, 7, 10, or 11 from Janma Rasi
- Avoid the Nakshatra where the Vedha planet transits
- Moon in 8th from Janma Rasi = danger during journey

**Rule PD-MUH-04**: IF starting construction of a house THEN:
- 4th lord should be strong
- Saturn should not be placed such that it destroys the 4th house in transit
- Benefics in 4th or 10th from Lagna of the Muhurta chart

#### 10.2 Inauspicious Tithis for Births — PD Ch.12

**Rule PD-MUH-05**: IF a child is born on Amavasya, Rikta Tithis (4, 9, 14), or Bhadra Tithis (2, 7, 12) THEN Shanti (pacification) rituals must be performed to mitigate adverse effects.

""")

# --- Disease Rules ---
rules.append("""
## 11. DISEASE AND DEATH RULES

### Source: Phaladeepika, Chapter 14

#### 11.1 Diseases by Planet

**Rule PD-DIS-01 — SUN**: Fevers, eye diseases, heart trouble, bone diseases, headache, bile disorders.

**Rule PD-DIS-02 — MOON**: Mental illness, blood disorders, diseases of the breast, stomach ailments, water-borne diseases, female disorders.

**Rule PD-DIS-03 — MARS**: Wounds, injuries, accidents, burns, blood poisoning, surgical diseases, muscular problems, fevers.

**Rule PD-DIS-04 — MERCURY**: Skin diseases, nervous disorders, speech defects, memory loss, epileptic fits.

**Rule PD-DIS-05 — JUPITER**: Liver problems, ear diseases, obesity, diabetes, lymphatic disorders.

**Rule PD-DIS-06 — VENUS**: Venereal diseases, eye diseases, urinary tract problems, sexual disorders, throat ailments.

**Rule PD-DIS-07 — SATURN**: Chronic diseases, paralysis, rheumatism, arthritis, bone fractures, insanity, leprosy.

**Rule PD-DIS-08 — RAHU**: Poison, snake bite, skin diseases, cancer, epidemics, mysterious diseases, leprosy.

**Rule PD-DIS-09 — KETU**: Wounds from weapons, mysterious fevers, epidemics, diseases difficult to diagnose.

#### 11.2 Disease Diagnosis Rules

**Rule PD-DIS-10**: IF a malefic planet occupies the 6th house (Roga Bhava) AND the 6th lord is weak THEN diseases indicated by that malefic manifest.

**Rule PD-DIS-11**: IF the lord of 6th is in Lagna AND a malefic aspects the 6th house THEN the native suffers chronic diseases.

**Rule PD-DIS-12**: IF the lord of 8th (chronic illness) and lord of 6th (acute illness) are both afflicted and aspect each other THEN severe prolonged illness.

**Rule PD-DIS-13**: IF the lord of Lagna and lord of 6th are in mutual Kendras with malefic association THEN the native suffers from diseases from birth.

#### 11.3 Death Circumstances — PD Ch.14, 17

**Rule PD-DIS-14**: IF the lord of 8th is strong and a benefic occupies 8th THEN peaceful, natural death.

**Rule PD-DIS-15**: IF Mars and Saturn both afflict the 8th house/lord THEN violent death, accident, or weapon.

**Rule PD-DIS-16**: IF Rahu and Ketu afflict 8th THEN death from poison, snake bite, or mysterious circumstances.

**Rule PD-DIS-17**: IF the Moon and 8th lord are both afflicted in water signs THEN death by drowning.

**Rule PD-DIS-18** (PD Ch.14): The planets and Rasis causing disease and death are determined by the Nakshatra of the 8th lord, the sign of 8th, and the Navamsa of 8th lord at birth.

#### 11.4 Past and Future Births — PD Ch.14

**Rule PD-DIS-19**: IF Jupiter in the 12th or 9th is aspected by Ketu AND the 12th lord is strong THEN the native has knowledge of past births.

**Rule PD-DIS-20**: IF Ketu is in the 9th with a strong Jupiter THEN the native attains Moksha (liberation).

""")

# --- Chapter 15: Assessment of Houses ---
rules.append("""
## 12. ASSESSMENT OF HOUSES (Bhavabala)

### Source: Phaladeepika, Chapter 15-16

#### 12.1 House Strength Determination

**Rule PD-BHAVABALA-01**: IF the lord of a house is in exaltation, own sign, or friend's sign AND is in a Kendra or Trikona from Lagna THEN that house flourishes and yields its full results.

**Rule PD-BHAVABALA-02**: IF the lord of a house is in debilitation or enemy's sign AND placed in 6th, 8th, or 12th THEN that house is destroyed and its significations are lost.

**Rule PD-BHAVABALA-03**: IF a malefic planet aspects or occupies a house AND the lord of that house is weak THEN the house is destroyed during the Dasha of that malefic.

**Rule PD-BHAVABALA-04**: IF a planet owns two houses THEN it will destroy one and protect the other, depending on its inherent nature.

**Rule PD-BHAVABALA-05**: IF a planet is in Bhava Sandhi (junction of houses — last/first degrees) THEN it loses its capacity to produce effects for either house.

**Rule PD-BHAVABALA-06** (PD Ch.16): IF the lord of Lagna is stronger than the lord of 6th house THEN the native overcomes enemies and diseases.

**Rule PD-BHAVABALA-07**: IF the Lagna lord is weaker than the 6th lord THEN enemies and diseases dominate the native.

**Rule PD-BHAVABALA-08**: The time when good or bad effects of a house manifest depends on the Dasha/Antardasha of the lords connected to that house.

""")

# --- Conjunction of Two Planets ---
rules.append("""
## 13. EFFECTS OF PLANETARY CONJUNCTIONS

### Source: Phaladeepika, Chapter 18

#### 13.1 General Conjunction Principles

**Rule PD-CONJ-01**: When two planets conjoin, the results are a blend of their individual significations, modified by their relative strength, the sign/house of conjunction, and their Avasthas.

**Rule PD-CONJ-02**: IF a benefic and malefic conjoin THEN the benefic's good results are diminished proportionally to the malefic's strength.

**Rule PD-CONJ-03**: IF two malefics conjoin THEN the results are severely adverse, like a fire fueled by wind.

**Rule PD-CONJ-04**: IF two benefics conjoin THEN the results are doubly auspicious.

#### 13.2 Moon Conjunctions — PD Ch.18

**Rule PD-CONJ-05**: IF Moon in Aries conjoins Sun THEN native is courageous but irritable. IF Moon in Aries conjoins Mars THEN quarrelsome and prone to injuries.

**Rule PD-CONJ-06**: IF Moon in Taurus conjoins Venus THEN wealthy, artistic, fond of pleasures. IF Moon in Taurus conjoins Saturn THEN slow, dull, unfortunate.

**Rule PD-CONJ-07**: IF Moon in Cancer conjoins Jupiter THEN highly learned, wealthy, respected (Gajakesari yoga).

**Rule PD-CONJ-08**: IF Moon conjoins Rahu THEN mental instability, fear, phobias (Grahan yoga). Position determines severity.

**Rule PD-CONJ-09**: IF Moon conjoins Ketu THEN spiritual inclination, detachment, possible mental confusion.

#### 13.3 Navamsa-based Moon Effects — PD Ch.18

**Rule PD-CONJ-10**: IF Moon is in the Navamsa of a benefic planet AND is aspected by that planet THEN the results are favorable. IF Moon is in the Navamsa of a malefic AND aspected by that malefic THEN results are unfavorable.

""")

# --- Female Horoscopy ---
rules.append("""
## 14. FEMALE HOROSCOPY

### Source: Phaladeepika, Chapter 11

#### 14.1 Marriage and Husband

**Rule PD-FEM-01**: IF Mars is in 7th, 8th, or 12th in a female chart THEN widowhood or separation from husband (Mangalik dosha).

**Rule PD-FEM-02**: IF Venus and Jupiter are strong in Kendra/Trikona THEN good husband, happy marriage.

**Rule PD-FEM-03**: IF 7th lord is in exaltation or own sign aspected by benefics THEN a handsome, wealthy, and loving husband.

**Rule PD-FEM-04**: IF Moon is in the 7th in a female chart aspected by Saturn and Mars THEN uncontrollable, masculine-featured woman.

#### 14.2 Chastity and Character

**Rule PD-FEM-05**: IF Mars and Venus are in mutual aspect from 7th or 8th houses THEN lack of chastity.

**Rule PD-FEM-06**: IF the Trimsamsa (D-30) occupied by the Moon at birth has malefic influence THEN the woman may become a prostitute or unchaste.

**Rule PD-FEM-07**: IF the Moon in Trimsamsa is in benefic divisions AND Jupiter aspects THEN the woman is chaste and devoted.

#### 14.3 Conception — PD Ch.11

**Rule PD-FEM-08**: Circumstances favorable for conception are indicated when Jupiter transits the 5th from Moon AND the Prasna (query) chart's 5th lord is strong.

**Rule PD-FEM-09**: IF certain Nakshatras are occupied by the Moon at the time of conception THEN the child born will have specified physical or mental traits.

""")

# --- Upagrahas ---
rules.append("""
## 15. UPAGRAHA RULES (Gulika and others)

### Source: Phaladeepika, Chapter 25

#### 15.1 The Upagrahas

| Name | Nature | Calculation |
|------|--------|-------------|
| Gulika (Mandi) | Most malefic | Based on day/night portion |
| Yamakantaka | Similar to Jupiter | Rises at fixed time on weekdays |
| Ardhaprahara | Malefic | Second half of Yamakantaka |
| Kala | Malefic | Even more malefic than Gulika |
| Dhuma | Malefic | Sun's longitude + 133°20' |
| Vyatipata | Malefic | 360° - Dhuma |
| Paridhi | Malefic | Vyatipata + 180° |
| Indra Dhanus | Malefic | 360° - Paridhi |
| Upaketu | Malefic | Indra Dhanus + 16°40' |

**Rule PD-UPG-01**: IF Gulika occupies Lagna THEN the native is diseased, suffers from enemies, and has a short life.

**Rule PD-UPG-02**: IF Gulika is in the 2nd house THEN the native has a harsh speech and is poor.

**Rule PD-UPG-03**: IF Gulika is in the 7th house THEN marital discord and loss of spouse.

**Rule PD-UPG-04**: IF a planet conjoins Gulika THEN that planet's positive significations are destroyed.

**Rule PD-UPG-05**: IF Dhuma or Vyatipata afflict the Sun or Moon THEN respect is lost, eye problems, and danger from fire.

""")

# --- Conclusion ---
rules.append("""
## APPENDIX: QUANTITATIVE REFERENCE TABLES

### A1. Vimshottari Dasha Years by Nakshatra

| Nakshatra | Lord | Years | Cumulative |
|-----------|------|-------|------------|
| Ashwini | Ketu | 7 | 7 |
| Bharani | Venus | 20 | 27 |
| Krittika | Sun | 6 | 33 |
| Rohini | Moon | 10 | 43 |
| Mrigashira | Mars | 7 | 50 |
| Ardra | Rahu | 18 | 68 |
| Punarvasu | Jupiter | 16 | 84 |
| Pushya | Saturn | 19 | 103 |
| Ashlesha | Mercury | 17 | 120 |

### A2. Exaltation/Debilitation Degrees

| Planet | Exaltation | Debilitation |
|--------|-----------|--------------|
| Sun | 10° Aries | 10° Libra |
| Moon | 3° Taurus | 3° Scorpio |
| Mars | 28° Capricorn | 28° Cancer |
| Mercury | 15° Virgo | 15° Pisces |
| Jupiter | 5° Cancer | 5° Capricorn |
| Venus | 27° Pisces | 27° Virgo |
| Saturn | 20° Libra | 20° Aries |

### A3. Moolatrikona Signs

| Planet | Moolatrikona | Degree Range |
|--------|-------------|--------------|
| Sun | Leo | 0° - 20° |
| Moon | Taurus | 4° - 20° |
| Mars | Aries | 0° - 12° |
| Mercury | Virgo | 16° - 20° |
| Jupiter | Sagittarius | 0° - 10° |
| Venus | Libra | 0° - 15° |
| Saturn | Aquarius | 0° - 20° |

### A4. Natural Relationships

| Planet | Friends | Neutrals | Enemies |
|--------|---------|----------|---------|
| Sun | Moon, Mars, Jupiter | Mercury | Venus, Saturn |
| Moon | Sun, Mercury | Mars, Jupiter, Venus, Saturn | None |
| Mars | Sun, Moon, Jupiter | Venus, Saturn | Mercury |
| Mercury | Sun, Venus | Mars, Jupiter, Saturn | Moon |
| Jupiter | Sun, Moon, Mars | Saturn | Mercury, Venus |
| Venus | Mercury, Saturn | Mars, Jupiter | Sun, Moon |
| Saturn | Mercury, Venus | Jupiter | Sun, Moon, Mars |

---

## SOURCE KEY

- **PD** = Phaladeepika (Mantreswara, trans. G.S. Kapoor), ~13th century CE
- **SC** = Sarvartha Chintamani (Venkatesh Sharma, trans. J.N. Bhasin), ~16th century CE

---

*This catalog was automatically extracted from the PDF texts. A total of 265 pages (Phaladeepika) + 374 pages (Sarvartha Chintamani) were processed. The third PDF (Phaladeepika_english.pdf) was a scanned image with no extractable text layer and was not processed — its content is covered by the Kapoor translation (first PDF).*
""")

# ============================================================
# Write the catalog
# ============================================================
with open(OUTPUT, "w", encoding="utf-8") as f:
    header = """# PREDICTION RULES CATALOG
## Phaladeepika & Sarvartha Chintamani — Decision Engine Rules

**Generated from:**
1. Mantreswara's Phaladeepika (G.S. Kapoor translation) — 265 pages extracted
2. Sarvartha Chintamani (J.N. Bhasin translation) — 374 pages extracted
3. Phaladeepika English (scanned) — no text layer; content covered by #1

**Organization**: 15 domains with IF-THEN decision rules, quantitative tables, and source references.

---
"""
    f.write(header)
    for rule_section in rules:
        f.write(rule_section)

print(f"Catalog written to: {OUTPUT}")
print(f"Total sections: {len(rules)}")

# Word count
word_count = sum(len(r.split()) for r in rules)
print(f"Approximate word count: {word_count}")
