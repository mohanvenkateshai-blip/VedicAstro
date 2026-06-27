"""
Vedic Prediction Engine — Main Synthesis Module

Combines Panchanga + Gochar + Dasha + Yoga predictions into a unified output.
Resolves contradictions between texts using priority rules (BPHS > PD > HS > GPD).

Usage:
    from vedic_engine import VedicPredictor
    
    engine = VedicPredictor()
    result = engine.predict(
        date="2026-06-23", time="12:00",
        lat=12.30, lon=76.65, tz=5.5,
        janma_rashi="Leo", janma_nakshatra="Purva Phalguni",
        birth_date="1975-04-22", birth_time="19:15",
        birth_lat=12.2958, birth_lon=76.6394, birth_tz=5.5,
    )
    print(result.summary)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..core.panchanga import compute_panchanga, PanchangaResult, RASHIS
from ..prediction.gochar import compute_gochar, GocharResult
from ..prediction.dasha import compute_dasha, DashaResult
from ..prediction.yoga import detect_yogas, DetectedYoga
from ..prediction.ashtakavarga import compute_ashtakavarga, compute_transit_ashtakavarga, AshtakavargaResult
from ..prediction.muhurta_yogas import evaluate_muhurta_yogas, muhurta_yogas_to_dict, MuhurtaYogaResult


@dataclass
class VedicPrediction:
    """Complete unified prediction output."""
    # Input
    query_date: str
    query_time: str
    query_lat: float
    query_lon: float
    query_tz: float

    # Natal info
    janma_rashi: Optional[str] = None
    janma_nakshatra: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_lat: Optional[float] = None
    birth_lon: Optional[float] = None
    birth_tz: Optional[float] = None

    # Computed
    panchanga: Optional[PanchangaResult] = None
    gochar: Optional[GocharResult] = None
    dasha: Optional[dict] = None
    yogas: Optional[list] = None
    ashtakavarga: Optional[dict] = None
    muhurta_yogas: Optional[dict] = None

    # Synthesis
    overall_verdict: str = "neutral"
    overall_score: int = 0
    summary: str = ""
    detailed_predictions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)

    # Metadata
    engine_version: str = "1.0.0"
    computed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class VedicPredictor:
    """Main prediction engine combining all modules."""

    def __init__(self):
        self.version = "1.0.0"

    def predict(self,
                date: str = None, time: str = "12:00",
                lat: float = 12.30, lon: float = 76.65, tz: float = 5.5,
                janma_rashi: str = None, janma_nakshatra: str = None,
                birth_date: str = None, birth_time: str = None,
                birth_lat: float = None, birth_lon: float = None,
                birth_tz: float = None, birth_moon_lon: float = None,
                natal_sign: dict = None) -> VedicPrediction:
        """Run the complete prediction pipeline.

        Args:
            date: Query date 'YYYY-MM-DD' (default: today)
            time: Query time 'HH:MM'
            lat, lon, tz: Query location
            janma_rashi: Native's Moon sign
            janma_nakshatra: Native's birth star
            birth_date, birth_time: Native's birth details
            birth_lat, birth_lon, birth_tz: Birth location
            natal_sign: dict of planet → rashi index (0=Aries)
        """
        if date is None:
            now = datetime.now()
            date = f"{now.year}-{now.month:02d}-{now.day:02d}"

        result = VedicPrediction(
            query_date=date, query_time=time,
            query_lat=lat, query_lon=lon, query_tz=tz,
            janma_rashi=janma_rashi, janma_nakshatra=janma_nakshatra,
            birth_date=birth_date, birth_time=birth_time,
            birth_lat=birth_lat, birth_lon=birth_lon, birth_tz=birth_tz,
        )

        # 1. Compute Panchanga (always)
        result.panchanga = compute_panchanga(date, time, lat, lon, tz)

        # 1b. Muhurta vara/tithi yogas (graph-backed when available)
        if result.panchanga:
            graph_hits = None
            try:
                from graph_rag.muhurta_rules_provider import active_muhurta_rules
                rules = active_muhurta_rules()
                if rules and result.panchanga:
                    p = result.panchanga
                    tip = p.tithi_num if p.tithi_num <= 15 else (
                        15 if p.tithi_num == 30 else p.tithi_num - 15
                    )
                    graph_hits = rules.yoga_hits(
                        ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"][
                            ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].index(p.weekday)
                        ],
                        p.tithi_group,
                        tip,
                    )
            except Exception:
                graph_hits = None
            my = evaluate_muhurta_yogas(
                result.panchanga.weekday,
                result.panchanga.tithi_num,
                result.panchanga.nakshatra,
                graph_hits=graph_hits,
            )
            result.muhurta_yogas = muhurta_yogas_to_dict(my)

        # 2. Compute Gochar / Transit (requires Janma Rashi)
        if janma_rashi:
            result.gochar = compute_gochar(
                date, time, lat, lon, tz,
                janma_rashi=janma_rashi,
                janma_nakshatra=janma_nakshatra,
                natal_sign=natal_sign,
            )

        # 3. Compute Dasha (requires birth date)
        if birth_date and janma_nakshatra:
            result.dasha = compute_dasha(
                birth_date, birth_time or "12:00",
                birth_nakshatra=janma_nakshatra,
                birth_moon_lon=birth_moon_lon,
                query_date=date,
            )

        # 4. Compute Yogas (requires birth chart)
        if natal_sign and isinstance(natal_sign, dict) and natal_sign:
            # Get lagna index — either from natal_sign or from ashtakavarga
            lagna_idx = natal_sign.get("Lagna", 0)
            result.yogas = detect_yogas(
                {k: v for k, v in natal_sign.items() if k != "Lagna"},
                lagna_idx,
            )

        # 5. Compute Ashtakavarga (requires birth chart)
        if natal_sign and isinstance(natal_sign, dict) and natal_sign:
            lagna_idx = natal_sign.get("Lagna", 0)
            akv = compute_ashtakavarga(
                {k: v for k, v in natal_sign.items() if k != "Lagna"},
                lagna_idx,
            )
            result.ashtakavarga = compute_transit_ashtakavarga(akv, date, time, lat, lon, tz)

        # 6. Synthesize
        result = self._synthesize(result)

        return result

    def _synthesize(self, r: VedicPrediction) -> VedicPrediction:
        """Synthesize all modules into coherent predictions."""

        # Panchanga summary
        if r.panchanga:
            p = r.panchanga
            r.detailed_predictions.append({
                "domain": "Panchanga",
                "items": [
                    f"Tithi: {p.tithi_name} ({p.tithi_paksha}) — {p.tithi_group} group — Lord {p.tithi_lord} — {p.tithi_verdict}",
                    f"Vaar: {p.weekday} — Lord {['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'][['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].index(p.weekday)]}",
                    f"Nakshatra: {p.nakshatra} — {p.nakshatra_nature} nature — Lord {p.nakshatra_lord}",
                    f"Yoga: {p.yoga_name} — {p.yoga_nature} — {p.yoga_verdict}",
                    f"Karana: {p.karana_name} — {p.karana_verdict}",
                    f"Sunrise: {p.sunrise:.2f}h · Sunset: {p.sunset:.2f}h",
                ]
            })

        # Gochar summary
        if r.gochar:
            g = r.gochar
            good = [p for p in g.planet_predictions if p.verdict == "shubh"]
            bad = [p for p in g.planet_predictions if p.verdict == "ashubh"]

            gochar_items = []
            for pp in g.planet_predictions:
                if pp.house_from_janma is not None:
                    status = "✓" if pp.verdict == "shubh" else ("✗" if pp.verdict == "ashubh" else "·")
                    gochar_items.append(
                        f"{pp.planet} in {pp.rashi} ({pp.nakshatra}) — {pp.house_from_janma}th from Janma Rasi — {status} {pp.house_quality}"
                    )

            r.detailed_predictions.append({
                "domain": "Gochar (Transit)",
                "score": g.overall_score,
                "verdict": g.overall_verdict,
                "items": gochar_items,
            })

            if g.sade_sati:
                r.warnings.append(f"⚠ Sade Sati {g.sade_sati['phase']} phase: {g.sade_sati['effect']}")
            if g.moorthy:
                r.detailed_predictions.append({
                    "domain": "Moorthy Nirnaya",
                    "items": [f"Moon in {g.moorthy['house']}th from Janma Rasi — {g.moorthy['name']}: {g.moorthy['description']}"]
                })
            if g.tara_balam:
                t = g.tara_balam
                r.detailed_predictions.append({
                    "domain": "Tara Balam",
                    "items": [f"{t['name']} — count {t['count']} from Janma Nak — {t['verdict']} (Paryaya {t['paryaya']})"]
                })

        # Muhurta vara/tithi yogas
        if r.muhurta_yogas:
            my = r.muhurta_yogas
            items = [my.get("summary", "")]
            for hit in my.get("active", [])[:6]:
                items.append(f"{hit.get('name')}: {hit.get('detail')} [{hit.get('source', '')}]")
            r.detailed_predictions.append({
                "domain": "Muhurta Yogas",
                "verdict": my.get("overall", "neutral"),
                "score": my.get("score", 0),
                "items": [i for i in items if i],
            })

        # Overall score
        scores = []
        if r.panchanga:
            pv = {"shubh": 5, "neutral": 0, "ashubh": -5}
            scores.append(pv.get(r.panchanga.tithi_verdict, 0))
            scores.append(pv.get(r.panchanga.yoga_verdict, 0))
            scores.append(pv.get(r.panchanga.karana_verdict, 0))
        if r.muhurta_yogas:
            scores.append(r.muhurta_yogas.get("score", 0))
        if r.gochar:
            scores.append(r.gochar.overall_score)
        if r.dasha:
            scores.append(r.dasha.dasha_score)

        r.overall_score = sum(scores) if scores else 0
        if r.overall_score >= 20:
            r.overall_verdict = "Highly Auspicious"
        elif r.overall_score >= 10:
            r.overall_verdict = "Favourable"
        elif r.overall_score >= 0:
            r.overall_verdict = "Mixed"
        elif r.overall_score >= -10:
            r.overall_verdict = "Caution"
        else:
            r.overall_verdict = "Inauspicious"

        # Dasha summary
        if r.dasha:
            d = r.dasha
            items = []
            if d.current_mahadasha:
                items.append(f"Mahadasha: {d.current_mahadasha.planet} ({d.current_mahadasha.start_date} → {d.current_mahadasha.end_date})")
            if d.current_antardasha:
                items.append(f"Antardasha: {d.current_antardasha.planet} ({d.current_antardasha.start_date} → {d.current_antardasha.end_date})")
            if d.yogini_start:
                items.append(f"Yogini: {d.yogini_start.yogini} ({d.yogini_start.nature})")
            r.detailed_predictions.append({
                "domain": "Dasha",
                "score": d.dasha_score,
                "items": items,
            })

        # Yoga summary
        if r.yogas:
            yoga_items = []
            for y in r.yogas:
                icon = "✦" if y.benefic else "▲"
                yoga_items.append(f"{icon} {y.name} ({y.category}): {y.description[:80]}")
            r.detailed_predictions.append({
                "domain": "Yogas",
                "items": yoga_items,
            })

        # Ashtakavarga summary
        if r.ashtakavarga:
            akv = r.ashtakavarga
            r.detailed_predictions.append({
                "domain": "Ashtakavarga",
                "items": [
                    f"SAV total: {akv.total_sav} (expect 337) — {'✓' if akv.total_sav == 337 else '⚠'}",
                    f"Moon transit: {akv.moon_transit_bindus} bindus in {RASHIS[akv.lagna_sign_idx] if hasattr(akv, 'lagna_sign_idx') else '—'} — {akv.moon_transit_verdict}",
                ],
            })

        # Build summary
        lines = []
        lines.append(f"═══ VEDIC PREDICTION ENGINE v{self.version} ═══")
        lines.append(f"Date: {r.query_date} {r.query_time} · Lat {r.query_lat}° Lon {r.query_lon}° UTC{r.query_tz:+}")
        lines.append(f"Overall: {r.overall_verdict} (Score: {r.overall_score})")
        if r.janma_rashi:
            lines.append(f"Natal: {r.janma_rashi} / {r.janma_nakshatra or '—'}")

        if r.panchanga:
            lines.append("")
            lines.append("—— Panchanga ——")
            lines.append(
                f"Tithi: {r.panchanga.tithi_name} {r.panchanga.tithi_paksha} | Vaar: {r.panchanga.weekday} | Nak: {r.panchanga.nakshatra} | Yoga: {r.panchanga.yoga_name} | Karana: {r.panchanga.karana_name}")
            lines.append(
                f"Sunrise: {r.panchanga.sunrise:.2f}h | Sunset: {r.panchanga.sunset:.2f}h")

        if r.gochar and r.gochar.planet_predictions:
            lines.append("")
            lines.append("—— Transit (Gochar) ——")
            for pp in r.gochar.planet_predictions:
                if pp.house_from_janma is not None:
                    icon = "✓" if pp.verdict == "shubh" else ("✗" if pp.verdict == "ashubh" else "·")
                    lines.append(
                        f"  {pp.planet}: {pp.rashi} ({pp.nakshatra}) — {pp.house_from_janma}th from Janma Rasi — {icon} {pp.house_quality}"
                    )
                else:
                    lines.append(f"  {pp.planet}: {pp.rashi} ({pp.nakshatra})")

        if r.dasha:
            lines.append("")
            lines.append("—— Dasha ——")
            lines.append(r.dasha.summary)

        if r.yogas:
            lines.append("")
            lines.append("—— Yogas Detected ——")
            for y in r.yogas[:5]:
                icon = "✦" if y.benefic else "▲"
                lines.append(f"  {icon} {y.name}: {y.description[:80]}")

        if r.warnings:
            lines.append("")
            lines.append("—— Warnings ——")
            for w in r.warnings:
                lines.append(f"  {w}")

        r.summary = "\n".join(lines)

        # Generate transit summary paragraph
        r.transit_summary = _generate_transit_summary(r)

        return r


def _generate_transit_summary(r: VedicPrediction) -> str:
    """Generate a brief natural-language paragraph describing the transit day's expected results."""

    def ordinal(n: int) -> str:
        if 11 <= (n % 100) <= 13:
            return f"{n}th"
        return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n%10]}"

    parts = []

    # Overall verdict
    verdict_desc = {
        "Highly Auspicious": "This is an exceptionally favourable day",
        "Favourable": "This is a favourable day",
        "Mixed": "This is a mixed day",
        "Caution": "This is a day requiring caution",
        "Inauspicious": "This is an inauspicious day",
    }
    parts.append(f"{verdict_desc.get(r.overall_verdict, 'A')} (score {r.overall_score}).")

    # Panchanga highlight
    if r.panchanga:
        p = r.panchanga
        tithi_str = f"The {p.tithi_name} tithi ({p.tithi_paksha} paksha, {p.tithi_group} group)"
        if p.tithi_verdict == "shubh":
            tithi_str += " supports new initiatives and growth"
        elif p.tithi_verdict == "ashubh":
            tithi_str += " advises restraint — best suited for cleansing and completion activities"
        parts.append(tithi_str + ".")

        nak_str = f"The Moon transits {p.nakshatra} ({p.nakshatra_nature} nature, {p.nakshatra_lord}-ruled)"
        parts.append(nak_str + ".")

    # Transit highlights
    if r.gochar and r.gochar.planet_predictions:
        good = [p for p in r.gochar.planet_predictions if p.verdict == "shubh" and p.house_from_janma is not None]
        bad = [p for p in r.gochar.planet_predictions if p.verdict == "ashubh" and p.house_from_janma is not None]

        if good:
            names = [f"{p.planet} (in {ordinal(p.house_from_janma)} from Janma Rasi)" for p in good[:3]]
            parts.append(f"Favourable transits: {', '.join(names)}.")
        if bad:
            names = [f"{p.planet} (in {ordinal(p.house_from_janma)})" for p in bad[:3]]
            parts.append(f"Challenging transits: {', '.join(names)}.")

        if r.gochar.sade_sati:
            parts.append(f"Sade Sati is in its {r.gochar.sade_sati['phase']} phase — {r.gochar.sade_sati['effect'].lower()}.")

    # Dasha context
    if r.dasha and r.dasha.current_mahadasha:
        d = r.dasha
        parts.append(f"You are in {d.current_mahadasha.planet} Mahadasha with {d.current_antardasha.planet} Antardasha.")

    # Yoga context
    if r.yogas:
        benefic_yogas = [y for y in r.yogas if y.benefic]
        if benefic_yogas:
            parts.append(f"Your natal chart carries {', '.join(y.name for y in benefic_yogas[:2])}, providing foundational support.")

    # Recommendation
    if r.overall_score >= 10:
        parts.append("This is a good day to move forward with important initiatives, especially those aligned with the favourable transit planets.")
    elif r.overall_score >= 0:
        parts.append("Proceed with moderate expectations — the day is favourable for routine activities but not ideal for major launches.")
    else:
        parts.append("Postpone significant decisions if possible; focus on planning, reflection, and completing pending tasks.")

    return " ".join(parts)
