from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .models import InvalidationReason


@dataclass
class RegisteredEngine:
    name: str
    on_refresh: Optional[Callable[[str], None]] = None
    on_invalidation: Optional[Callable[[List[str], InvalidationReason, str], None]] = None


@dataclass
class EngineRegistry:
    _engines: Dict[str, RegisteredEngine] = field(default_factory=dict)

    def register(self, name: str, on_refresh: Optional[Callable] = None,
                 on_invalidation: Optional[Callable] = None) -> RegisteredEngine:
        engine = RegisteredEngine(name=name, on_refresh=on_refresh, on_invalidation=on_invalidation)
        self._engines[name] = engine
        return engine

    def notify_refresh(self, new_version: str):
        for eng in self._engines.values():
            if eng.on_refresh:
                try:
                    eng.on_refresh(new_version)
                except Exception:
                    pass  # engines should be resilient

    def notify_invalidation(self, node_ids: List[str], reason: InvalidationReason, details: str):
        for eng in self._engines.values():
            if eng.on_invalidation:
                try:
                    eng.on_invalidation(node_ids, reason, details)
                except Exception:
                    pass

    def registered_names(self) -> List[str]:
        return list(self._engines.keys())
