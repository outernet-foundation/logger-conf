# log-conf

Opinionated stdlib-`logging` configuration for Python. One call — `configure_logging("my-service")` — stands up a coherent logging topology over the standard library `logging` module (it does *not* replace the log-call API; callers still write `logger.info(...)`). It decides where records go and how they're formatted:

- a **human-readable stderr stream** (`HH:MM:SS [level] msg key=value`) for the operator watching now,
- an optional **durable structured JSONL file** for later inspection, `jq`, and agent tail-grep,
- optional **OTLP export** (to Loki/Grafana) for cross-service aggregation, behind an `[otlp]` extra.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync            # core only (human stderr + JSON file)
uv sync --extra otlp   # add OTLP export support
```

## Usage

```python
from log_conf import configure_logging
from logging import getLogger

configure_logging("my-service", log_file_path=Path("logs/my-service.jsonl"))
logger = getLogger(__name__)
logger.info("started", extra={"port": 8080})
```

OTLP export activates automatically when `OTEL_EXPORTER_OTLP_ENDPOINT` is set and `log-conf[otlp]` is installed. Attribution (`service_namespace`, etc.) and uvicorn-logger wiring are optional kwargs; see `configure_logging`'s signature.

## Consuming from another repo

Install from PyPI:

```toml
[project]
dependencies = ["log-conf>=0.1.0"]
# for OTLP: dependencies = ["log-conf[otlp]>=0.1.0"]
```

To test an unreleased change, pin the repo at a git ref in a scratch branch instead (`log-conf = { git = "https://github.com/outernet-foundation/logconf.git", rev = "<sha>" }` under `[tool.uv.sources]`) and drop the pin when the release lands.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv run pytest
```
