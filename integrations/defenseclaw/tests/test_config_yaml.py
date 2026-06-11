"""Behavioural tests for the SplunkGate x DefenseClaw drop-in YAML (story-dc-01)."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

_YAML_PATH = Path(__file__).parent.parent / "examples" / "defenseclaw.yaml"
_README_PATH = Path(__file__).parent.parent / "README.md"
_SOURCETYPE_VERDICT = "cisco_ai_defense:splunkgate_verdict"
_SOURCETYPE_JUDGE = "cisco_ai_defense:splunkgate_judge"


@pytest.fixture(scope="module")
def config() -> dict[str, object]:
    """Parse the YAML once per module."""
    return cast("dict[str, object]", yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def hec_sink(config: dict[str, object]) -> dict[str, object]:
    """Return the single `splunk_hec` audit sink entry."""
    audit = cast("dict[str, object]", config["audit"])
    sinks = cast("list[dict[str, object]]", audit["sinks"])
    hec = [s for s in sinks if s.get("type") == "splunk_hec"]
    assert len(hec) == 1, "exactly one splunk_hec sink must be present"
    return hec[0]


def test_yaml_parses_to_a_dict(config: dict[str, object]) -> None:
    """Sanity check — the YAML is well-formed and decodes to a mapping."""
    assert isinstance(config, dict)
    assert "audit" in config


def test_sink_type_is_splunk_hec(hec_sink: dict[str, object]) -> None:
    """The single sink must declare `type: splunk_hec` verbatim."""
    assert hec_sink["type"] == "splunk_hec"


def test_sourcetype_is_canonical_splunkgate_verdict(hec_sink: dict[str, object]) -> None:
    """sourcetype must be the exact ADR-005 string — the SOC pivot key."""
    assert hec_sink["sourcetype"] == _SOURCETYPE_VERDICT


def test_source_type_overrides_route_judge_and_verdict_streams(
    hec_sink: dict[str, object],
) -> None:
    """Both stream→sourcetype overrides must be present and canonical."""
    overrides = cast("dict[str, str]", hec_sink["source_type_overrides"])
    assert overrides["guardrail-verdict"] == _SOURCETYPE_VERDICT
    assert overrides["llm-judge-response"] == _SOURCETYPE_JUDGE


def test_endpoint_and_token_use_splunkgate_env_var_names(
    hec_sink: dict[str, object],
) -> None:
    """env-var names are load-bearing — they match docs/architecture.md § Coding standards rule 6."""
    assert "${SPLUNKGATE_SPLUNK_HEC_URL}" in cast("str", hec_sink["endpoint"])
    assert "${SPLUNKGATE_SPLUNK_HEC_TOKEN}" in cast("str", hec_sink["token"])
    assert "${SPLUNKGATE_SPLUNK_INDEX}" in cast("str", hec_sink["index"])


def test_defenseclaw_upstream_defaults_preserved(hec_sink: dict[str, object]) -> None:
    """Defaults match internal/audit/sinks/splunk_hec.go lines 235-243 verbatim."""
    assert hec_sink["batch_size"] == 50
    assert hec_sink["flush_interval_s"] == 5
    assert hec_sink["circuit_breaker_threshold"] == 5
    assert hec_sink["circuit_breaker_cooldown_s"] == 60
    assert hec_sink["max_retries"] == 3


def test_verify_tls_overrides_to_secure_default(hec_sink: dict[str, object]) -> None:
    """SplunkGate flips `verify_tls` to True per CLAUDE.md hard rule (no verify=False in production)."""
    assert hec_sink["verify_tls"] is True


def test_source_field_preserves_defenseclaw_provenance(hec_sink: dict[str, object]) -> None:
    """We override sourcetype but keep `source: splunkgate` — analyst-visible provenance label."""
    assert hec_sink["source"] == "splunkgate"


def test_readme_cites_pinned_defenseclaw_commit() -> None:
    """README must pin the exact commit, not 'latest' — v0.6.6+ may rename sink fields."""
    text = _README_PATH.read_text(encoding="utf-8")
    assert "e1cb4d93fba70f5ffba8052ee6cfc696abdf125f" in text


def test_readme_credits_defenseclaw_apache_license() -> None:
    """The README must credit DefenseClaw upstream under Apache-2.0."""
    text = _README_PATH.read_text(encoding="utf-8")
    assert "Apache" in text


def test_readme_references_canonical_sourcetype_at_least_twice() -> None:
    """BDD criterion 1 — sourcetype mentioned in config + verification sections."""
    text = _README_PATH.read_text(encoding="utf-8")
    assert text.count(_SOURCETYPE_VERDICT) >= 2


def test_readme_carries_no_fork_disclaimer() -> None:
    """The 'we do not fork DefenseClaw' disclaimer is the licensing wedge."""
    text = _README_PATH.read_text(encoding="utf-8")
    assert "does not fork" in text.lower() or "config delta" in text.lower()
