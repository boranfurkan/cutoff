from audit import log


def test_parse_known_line():
    line = "2025-03-01 10:15:00.123 | INFO     | audit.log:record:17 - ada login"
    assert log.parse_line(line)["message"] == "ada login"


def test_non_record_line_is_ignored():
    assert log.parse_line("Traceback (most recent call last):") is None


def test_record_writes_a_line(tmp_path):
    path = tmp_path / "audit.log"
    log.open_log(str(path))
    log.record("ada", "login")
    log.logger.complete()
    assert "ada login" in path.read_text()
