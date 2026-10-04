# logger-conf

## What this is

`logger-conf` (import `logger_conf`) is an opinionated stdlib-`logging` configuration: one call (`configure_logging`) stands up a coherent logging topology over Python's standard library `logging` — it does **not** replace the log-call API (callers still write `logger.info(...)`). It decides where records go and how they're formatted.

## The three-sink policy

`configure_logging` wires up to three sinks, and which sinks are active is deliberate:

- **stderr stream, always, human-formatted** (`HumanFormatter`: `HH:MM:SS [level] msg key=value`). For the operator watching the terminal now.
- **JSONL file, when `log_file_path` is passed.** Rotating (`RotatingFileHandler`). Always JSON when it exists, never human text — the local file is the durable structured record (`jq`-able, agent-tail-friendly); OTLP is a best-effort remote mirror, never a substitute for file structure, because OTLP can drop records (batching, collector down, network) and structure that lived only in OTLP would be lost on any hiccup.
- **OTLP export, optional, when `OTEL_EXPORTER_OTLP_ENDPOINT` is set AND the `[otlp]` extra is installed.** Mirrors records to a collector (Loki/Grafana). Behind an optional extra so consumers that don't aggregate (CLI scripts) don't drag in `opentelemetry-sdk`.

## OTLP optional-extra design

opentelemetry is **not** a core dependency. The import lives behind a wrapper submodule (`_otlp.py`) that imports opentelemetry unconditionally; `config.py` imports `_otlp` under `try/except ImportError`. A consumer without `[otlp]` never pays the import cost or the dependency. If the env var is set but the extra isn't installed, `configure_logging` prints a one-line warning to stderr and skips OTLP rather than crashing — the operator asked for export but didn't install the machinery.

## Dependencies

One core dependency: `python-json-logger` (stdlib has no JSON formatter; hand-rolling one reinvents exception serialization and extras filtering that `python-json-logger` handles robustly). Unlike `bashrun` (zero-dep by design — its job is wrapping `subprocess`), a logging-configuration package legitimately needs a JSON formatter. `[otlp]` is the only optional extra.

## Attribution

Resource attributes (`service.name`, `service.namespace` when passed, `service.instance.id`, `service.version` from `SERVICE_VERSION`, `deployment.environment.name` from `DEPLOYMENT_ENVIRONMENT`, `container.name` from `HOSTNAME`) are attached to OTLP records. `service_namespace` is parameterized — each caller passes its own.

## Release flow

release-devkit's `AGENTS.md` owns the three-workflow contract; this repo follows it unchanged. Repo-specific facts: release-devkit is never a project dependency, and API-breaking changes ship with a manually bumped `major_minor` (patch-auto assumes additive changes).
