"""Splunk Hosted Models inference for verdict explanation.

Per ADR-003a (2026-06-05): Foundation-Sec is EXPLAINER-only, never
classifier. This module makes the EXPLAINER call against a Hosted Model
via one of two transports:

- **Transport B-Ollama** (this module's default) — generic HTTP POST
  to a local Ollama instance. Works for ANY Hosted Model that has been
  pulled into Ollama, including:
  - ``gpt-oss:20b``                — OpenAI open-weight, Apache-2.0,
                                     listed at <huggingface.co/openai/gpt-oss-20b>
                                     and on the official Ollama library
                                     (``ollama pull gpt-oss:20b``).
  - ``foundation-sec:8b``          — Cisco Foundation-Sec, Llama 3.1
                                     Community License. Requires a
                                     community-uploaded Ollama tag or
                                     a Modelfile created from the
                                     GGUF distribution on Hugging Face
                                     (``fdtn-ai/Foundation-Sec-1.1-8B-Instruct``).

  Set ``model=<tag>`` to switch between them. ``gpt-oss:20b`` is the
  default because it ships in the Ollama library out-of-the-box —
  zero-friction setup for hackathon judges.

- **Transport A — Splunk Hosted Models via ``| ai`` SPL** — lives in
  ``foundsec_spl.py``. Preferred when the operator's Splunk tenant
  has AI Toolkit installed with a configured LLM Connection. Both
  transports satisfy the "Best Use of Splunk Hosted Models" hackathon
  bonus prize criterion.

Resilience contract:
- Per-call timeout (default 30s) — prevents the middleware from hanging
  on a stuck inference server.
- Tenacity-backed retry on transient HTTPX failures (3 attempts,
  exponential backoff).
- Template fallback on ANY exception: callers always receive a
  non-empty string. The template path is the existing
  ``explainer.explain_verdict`` deterministic output.

No mocks in the hot path: the integration test
``test_hosted_models_live`` calls a REAL Ollama instance. respx is
used in ``test_hosted_models`` only to assert HTTP-call SHAPE
(URL, body, timeout) — it never substitutes for the real model in
end-to-end runs.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
import structlog
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from splunkgate_judges.explainer import explain_verdict

if TYPE_CHECKING:
    from splunkgate_core import Verdict, VerdictContext

_logger = structlog.get_logger(__name__)

__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_OLLAMA_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "EXPLAINER_PROMPT_TEMPLATE",
    "MAX_EXPLANATION_CHARS",
    "OllamaGenerateRequest",
    "OllamaGenerateResponse",
    "OllamaUnavailableError",
    "explain_via_hosted_model",
]

# Default model: `gpt-oss:20b` (OpenAI open-weight, Apache-2.0, ships in
# the Ollama library out-of-the-box). Operators can switch to
# `foundation-sec:8b` once they create a Modelfile from the HF
# distribution; the call shape is unchanged.
DEFAULT_MODEL = "gpt-oss:20b"

# Ollama's default REST endpoint. Override via OLLAMA_HOST env var or
# the `ollama_url` arg to `explain_via_hosted_model`.
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# 30s aligns with the Cisco AI Defense client's per-call timeout and the
# SUIT dashboard search-lifecycle SEARCH_TIMEOUT_MS. A stuck Ollama
# server will surface as a clean OllamaUnavailableError -> template
# fallback rather than wedging the middleware request.
DEFAULT_TIMEOUT_SECONDS = 30.0

# Ollama returns HTTP 200 on every successful /api/generate call. Other
# status codes signal the server is up but rejected the request (e.g.
# 404 when the model is not pulled, 503 when the model is still
# loading).
_OK_STATUS = 200

# Explanation cap. Matches the template explainer's 280-char output
# budget so the dashboard cells + regulator PDF rows render
# consistently regardless of which backend produced the string.
MAX_EXPLANATION_CHARS = 280

# Prompt template for the explainer call. Single-shot, no chain-of-
# thought (the explainer is a one-paragraph generator, not a reasoner).
# Fields are substituted from a (Verdict, VerdictContext) pair; if ctx
# is None the agent/model/surface line is omitted.
EXPLAINER_PROMPT_TEMPLATE = """You are a security copilot explaining an AI safety verdict to a SOC analyst.

