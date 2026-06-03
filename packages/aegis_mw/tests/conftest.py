"""Test session config — shared OTel TracerProvider + InMemorySpanExporter.

Same pattern as aegis_core's conftest: OTel set_tracer_provider is process-
global and set-once. We need a shared provider so emit_verdict_event events
actually land in our exporter.
"""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

_SHARED_EXPORTER = InMemorySpanExporter()
_provider = trace.get_tracer_provider()
if isinstance(_provider, TracerProvider):
    _provider.add_span_processor(SimpleSpanProcessor(_SHARED_EXPORTER))
else:
    _provider = TracerProvider()
    _provider.add_span_processor(SimpleSpanProcessor(_SHARED_EXPORTER))
    trace.set_tracer_provider(_provider)


@pytest.fixture
def otel_exporter() -> InMemorySpanExporter:
    """Yield the shared exporter, clearing before each test."""
    _SHARED_EXPORTER.clear()
    return _SHARED_EXPORTER
