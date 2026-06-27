# To build an automated yoga and Muhurta computing engine

To build an automated yoga and Muhurta computing engine, your software must move past static text matching and implement a dynamic, multi-layered relational database and state machine.

Since system restrictions prevent direct binary downloads outside the local environment, I have provided the complete production-grade Python script at the bottom of this response. Running it locally will immediately generate a beautifully styled, corporate-grade .docx file complete with professional typography, custom margins, and clean data architectures.

Below is the complete exhaustive architectural manual, algorithmic logic, and structural matrices required to program your logic engine.

1. Logic Engine Core Architecture & Computational Flow

To accurately compute classical yogas without generating false positives, the logic engine must evaluate planetary states sequentially. A yoga is never a simple "planet in house" check; it is a conditional vector equation.

[1. Positional Inputs (Ephemeris)] 

               │

               ▼

[2. Planetary Dignity Engine (Shadbala / D9)] 

               │

               ▼

[3. Modification Filters (Combustion / War / Rashi Sandhi)] 

               │

               ▼

[4. Combinatorial Matrix (Lords, Aspects, Conjunctions)] 

               │

               ▼

[5. Dynamic Evaluation Engine (Natal Potential vs. Transit Window)]

Required Programmatic Input Vector

For every calculation, the engine requires an array containing the following state parameters for all 9 planets ($P_1$ to $P_9$) plus the Ascendant ($Lagna$):

Longitude ($\lambda$): Float value ($0.0^\circ$ to $359.99^\circ$).

House Placement ($H_n$): Integer (1 to 12) calculated from the chosen house-cusp system (typically Sri Pati or Equal House for classical yogas).

Sign Placement ($R_n$): Integer (1 to 12) representing Aries to Pisces.

Relationship Matrix ($Rel_{nm}$): Temporary and Compound friendships (Mitrata) calculated per chart.

Combustion Status ($Combust_n$): Boolean value based on longitudinal proximity to the Sun.

Planetary War Status ($War_n$): Boolean value flagged if two non-luminary planets sit within $1^\circ 0' 0''$ of each other.

Speed Vector ($\dot{\lambda}$): Identifying Retrogradation ($Retro_n = \text{True/False}$).

2. Mathematical Definition of Planetary Afflictions & Modifications

Before the core yoga rules are run, your application must process the baseline modifications that dictate whether a yoga is Functional/Effective or Dysfunctional/Ineffective.

A. Combustion (Astangata) Logic

A planet loses its external material expression if its longitude falls within the critical orb of the Sun ($\lambda_{\text{Sun}}$).

$$\text{If } |\lambda_n - \lambda_{\text{Sun}}| \le \theta_{\text{combust}}, \text{ then } Combust_n = \text{True}$$

Mars: $17^\circ$

Mercury: $14^\circ$ (Retrograde: $12^\circ$)

Jupiter: $11^\circ$

Venus: $10^\circ$ (Retrograde: $8^\circ$)

Saturn: $15^\circ$

Programmatic Behavior: If $Combust_n = \text{True}$, any auspicious yoga dependent on $Item_n$ is marked as Materially Inert but remains Intellectually/Spiritually Active.

B. Planetary War (Graha Yuddha) Logic

Applies only to non-luminary planets (Mars, Mercury, Jupiter, Venus, Saturn).

$$\text{If } |\lambda_m - \lambda_n| < 1.0^\circ \text{ and } m, n \in \{\text{Mars, Mercury, Jupiter, Venus, Saturn}\}$$

Winner Determination: The planet with the higher declination or, classically, the lower longitude within the sign wins the war ($\text{Status} = \text{Victor}$).

Loser Condition: The planet with the higher longitude loses ($\text{Status} = \text{Defeated}$).

Programmatic Behavior: The defeated planet's positive yogas are completely neutralized, and its Dasha periods trigger systemic structural instability.

