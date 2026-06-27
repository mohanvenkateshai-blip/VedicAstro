# vedic yoga logic engine

Vedic Astrology Yoga Engine Specification
 Algorithmic Blueprints from Brihat Parashara Hora Shastra, Saravali, and Jataka Tattva for Muhurta Software Architecture
 

 
 
 
 1. Core Data Models
 2. Modification Engine
 3. Planetary Yoga Libraries
 4. Transit (Gochara) Engine
 5. Implementation Architecture
 
 

 
 
 1. Core Data Models & Mathematical Specifications
 To program an absolute mathematical engine for parsing structural yogas, specific foundational objects and lookups must be rigorously mapped. The coordinates are calculated down to precise degrees, minutes, and seconds of arc using an Ayanamsha framework (e.g., Lahiri or True Chitra).
 
 1.1 Primitive System Maps
 // Planet Primitives Mapping
PLANETS = { 0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 4: "Jupiter", 5: "Venus", 6: "Saturn", 7: "Rahu", 8: "Ketu" };

// Rashi Primitives Mapping
RASHIS = { 1: "Aries", 2: "Taurus", 3: "Gemini", 4: "Cancer", 5: "Leo", 6: "Virgo", 
 7: "Libra", 8: "Scorpio", 9: "Sagittarius", 10: "Capricorn", 11: "Aquarius", 12: "Pisces" };

// Sign Attributes Matrix for Elements and Modality
RASHI_ATTRIBUTES = {
 1: {"modality": "Chara", "element": "Fire", "lord": 2},
 2: {"modality": "Sthira", "element": "Earth", "lord": 5},
 3: {"modality": "Dvisvabhava","element": "Air", "lord": 3},
 4: {"modality": "Chara", "element": "Water", "lord": 1},
 5: {"modality": "Sthira", "element": "Fire", "lord": 0},
 6: {"modality": "Dvisvabhava","element": "Earth", "lord": 3},
 7: {"modality": "Chara", "element": "Air", "lord": 5},
 8: {"modality": "Sthira", "element": "Water", "lord": 2},
 9: {"modality": "Dvisvabhava","element": "Fire", "lord": 4},
 10: {"modality": "Chara", "element": "Earth", "lord": 6},
 11: {"modality": "Sthira", "element": "Air", "lord": 6},
 12: {"modality": "Dvisvabhava","element": "Water", "lord": 4}
};

 1.2 Exaltation, Debilitation, and Moolatrikona Boundaries
 Planetary strength changes dynamically based on coordinates. The deep exaltation (Paramochha) and deep debilitation (Paramaneecha) boundaries are defined as follows:
 
 
 
 Planet ID
 Name
 Exaltation Rashi
 Deep Degree
 Debilitation Rashi
 Moolatrikona Rashi / Range
 
 
 
 0Sun1 (Aries)10°7 (Libra)5 (Leo): 0° - 20°
 1Moon2 (Taurus)3°8 (Scorpio)2 (Taurus): 3° - 30°
 2Mars10 (Capricorn)28°4 (Cancer)1 (Aries): 0° - 12°
 3Mercury6 (Virgo)15°12 (Pisces)6 (Virgo): 15° - 20°
 4Jupiter4 (Cancer)5°10 (Capricorn)9 (Sagittarius): 0° - 10°
 5Venus12 (Pisces)27°6 (Virgo)7 (Libra): 0° - 15°
 6Saturn7 (Libra)20°1 (Aries)11 (Aquarius): 0° - 20°
 
 

 1.3 Positional Aspect (Graha Drishti) Logic
 Every planet projects an aspect to the 7th house relative to its position. Specific planets have special geometric aspects (Vishesha Drishti) which must be programmed with full strength ($1.0$ weight) according to Parashari rules:
 
 Aspect Target House Equation: $H_{target} = (H_{source} + AspectOffset - 1) \pmod{12} + 1$
 
 
 Mars (2): Special aspects to the 4th and 8th houses.
 Jupiter (4): Special aspects to the 5th and 9th houses.
 Saturn (6): Special aspects to the 3rd and 10th houses.
 Rahu (7) & Ketu (8): Outer nodes project 5th and 9th aspects according to standard commentary traditions in BPHS.
 
 

 
 
 2. The Modification Engine (Rules of Integrity & Strength)
 Yogas cannot be calculated solely by sign or house placement. They are modified by mathematical criteria representing solar combustion, mutual planetary wars, positional cancellation, and aspect integrity.

 2.1 Combustion (Astayana) Orbs Matrix
 If a planet's longitude relative to the Sun is within the specified longitudinal difference limit, it shifts to a combust = true state, rendering structural benefic yogas highly dysfunctional or neutralized.
 // Combustion logic engine data bounds
