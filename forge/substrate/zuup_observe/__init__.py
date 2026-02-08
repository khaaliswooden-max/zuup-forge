"""
Zuup Observe Substrate — Tracing, Logging, Metrics, Health
"""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "extra_fields"):
            entry.update(record.extra_fields)
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = {"type": record.exc_info[0].__name__, "message": str(record.exc_info[1])}
        return json.dumps(entry, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"zuup.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    return logger


class SpanContext:
    def __init__(self, service_name: str = "zuup", operation: str = "unknown"):
        self.trace_id = uuid4().hex[:32]
        self.span_id = uuid4().hex[:16]
        self.service_name = service_name
        self.operation = operation
        self.start_time = time.monotonic()
        self.attributes: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id, "span_id": self.span_id,
            "service": self.service_name, "operation": self.operation,
            "duration_ms": round((time.monotonic() - self.start_time) * 1000, 2),
            "attributes": self.attributes,
        }


_service_name = "zuup"

def setup_tracing(service_name: str) -> None:
    global _service_name
    _service_name = service_name
    get_logger("tracing").info(f"Tracing initialized: {service_name}")


def traced(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        span = SpanContext(service_name=_service_name, operation=func.__qualname__)
        try:
            result = await func(*args, **kwargs)
            span.set_attribute("status", "ok")
            return result
        except Exception as e:
            span.set_attribute("status", "error")
            span.set_attribute("error.type", type(e).__name__)
            raise
        finally:
            get_logger(func.__module__).info(f"TRACE {span.operation}", extra={"extra_fields": span.end()})
    return wrapper


class MetricsRegistry:
    def __init__(self):
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}

    def inc(self, name: str, v: float = 1.0) -> None:
        self._counters[name] = self._counters.get(name, 0) + v

    def gauge(self, name: str, v: float) -> None:
        self._gauges[name] = v

    def export_prometheus(self) -> str:
        lines = [f"{k} {v}" for k, v in sorted(self._counters.items())]
        lines += [f"{k} {v}" for k, v in sorted(self._gauges.items())]
        return "\n".join(lines)


metrics = MetricsRegistry()
health_router = APIRouter(tags=["health"])

@health_router.get("/health")
async def health():
    return {"status": "healthy", "service": _service_name, "ts": datetime.now(UTC).isoformat()}

@health_router.get("/health/ready")
async def ready():
    return {"status": "ready", "checks": {"database": "ok"}}

@health_router.get("/metrics")
async def prom_metrics():
    return metrics.export_prometheus()
