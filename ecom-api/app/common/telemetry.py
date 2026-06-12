from __future__ import annotations

import logging

from fastapi import FastAPI

from app.config import get_settings

logger = logging.getLogger(__name__)


def setup_telemetry(app: FastAPI, service_name: str) -> None:
    """Enable OTLP export to OpsAI OTel Collector (architecture phase 2).

    Coexists with prometheus-fastapi-instrumentator `/metrics` during transition.
    Reads OTEL_* from ecom-api/.env via pydantic Settings (not raw os.environ).
    """
    settings = get_settings()
    if not settings.otel_enabled:
        logger.debug("OpenTelemetry disabled (set OTEL_ENABLED=true in ecom-api/.env)")
        return

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("OpenTelemetry packages missing; skip telemetry for %s", service_name)
        return

    endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": settings.app_env,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
        export_interval_millis=settings.otel_metric_export_interval_ms,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{endpoint}/v1/logs"))
    )
    root_logger = logging.getLogger()
    if not any(isinstance(handler, LoggingHandler) for handler in root_logger.handlers):
        otlp_handler = LoggingHandler(level=logging.NOTSET, logger_provider=log_provider)
        root_logger.addHandler(otlp_handler)

    LoggingInstrumentor().instrument(set_logging_format=False)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/metrics,/health")

    logger.info("OpenTelemetry enabled service=%s endpoint=%s", service_name, endpoint)
