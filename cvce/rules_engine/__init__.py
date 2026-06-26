"""Unified Vedic Rules Engine — single source of truth for all astrological rules.

Loads rules.json at import time. All queries are O(1) dict lookups.
No computation — this engine answers "what rule applies?" given computed positions.
"""
from .engine import RuleEngine

__all__ = ["RuleEngine"]
