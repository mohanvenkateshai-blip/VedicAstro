"""
Fuse Vimshottari Dasha quality with a transit snapshot for a time window.

For each Maha–Antar period we:
  1. Pick the midpoint date as a representative transit snapshot.
  2. Compute planetary positions at that date (compute_gochar).
  3. Run TransitImpactAnalyzer against the native's natal chart.
  4. Merge the Dasha score with the transit score.
  5. Derive domain-level predictions (career, wealth, health, family, caution).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


_HOUSE_DOMAIN: dict[int, str] = {
    1: "career", 2: "wealth", 3: "career",
    4: "family", 5: "wealth", 6: "career",
    7: "family", 8: "health", 9: "wealth",
    10: "career", 11: "wealth", 12: "health",
}


def fuse_dasha_transit(
    maha_lord: str,
    antar_lord: str,
    start_date: str,
    end_date: str,
    lat: float,
    lon: float,
    tz: float,
    lagna_rashi: Optional[str],
    janma_rashi: Optional[str],
    janma_nakshatra: Optional[str],
    natal_sign: Optional[dict],
    dasha_intel: Optional[dict],
) -> Optional[dict]:
    """
    Return a combined Dasha+Transit prediction dict, or None on any error.
    """
    from vedic_engine.prediction.gochar import compute_gochar
    from vedic_engine.synthesis.transit_analyzer import TransitImpactAnalyzer

    try:
        start = date.fromisoformat(start_date[:10])
        end   = date.fromisoformat(end_date[:10])
        mid   = start + (end - start) // 2
        dasha_score = int((dasha_intel or {}).get("score", 0))

        # ── Transit snapshot ──────────────────────────────────────────────────
        gochar = compute_gochar(
            date_str=mid.isoformat(),
            lat=lat, lon=lon, tz=tz,
            janma_rashi=janma_rashi,
            janma_nakshatra=janma_nakshatra,
            natal_sign=natal_sign,
        )
        ti = TransitImpactAnalyzer().analyze(
            gochar,
            natal_sign=natal_sign,
            dasha_maha=maha_lord,
            dasha_antar=antar_lord,
            dasha_score=dasha_score,
        )
        if ti is None:
            return None

        transit_score   = ti.overall_score
        combined_score  = dasha_score + transit_score
        combined_verdict = "shubh" if combined_score > 0 else "ashubh"

        # ── Key transits (top 4 by absolute impact) ──────────────────────────
        planets = ti.planets  # list[dict]
        sorted_planets = sorted(planets, key=lambda p: abs(p.get("score", 0)), reverse=True)
        key_transits = [
            {
                "planet":        p.get("planet", ""),
                "rashi":         p.get("rashi", ""),
                "house_from_moon": p.get("house_from_janma"),
                "verdict":       p.get("final_verdict", ""),
                "impact":        p.get("primary_driver", ""),
            }
            for p in sorted_planets[:4]
        ]

        # ── Domain predictions — seed from Dasha intelligence ─────────────────
        d = dasha_intel or {}
        career  = list(d.get("profession", []))[:1]
        wealth  = list(d.get("wealth",     []))[:1]
        health  = list(d.get("health",     []))[:1]
        family  = list(d.get("family",     []))[:1]
        caution = list(d.get("caution",    []))[:1]

        # Augment with transit planet insights bucketed by transiting house
        for p in sorted_planets:
            house   = p.get("house_from_janma") or 0
            domain  = _HOUSE_DOMAIN.get(house)
            if not domain:
                continue
            is_good = p.get("final_verdict") == "shubh"
            impacts = p.get("positive_impact", []) if is_good else p.get("negative_impact", [])
            if not impacts:
                impacts = [p.get("primary_driver", "")]
            snippet = f"{p.get('planet')} in {p.get('rashi')} (house {house}): {impacts[0]}"

            if domain == "career" and len(career) < 2:
                career.append(snippet)
            elif domain == "wealth" and len(wealth) < 2:
                wealth.append(snippet)
            elif domain == "health" and len(health) < 2:
                health.append(snippet)
            elif domain == "family" and len(family) < 2:
                family.append(snippet)

            if not is_good and len(caution) < 2:
                caution.append(snippet)

        # ── Summary ───────────────────────────────────────────────────────────
        quality    = "favourable" if combined_verdict == "shubh" else "challenging"
        dasha_note = (d.get("summary") or "")[:80].rstrip(".")
        transit_note = (ti.day_summary or "")[:100].rstrip(".")
        summary = (
            f"{maha_lord}–{antar_lord} ({start_date[:7]} → {end_date[:7]}) "
            f"is overall {quality} "
            f"(Dasha {dasha_score:+d} · Transit {transit_score:+d} = {combined_score:+d}). "
            f"{dasha_note}. At mid-period ({mid.isoformat()}): {transit_note}."
        )

        return {
            "combined_verdict": combined_verdict,
            "combined_score":   combined_score,
            "dasha_score":      dasha_score,
            "transit_score":    transit_score,
            "snapshot_date":    mid.isoformat(),
            "summary":          summary,
            "key_transits":     key_transits,
            "career":           career,
            "wealth":           wealth,
            "health":           health,
            "family":           family,
            "caution":          caution,
        }

    except Exception:
        return None