C. Rashi Sandhi & Bhava Sandhi Logic

Planets sitting on the structural boundary lines between signs or houses cannot hold structural integrity.

$$\text{If } (\lambda_n \pmod{30^\circ}) \le 1.0^\circ \text{ or } (\lambda_n \pmod{30^\circ}) \ge 29.0^\circ, \text{ then } Sandhi_n = \text{True}$$

Programmatic Behavior: The structural potency coefficient ($C_{\text{potency}}$) of the planet drops to $0.0$. The yoga is mathematically Ineffective.

3. The Exhaustive Yoga Combinatorial Directory

The following database matrix dictates the rules for formation, amplification, and structural functional statuses across the three foundational texts.

A. Pancha Mahapurusha Yogas (Source: BPHS / Saravali)

Applies only when planets occupy Angular houses ($H_n \in \{1, 4, 7, 10\}$) from the Ascendant.

Yoga Name

Planet (Pn​)

Essential Dignity Conditions (Rn​)

Functional Target / Output

Modification & Disruption Rules

Ruchaka

Mars

Own Sign ($1, 8$) or Exalted ($10$)

Executive execution, military command, physical courage.

Neutralized if: Mars conjoins Rahu/Ketu. Enhanced if: Aspected by a strong 9th Lord.

Bhadra

Mercury

Own Sign ($3, 6$) or Exalted ($6$)

Supreme commercial strategy, logic, advanced systems design.

Neutralized if: Combust by Sun. Ineffective if: Moon sits in 8th house, causing mental exhaustion.

Hamsa

Jupiter

Own Sign ($9, 12$) or Exalted ($4$)

Institutional authority, moral architecture, jurisprudence.

Neutralized if: Subject to Kendradhipati Dosha (acting as a functional malefic for Gemini/Virgo ascendants).

Malavya

Venus

Own Sign ($2, 7$) or Exalted ($12$)

High-fidelity design, media assets, strategic negotiation.

Neutralized if: Afflicted by Saturn or Mars in the Navamsha (D9) chart.

Sasa

Saturn

Own Sign ($10, 11$) or Exalted ($7$)

Mass governance, structural execution, systematic scaling.

Enhanced if: Sits in the 10th house from Ascendant. Dysfunctional if: Sun aspects, creating institutional friction.

B. Nabhasa Yogas (Source: BPHS / Saravali)

These structural configurations shape the entire chart. They do not depend on Dashas; they represent permanent baseline code running continuously.

1. Asraya Yogas (Sign-Based Spatial Layout)

Rajju Yoga Formation: All 7 visible planets occupy Moveable Signs ($1, 4, 7, 10$).

Logic Engine Check: all(Sign[p] in [1, 4, 7, 10] for p in VisiblePlanets)

Functional Output: High operational agility, constant geographical mobility, highly fluctuating asset liquidity.

Musala Yoga Formation: All 7 visible planets occupy Fixed Signs ($2, 5, 8, 11$).

Logic Engine Check: all(Sign[p] in [2, 5, 8, 11] for p in VisiblePlanets)

Functional Output: Deep structural stability, asset preservation, resistance to external pivots.

Nala Yoga Formation: All 7 visible planets occupy Dual Signs ($3, 6, 9, 12$).

Logic Engine Check: all(Sign[p] in [3, 6, 9, 12] for p in VisiblePlanets)

Functional Output: Multi-threaded cognitive processing, continuous intellectual development, low asset solidification.

2. Akriti Yogas (Geometric Mapping Patterns)

Sakata Yoga: All 7 visible planets sit strictly in the 1st and 7th houses.

Logic Engine Check: all(House[p] in [1, 7] for p in VisiblePlanets)

Functional Output: A cyclical life curve resembling a rotating wheel. Sudden wealth followed by sudden structural realignments.

Vihaga Yoga: All 7 visible planets sit strictly in the 4th and 10th houses.

