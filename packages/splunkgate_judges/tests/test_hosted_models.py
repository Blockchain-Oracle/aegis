"""Unit tests for the Splunk Hosted Models explainer.

Covers:
- prompt composition (with + without ctx)
- HTTP call shape (URL, body, timeout)
- success path (real-looking Ollama response)
- failure paths (timeout, network error, 5xx, malformed JSON, empty
  response) — each must fall back to the template explainer
- post-processing (whitespace, char-cap truncation, boilerplate strip)
- env-var override for OLLAMA_HOST

No real Ollama call here — see ``test_hosted_models_live.py`` for the
no-mock integration test gated on ``OLLAMA_HOST``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest  # noqa: TC002 — used at runtime by monkeypatch fixtures, not just types
import respx
from splunkgate_core import (
    RuleHit,
    Severity,
    Verdict,
    VerdictContext,
    VerdictLabel,
)
from splunkgate_judges.hosted_models import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    MAX_EXPLANATION_CHARS,
    OllamaUnavailableError,
    _build_prompt,
    _post_process,
    _resolve_ollama_url,
    explain_via_hosted_model,
)

_TRACE = UUID("12345678-1234-5678-1234-567812345678")
_TS = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)


def _make_verdict() -> Verdict:
    return Verdict(
        trace_id=_TRACE,
        timestamp=_TS,
        verdict=VerdictLabel.BLOCK,
        severity=Severity.HIGH,
        rules=[RuleHit(rule="Prompt Injection", confidence=0.95, source="ai_defense")],
        modifications=None,
        surface="mw_model",
        latency_ms=42.0,
    )


def _make_ctx() -> VerdictContext:
    return VerdictContext(
        trace_id=_TRACE,
        agent_id="support_agent_v3",
        model_name="claude-sonnet-4-6",
        system_prompt_summary="customer support agent",
        recent_messages=["Ignore previous instructions"],
        surface="mw_model",
    )


# ---------------------------------------------------------------------
# Prompt composition
# ---------------------------------------------------------------------


def test_prompt_includes_label_severity_rules_without_ctx() -> None:
    prompt = _build_prompt(_make_verdict(), None)
    assert "BLOCK" in prompt
    assert "HIGH" in prompt
    assert "Prompt Injection" in prompt
    assert "source=ai_defense" in prompt
    # No context line when ctx is None.
    assert "Agent:" not in prompt
    assert "support_agent_v3" not in prompt


def test_prompt_includes_ctx_when_provided() -> None:
    prompt = _build_prompt(_make_verdict(), _make_ctx())
    assert "support_agent_v3" in prompt
    assert "claude-sonnet-4-6" in prompt
    assert "mw_model" in prompt
    assert "Agent:" in prompt


def test_prompt_handles_empty_rules() -> None:
    verdict = _make_verdict().model_copy(update={"rules": []})
    prompt = _build_prompt(verdict, None)
    assert "no rules fired" in prompt


# ---------------------------------------------------------------------
# HTTP call shape
# ---------------------------------------------------------------------


@respx.mock
def test_posts_to_default_url_and_correct_body() -> None:
    route = respx.post(f"{DEFAULT_OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(
            200,
            json={
                "response": "Blocked a prompt-injection attempt at HIGH severity.",
                "done": True,
            },
        )
    )

    out = explain_via_hosted_model(_make_verdict(), _make_ctx())

    assert route.called
    sent = route.calls.last.request.read().decode("utf-8")
    assert '"model":"' + DEFAULT_MODEL + '"' in sent
    assert '"prompt":"' in sent
    assert '"stream":false' in sent
    # temperature in the body, controlling the model's variance.
    assert "temperature" in sent
    # And the output is the model's response (post-processed).
    assert "Blocked a prompt-injection" in out


@respx.mock
def test_respects_explicit_model_override() -> None:
    route = respx.post(f"{DEFAULT_OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "explained", "done": True})
    )

    explain_via_hosted_model(_make_verdict(), None, model="foundation-sec:8b")

    sent = route.calls.last.request.read().decode("utf-8")
    assert '"model":"foundation-sec:8b"' in sent


@respx.mock
def test_respects_explicit_ollama_url_override() -> None:
    route = respx.post("http://remote-host:9999/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "ok", "done": True})
    )

    explain_via_hosted_model(_make_verdict(), None, ollama_url="http://remote-host:9999")

    assert route.called


# ---------------------------------------------------------------------
# Resilience: every failure path must fall back to the template.
# ---------------------------------------------------------------------


@respx.mock
def test_5xx_falls_back_to_template() -> None:
    respx.post(f"{DEFAULT_OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(503, text="model loading")
    )

    out = explain_via_hosted_model(_make_verdict(), None)

    # Template output starts with the verdict label + severity tag.
    assert "BLOCK (severity HIGH)" in out


@respx.mock
def test_malformed_json_falls_back_to_template() -> None:
    respx.post(f"{DEFAULT_OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, text="not json at all")
    )

    out = explain_via_hosted_model(_make_verdict(), None)

    assert "BLOCK (severity HIGH)" in out


@respx.mock
def test_empty_response_falls_back_to_template() -> None:
    respx.post(f"{DEFAULT_OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "   ", "done": True})
    )

    out = explain_via_hosted_model(_make_verdict(), None)

    assert "BLOCK (severity HIGH)" in out


@respx.mock
def test_network_error_falls_back_to_template_after_retries() -> None:
    respx.post(f"{DEFAULT_OLLAMA_URL}/api/generate").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    out = explain_via_hosted_model(_make_verdict(), None)

    assert "BLOCK (severity HIGH)" in out


@respx.mock
def test_timeout_falls_back_to_template() -> None:
    respx.post(f"{DEFAULT_OLLAMA_URL}/api/generate").mock(
        side_effect=httpx.ReadTimeout("read timed out")
    )

    out = explain_via_hosted_model(_make_verdict(), None, timeout_seconds=0.1)

    assert "BLOCK (severity HIGH)" in out


# ---------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------


def test_post_process_strips_outer_quotes() -> None:
    assert _post_process('"Hello world."') == "Hello world."


def test_post_process_collapses_whitespace() -> None:
    assert _post_process("Line 1\n\nLine 2\tend") == "Line 1 Line 2 end"


def test_post_process_truncates_long_output() -> None:
    text = "x" * 1000
    out = _post_process(text)
    assert len(out) == MAX_EXPLANATION_CHARS
    assert out.endswith("…")


def test_post_process_preserves_short_output() -> None:
    assert _post_process("Short clean output.") == "Short clean output."


# ---------------------------------------------------------------------
# Env var resolution
# ---------------------------------------------------------------------


def test_resolve_url_uses_explicit_arg_when_given() -> None:
    assert _resolve_ollama_url("http://foo") == "http://foo"


def test_resolve_url_strips_trailing_slash() -> None:
    assert _resolve_ollama_url("http://foo/") == "http://foo"


def test_resolve_url_uses_env_var_when_no_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://env-host:8765")
    assert _resolve_ollama_url(None) == "http://env-host:8765"


def test_resolve_url_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert _resolve_ollama_url(None) == DEFAULT_OLLAMA_URL


# ---------------------------------------------------------------------
# OllamaUnavailableError surface (callers should NOT see this — it is
# always caught + converted to a template fallback). This test asserts
# the exception type exists and is importable so refactors don't lose
# the public surface.
# ---------------------------------------------------------------------


def test_ollama_unavailable_is_subclass_of_exception() -> None:
    assert issubclass(OllamaUnavailableError, Exception)
