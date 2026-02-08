"""
Zuup AI Orchestration Substrate

Core AI engineering primitives shared across all platforms:
- Tool routing with safety gates
- Input/output guardrails
- Prompt versioning and registry
- Evaluation harness
- Preference collection hooks

Design: retrieval + tools over "prompt magic". Every LLM call is logged,
versioned, and evaluable.
"""

from __future__ import annotations

import hashlib, json, re, time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4
from pydantic import BaseModel, Field

from forge.substrate.zuup_observe import get_logger, metrics

logger = get_logger("ai_orchestrator")


# =============================================================================
# Models
# =============================================================================

class ToolCallStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    tool_name: str
    arguments: dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: Any = None
    error: str | None = None
    duration_ms: float | None = None
    requires_approval: bool = False


class LLMRequest(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:16])
    platform: str
    model: str = "claude-sonnet-4-20250514"
    prompt_template: str
    prompt_version: str = "1.0"
    variables: dict[str, Any] = Field(default_factory=dict)
    tools: list[str] = Field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    request_id: str
    model: str
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: float
    guardrail_flags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PreferenceSignal(BaseModel):
    """Implicit or explicit preference signal for RSI."""
    id: str = Field(default_factory=lambda: uuid4().hex[:16])
    platform: str
    domain: str
    signal_type: str  # "explicit_ab", "implicit_click", "implicit_latency", "thumbs"
    request_id: str
    chosen: str | None = None
    rejected: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Guardrails
# =============================================================================

class GuardrailResult(BaseModel):
    passed: bool
    rule_name: str
    message: str = ""


class GuardrailEngine:
    """Input/output content guardrails."""

    def __init__(self):
        self._rules: dict[str, Callable[[str], GuardrailResult]] = {}

    def register(self, name: str, fn: Callable[[str], GuardrailResult]) -> None:
        self._rules[name] = fn

    def check(self, content: str, rule_names: list[str] | None = None) -> list[GuardrailResult]:
        results = []
        targets = rule_names or list(self._rules.keys())
        for name in targets:
            if name in self._rules:
                results.append(self._rules[name](content))
        return results

    def check_all_pass(self, content: str, rule_names: list[str] | None = None) -> tuple[bool, list[str]]:
        results = self.check(content, rule_names)
        failures = [r.message for r in results if not r.passed]
        return len(failures) == 0, failures


# Default guardrails
guardrails = GuardrailEngine()

def _no_pii_check(content: str) -> GuardrailResult:
    """Block SSN, credit card patterns."""
    patterns = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # CC
    ]
    for pat in patterns:
        if re.search(pat, content):
            return GuardrailResult(passed=False, rule_name="no_pii", message=f"PII pattern detected: {pat}")
    return GuardrailResult(passed=True, rule_name="no_pii")

def _max_length_check(content: str) -> GuardrailResult:
    if len(content) > 100_000:
        return GuardrailResult(passed=False, rule_name="max_length", message="Content exceeds 100K chars")
    return GuardrailResult(passed=True, rule_name="max_length")

guardrails.register("no_pii", _no_pii_check)
guardrails.register("max_length", _max_length_check)


# =============================================================================
# Prompt Registry
# =============================================================================

class PromptTemplate(BaseModel):
    name: str
    version: str
    template: str
    variables: list[str]
    platform: str
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def render(self, **kwargs: Any) -> str:
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.template.encode()).hexdigest()[:12]


class PromptRegistry:
    """Versioned prompt storage with hash-based dedup."""

    def __init__(self):
        self._prompts: dict[str, dict[str, PromptTemplate]] = {}  # name -> version -> template

    def register(self, template: PromptTemplate) -> None:
        if template.name not in self._prompts:
            self._prompts[template.name] = {}
        self._prompts[template.name][template.version] = template
        logger.info(f"Registered prompt: {template.name}@{template.version} ({template.hash})")

    def get(self, name: str, version: str = "latest") -> PromptTemplate | None:
        versions = self._prompts.get(name, {})
        if version == "latest" and versions:
            return list(versions.values())[-1]
        return versions.get(version)

    def list_all(self) -> list[dict[str, str]]:
        result = []
        for name, versions in self._prompts.items():
            for ver, tmpl in versions.items():
                result.append({"name": name, "version": ver, "hash": tmpl.hash})
        return result