Logic Engine Check: all(House[p] in [4, 10] for p in VisiblePlanets)

Functional Output: Publicly exposed lifestyle, constant career scaling, high home-base volatility.

Gada Yoga: All planets occupy two adjacent Kendra houses (e.g., 1st and 4th, 4th and 7th, 7th and 10th, 10th and 1st).

Logic Engine Check: Iterative verification of adjacent pairs of Kendra houses.

Functional Output: Monomaniacal focus on building early-stage defense and security assets.

3. Sankhya Yogas (Distribution/Density Vectors)

Evaluated only if no structural Asraya or Akriti configurations are triggered.

Vallaki Yoga: Planets distributed across exactly 7 distinct signs. (Polymath intellect, high-fidelity creative output).

Dama Yoga: Planets distributed across exactly 6 distinct signs. (High public safety net, community asset builder).

Pasa Yoga: Planets distributed across exactly 5 distinct signs. (Extensive structural corporate networks).

Kedara Yoga: Planets distributed across exactly 4 distinct signs. (Tangible real-estate holdings, heavy infrastructure focus).

Sula Yoga: Planets packed tightly into exactly 3 distinct signs. (Single-minded execution, high friction, severe boundary structures).

Yuga Yoga: Planets packed tightly into exactly 2 distinct signs. (Extreme duality, structural restrictions, unpredictable public standing).

Gola Yoga: All 7 visible planets compressed into a single sign. (Severe systemic limitations, extreme isolated genius, or absolute resource exhaustion).

C. Jataka Tattva Core Combinations (Source: Mahadeva)

The Jataka Tattva breaks down formulas using micro-elemental conditions (Tattvas). It relies on precise math involving house-lord combinations.

Vipareeta Raja Yoga (Reverse Structural Elevation):

Logic Rule: The 6th, 8th, or 12th house lord must occupy the 6th, 8th, or 12th house, while being completely unassociated with Kendra/Trikona lords.

Algorithmic Target: if House[LordOf(6)] in [6, 8, 12] and not AspectedByKendraLords(LordOf(6)): Status = Functional

Output: Converts competitor vulnerabilities, institutional errors, or broad systemic crashes into immediate status elevation.

Dhana Yoga (Capital Realization Matrix):

Logic Rule: Mutual combinations, aspects, or exchanges between the 1st, 2nd, 5th, 9th, and 11th house lords.

Mathematical Indexing: Generate a relational score between these nodes. If the connectivity value $V_{\text{connect}} \ge 3$, the yoga is flagged as Highly Profitable.

4. Architectural Rules for Modification & Cancellation

Your logic engine must apply validation layers to prevent dead code from running.

Is Natal Combination Present?

          │

          ├──► NO  ──► Terminate Check

          │

          └──► YES ──► Check Combustion, War, and Affliction

                                 │

                                 ├──► Fails Dignity ──► Mark Dysfunctional

                                 │

                                 └──► Passes ───────► Evaluate Cancellation Factors (e.g., Neechabhanga)

                                                                 │

                                                                 └──► Valid Cancellation? ──► Mark Re-activated (Auspicious)

A. Neechabhanga Raja Yoga (Algorithmic Cancellation Architecture)

When a planet is debilitated ($R_n = \text{Debilitation Sign}$), its performance coefficient is initially set to $-1.0$. Your engine must run a loop checking five validation parameters to see if this weakness converts into a functional strength:

Python

