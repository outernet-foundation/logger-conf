import json
import logging
from pathlib import Path

from logger_conf import HumanFormatter, configure_logging


def _make_record(message: str, **extras: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1, msg=message, args=None, exc_info=None
    )
    for key, value in extras.items():
        setattr(record, key, value)
    return record


class TestHumanFormatter:
    def test_renders_timestamp_level_message(self):
        formatted = HumanFormatter().format(_make_record("hello"))
        assert formatted.endswith("[info] hello")
        assert formatted[:8].count(":") == 2

    def test_appends_extras_as_key_value_pairs(self):
        formatted = HumanFormatter().format(_make_record("hello", container="foo", count=3))
        suffix = formatted.split("[info] hello ", 1)[1]
        assert "container=foo" in suffix
        assert "count=3" in suffix

    def test_omits_extras_when_none(self):
        formatted = HumanFormatter().format(_make_record("hello"))
        assert " " not in formatted.split("[info] hello")[1]


class TestConfigureLogging:
    def test_writes_json_lines_with_service_field(self, tmp_path: Path):
        log_file = tmp_path / "svc.jsonl"
        returned = configure_logging("svc", log_file_path=log_file)
        assert returned == log_file

        logging.getLogger("svc").info("did a thing", extra={"event": "thing_done"})

        for handler in logging.getLogger().handlers:
            handler.flush()
        lines = [line for line in log_file.read_text().splitlines() if line.strip()]
        assert lines, "expected at least one JSON log line"
        record = json.loads(lines[-1])
        assert record["service"] == "svc"
        assert record["level"] == "INFO"
        assert record["event"] == "thing_done"
