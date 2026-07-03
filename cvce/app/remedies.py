"""Hand-curated practical remedies, grouped by recurring dosha/yoga theme.

Not a literal per-yoga lookup — real horoscopes recur around a handful of
classical affliction *themes* far more often than they produce genuinely
novel combinations, so remedies are grouped by theme (which planet is
afflicted / what kind of affliction) rather than by the ~40 individual
yoga names report_facts.py detects.

Deliberately NOT auto-extracted from the ingested Knowledge Graph book
`Vedic_remedies_by_srath_pdf_free` (Sanjay Rath, "Vedic Remedies") — that
book was checked during authoring (knowledge-graph/raw/
Vedic_remedies_by_srath_pdf_free.md) and is dense with mantra/gemology/
Vaastu prescriptions and "medium" OCR quality, which is exactly the
textbook-theory-remedy pattern this module is meant to avoid surfacing
verbatim. The remedies below are practical, behavioral, and doable —
what someone can actually act on this week — not a chanting schedule.

One genuinely classical principle IS carried over deliberately: the book's
own "Remedial Measures" chapter (p.3-4) names Muhurtha (choosing an
auspicious time to start an activity) as a primary, non-ritual remedy for
a chart's negative indications — "the best remedy is to start the
concerned activity at a most auspicious date and time." That's directly
actionable with this app's own Muhurta tool, so every theme below points
back to it for major decisions falling inside a flagged window.
"""

from __future__ import annotations

REMEDY_THEMES: dict[str, dict] = {
    "saturn_affliction": {
        "label": "Saturn-related strain",
        "remedies": [
            "Saturn rewards structure and punishes disorder — protect a consistent sleep/work routine through this period rather than letting it slide.",
            "Avoid making major irreversible decisions (property, resignation, marriage) in the sharpest weeks of this window if they can reasonably wait; Saturn periods reward patience over speed.",
            "Regular physical labor or exercise gives Saturn's restrictive energy somewhere to go instead of surfacing as pessimism or friction with authority figures.",
            "Check the Muhurta tool before locking in the timing of anything major during this window.",
        ],
    },
    "rahu_ketu_axis": {
        "label": "Rahu-Ketu (nodal) stress",
        "remedies": [
            "Nodal periods amplify shortcuts and speculation — put a 48-hour rule on any high-stakes, fast-moving decision (investments, big purchases, sudden opportunities) before committing.",
            "Keep a paper trail: get agreements in writing and verify sources directly rather than trusting secondhand information, since Rahu periods are classically linked to deception or confusion.",
            "Ketu's detachment can show up as drift or losing interest mid-project — anchor with one grounding daily habit (journaling, meditation, a fixed morning routine) so momentum doesn't quietly slip.",
            "For anything with real stakes, use the Muhurta tool to pick the start time rather than acting on impulse.",
        ],
    },
    "weak_moon": {
        "label": "Afflicted or weak Moon",
        "remedies": [
            "Protect sleep and hydration first — Moon-related strain shows up fastest as mood volatility, and both are the cheapest levers to stabilize it.",
            "Build a regular emotional check-in (a journal, a therapist, a trusted person you actually talk to) rather than waiting for a crisis to process what's building up.",
            "Delay emotionally-loaded decisions until you've had a full night's sleep and 24 hours of distance — this period makes reactive calls costlier than usual.",
            "Keep in closer contact with whoever is your actual support system (family or chosen) through this window; isolation compounds a weak Moon's effects.",
        ],
    },
    "mangal_dosha": {
        "label": "Mars affliction / Mangal Dosha",
        "remedies": [
            "Give Mars's extra energy a physical outlet — regular intense exercise or a martial discipline — before it surfaces as conflict at home or work.",
            "In arguments during this period, build in a deliberate pause before responding; Mars periods make the first reaction sharper than intended.",
            "Avoid rushing big financial or relationship commitments — Mars wants speed, this window rewards a slower deliberate pace instead.",
        ],
    },
    "debilitated_planet": {
        "label": "Debilitated key planet",
        "remedies": [
            "Don't over-invest your identity or self-worth in this planet's life domain while it's debilitated — treat setbacks here as period-specific, not permanent verdicts.",
            "Build redundancy in that domain (a second income stream if it's Mercury/career, a second close relationship if it's Venus, etc.) rather than relying on one point of failure.",
            "Bring in a mentor or second opinion for decisions in that specific domain during this window instead of going solo.",
        ],
    },
    "combust_planet": {
        "label": "Combust planet",
        "remedies": [
            "A combust planet's domain does better out of the spotlight this period — favor collaboration and shared credit over solo, ego-driven pushes.",
            "If this affects a public-facing area (career, reputation), let results speak before actively promoting them; over-asserting during combustion tends to backfire.",
        ],
    },
    "weak_jupiter": {
        "label": "Weak or afflicted Jupiter",
        "remedies": [
            "Deliberately seek out a mentor or teacher this period rather than relying on self-direction — weak Jupiter periods respond well to outside guidance.",
            "Invest time in structured learning (a course, a certification, real study) instead of assuming existing knowledge is enough.",
            "Watch for overconfidence masking the underlying weak judgment signal — get a second opinion before big bets.",
        ],
    },
    "venus_affliction": {
        "label": "Afflicted Venus",
        "remedies": [
            "Put major purchases and relationship commitments through a cooling-off period before finalizing — Venus afflictions often show up as impulsive spending or attachment decisions.",
            "Keep a written budget through this window; financial judgment specifically softens under Venus strain.",
            "Have significant agreements (financial or relational) reviewed by someone else before signing.",
        ],
    },
    "mercury_affliction": {
        "label": "Afflicted Mercury",
        "remedies": [
            "Slow down before sending anything important — afflicted Mercury periods are error-prone for communication and contracts specifically.",
            "Get written agreements reviewed by a second person before signing, especially under time pressure.",
            "If a miscommunication happens, address it directly and promptly rather than letting it compound — this period makes small misunderstandings grow faster than usual.",
        ],
    },
    "sun_affliction": {
        "label": "Afflicted Sun",
        "remedies": [
            "Watch for friction with authority figures (bosses, parents, officials) escalating faster than the situation warrants during this period — de-escalate early.",
            "Don't let identity or self-worth ride entirely on one title, position, or public role right now; this window tests exactly that attachment.",
            "Prioritize consistent health checkups — Sun governs vitality, and afflictions here are worth taking seriously rather than pushing through.",
        ],
    },
    "general": {
        "label": "General guidance",
        "remedies": [
            "Track major decisions made during this window in a simple log, and revisit them in 60-90 days — dasha-driven judgment shifts are easier to see in hindsight than in the moment.",
            "For anything time-sensitive and high-stakes in this window, check the Muhurta tool for a more favorable start time.",
        ],
    },
}