def check_neechabhanga(planet, chart):

    if not chart.is_debilitated(planet):

        return False

        

    deb_sign = chart.get_sign(planet)

    dispositor = chart.get_sign_lord(deb_sign)

    exaltation_planet = chart.get_exaltation_planet(deb_sign)

    exaltation_dispositor = chart.get_sign_lord(chart.get_exaltation_sign(planet))

    

    # Rule 1: Is the dispositor in a Kendra from Ascendant or Moon?

    if chart.is_in_kendra_from_lagna_or_moon(dispositor):

        return True

        

    # Rule 2: Is the exaltation planet in a Kendra from Ascendant or Moon?

    if chart.is_in_kendra_from_lagna_or_moon(exaltation_planet):

        return True

        

    # Rule 3: Is the lord of the planet's exaltation sign in a Kendra from Ascendant or Moon?

    if chart.is_in_kendra_from_lagna_or_moon(exaltation_dispositor):

        return True

        

    # Rule 4: Is the debilitated planet directly aspected by its own dispositor?

    if chart.has_aspect(from_planet=dispositor, to_planet=planet):

        return True

        

    return False

If check_neechabhanga returns True, update the planetary status:

$$\text{Potency}_{\text{planet}} = | \text{Initial Deficit} | \times 1.5$$

The text commands that this triggers an ultimate architectural turnaround: early-stage operational friction followed by massive scaling.

5. Dynamic Muhurta Logic: The Transit Validation Engine

To calculate a true Muhurta (Inception Window) or predict the exact Fruition Timeline of a natal yoga, your logic engine must evaluate the intersection of the natal blueprint with real-time transit data.

       [ NATAL BLUEPRINT ]                           [ REAL-TIME TRANSIT ]

   Static potential code stored                Continuous stream of planetary coordinates

                 │                                           │

                 └───────────────────┬───────────────────────┘

                                     ▼

                    [ THE DASHA / BHUKTI EXECUTIVE GATEWAY ]

                        Is the time window open? (True)

                                     │

                                     ▼

                      [ THE GEOGRAPHIC CATALYST MATRIX ]

                 Do transit longitudes aspect or conjoin natal nodes?

                                     │

                                     ▼

                              [ FRUITION POINT ]

The Three-Tier Logic Matrix

The Structural Blueprint (Natal Chart): Compiles the native's capacity code. If a yoga does not exist in the natal chart, no transit configuration can trigger it.

The Executive Window (Vimshottari Dasha): The time coordinate framework. If a native has a potent Bhadra Yoga, it remains dormant until the Dasha or Bhukti lord matches the participating planets.

