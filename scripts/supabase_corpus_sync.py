"""Stable import path for helpers in supabase-corpus-sync.py (hyphenated filename)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "supabase-corpus-sync.py"
_SPEC = importlib.util.spec_from_file_location("supabase_corpus_sync_impl", _PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load Supabase sync helpers from {_PATH}")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

load_env = _MOD.load_env
api_request = _MOD.api_request