# Planet -> theme, used only as a fallback when a yoga's own text reads as
# challenging (see _reads_negative) and a natural malefic is involved — not
# applied indiscriminately to every yoga that happens to name that planet.
_PLANET_THEME_MAP: dict[str, str] = {
    "Saturn": "saturn_affliction",
    "Rahu": "rahu_ketu_axis",
    "Ketu": "rahu_ketu_axis",
    "Mars": "mangal_dosha",
}

_NEGATIVE_KEYWORDS = (
    "grief", "loss", "losses", "lose", "loses", "lost", "danger", "disease",
    "poverty", "enem", "obstacle", "conflict", "quarrel", "debt", "litigation",
    "accident", "death", "distress", "trouble", "misfortune", "adversity",
    "sorrow", "illness", "suffering", "hindrance", "delay", "insignificant",
    "denial", "deprive", "unhappy", "sin",
)

# Verbs/phrases that flip a following negative word into a positive outcome —
# "overcomes enemies" and "triumph over adversity" are auspicious, not
# afflictions. Without this, a naive keyword match misreads them as negative.
_POSITIVE_FLIP_WORDS = (
    "overcome", "overcomes", "overcoming", "triumph", "triumphs", "victory",
    "success", "win", "wins", "winning", "conquer", "conquers", "defeat",
    "defeats", "free", "rise", "protection", "immune", "resist", "resists",
)


def _reads_negative(text: str) -> bool:
    """True if the yoga's own text reads as classically challenging.

    A negative keyword doesn't count if a "flip" word (overcome, triumph,
    success, etc.) appears within the preceding few words — e.g. "overcomes
    enemies" or "success through adversity" are auspicious framings that
    happen to contain a negative-sounding noun, not an affliction.
    """
    words = (text or "").lower().replace(",", " ").replace(";", " ").split()
    for i, w in enumerate(words):
        if not any(w.startswith(kw) for kw in _NEGATIVE_KEYWORDS):
            continue
        window = words[max(0, i - 3) : i]
        if any(any(fw in ww for fw in _POSITIVE_FLIP_WORDS) for ww in window):
            continue
        return True
    return False


def remedy_for_yoga(
    planets_involved: list[str],
    dignity_by_planet: dict[str, str | None],
    description: str = "",
) -> dict | None:
    """Pick a remedy theme, but only when something in the chart actually
    warrants one.

    Priority order:
    1. A planet genuinely afflicted (debilitated/combust) among those
       involved — the most concrete, specific trigger.
    2. The yoga's own classical text reads as challenging (loss, disease,
       conflict, etc.) AND a natural malefic (Saturn/Mars/Rahu/Ketu) is
       involved — that malefic's theme.
    3. The text reads as challenging but no specific malefic trigger exists
       — general guidance rather than nothing.
    4. Otherwise: None. Positive/neutral yogas (e.g. Harsha Yoga, a
       genuinely auspicious Jupiter combination) get no remedy — attaching
       "weak Jupiter" advice to a yoga where Jupiter is strong would be
       exactly the mismatched, generic output this feature exists to avoid.
    """
    if not planets_involved:
        return None

    for p in planets_involved:
        dignity = dignity_by_planet.get(p)
        if dignity == "debilitated":
            return {"theme": "debilitated_planet", **REMEDY_THEMES["debilitated_planet"]}
        if dignity == "combust":
            return {"theme": "combust_planet", **REMEDY_THEMES["combust_planet"]}

    if _reads_negative(description):
        for p in planets_involved:
            theme_key = _PLANET_THEME_MAP.get(p)
            if theme_key:
                return {"theme": theme_key, **REMEDY_THEMES[theme_key]}
        return {"theme": "general", **REMEDY_THEMES["general"]}

    return None
