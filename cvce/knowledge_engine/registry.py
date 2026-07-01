from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .models import InvalidationReason


@dataclass
class RegisteredEngine:
    name: str
    on_refresh: Callable[[str], None] | None = None
    on_invalidation: Callable[[list[str], InvalidationReason, str], None] | None = None


@dataclass
class EngineRegistry:
    _engines: dict[str, RegisteredEngine] = field(default_factory=dict)

    def register(
        self, name: str, on_refresh: Callable | None = None, on_invalidation: Callable | None = None
    ) -> RegisteredEngine:
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

    def ensure_registration(self, engine_name: str, on_refresh: Callable | None = None, on_invalidation: Callable | None = None) -> RegisteredEngine:
        if engine_name not in self._engines:
            return self.register(engine_name, on_refresh, on_invalidation)
        return self._engines[engine_name]

    def notify_invalidation(self, node_ids: list[str], reason: InvalidationReason, details: str):
        for eng in self._engines.values():
            if eng.on_invalidation:
                try:
                    eng.on_invalidation(node_ids, reason, details)
                except Exception:
                    pass

    def registered_names(self) -> list[str]:
        return list(self._engines.keys())
