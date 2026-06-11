"""SafetyAgentMiddleware — outer session boundary + trace_id seeding.

Surface 1's outermost wrap. Sits ABOVE model / tool / subagent middleware:
every Verdict emitted during a single `Agent.invoke()` call shares the
same `trace_id` so the SOC analyst can pivot from one verdict to the full
session trail in one click on the `verdict_inspector.xml` dashboard.

What it does:
- (a) reads or generates a session `trace_id`. If `request.thread_id` is
  set the trace_id is deterministically derived from it (UUIDv5 in a
  fixed namespace) so re-invocations of the same thread share the same
  trace_id. Otherwise UUIDv4.
- (b) binds the trace_id to `splunkgate_core.trace` (ContextVar) so child
  middlewares — and `splunkgate_core.otel.emit_verdict_event` — pick it up
  via `current_trace_id()`. Also binds via `structlog.contextvars` so
  every log line in this session is tagged.
- (c) wraps `await handler(request)` in try/finally. The `finally` emits
  a session-summary verdict (`surface="mw_agent"`, `verdict=ALLOW` on
  happy path, `verdict=BLOCK` if a `SplunkGateError` propagated) and
  unbinds the contextvars.
- (d) honours a previously-bound trace_id — if the parent already set
  one, we reuse it and skip the bind/unbind cycle. The summary verdict
  still emits.
- (e) non-`SplunkGateError` exceptions (e.g. splunklib.ai's
  `TimeoutExceededException`) propagate untouched; we only own
  `SplunkGateError` outcomes.

Per `../../../context/02-agent-frameworks/06-splunklib-ai-deep-read.md`,
splunklib.ai's `Agent` auto-generates a 32-hex-char trace_id at
construction. SplunkGate's session trace_id is independent of that — we
need a UUID because `Verdict.trace_id` is typed as UUID. The two coexist;
SOC analysts can pivot on either.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import NAMESPACE_OID, UUID, uuid4, uuid5

import structlog
from splunkgate_core.errors import SplunkGateError
from splunkgate_core.trace import bind_trace_id, current_trace_id, unbind_trace_id
from splunkgate_core.verdict import Severity, Verdict, VerdictLabel
from splunklib.ai.messages import AgentResponse
from splunklib.ai.middleware import AgentMiddleware, AgentRequest

from splunkgate_mw._fail_closed import safe_emit
from splunkgate_mw.config import Config
from splunkgate_mw.profiles import Profile

if TYPE_CHECKING:
    from contextvars import Token

__all__ = ["SafetyAgentMiddleware"]

_logger = structlog.get_logger(__name__)
_SURFACE = "mw_agent"

# UUIDv5 namespace for thread_id-derived trace_ids — fixed so the same
# thread always maps to the same trace_id across processes/runs. Per the
# story spec, this enables stable correlation across re-invocations.
_THREAD_NAMESPACE = uuid5(NAMESPACE_OID, "splunkgate.thread_id.namespace")

AgentMiddlewareHandler = Callable[[AgentRequest], Awaitable[AgentResponse[Any | None]]]


def _derive_trace_id(thread_id: str | None) -> UUID:
    """Derive the session trace_id deterministically when thread_id is set."""
    if thread_id:
        return uuid5(_THREAD_NAMESPACE, thread_id)
    return uuid4()


def _summary_verdict(  # noqa: PLR0913 — every field is a load-bearing summary attribute
    *,
    trace_uuid: UUID,
    now: datetime,
    latency_ms: float,
    label: VerdictLabel,
    severity: Severity,
    profile_name: str,
    explanation: str | None,
) -> Verdict:
    """Build the session-summary verdict emitted in the finally clause."""
    return Verdict(
        trace_id=trace_uuid,
        timestamp=now,
        verdict=label,
        severity=severity,
        rules=[],
        surface=_SURFACE,
        latency_ms=latency_ms,
        explanation=explanation,
        agent_id=profile_name,
    )


class SafetyAgentMiddleware(AgentMiddleware):  # type: ignore[misc]
    """Outer session boundary. Seeds trace_id + emits session summary."""

    def __init__(
        self,
        *,
        profile: str | Profile = "default",
        config: Config | None = None,
    ) -> None:
        """Wire profile + config + structlog binder for the session."""
        self._config: Config = config if config is not None else Config()
        self._profile = (
            profile if isinstance(profile, Profile) else Profile(name=profile, description="")
        )
        self._logger = structlog.get_logger("SafetyAgentMiddleware").bind(
            profile=self._profile.name,
        )

    async def agent_middleware(
        self,
        request: AgentRequest,
        handler: AgentMiddlewareHandler,
    ) -> AgentResponse[Any | None]:
        """Seed trace_id, bind contextvars, delegate, emit session summary in finally.

        Every emitted verdict carries surface="mw_agent". On happy path
        the summary is ALLOW; on SplunkGateError it is BLOCK. Non-
        SplunkGateError exceptions propagate without emitting a summary.
        """
        # (d) honour a previously-bound trace_id — reuse it rather than
        # overwrite. The parent process (a unit-test fixture, an outer
        # Splunk modular input) may have set one already.
        existing = current_trace_id()
        i_bound_it = existing is None
        trace_uuid = existing or _derive_trace_id(getattr(request, "thread_id", None))

        token: Token[UUID | None] | None = bind_trace_id(trace_uuid) if i_bound_it else None
        structlog_token = structlog.contextvars.bind_contextvars(
            trace_id=str(trace_uuid),
            **{"splunkgate.surface": _SURFACE, "splunkgate.profile": self._profile.name},
        )

        now = datetime.now(UTC)
        started = time.perf_counter()
        # Sentinel: was a SplunkGateError raised? Only those convert to BLOCK
        # summary; other exceptions (TimeoutExceeded, etc.) propagate without
        # a summary because we only own SplunkGateError outcomes.
        spg_error: SplunkGateError | None = None
        try:
            return await handler(request)
        except SplunkGateError as exc:
            spg_error = exc
            raise
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            if spg_error is not None:
                label = VerdictLabel.BLOCK
                severity = Severity.HIGH
                explanation = f"Session ended with {type(spg_error).__name__}: {spg_error!s}"
            else:
                label = VerdictLabel.ALLOW
                severity = Severity.NONE_SEVERITY
                explanation = None
            summary = _summary_verdict(
                trace_uuid=trace_uuid,
                now=now,
                latency_ms=latency_ms,
                label=label,
                severity=severity,
                profile_name=self._profile.name,
                explanation=explanation,
            )
            safe_emit(summary)
            self._logger.info(
                "agent_session_summary",
                trace_id=str(trace_uuid),
                label=label.value,
                latency_ms=latency_ms,
            )
            # Unbind contextvars only if we bound them — borrowed
            # trace_ids stay bound for the outer scope.
            structlog.contextvars.reset_contextvars(**structlog_token)
            if i_bound_it and token is not None:
                unbind_trace_id(token)