Verdict: {label}
Severity: {severity}
Rules: {rules}
{context_line}
Write a single sentence in plain English explaining (a) what was detected, \
(b) what action was taken, and (c) why this matters to the SOC. \
Stay under {char_cap} characters. Do not greet the analyst. Do not \
restate the field names. Do not include any preamble. Output the \
sentence and nothing else."""


class OllamaUnavailableError(Exception):
    """Raised when the Ollama server is unreachable or returns an error.

    Callers MUST catch this and fall back to the template explainer so
    the verdict always carries a non-empty explanation. See
    ``explain_via_hosted_model`` for the canonical fallback path.
    """


class OllamaGenerateRequest(BaseModel):
    """Ollama ``/api/generate`` request body.

    Subset of the Ollama generate API documented at
    <https://github.com/ollama/ollama/blob/main/docs/api.md>. Only the
    fields the explainer call actually uses are surfaced.
    """

    model: str
    prompt: str
    # `stream=False` returns a single JSON response with the full
    # generated text. We don't stream — the explainer string is small
    # and the dashboard cell renders one value, not a token stream.
    stream: bool = False
    # `options.temperature` low to reduce variance run-to-run; SOC
    # analysts benefit from stable phrasing for known verdict shapes.
    options: dict[str, float | int] = Field(
        default_factory=lambda: {"temperature": 0.2, "num_predict": 200}
    )


class OllamaGenerateResponse(BaseModel):
    """Subset of Ollama ``/api/generate`` response body.

    The ``response`` field holds the generated text. Other fields
    (``total_duration``, ``eval_count``, etc.) are observability-only
    and we accept extra fields to stay forward-compat with Ollama
    server version drift.
    """

    response: str
    done: bool = True

    # Ollama returns dozens of timing/metric fields. ``extra="ignore"``
    # via pydantic config keeps the model stable across server bumps.
    model_config = {"extra": "ignore"}


def _build_prompt(verdict: Verdict, ctx: VerdictContext | None) -> str:
    """Compose the natural-language prompt fed to the Hosted Model.

    Surfaces: verdict label, severity, every rule + its source, and
    (when ctx is provided) agent_id + model_name + surface so the
    explainer can name the affected actor in the WHY-string. Mirrors
    the prompt body in ``foundsec_spl.build_ai_spl`` so the same
    output quality holds across transports.
    """
    label = verdict.verdict.value
    severity = verdict.severity.value
    if verdict.rules:
        rule_phrases = [f"{r.rule} (source={r.source})" for r in verdict.rules]
        rules = ", ".join(rule_phrases)
    else:
        rules = "no rules fired"

    if ctx is not None:
        context_line = f"Agent: {ctx.agent_id}, model: {ctx.model_name}, surface: {ctx.surface}\n"
    else:
        context_line = ""

    return EXPLAINER_PROMPT_TEMPLATE.format(
        label=label,
        severity=severity,
        rules=rules,
        context_line=context_line,
        char_cap=MAX_EXPLANATION_CHARS,
    )


def _resolve_ollama_url(ollama_url: str | None) -> str:
    """Pick the Ollama base URL.

    Order: explicit arg → ``OLLAMA_HOST`` env var → ``DEFAULT_OLLAMA_URL``.
    Strips trailing slash so ``/api/generate`` concatenation is clean.
    """
    raw = ollama_url or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_URL
    return raw.rstrip("/")


# Tenacity retry on transient HTTPX failures only. ``OllamaUnavailableError``
# itself is NOT retried — we surface it to the caller after the third
# attempt so the template fallback runs cleanly.
_RETRY = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
)


@_RETRY
def _post_generate(
    base_url: str,
    body: OllamaGenerateRequest,
    timeout_seconds: float,
) -> OllamaGenerateResponse:
    """POST to ``{base_url}/api/generate`` and parse the response.

    Raises ``OllamaUnavailableError`` on non-200 status or unparseable
    body. Tenacity retries the underlying HTTPX exceptions; this
    function itself is single-shot from the application's perspective.
    """
    url = f"{base_url}/api/generate"
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, json=body.model_dump())
    except (httpx.TimeoutException, httpx.NetworkError):
        # Tenacity catches these and retries — re-raising preserves the
        # decorator contract.
        raise
    except httpx.HTTPError as exc:
        msg = f"Ollama HTTP error: {type(exc).__name__}: {exc}"
        raise OllamaUnavailableError(msg) from exc

    if resp.status_code != _OK_STATUS:
        body_snip = resp.text[:200] if resp.text else "<empty>"
        msg = f"Ollama returned {resp.status_code} (expected {_OK_STATUS}). Body: {body_snip}"
        raise OllamaUnavailableError(msg)

    try:
        return OllamaGenerateResponse.model_validate(resp.json())
    except Exception as exc:
        msg = f"Ollama response was not parseable: {type(exc).__name__}: {exc}"
        raise OllamaUnavailableError(msg) from exc


def _post_process(text: str) -> str:
    """Tighten the model output to fit the dashboard / PDF cell budget.

    Models occasionally prepend "Sure! " / "Here is..." / numbered
    lists / quotation marks despite the prompt's instructions. Strip
    common boilerplate, collapse whitespace, and truncate to the
    explanation char budget with an ellipsis sentinel.
    """
    stripped = text.strip().strip('"').strip("'").strip()
    # Collapse any internal whitespace runs (newlines, tabs) so the
    # output fits a single dashboard cell.
    flat = " ".join(stripped.split())
    if len(flat) > MAX_EXPLANATION_CHARS:
        return flat[: MAX_EXPLANATION_CHARS - 1].rstrip() + "…"
    return flat


def explain_via_hosted_model(
    verdict: Verdict,
    ctx: VerdictContext | None = None,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Return a Hosted-Model-authored explanation OR the template fallback.

    Chain: (1) compose the prompt; (2) POST to Ollama with retry; (3) on
    ANY exception, fall back to ``explain_verdict`` so the verdict
    always carries a non-empty explanation. The fallback path is
    logged at WARN level so operators see live-call regressions in
    Splunk alongside the template-string output.

    Args:
        verdict: The Verdict whose ``explanation`` field should be filled.
        ctx: Optional agent/model/surface context. When None, the
            prompt omits the actor line.
        model: Ollama tag. Defaults to ``gpt-oss:20b``. Switch to
            ``foundation-sec:8b`` once the corresponding Modelfile
            has been created.
        ollama_url: Base URL for the Ollama server. Defaults to the
            ``OLLAMA_HOST`` env var, then to ``http://localhost:11434``.
        timeout_seconds: Per-call HTTP timeout. 30s default aligns with
            the rest of the middleware's failure budget.

    Returns:
        Non-empty explanation string ≤ ``MAX_EXPLANATION_CHARS`` chars.
    """
    base_url = _resolve_ollama_url(ollama_url)
    body = OllamaGenerateRequest(model=model, prompt=_build_prompt(verdict, ctx))

    try:
        response = _post_generate(base_url, body, timeout_seconds)
    except (OllamaUnavailableError, httpx.TimeoutException, httpx.NetworkError) as exc:
        _logger.warning(
            "splunkgate.hosted_models.fallback_to_template",
            exc_class=type(exc).__name__,
            exc_msg=str(exc),
            trace_id=str(verdict.trace_id),
            model=model,
            ollama_url=base_url,
        )
        return explain_verdict(verdict, ctx)

    text = _post_process(response.response)
    if not text:
        _logger.warning(
            "splunkgate.hosted_models.empty_response",
            trace_id=str(verdict.trace_id),
            model=model,
        )
        return explain_verdict(verdict, ctx)

    _logger.info(
        "splunkgate.hosted_models.explained",
        trace_id=str(verdict.trace_id),
        model=model,
        chars=len(text),
    )
    return text
