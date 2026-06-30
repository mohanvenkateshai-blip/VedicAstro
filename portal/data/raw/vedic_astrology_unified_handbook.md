# vedic astrology unified handbook

Vedic Astrology & Muhurta Computation Engine Handbook
 Comprehensive Integration Blueprint for Planetary (Graha) and Almanac (Panchanga) Logic Engine Development
 

 
 
 
 Handbook Chapters
 
 1. Computational Primitives
 2. Planetary State Modifiers
 3. Structural Graha Yogas
 4. Almanac & Panchanga Yogas
 5. Transit & Gochara Verification
 6. Unified Software Architecture
 
 

 
 
 
 
 
 1. Computational Primitives & Geometric Data Models
 To construct a deterministic software computation engine for Vedic horoscopy (Jataka) and time-selection (Muhurta), you must first standardize coordinate maps. Astronomical inputs must convert seamlessly into bounded cyclical values ($0^{\circ}$ to $359^{\circ}59'59"$) corrected by sidereal ayanamsha calculations (e.g., True Chitra/Lahiri).
 
 1.1 Primitive ID Standardizations
 Planetary, Sign, and Nakshatra primitives must be modeled using persistent strict indexes. This prevents translation bugs between asynchronous API data blocks and the logic evaluating structural yoga forms.
 // Strict Architectural Index Definitions
const PLANET_IDS = { SUN: 0, MOON: 1, MARS: 2, MERCURY: 3, JUPITER: 4, VENUS: 5, SATURN: 6, RAHU: 7, KETU: 8 };

const RASHI_IDS = { ARIES: 1, TAURUS: 2, GEMINI: 3, CANCER: 4, LEO: 5, VIRGO: 6, 
 LIBRA: 7, SCORPIO: 8, SAGITTARIUS: 9, CAPRICORN: 10, AQUARIUS: 11, PISCES: 12 };

 1.2 Exaltation, Debilitation, and Moolatrikona Coordinates Map
 Planetary strength evaluation relies on specific sign structures and geometric degree limits. The logic engine calculates properties dynamically using the absolute boundary mappings below:
 
 
 
 Planet ID
 Name
 Exaltation Sign (Rashi ID)
 Deep Degree (Paramochha)
 Debilitation Sign (Rashi ID)
 Moolatrikona Range & Sign
 
 
 
 0Sun1 (Aries)10°7 (Libra)Leo (5): 0° to 20°
 1Moon2 (Taurus)3°8 (Scorpio)Taurus (2): 3.1° to 30°
 2Mars10 (Capricorn)28°4 (Cancer)Aries (1): 0° to 12°
 3Mercury6 (Virgo)15°12 (Pisces)Virgo (6): 15° to 20°
 4Jupiter4 (Cancer)5°10 (Capricorn)Sagittarius (9): 0° to 10°
 5Venus12 (Pisces)27°6 (Virgo)Libra (7): 0° to 15°
 6Saturn7 (Libra)20°1 (Aries)Aquarius (11): 0° to 20°
 
 

 1.3 Positional Aspect (Graha Drishti) Evaluation Vector
 Every planet projects an aspect vector to the 7th house from its current house position. Specific outer planets apply full strength aspects ($1.0$ weight) to additional geometric house indices. These special aspects (Vishesha Drishti) must be hardcoded inside the geometric solver:
 
 
 Mathematical Aspect Solver Equation
 Target House Index = ((SourceHouse + HouseOffset - 1) % 12) + 1
 
 
 
 Mars (ID 2): Projects special full-strength aspects to house offsets 4 and 8.
 Jupiter (ID 4): Projects special full-strength aspects to house offsets 5 and 9.
 Saturn (ID 6): Projects special full-strength aspects to house offsets 3 and 10.
 Rahu/Ketu (IDs 7 & 8): Project secondary structural aspects to house offsets 5 and 9.
 
 

 
 
 2. The Planetary State Modifier Engine
 A planetary placement cannot be validated solely by its presence in a sign or house. The state engine must compute physical and astronomical overrides that can neutralize, mutate, or cancel a yoga's functionality.

 2.1 Solar Combustion (Astayana) Orbs Matrix
 When a planet's absolute longitudinal proximity to the Sun falls within specific degree boundaries, it enters a is_combust = true state. This status mutes or drops positive structural yoga outputs to neutral/zero.
 
 
 
 Planet ID
 Planet Name
 Combustion Limit (Direct Motion)
 Combustion Limit (Retrograde Motion)
 
 
 
 1Moon12° 00'N/A
 2Mars17° 00'17° 00'
 3Mercury14° 00'12° 00'
 4Jupiter11° 00'11° 00'
 5Venus10° 00'8° 00'
 6Saturn15° 00'15° 00'
 
 

 2.2 Planetary War (Graha Yuddha) Logic Solver
 When two non-luminary planets (Mars through Saturn, IDs 2 to 6) occupy the same sign within an absolute longitudinal difference of less than or equal to $1^\circ 00'00"$, the engine asserts a Graha Yuddha flag. The planet with the lower longitude within the sign is declared the victor, while the losing planet's beneficial yoga outputs are muted or flagged as dysfunctional.

 2.3 Debilitation Cancellation (Neechabhanga) Algorithmic Matrix
 If a planet is flagged as is_debilitated = true, the engine runs a series of conditional evaluation loops to see if a Neechabhanga Raja Yoga applies. This scenario converts structural weakness into functional strength.
 
 function evaluateNeechabhanga(planetId, chartData) {
 if (!chartData.planets[planetId].isDebilitated) return false;
 
 let currentRashi = chartData.planets[planetId].rashi;
 let rashiLord = RASHI_ATTRIBUTES[currentRashi].lord;
 let exaltationLord = getExaltationLordOfSign(currentRashi);
 
 // Condition 1: Sign Lord or Exaltation Lord occupies a Kendra (1, 4, 7, 10) from Lagna
 if (isKendraFromLagna(rashiLord, chartData) || isKendraFromLagna(exaltationLord, chartData)) {
 return true;
 }
 
 // Condition 2: Sign Lord or Exaltation Lord occupies a Kendra from the Moon
 if (isKendraFromMoon(rashiLord, chartData) || isKendraFromMoon(exaltationLord, chartData)) {
 return true;
 }
 
 return false;
}
 

 
 
 3. Structural Graha Yogas (Classical Horoscopy Library)
 This chapter contains the algorithmic rules for structural planetary combinations from Brihat Parashara Hora Shastra, Saravali, and Jataka Tattva. These rules are used to identify latent capabilities in a natal chart or specific operational profiles for a given time window.

 3.1 Pancha Mahapurusha Yogas
 These yogas are triggered when a non-luminary planet occupies its own sign, moolatrikona, or exaltation sign while simultaneously located in a Kendra house (1st, 4th, 7th, or 10th) from the Ascendant.
 
 
 
 Yoga Name
 Planet ID
 Valid Target Signs
 Functional Manifestation
 Dysfunctional Triggers (Muting)
 
 
 
 
 Ruchaka Yoga
 2 (Mars)
 1, 8, 10
 High executive execution, command, systemic physical drive.
 Combustion or direct aspect from a weak Saturn.
 
 
 Bhadra Yoga
 3 (Mercury)
 3, 6
 High analytical performance, algorithmic calculation expertise.
 Combustion or structural affliction from the 8th lord.
 
 
 Hamsa Yoga
 4 (Jupiter)
 4, 9, 12
 Systemic design wisdom, ethical clarity, long-range planning.
 Combustion or Kendradhipati Dosha modifications.
 
 
 Malavya Yoga
 5 (Venus)
 2, 7, 12
 Aesthetic mastery, financial architecture development.
 Combustion or a heavily waned Moon.
 
 
 Sasa Yoga
 6 (Saturn)
 7, 10, 11
 Infrastructural scale, systemic operational endurance.
 Direct conflict aspects from the Sun or Mars.
 
 
 

 3.2 Nabhasa Yogas (Spatial Layout Frameworks)
 Per Saravali, Nabhasa Yogas depend strictly on how planets are distributed across signs or houses, without looking at sign lords. They establish the foundational system architecture of a chart.
 
 A. Asraya Yogas (Sign Shape Anchors)
 
 Musala Yoga: Triggered when all seven native planets are located exclusively inside Fixed Signs (2, 5, 8, 11). This indicates a highly stable system that resists rapid code refactoring or positional changes.
 Nabla Yoga: Triggered when all seven native planets are located exclusively inside Dual Signs (3, 6, 9, 12). This represents versatile, multi-threaded processing capabilities that can be prone to decision loops.
 

 B. Akriti Yogas (Geometric House Distributions)
 
 Gada Yoga: All seven planets must be clustered in two adjacent Kendra houses (e.g., houses 1 and 4, or 4 and 7).
 Sakata Yoga: All planets must be stationed exclusively within the 1st and 7th house axis. This design produces dynamic interpersonal shifts and alternating focus cycles.
 Vihaga Yoga: All planets must occupy the 4th and 10th house axis exclusively. This indicates high system visibility, public impact, and strong structural execution.
 

 3.3 Combined Planetary Construct Yogas
 
 Gaja Kesari Yoga: Triggered when Jupiter is located in a Kendra house (1st, 4th, 7th, 10th) relative to the Moon's position.
 
 Gaja Kesari House Distance Rule
 ((House_Jupiter - House_Moon + 12) % 12) + 1 ∈ {1, 4, 7, 10}
 
 Enhancement: Jupiter is exalted or in its own sign. Neutralization: Jupiter is combust, or the Moon is heavily waned (within $72^\circ$ of solar proximity).
 
 Kemadruma Yoga: Triggered if there are no planets (excluding the Sun, Rahu, and Ketu) in both the 2nd and 12th houses relative to the Moon. This indicates structural vulnerability or lack of systemic support.
 
 Kemadruma Verification Rule
 if (CountPlanets(House_Moon - 1) == 0 && CountPlanets(House_Moon + 1) == 0) return YOGA_ACTIVE;
 
 Cancellation (Kemadruma Bhanga): If any planet occupies a Kendra house relative to either the Lagna or the Moon, the engine flags the yoga as cancelled, converting structural isolation into independence and resilience.
 
 
 

 
 
 4. Almanac & Panchanga Yogas (Time-Selection Windows)
 Unlike Graha Yogas, which evaluate planetary geometry relative to an ascendant, Almanac Yogas calculate time-varying values derived from solar-lunar longitudes and time coordinates. These calculations are critical for filtering out unviable time windows in Muhurta software.

 4.1 The Nitya Yoga Calculation Engine
 Nitya Yogas represent the combined absolute sidereal longitudes of the Sun and the Moon. There are 27 Nitya Yogas, each covering an arc of $13^\circ 20'$ ($800'$ of arc). **Shobhana Yoga** is the 5th configuration in this sequence.

 
 Nitya Yoga Index Formula
 YNitya = Math.floor(((SunLongitude + MoonLongitude) % 360) / 13.333333) + 1
 

 The 27 Nitya Yoga Registry Matrix
 Your lookup dictionary must evaluate whether the current index returns a benefic or malefic state block:
 const NITYA_YOGA_REGISTRY = {
 1: { name: "Vishkumbha", type: "Malefic" }, 2: { name: "Preeti", type: "Benefic" },
 3: { name: "Ayushman", type: "Benefic" }, 4: { name: "Saubhagya", type: "Benefic" },
 5: { name: "Shobhana", type: "Benefic" }, 6: { name: "Atiganda", type: "Malefic" },
 7: { name: "Sukarma", type: "Benefic" }, 8: { name: "Dhriti", type: "Benefic" },
 9: { name: "Shoola", type: "Malefic" }, 10: { name: "Ganda", type: "Malefic" },
 11: { name: "Vriddhi", type: "Benefic" }, 12: { name: "Dhruva", type: "Benefic" },
 13: { name: "Vyaghata", type: "Malefic" }, 14: { name: "Harshana", type: "Benefic" },
 15: { name: "Vajra", type: "Malefic" }, 16: { name: "Siddhi", type: "Benefic" },
 17: { name: "Vyatipata", type: "Malefic" }, 18: { name: "Variyan", type: "Benefic" },
 19: { name: "Parigha", type: "Malefic" }, 20: { name: "Shiva", type: "Benefic" },
 21: { name: "Siddha", type: "Benefic" }, 22: { name: "Sadhya", type: "Benefic" },
 23: { name: "Shubha", type: "Benefic" }, 24: { name: "Shukla", type: "Benefic" },
 25: { name: "Brahma", type: "Benefic" }, 26: { name: "Indra", type: "Benefic" },
 27: { name: "Vaidhriti", type: "Malefic" }
};
 System Rule for Shobhana Yoga (Index 5): This configuration acts as a positive enhancement filter for stability and growth, mitigating minor malefic planetary transits during time-window generation.

 4.2 Weekday-Nakshatra Intersections (Anandadi & Mishraka Yogas)
 These yogas evaluate the alignment of the current **Weekday (Vara)** with the transiting **Moon's Nakshatra**. When specific combinations occur, they create structural blocks that take precedence over standard planetary house alignments.

 
 Critical Exception Rule (Nasa & Dagdha Yogas): If the engine identifies a Nasa or Dagdha condition, the current time window is instantly disqualified (is_executable = false), skipping subsequent planetary yoga scoring loops.
 

 The Primary Structural Intersections Table
 
 
 
 Weekday (Vara ID)
 Nasa Yoga Nakshatras (Loss/Destruction)
 Kana Yoga Nakshatras (Inherent Defect)
 Dagdha Yoga Nakshatras (Burned/Failure)
 
 
 
 
 0 (Sunday)
 Ashwini (1), Magha (10), Vishakha (16), Anuradha (17), Jyeshtha (18)
 Jyeshtha (18) (Conditional)
 Bharani (2)
 
 
 1 (Monday)
 Krittika (3), Uttaraphalguni (12), Chitra (14), Vishakha (16)
 Anuradha (17)
 Chitra (14)
 
 
 2 (Tuesday)
 Mrigashira (5), Ardra (6), Dhanishta (23), Shatabhisha (24)
 Purvabhadrapada (25)
 Ashlesha (9)
 
 
 3 (Wednesday)
 Ashwini (1), Bharani (2), Krittika (3), Rohini (4)
 Uttarabhadrapada (26)
 Hasta (13)
 
 
 4 (Thursday)
 Punarvasu (7), Pushya (8), Ashlesha (9)
 Peechavalli (Custom offset)
 Anuradha (17)
 
 
 5 (Friday)
 Uttaraphalguni (12), Hasta (13), Chitra (14)
 Jyeshtha (18)
 Purvashadha (20)
 
 
 6 (Saturday)
 Rohini (4), Mrigashira (5), Shatabhisha (24)
 Revati (27)
 Revati (27)
 
 
 
 

 
 
 5. Transit (Gochara) Logic & Dynamic Filters
 For a Muhurta application, a static natal configuration represents latent potential. Transits act as time-varying wave functions that trigger or suppress these states. The dynamic processing module maps transiting positions against the natal reference frame.

 5.1 Planetary Transit Vedha (Obstruction) Matrix
 Planets in transit distribute positive or negative metrics relative to the natal Moon sign. However, if another transiting planet occupies a corresponding **Vedha** house position concurrently, that transit's influence is temporarily obstructed.
 
 
 Exception to Vedha Rules: The logic engine must exempt specific relationships from mutual obstruction flags:
 if ((TransitSun && TransitSaturn) || (TransitMercury && TransitMoon)) { bypassVedhaCheck(); }
 

 5.2 Ashtakavarga Dynamic Threshold Filter
 A transiting planet moving through a house with low **Bhinnashtakavarga Bindu counts** cannot activate beneficial planetary yogas. The dynamic validation script must apply the scoring parameters below:
 
 Bindu Score < 4: Disables beneficial natal yoga triggers. The house lacks sufficient energy to support execution.
 4 ≤ Bindu Score ≤ 5: Standard operational state. Yogas execute at baseline efficiency.
 Bindu Score ≥ 6: Enhanced peak activation state. Yoga execution efficiency scales positively.
 
 

 
 
 6. Unified Software Architecture & Pipeline Execution
 To run these calculations without performance bottlenecks, your software should implement a two-tier verification firewall. The system first filters out non-viable time windows using fast almanac calculations before running complex planetary house-aspect algorithms.

 6.1 Comprehensive Engine Ingestion JSON Schema
 This standardized data structure provides the parameters necessary to evaluate both planetary and almanac yogas simultaneously:
 {
 "engine_timestamp": {
 "julian_day": 2461192.91,
 "utc_iso": "2026-06-01T15:56:00Z"
 },
 "almanac_inputs": {
 "weekday_id": 1,
 "sun_longitude": 46.5211,
 "moon_longitude": 214.1102,
 "active_nakshatra_id": 16
 },
 "natal_baseline": {
 "ascendant_house_rashi": 6,
 "moon_rashi_id": 8,
 "bhinnashtakavarga": {
 "jupiter": [5, 4, 6, 2, 5, 7, 3, 4, 5, 6, 4, 3]
 }
 },
 "transit_positions": {
 "4": { "planet_name": "Jupiter", "current_rashi": 4, "current_house_from_lagna": 11, "is_combust": false }
 }
}

 6.2 The Complete Verification Pipeline
 This master routine handles window validation by processing the rules defined in this handbook in sequence:
 
 function evaluateTimeWindow(inputData) {
 // TIER 1: ALMANAC AND PANCHANGA FIREWALL
 let nityaYogaIndex = calculateNityaYoga(inputData.almanac_inputs.sun_longitude, inputData.almanac_inputs.moon_longitude);
 let nityaYoga = NITYA_YOGA_REGISTRY[nityaYogaIndex];
 
 // Check Vara-Nakshatra exceptions (Nasa / Dagdha)
 let almanacException = checkVaraNakshatraExceptions(inputData.almanac_inputs.weekday_id, inputData.almanac_inputs.active_nakshatra_id);
 if (almanacException.is_disqualified) {
 return { status: "DISQUALIFIED", reason: "Almanac Block: " + almanacException.flag_type };
 }

 // TIER 2: PLANETARY STATE MODIFIERS
 let modifiedPlanets = runStateModifiers(inputData.transit_positions);

 // TIER 3: STRUCTURAL YOGA MATRIX SCORING
 let activeGrahaYogas = parseGrahaYogas(modifiedPlanets, inputData.natal_baseline);
 
 // TIER 4: DYNAMIC TRANSIT VEDHA & ASHTAKAVARGA FILTERS
 let finalScore = 1.0;
 if (nityaYoga.type === "Benefic") finalScore += 0.25;
 
 return {
 status: "VALID_WINDOW",
 computational_weight: finalScore,
 active_yogas: activeGrahaYogas
 };
}
 

 
 

 
 Unified Vedic Astrology Engineering Specifications Handbook • Structured for Automated Systems Development © 2026