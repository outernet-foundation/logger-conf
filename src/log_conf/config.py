from __future__ import annotations

import logging
import logging.config
import os
import socket
import sys
from pathlib import Path
from tempfile import mkdtemp
from types import ModuleType

from pythonjsonlogger.json import JsonFormatter

try:
    from . import _otlp
except ImportError:
    _otlp = None

_STANDARD_LOG_RECORD_ATTRS = frozenset({
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
})


class HumanFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%H:%M:%S")
        base = f"{timestamp} [{record.levelname.lower()}] {record.getMessage()}"
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_RECORD_ATTRS and not key.startswith("_")
        }
        if not extras:
            return base
        rendered_extras = " ".join(f"{key}={value}" for key, value in extras.items())
        return f"{base} {rendered_extras}"


def _resolve_log_file_path(requested: Path) -> Path:
    # Fall back to a tmp dir if the requested path isn't writable, so callers (e.g. an OpenAPI
    # dump on a dev machine without /var access) succeed without forcing every callsite to set
    # an override.
    try:
        requested.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return Path(mkdtemp(prefix=f"{requested.stem}-logs-")) / requested.name
    else:
        return requested


def configure_logging(
    service_name: str,
    *,
    service_namespace: str | None = None,
    instance_id: str | None = None,
    log_file_path: Path | None = None,
    uvicorn_logger_handlers: bool = False,
) -> Path | None:
    # stderr is always human-formatted (for the operator watching); the file, when requested,
    # is always JSON (the durable structured record, jq/agent-tail friendly); OTLP, when an
    # endpoint is configured and the [otlp] extra is installed, mirrors records to an aggregator.
    instance_id = instance_id or socket.gethostname()

    handlers: dict[str, dict[str, object]] = {
        "stream": {"class": "logging.StreamHandler", "formatter": "human", "stream": sys.stderr},
    }
    handler_names: list[str] = ["stream"]

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_module: ModuleType | None = _otlp
        if otlp_module is None:
            sys.stderr.write(
                "OTEL_EXPORTER_OTLP_ENDPOINT is set but log-conf[otlp] is not installed; skipping OTLP export.\n"
            )
        else:
            resource = otlp_module.build_resource(service_name, service_namespace, instance_id)
            handlers["otlp"] = {
                "()": lambda res=resource, ep=otlp_endpoint: otlp_module.build_handler(res, ep),
            }
            handler_names.append("otlp")

    resolved_log_file_path: Path | None = None
    if log_file_path is not None:
        resolved_log_file_path = _resolve_log_file_path(log_file_path)
        handlers["file"] = {
            "()": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": str(resolved_log_file_path),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        }
        handler_names.append("file")

    loggers: dict[str, dict[str, object]] = {}
    if uvicorn_logger_handlers:
        for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
            loggers[name] = {"handlers": handler_names, "level": "INFO", "propagate": False}

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "human": {"()": HumanFormatter},
            "json": {
                "()": JsonFormatter,
                "format": "%(levelname)s %(name)s %(message)s",
                "rename_fields": {"levelname": "level"},
                "timestamp": True,
                "static_fields": {"service": service_name},
            },
        },
        "handlers": handlers,
        "root": {"handlers": handler_names, "level": "INFO"},
        "loggers": loggers,
    })

    return resolved_log_file_path
