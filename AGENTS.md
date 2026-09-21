# logger-conf

## What this is

`logger-conf` (import `logger_conf`) is an opinionated stdlib-`logging` configuration: one call (`configure_logging`) stands up a coherent logging topology over Python's standard library `logging` — it does **not** replace the log-call API (callers still write `logger.info(...)`). It decides where records go and how they're formatted.

## The three-sink policy

`configure_logging` wires up to three sinks, and which sinks are active is deliberate:

- **stderr stream, always, human-formatted** (`HumanFormatter`: `HH:MM:SS [level] msg key=value`). For the operator watching the terminal now.
- **JSONL file, when `log_file_path` is passed.** Rotating (`RotatingFileHandler`). This is the **durable structured record** — `jq`-able, agent-tail-friendly. It is *always* JSON when it exists (never human text). The local file is the durable record of truth; OTLP (below) is a best-effort remote mirror, never a substitute for file structure. Reason: OTLP can drop records (batching, collector down, network); if structure lived only in OTLP and the file were human text, structured data would be lost on any OTLP hiccup.
- **OTLP export, optional, when `OTEL_EXPORTER_OTLP_ENDPOINT` is set AND the `[otlp]` extra is installed.** Mirrors records to a collector (Loki/Grafana). Behind an optional extra so consumers that don't aggregate (CLI scripts) don't drag in `opentelemetry-sdk`.

This policy supersedes the two originals it was unified from: the pulsar variant (JSON file + human stderr, no OTLP) and the placeframe variant (human stderr + OTLP, optional human file). The unification keeps pulsar's always-JSON-file strength and adds placeframe's OTLP/robustness — at the cost of reverting placeframe's file to JSON (acceptable: most placeframe services pass no `log_file_path`, so the blast radius is the few that do, which gain a durable structured record they previously lacked).

## OTLP optional-extra design

opentelemetry is **not** a core dependency. The import lives behind a wrapper submodule (`_otlp.py`) that imports opentelemetry unconditionally; `config.py` imports `_otlp` under `try/except ImportError`. A consumer without `[otlp]` never pays the import cost or the dependency. If the env var is set but the extra isn't installed, `configure_logging` prints a one-line warning to stderr and skips OTLP rather than crashing — the operator asked for export but didn't install the machinery.

## Dependencies

One core dependency: `python-json-logger` (stdlib has no JSON formatter; hand-rolling one reinvents exception serialization and extras filtering that `python-json-logger` handles robustly). Unlike `bashrun` (zero-dep by design — its job is wrapping `subprocess`), a logging-configuration package legitimately needs a JSON formatter. `[otlp]` is the only optional extra.

## Attribution

Resource attributes (`service.name`, `service.namespace` when passed, `service.instance.id`, `service.version` from `SERVICE_VERSION`, `deployment.environment.name` from `DEPLOYMENT_ENVIRONMENT`, `container.name` from `HOSTNAME`) are attached to OTLP records. `service_namespace` is parameterized — each caller passes its own (pulsar→`"pulsar"`, placeframe→`"placeframe"`, etc.); the placeframe variant's hardcoded namespace became a parameter here.

## Provenance

`HumanFormatter` and `_STANDARD_LOG_RECORD_ATTRS` existed byte-identically in both pulsar's and placeframe's `common` packages; this is now their canonical home. See `design/workspace-redesign.md` in the pulsar repo and the `pylogconf`/`logconf` extraction discussion for the convergence rationale.

## Name

The distribution and import renamed from `logconf`/`logconf` to `logger-conf`/`logger_conf` (2026-09-20): the bare PyPI name is owned by an unrelated same-purpose package, and `placeframe-common`'s published wheel required `logconf[otlp]` — resolving onto the foreign code. Both levels renamed together per the import==distribution-name convention; the GitHub repo renamed with it (`logconf` → `logger-conf`, redirects cover old links). An earlier same-day ruling of `log-conf` was superseded before anything published — no artifact ever carried it.

## Release flow

Publishing rides `ci.yml`'s `publish` job on every push to `main` (gated on the check job): pubpkg — invoked uvx-isolated from a pinned git ref, never a project dependency — computes the plan from the tag ledger and path-diff, patches the version ephemerally, and publishes to PyPI under OIDC trusted publishing (pending publisher bound to `ci.yml`, no environment). The committed `pyproject.toml` version is permanently the `0.0.0.dev0` sentinel; the `logger-conf-v*` tags are the version ledger (first release `0.1.0`, patch-auto thereafter). API-breaking changes ship with a manually bumped version — patch-auto assumes additive changes.
