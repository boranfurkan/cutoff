from audit import log


def test_recorded_events_can_be_read_back(tmp_path):
    path = tmp_path / "audit.log"
    log.open_log(str(path))
    log.record("ada", "login")
    log.record("bob", "export-data")
    log.logger.complete()
    assert log.read_events(str(path)) == [("ada", "login"), ("bob", "export-data")]
