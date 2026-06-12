"""SplunkGate middleware config — frozen pydantic model.

Per architecture.md § "API schemas" → Config, the five fields locked here
are read by every Surface 1 middleware before any AI Defense / DefenseClaw
call. Fields default to safe-for-demo values; production deployments must
set `ai_defense_api_key` via env var or kwarg.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

__all__ = ["Config", "ExplainerBackend"]

# The four valid explainer routings. Default is "template" — pure-Python,
# zero dependencies, deterministic — which makes every test predictable
# and lets the middleware ship without Ollama installed. Operators flip
# to "ollama" once they have a Hosted Model running locally (or in a
# remote inference host reachable at ``OLLAMA_HOST``). "ai_spl" is the
# Splunk-native ``| ai`` SPL path documented in ADR-003a; it remains
# mock-default until a tenant confirms Splunk Hosted Models access.
ExplainerBackend = Literal["template", "ollama", "ai_spl"]


class Config(BaseModel):
    """Frozen configuration for every SplunkGate middleware class."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ai_defense_endpoint: str = Field(
        default="https://us.api.inspect.aidefense.security.cisco.com",
        description="Cisco AI Defense Inspection API regional endpoint.",
    )
    ai_defense_api_key: SecretStr | None = Field(
        default=None,
        description="Cisco AI Defense API key. None when SPLUNKGATE_AI_DEFENSE_MOCK=1.",
    )
    foundation_sec_enabled: bool = Field(
        default=True,
        description=(
            "Whether to populate Verdict.explanation with an explainer-generated "
            "string. False = leave explanation=None. True + explainer_backend "
            "selects the transport."
        ),
    )
    explainer_backend: ExplainerBackend = Field(
        default="template",
        description=(
            'Explainer transport. "template" = deterministic Python template '
            '(default, zero deps). "ollama" = real Hosted Model via local '
            "Ollama HTTP API (gpt-oss:20b by default; foundation-sec:8b once "
            'a Modelfile is created). "ai_spl" = Splunk Hosted Models via '
            "the ``| ai`` SPL command (ADR-003a Transport A; mock-default)."
        ),
    )
    explainer_model: str = Field(
        default="gpt-oss:20b",
        description=(
            'Hosted Model tag passed to Ollama when explainer_backend="ollama". '
            "Defaults to OpenAI's open-weight gpt-oss-20b (Apache-2.0, in the "
            "Ollama library out-of-the-box)."
        ),
    )
    explainer_ollama_url: str | None = Field(
        default=None,
        description=(
            "Ollama base URL when explainer_backend=ollama. None falls through "
            "to the ``OLLAMA_HOST`` env var, then to ``http://localhost:11434``."
        ),
    )
    escalate_on_first_pass_hit: bool = Field(
        default=True,
        description="If splunklib.security first-pass flags risk, skip AI Defense call.",
    )
    splunklib_security_first_pass: bool = Field(
        default=True,
        description="Whether to run splunklib.security as the cheap first-pass scan.",
    )
