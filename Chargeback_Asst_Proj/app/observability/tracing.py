from __future__ import annotations

from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode

from app.config import settings

_configured = False


def configure_tracing() -> None:
    global _configured
    if _configured or not settings.ENABLE_OTEL:
        return
    provider = TracerProvider(resource=Resource.create({'service.name': 'agentic-chargeback-assistant'}))
    if settings.ENABLE_OTEL_CONSOLE_EXPORTER:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _configured = True


configure_tracing()
_tracer = trace.get_tracer('agentic_chargeback')


@contextmanager
def trace_span(name: str, **attrs):
    with _tracer.start_as_current_span(name) as span:
        for key, value in attrs.items():
            if value is not None and isinstance(value, (str, bool, int, float)):
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