COMBUSTION_ORBS = {
 1: {"direct": 12, "retrograde": 12}, // Moon
 2: {"direct": 17, "retrograde": 17}, // Mars
 3: {"direct": 14, "retrograde": 12}, // Mercury
 4: {"direct": 11, "retrograde": 11}, // Jupiter
 5: {"direct": 10, "retrograde": 8}, // Venus
 6: {"direct": 15, "retrograde": 15} // Saturn
};

 2.2 Planetary War (Graha Yuddha) Logic
 When two non-luminary planets (Mars through Saturn) are within 1° ($1^{\circ} 00' 00"$) of longitudinal proximity, a Graha Yuddha condition is asserted. The planet with the lower absolute longitude inside the sign is mathematically declared the victor, while the defeated planet's positive yoga outputs are completely muted.

 2.3 Neechabhanga (Debilitation Cancellation) Validation Matrix
 Per BPHS and Saravali, a debilitated planet can form a powerful Raja Yoga if any of the following programmatic evaluation chains return true:
 def check_neechabhanga(planet_id, chart_data):
 deb_sign = RASHI_ATTRIBUTES[chart_data[planet_id]['rashi']]
 if not chart_data[planet_id]['is_debilitated']:
 return False
 
 rashi_lord = deb_sign['lord']
 exaltation_lord = get_exaltation_lord_of_sign(chart_data[planet_id]['rashi'])
 
 # Rule 1: The lord of the debilitated sign is in a Kendra from Lagna OR Moon
 if is_kendra_from_lagna_or_moon(rashi_lord, chart_data):
 return True
 
 # Rule 2: The planet that gets exalted in the debilitated sign is in a Kendra from Lagna OR Moon
 if is_kendra_from_lagna_or_moon(exaltation_lord, chart_data):
 return True
 
 # Rule 3: The lord of the rashi where the debilitated planet gets exalted is in a Kendra from Lagna OR Moon
 nat_exalt_rashi = PLANET_EXALTATION_DATA[planet_id]['rashi']
 nat_exalt_lord = RASHI_ATTRIBUTES[nat_exalt_rashi]['lord']
 if is_kendra_from_lagna_or_moon(nat_exalt_lord, chart_data):
 return True
 
 return False
 

 
 
 3. Core Yoga Libraries & Algorithmic Rules
 This section details the programmatic criteria for the primary planetary yogas across Brihat Parashara Hora Shastra, Saravali, and Jataka Tattva.

 
 3.1 Pancha Mahapurusha Yogas
 Formed when a non-luminary planet occupies its own sign, moolatrikona, or exaltation sign while simultaneously located in a Kendra house (1st, 4th, 7th, 10th) from the Ascendant.
 
 
 
 
 Yoga Name
 Planet
 Valid Signs
 Functional Manifestation
 Dysfunctional Triggers
 
 
 
 
 Ruchaka Yoga
 Mars (2)
 1, 8, 10
 High vitality, command, strategic leadership, structural clarity.
 Combust, or aspected by weak Saturn or Rahu.
 
 
 Bhadra Yoga
 Mercury (3)
 3, 6
 Exceptional analytical intellect, flawless algorithmic logic, wealth.
 Combust, or influenced by malefic 8th house connectivity.
 
 
 Hamsa Yoga
 Jupiter (4)
 4, 9, 12
 High ethical standing, universal knowledge, spiritual design authority.
 Combust, or afflicted by Kendradhipati Dosha (functional maleficence).
 
 
 Malavya Yoga
 Venus (5)
 2, 7, 12
 Aesthetic mastery, financial prosperity, high-fidelity creative output.
 Combust, or conjunct a heavily damaged Moon.
 
 
 Sasa Yoga
 Saturn (6)
 7, 10, 11
 Mass governance, enduring systems, infrastructural patience.
 Aspected by Mars or Sun, introducing internal systemic friction.
 
 
 

 def evaluate_pancha_mahapurusha(chart_data):
 target_planets = [2, 3, 4, 5, 6] # Ma, Me, Ju, Ve, Sa
 kendra_houses = [1, 4, 7, 10]
 active_yogas = []
 
 for p in target_planets:
 p_house = chart_data[p]['house']
 p_rashi = chart_data[p]['rashi']
 
 if p_house in kendra_houses:
 is_own = (p_rashi == RASHI_ATTRIBUTES[p_rashi]['lord'])
 is_exalt = (p_rashi == PLANET_EXALTATION_DATA[p]['rashi'])
 
 if is_own or is_exalt:
 status = "Functional"
 if chart_data[p]['is_combust'] or chart_data[p]['in_graha_yuddha_lose']:
 status = "Dysfunctional / Blocked"
 
 active_yogas.append({"yoga_name": get_mahapurusha_name(p), "status": status})
 return active_yogas

 
 3.2 Nabhasa Yogas (Structural Formations)
 Per Saravali and BPHS, Nabhasa Yogas depend strictly on the distribution of planets across houses or signs, completely filtering out specific sign lords. They remain active throughout a subject's life and act as structural framework constants.
 
 A. Asraya Yogas
 
 Musala Yoga: All planets restricted exclusively to Fixed Rashis (2, 5, 8, 11). System output: High stability, slow to pivot, unyielding architecture.
 Nabla Yoga: All planets restricted exclusively to Dual Rashis (3, 6, 9, 12). System output: Versatile, dual-threaded, highly analytical, vulnerable to decision paralysis.
 

 B. Akriti Yogas (Geometric Distribution)
 
 Gada Yoga: All seven planets (Sun through Saturn) must be stationed in two adjacent Kendra houses (e.g., 1st and 4th houses).
 Sakata Yoga: All planets must occupy exclusively the 1st and 7th houses. Yields structural disruptions balanced by extreme bursts of interpersonal focus.
 Vihaga (Bird) Yoga: All planets occupy exclusively the 4th and 10th houses. High executive visibility, dynamic career focus.
 Sringa Yoga: All planets clustered inside Trikona houses (1st, 5th, and 9th). Exceptional design logic, easy structural manifestion of natural talents.
 Hala Yoga: All planets localized in sequential triangular chains across houses (e.g., 2nd, 6th, and 10th houses - the Artha houses).
 

 
 3.3 Raja Yogas and Structural Combinations
 Raja Yogas represent systemic energy transfers between Kendra (action/pivot vectors) and Trikona (fortune/purpose vectors) houses.
 
 def evaluate_parashari_raja_yogas(chart_data):
 kendra_lords = [get_house_lord(h, chart_data) for h in [1, 4, 7, 10]]
 trikona_lords = [get_house_lord(h, chart_data) for h in [1, 5, 9]]
 
 detected_raja_yogas = []
 
 # Check for direct conjunctions or mutual aspects
 for kl in kendra_lords:
 for tl in trikona_lords:
 if kl == tl: 
 continue # Skip self-referential identity
 
 if are_conjunct(kl, tl, chart_data):
 detected_raja_yogas.append({
 "combination": f"Conjunction of Lord {kl} and Lord {tl}",
 "type": "Kendra-Trikona Sambandha Raja Yoga"
 })
 elif have_mutual_aspect(kl, tl, chart_data):
 detected_raja_yogas.append({
 "combination": f"Mutual Aspect between Lord {kl} and Lord {tl}",
 "type": "Kendra-Trikona Drishti Raja Yoga"
 })
 return detected_raja_yogas

 Key Classic Combinations from Jataka Tattva & Saravali
 
 Gaja Kesari Yoga: Jupiter positioned in a Kendra house (1st, 4th, 7th, 10th) measured relative to the Moon's placement. 
 Condition: $((House_{Jupiter} - House_{Moon} + 12) \pmod{12} + 1) \in \{1, 4, 7, 10\}$
 Enhancement: Jupiter is exalted or in its own sign. Neutralization: Jupiter is combust, or the Moon is heavily waned (within 72° of the Sun).
 
 Adhi Yoga (Lagnadhi / Chandradhi): Benefics (Mercury, Jupiter, Venus) positioned in the 6th, 7th, and 8th houses measured from either the Lagna or Moon. Yields exceptional strategic dominance and protection against systemic failures.
 Kemadruma Yoga: Evaluated when there are no planets (excluding Sun, Rahu, and Ketu) in both the 2nd and 12th houses relative to the Moon.
 Condition: $Count(Planets \in \{House_{Moon}-1, House_{Moon}+1\}) == 0$
 Cancellation Pattern: If any planets are in a Kendra from the Ascendant or Moon, the yoga is mathematically cancelled (Kemadruma Bhanga), turning structural vulnerability into resilience.
 
 
 

 
 
 4. Transit (Gochara) Logic Engine & Muhurta Optimization
 For a Muhurta application, a static natal yoga is merely latent capability. Transits act as time-varying wave functions that trigger or suppress these configurations. The structural calculus requires evaluating the transiting coordinate space over the natal frame.

 4.1 Planetary Transit Vedha (Obstruction) Matrix
 Planets in transit distribute positive or negative metrics relative to the natal Moon's rashi. However, if another transiting planet occupies a specific Vedha house position concurrently, the transit's influence is temporarily obstructed.
 
 
 
 
 Planet ID
 Benefic Transit Houses (From Moon)
 Corresponding Obstruction (Vedha) Houses
 Exemptions & Core Rules
 
 
 
 0 (Sun)3, 6, 10, 119, 12, 4, 5No Vedha between Sun and Saturn.
 1 (Moon)1, 3, 6, 7, 10, 115, 9, 12, 2, 4, 8Exempt from native structural limits.
 2 (Mars)3, 6, 1112, 9, 5Direct physical blockages if Vedha active.
 3 (Mercury)2, 4, 6, 8, 10, 115, 3, 9, 1, 8, 12Intellectual processing delays under Vedha.
 4 (Jupiter)2, 5, 7, 9, 1112, 4, 14, 10, 8Note: House 14 maps to House 2 in cyclic wrapping.
 5 (Venus)1, 2, 3, 4, 5, 8, 9, 11, 128, 7, 1, 10, 9, 5, 11, 3, 6Complex interlocking arrays.
 6 (Saturn)3, 6, 1112, 9, 5No Vedha between Saturn and Sun.
 
 

 4.2 The Ashtakavarga Dynamic Filter
 A transiting planet passing through a house that possesses low Ashtakavarga B बिंदु (Bindus) in its specific planetary chart (Bhinnashtakavarga) cannot activate a beneficial natal yoga. The operational algorithm for Muhurta verification is defined below:

 def verify_transit_trigger(transit_planet, target_house, natal_chart, transit_chart):
 # Step 1: Check baseline natal availability of the yoga
 if not natal_chart.has_yoga_relationship(transit_planet):
 return "No Natal Base Connection"
 
 # Step 2: Validate current Bhinnashtakavarga Bindu Count for the planet in that house
 bindu_score = natal_chart.get_ashtakavarga_bindus(transit_planet, target_house)
 if bindu_score < 4:
 return "Ineffective - Insufficient Bindu Energy Field (< 4)"
 
 # Step 3: Parse Vedha Interception Matrix
 if is_obstructed_by_vedha(transit_planet, target_house, transit_chart):
 return "Blocked - Vedha Interception Asserted"
 
 # Step 4: Evaluate transit structural integrity (Combustion/Debilitation)
 if transit_chart[transit_planet]['is_combust']:
 return "Functional Malefic - Distorted by Combustion"
 
 if bindu_score >= 6:
 return "Enhanced / Peak Activation Window"
 
 return "Functional / Effective"
 

 
 
 5. Software Application Logic Engine Architecture
 To program this logic into a real-time computation engine for Muhurta selection, implement a decoupled evaluation pipeline. The calculations process a series of matrices from raw planetary coordinates down to actionable binary state evaluation objects.

 5.1 Complete Structural JSON Data Schema
 Below is the standard JSON layout required by the calculation pipeline to validate all structural conditions from BPHS, Saravali, and Jataka Tattva simultaneously.
 {
 "calculation_metadata": {
 "jd": 2461192.91,
 "ayanamsha_value": 24.23412,
 "timestamp_utc": "2026-06-01T10:19:00Z"
 },
 "ascendant": {
 "rashi": 6,
 "longitude_in_rashi": 14.5212
 },
 "planetary_positions": {
 "0": { "name": "Sun", "rashi": 2, "house": 9, "longitude": 16.2231, "is_retrograde": false, "is_combust": false },
 "1": { "name": "Moon", "rashi": 8, "house": 3, "longitude": 4.1102, "is_retrograde": false, "is_combust": false },
 "4": { "name": "Jupiter", "rashi": 4, "house": 11, "longitude": 5.0021, "is_retrograde": true, "is_combust": false }
 },
 "house_cusps": {
 "1": { "start_rashi": 6, "center": 15.0 },
 "2": { "start_rashi": 7, "center": 15.0 }
 }
}

 5.2 Logic Core Pipeline
 
 Coordinate Processing Stage: Ingest epoch timestamps, apply Ayanamsha correction, compute absolute longitudes ($0^{\circ}$ to $360^{\circ}$), and map planetary coordinates to their respective houses and signs based on the selected house-cusp system (e.g., Shripati or Equal House).
 State Assignment Stage: Evaluate positional properties to flag states such as combustion, retrogradation, Graha Yuddha victory/defeat, and directional strength (Dig Bala).
 Yoga Evaluation Stage: Run the structural array algorithms against the processed state data. This stage maps the spatial rules defined in BPHS and Saravali, processing structural dependencies and cancellations (such as Neechabhanga).
 Transit Verification Stage: Project the target time vectors onto the natal baseline. Calculate the current house positions from the natal Moon, evaluate the dynamic Vedha matrix, check Ashtakavarga thresholds, and output the final structural score.
 
 
 

 
 Architectural Core Specifications Document • Structured for Automated Systems Engineering.