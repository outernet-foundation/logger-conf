# Wrapper module (suppression boundary): the opentelemetry SDK exposes its public logging API
# under underscore-prefixed modules (opentelemetry._logs, opentelemetry.sdk._logs,
# ..._log_exporter), so the import-private-name lint is unavoidable here. config.py imports this
# module behind a try/except so consumers without the [otlp] extra never pay the import cost; the
# per-file ignore for import-private-name lives in ruff.toml.
from __future__ import annotations

import logging
import os

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource


def build_resource(service_name: str, service_namespace: str | None, instance_id: str) -> Resource:
    attributes: dict[str, str] = {
        "service.name": service_name,
        "service.instance.id": instance_id,
        "service.version": os.environ.get("SERVICE_VERSION", "unknown"),
        "deployment.environment.name": os.environ.get("DEPLOYMENT_ENVIRONMENT", "development"),
        "container.name": os.environ.get("HOSTNAME", instance_id),
    }
    if service_namespace is not None:
        attributes["service.namespace"] = service_namespace
    return Resource.create(attributes)


def build_handler(resource: Resource, endpoint: str) -> LoggingHandler:
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True)))
    set_logger_provider(provider)
    return LoggingHandler(level=logging.NOTSET, logger_provider=provider)
