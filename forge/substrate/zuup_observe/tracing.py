"""Zuup Observe: tracing, metrics, structured logging."""

from __future__ import annotations
import functools, logging, time
from typing import Any, Callable


class StructuredLogger:
    def __init__(self, service: str, platform: str = "forge"):
        self.service = service
        self.platform = platform
        self._logger = logging.getLogger(f"zuup.{platform}.{service}")

    def _fmt(self, level: str, msg: str, **kw) -> dict:
        return {"ts": time.time(), "level": level, "svc": self.service, "msg": msg, **kw}

    def info(self, msg: str, **kw): self._logger.info(str(self._fmt("INFO", msg, **kw)))
    def warn(self, msg: str, **kw): self._logger.warning(str(self._fmt("WARN", msg, **kw)))
    def error(self, msg: str, **kw): self._logger.error(str(self._fmt("ERROR", msg, **kw)))


def setup_tracing(service_name: str) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        trace.set_tracer_provider(provider)
    except ImportError:
        pass


def traced(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            return await func(*args, **kwargs)
        finally:
            pass  # OTEL span in production
    return wrapper


class MetricsCollector:
    def __init__(self):
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment(self, name: str, value: int = 1): self._counters[name] = self._counters.get(name, 0) + value
    def observe(self, name: str, value: float): self._histograms.setdefault(name, []).append(value)


metrics = MetricsCollector()
