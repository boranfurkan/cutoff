from typer.testing import CliRunner

from tool.main import app


def test_export_iso_date():
    r = CliRunner().invoke(app, ["export", "2025-03-01"])
    assert r.exit_code == 0 and r.output.strip() == "exporting csv since 2025-03-01"


def test_export_json():
    r = CliRunner().invoke(app, ["export", "2025-03-01T08:30:00", "--fmt", "json"])
    assert r.output.strip() == "exporting json since 2025-03-01"


def test_formats():
    assert CliRunner().invoke(app, ["formats"]).output.strip() == "csv json"


def test_words_rejected():
    assert CliRunner().invoke(app, ["export", "yesterday"]).exit_code == 2
