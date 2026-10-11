from __future__ import annotations

from threading import Lock

from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

from app.config import settings

if settings.ENABLE_OTEL:
    otel_metrics.set_meter_provider(MeterProvider(
        resource=Resource.create({'service.name': 'agentic-chargeback-assistant'}),
    ))

_meter = otel_metrics.get_meter('agentic_chargeback')
_counter = _meter.create_counter('chargeback_events_total', description='Chargeback processing event counts')


class Metrics:
    def __init__(self):
        self.values: dict[str, float] = {}
        self._lock = Lock()

    def increment(self, name: str, value: float = 1.0) -> None:
        _counter.add(value, {'event': name})
        with self._lock:
            self.values[name] = self.values.get(name, 0.0) + value

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            return dict(self.values)


metrics = Metrics()
