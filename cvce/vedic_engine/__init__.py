"""
Vedic Prediction Engine — Unified Panchanga + Gochar + Dasha + Yoga Predictor

Sources (all in /Gyan/):
  - Gochar Phaladeepika (Pulippani) — transit rules, Moorthy Nirnaya, Vedha
  - Brihat Parasara Hora Sastra — foundational principles
  - Hora Sara (Prithuyasas) — transit, yoga, dasha
  - Phaladeepika (Mantreswara) — planetary results, yogas
  - Sarvartha Chintamani — comprehensive prediction
  - Jaimini Sutras — Chara Dasha, Karakas
  - Yogini Dasha (Goel) — 8-fold dasha system

Architecture:
  1. core/        — astronomy, panchanga computation
  2. rules/       — rule tables extracted from each text
  3. prediction/  — per-domain prediction modules
  4. synthesis/   — combines all modules, resolves contradictions, generates output
"""

from .synthesis.engine import VedicPredictor

__all__ = ["VedicPredictor"]
