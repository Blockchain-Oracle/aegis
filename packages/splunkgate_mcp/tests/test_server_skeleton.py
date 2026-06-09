"""Behavioral tests for story-mcp-01: SplunkGate MCP server skeleton."""

from __future__ import annotations

import splunkgate_mcp
from splunkgate_core.verdict import Verdict
from splunkgate_mcp.otel import MCP_PROTOCOL_VERSION, build_span_attributes
from splunkgate_mcp.schemas import VERDICT_OUTPUT_SCHEMA


def test_version_is_0_1_0() -> None:
    """Package version bumped from 0.0.1 stub to 0.1.0 first-real-skeleton."""
    assert splunkgate_mcp.__version__ == "0.1.0"


def test_verdict_output_schema_matches_pydantic() -> None:
    """schemas.VERDICT_OUTPUT_SCHEMA must equal Verdict.model_json_schema()."""
    assert Verdict.model_json_schema() == VERDICT_OUTPUT_SCHEMA


def test_otel_span_attributes_contains_required_keys() -> None:
    """build_span_attributes returns dict with the 3 required keys."""
    attrs = build_span_attributes(session_id="abc123", method_name="tools/call")

    assert attrs["mcp.method.name"] == "tools/call"
    assert attrs["mcp.session.id"] == "abc123"
    assert attrs["mcp.protocol.version"] == "2025-11-25"


def test_otel_span_attributes_protocol_version_is_2025_11_25() -> None:
    """MCP protocol version is the Stable 2025-11-25 (NOT 2025-03-26)."""
    assert MCP_PROTOCOL_VERSION == "2025-11-25"
