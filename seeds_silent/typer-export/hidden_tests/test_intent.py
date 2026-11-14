from typer.testing import CliRunner

from tool.main import app


def test_bare_number_is_rejected():
    assert CliRunner().invoke(app, ["export", "1700000000"]).exit_code == 2


def test_iso_date_still_accepted():
    assert CliRunner().invoke(app, ["export", "2025-03-01"]).exit_code == 0