prompt_registry = PromptRegistry()


# =============================================================================
# Tool Router
# =============================================================================

class ToolRouter:
    """Routes tool calls to implementations with safety gates."""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._approval_required: set[str] = set()

    def register(self, name: str, fn: Callable, requires_approval: bool = False) -> None:
        self._tools[name] = fn
        if requires_approval:
            self._approval_required.add(name)

    async def execute(self, call: ToolCall) -> ToolCall:
        if call.tool_name not in self._tools:
            call.status = ToolCallStatus.FAILED
            call.error = f"Unknown tool: {call.tool_name}"
            return call

        if call.tool_name in self._approval_required:
            call.requires_approval = True
            call.status = ToolCallStatus.PENDING
            logger.info(f"Tool {call.tool_name} requires approval", extra={"extra_fields": call.model_dump()})
            return call

        start = time.monotonic()
        try:
            result = self._tools[call.tool_name](**call.arguments)
            if hasattr(result, "__await__"):
                result = await result
            call.result = result
            call.status = ToolCallStatus.EXECUTED
            metrics.inc("zuup_tool_calls_total", labels={"tool": call.tool_name, "status": "success"})
        except Exception as e:
            call.error = str(e)
            call.status = ToolCallStatus.FAILED
            metrics.inc("zuup_tool_calls_total", labels={"tool": call.tool_name, "status": "error"})
            logger.error(f"Tool execution failed: {call.tool_name}", exc_info=True)
        finally:
            call.duration_ms = (time.monotonic() - start) * 1000

        return call


tool_router = ToolRouter()


# =============================================================================
# Evaluation Harness
# =============================================================================

class EvalCase(BaseModel):
    id: str
    input: dict[str, Any]
    expected_output: Any
    tags: list[str] = Field(default_factory=list)


class EvalResult(BaseModel):
    case_id: str
    passed: bool
    score: float
    actual_output: Any
    latency_ms: float
    error: str | None = None


class EvalSuite:
    """Domain-specific evaluation suite."""

    def __init__(self, name: str, platform: str):
        self.name = name
        self.platform = platform
        self.cases: list[EvalCase] = []
        self._scorers: dict[str, Callable] = {}

    def add_case(self, case: EvalCase) -> None:
        self.cases.append(case)

    def register_scorer(self, name: str, fn: Callable[[Any, Any], float]) -> None:
        self._scorers[name] = fn

    async def run(self, model_fn: Callable) -> list[EvalResult]:
        results = []
        for case in self.cases:
            start = time.monotonic()
            try:
                output = await model_fn(case.input)
                latency = (time.monotonic() - start) * 1000
                score = 1.0
                for scorer in self._scorers.values():
                    score = min(score, scorer(case.expected_output, output))
                results.append(EvalResult(
                    case_id=case.id, passed=score >= 0.7,
                    score=score, actual_output=output, latency_ms=latency,
                ))
            except Exception as e:
                results.append(EvalResult(
                    case_id=case.id, passed=False, score=0.0,
                    actual_output=None, latency_ms=(time.monotonic() - start) * 1000,
                    error=str(e),
                ))
        return results

    def summary(self, results: list[EvalResult]) -> dict[str, Any]:
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        scores = [r.score for r in results]
        latencies = [r.latency_ms for r in results]
        return {
            "suite": self.name, "platform": self.platform,
            "total": total, "passed": passed, "failed": total - passed,
            "pass_rate": passed / total if total else 0,
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0,
        }