The Trigger Mechanism (Gochara/Transit): The spatial coordinate catalyst. Material validation occurs when transiting planets pass over or form a exact $180^\circ$, $120^\circ$, or $90^\circ$ aspect to the exact natal longitudes ($\pm 3^\circ 20'$ orb).

Algorithmic Logic for Timing Engine Execution

Python

def evaluate_fruition_state(natal_yoga, current_dasha, transit_positions):

    # Step 1: Ensure the time gateway is unlocked

    if current_dasha.major_lord not in natal_yoga.key_planets:

        if current_dasha.sub_lord not in natal_yoga.key_planets:

            return "Dormant (Time Gateway Closed)"

            

    # Step 2: Check transit coordinate intersections

    for t_planet in transit_positions.planets:

        for n_planet in natal_yoga.key_planets:

            orb = abs(t_planet.longitude - n_planet.natal_longitude)

            

            # Exact aspect or conjunction trigger

            if orb <= 3.33 or abs(orb - 180.0) <= 3.33:

                if t_planet.dignity_score > 0 and not t_planet.is_combust:

                    return "ACTIVE FRUITION: High Material/Operational Execution Window"

                else:

                    return "MUTED FRUITION: Structural Obstacles Present In External Environment"

                    

    return "Trigger Pending (Awaiting Transit Conjunction)"

6. Document Automation Engine (Python Source Code)

Run this Python script locally to generate the complete corporate-grade document structure with precise page margins and professional table formatting.

Python

import docx

from docx import Document

from docx.shared import Inches, Pt, RGBColor

from docx.enum.text import WD_ALIGN_PARAGRAPH

from docx.enum.table import WD_TABLE_ALIGNMENT

from docx.oxml import parse_xml, OxmlElement

from docx.oxml.ns import nsdecls, qn

def create_jyotish_engine_document():

    doc = Document()

    

    # Configure strict professional margins

    for section in doc.sections:

        section.top_margin = Inches(1)

        section.bottom_margin = Inches(1)

        section.left_margin = Inches(1)

        section.right_margin = Inches(1)

    # Color Palette Specifications

    COLOR_PRIMARY_HEX = "1B365D"    # Corporate Navy

    COLOR_SECONDARY_HEX = "4A777A"  # Muted Teal

    COLOR_LIGHT_BG_HEX = "F4F6F8"   # Subtle Gray

    

    COLOR_PRIMARY = RGBColor(27, 54, 93)

    COLOR_SECONDARY = RGBColor(74, 119, 122)

    COLOR_TEXT = RGBColor(43, 43, 43)

    # Configure Default Base Typographic Style

    style_normal = doc.styles['Normal']

    style_normal.font.name = 'Arial'

    style_normal.font.size = Pt(10.5)

    style_normal.font.color.rgb = COLOR_TEXT

    style_normal.paragraph_format.line_spacing = 1.25

    style_normal.paragraph_format.space_after = Pt(6)

    def set_cell_background(cell, color_hex):

        shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')

        cell._tc.get_or_add_tcPr().append(shading_elm)

    def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):

        tcPr = cell._tc.get_or_add_tcPr()

        tcMar = OxmlElement('w:tcMar')

        for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:

            node = OxmlElement(m)

            node.set(qn('w:w'), str(val))

            node.set(qn('w:type'), 'dxa')

            tcMar.append(node)

        tcPr.append(tcMar)

    def add_heading_1(text):

        p = doc.add_paragraph()

        p.paragraph_format.space_before = Pt(20)

        p.paragraph_format.space_after = Pt(8)

        p.paragraph_format.keep_with_next = True

        run = p.add_run(text)

        run.font.size = Pt(14)

        run.font.bold = True

        run.font.color.rgb = COLOR_PRIMARY

        return p

    def add_heading_2(text):

        p = doc.add_paragraph()

        p.paragraph_format.space_before = Pt(14)

        p.paragraph_format.space_after = Pt(4)

        p.paragraph_format.keep_with_next = True

        run = p.add_run(text)

        run.font.size = Pt(11.5)

        run.font.bold = True

        run.font.color.rgb = COLOR_SECONDARY

        return p

    # Title Block

    p_title = doc.add_paragraph()

    p_title.paragraph_format.space_before = Pt(10)

    p_title.paragraph_format.space_after = Pt(2)

    run_title = p_title.add_run("JYOTISH YOGA LOGIC ENGINE MANUAL")

    run_title.font.size = Pt(22)

    run_title.font.bold = True

    run_title.font.color.rgb = COLOR_PRIMARY

    p_sub = doc.add_paragraph()

    p_sub.paragraph_format.space_after = Pt(24)

    run_sub = p_sub.add_run("Programmatic Specifications for BPHS, Jataka Tattva, and Saravali Yoga Formulations")

    run_sub.font.size = Pt(11)

    run_sub.font.italic = True

    run_sub.font.color.rgb = COLOR_SECONDARY

    # Section 1

    add_heading_1("1. Architectural Overview & Compute Pipelines")

    doc.add_paragraph(

        "This specification sheet defines the mathematical foundations and conditional criteria needed "

        "to translate classical Vedic astrology configurations into deterministic code. It prevents "

        "false positives by evaluating planetary states sequentially using real-time ephemeris input vectors."

    )

    # Section 2

    add_heading_1("2. Mathematical Modifiers & Filters")

    doc.add_paragraph(

        "A planetary yoga can only be considered functional if it passes baseline modification filtering. "

        "Combustion, planetary war (Graha Yuddha), and positional boundaries (Rashi Sandhi) can change "

        "a planet's performance coefficient from active to inert before core combinations are processed."

    )

    # Section 3: Master Table Configuration

    add_heading_1("3. Core Classical Yoga Permutation Directory")

    

    yoga_data = [

        ["Pancha Mahapurusha", "Ruchaka Yoga", "Mars in Kendra (1, 4, 7, 10) in Own/Exalted sign. Commands high physical energy and operational focus."],

        ["Pancha Mahapurusha", "Bhadra Yoga", "Mercury in Kendra in Own/Exalted sign. Drives strategic commerce, software architectures, logic."],

        ["Pancha Mahapurusha", "Hamsa Yoga", "Jupiter in Kendra in Own/Exalted sign. Institutional authority, jurisprudence, academic design."],

        ["Pancha Mahapurusha", "Malavya Yoga", "Venus in Kendra in Own/Exalted sign. High-fidelity design, diplomatic mastery, asset management."],

        ["Pancha Mahapurusha", "Sasa Yoga", "Saturn in Kendra in Own/Exalted sign. Systematic scaling, multi-threaded workforce coordination."],

        ["Nabhasa (Asraya)", "Rajju Yoga", "All 7 planets in Moveable signs. High operational pivot speeds, geographical fluidity."],

        ["Nabhasa (Asraya)", "Musala Yoga", "All 7 planets in Fixed signs. Deep structural asset retention, structural resistance to change."],

        ["Nabhasa (Asraya)", "Nala Yoga", "All 7 planets in Dual signs. Conceptual flexibility, variable execution paths, multi-threaded analysis."],

        ["Prosperity & Power", "Vipareeta Raja", "6/8/12 lords sitting strictly within 6/8/12 houses. Converts external crashes into rapid system ascents."],

        ["Prosperity & Power", "Neechabhanga", "Debilitation canceled by sign/exaltation lord sitting in Kendra houses from Lagna or Moon."]

    ]

    table = doc.add_table(rows=len(yoga_data) + 1, cols=3)

    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    col_widths = [Inches(1.5), Inches(1.5), Inches(3.5)]

    hdr_cells = table.rows[0].cells

    hdr_cells[0].text = "Category"

    hdr_cells[1].text = "Yoga Name"

    hdr_cells[2].text = "Programmatic Definition & Output Profile"

    for cell in hdr_cells:

        set_cell_background(cell, COLOR_PRIMARY_HEX)

        set_cell_margins(cell)

        p = cell.paragraphs[0]

        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        run = p.runs[0]

        run.font.bold = True

        run.font.color.rgb = RGBColor(255, 255, 255)

        run.font.size = Pt(9.5)

    for r_idx, row_data in enumerate(yoga_data):

        row_cells = table.rows[r_idx + 1].cells

        bg_color = COLOR_LIGHT_BG_HEX if r_idx % 2 == 1 else "FFFFFF"

        for c_idx, text in enumerate(row_data):

            row_cells[c_idx].text = text

            set_cell_background(row_cells[c_idx], bg_color)

            set_cell_margins(row_cells[c_idx])

            p = row_cells[c_idx].paragraphs[0]

            p.runs[0].font.size = Pt(9)

            if c_idx < 2:

                p.runs[0].font.bold = True

    for row in table.rows:

        for idx, width in enumerate(col_widths):

            row.cells[idx].width = width

    # Section 4

    add_heading_1("4. Dynamic Muhurta & Transit Intersection Validation")

    doc.add_paragraph(

        "A natal configuration represents a chart's potential capacity, but its execution window is unlocked "

        "by the Vimshottari Dasha state machine. Physical activation occurs when real-time transiting "

        "longitudes cross the exact natal coordinates within a strict 3-degree, 20-minute operational orb."

    )

    output_path = "Jyotish_Yoga_Logic_Engine_Manual.docx"

    doc.save(output_path)

    print(f"Document built successfully at: {output_path}")

if __name__ == "__main__":

    create_jyotish_engine_document()