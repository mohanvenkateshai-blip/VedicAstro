"""
PerformanceMonitor — Detects slow responses, high latency, infinite loops,
degraded performance in registered engines and KnowledgeEngine.

Monitors:
- KnowledgeEngine health, cache hit rates, refresh cycle timing
- Per-engine operation latency via timing wrappers
- Threshold breaches trigger logging + optional alert callbacks

Integrates with global refresh trigger by wrapping trigger_global_refresh.
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .engine import KnowledgeEngine
from .integration import get_knowledge_engine

logger = logging.getLogger(__name__)


@dataclass
class MonitorConfig:
    """Threshold configuration for performance alerts."""

    max_latency_ms: float = 5000.0  # per-operation
    max_refresh_time_ms: float = 30000.0
    min_cache_hit_rate: float = 0.6
    max_invalidation_count: int = 100
    loop_detection_timeout_s: float = 30.0
    alert_on_breach: bool = True


@dataclass
class PerformanceMonitor:
    """Central performance monitor for VedicAstro engines."""

    config: MonitorConfig = field(default_factory=MonitorConfig)
    _metrics: dict[str, list[float]] = field(default_factory=dict)
    _cache_stats: dict[str, Any] = field(default_factory=dict)
    _last_refresh_duration_ms: float | None = None
    _alert_callbacks: list[Callable[[str, dict], None]] = field(default_factory=list)

    def time_operation(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """Time a function call; log/alert on threshold breach. Detects slow ops."""
        start = time.perf_counter()
        try:
            # Simple timeout wrapper using futures for loop/infinite detection
            from concurrent.futures import ThreadPoolExecutor
            from concurrent.futures import TimeoutError as FutureTimeout

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    result = future.result(timeout=self.config.loop_detection_timeout_s)
                except FutureTimeout:
                    self._alert(
                        f"timeout_detected_{name}",
                        {"timeout_s": self.config.loop_detection_timeout_s},
                    )
                    raise TimeoutError(
                        f"Operation {name} exceeded {self.config.loop_detection_timeout_s}s — possible infinite loop"
                    )
        except Exception:
            # Fallback without timeout if ThreadPool fails (e.g. non-picklable)
            result = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        self._record_metric(name, duration_ms)
        if duration_ms > self.config.max_latency_ms:
            self._alert(
                f"slow_response_{name}",
                {"duration_ms": duration_ms, "threshold": self.config.max_latency_ms},
            )
        return result

    def _record_metric(self, name: str, duration_ms: float) -> None:
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(duration_ms)
        # keep last 100 samples
        if len(self._metrics[name]) > 100:
            self._metrics[name] = self._metrics[name][-100:]

    def _alert(self, alert_type: str, details: dict[str, Any]) -> None:
        payload = {
            "type": alert_type,
            "timestamp": time.time(),
            "details": details,
            "config": self.config.__dict__,
        }
        logger.warning("PERF_ALERT: %s | %s", alert_type, details)
        if self.config.alert_on_breach:
            for cb in self._alert_callbacks:
                try:
                    cb(alert_type, payload)
                except Exception:
                    pass  # callbacks must not break monitoring

    def register_alert_callback(self, callback: Callable[[str, dict], None]) -> None:
        self._alert_callbacks.append(callback)

    def monitor_knowledge_engine_health(self, ke: KnowledgeEngine | None = None) -> dict[str, Any]:
        """Check KE health + invalidation count; alert if degraded."""
        ke = ke or get_knowledge_engine()
        health = ke.health()
        if health.get("invalidated_count", 0) > self.config.max_invalidation_count:
            self._alert("high_invalidation_count", {"count": health["invalidated_count"]})
        if not health.get("healthy"):
            self._alert("knowledge_unhealthy", health)
        return health

    def monitor_cache_hit_rate(self) -> dict[str, Any]:
        """Inspect lru_cache stats from integration layer."""
        try:
            from .integration import get_knowledge_engine

            cache_info = get_knowledge_engine.cache_info()
            hits = cache_info.hits
            misses = cache_info.misses
            total = hits + misses
            hit_rate = hits / total if total > 0 else 0.0
            stats = {
                "hits": hits,
                "misses": misses,
                "hit_rate": hit_rate,
                "currsize": cache_info.currsize,
            }
            self._cache_stats = stats
            if hit_rate < self.config.min_cache_hit_rate and total > 10:
                self._alert(
                    "low_cache_hit_rate",
                    {"hit_rate": hit_rate, "threshold": self.config.min_cache_hit_rate},
                )
            return stats
        except Exception as exc:
            logger.debug("Cache stats unavailable: %s", exc)
            return {"error": str(exc)}

    def monitor_refresh_cycle(self, ke: KnowledgeEngine, reason: str = "monitor") -> dict[str, Any]:
        """Wrap global refresh with timing; alert on slow refresh."""
        start = time.perf_counter()
        result = ke.trigger_global_refresh(reason=reason)
        duration_ms = (time.perf_counter() - start) * 1000
        self._last_refresh_duration_ms = duration_ms
        if duration_ms > self.config.max_refresh_time_ms:
            self._alert("slow_refresh_cycle", {"duration_ms": duration_ms, "reason": reason})
        result["monitor_duration_ms"] = duration_ms
        return result

    def get_summary(self) -> dict[str, Any]:
        """Return aggregated performance summary."""
        avg_latencies = {k: sum(v) / len(v) for k, v in self._metrics.items() if v}
        return {
            "config": self.config.__dict__,
            "avg_latencies_ms": avg_latencies,
            "last_refresh_ms": self._last_refresh_duration_ms,
            "cache_stats": self._cache_stats,
            "samples_collected": {k: len(v) for k, v in self._metrics.items()},
        }


def timed_engine_operation(monitor: PerformanceMonitor, op_name: str):
    """Decorator factory to wrap registered engine callbacks with timing."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return monitor.time_operation(op_name, func, *args, **kwargs)

        return wrapper

    return decorator


# Convenience singleton for app-wide use
_default_monitor: PerformanceMonitor | None = None


def get_performance_monitor(config: MonitorConfig | None = None) -> PerformanceMonitor:
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = PerformanceMonitor(config=config or MonitorConfig())
    return _default_monitor
