from typer.testing import CliRunner

from tool import main


def test_deploy_percent():
    r = CliRunner().invoke(main.app, ["deploy", "api", "--traffic", "25%"])
    assert r.exit_code == 0, r.output
    assert r.output.strip() == "deploying api at 0.25"


def test_dry_run():
    r = CliRunner().invoke(main.app, ["deploy", "api", "--dry-run"])
    assert r.output.strip() == "would deploy api at 1.00"


def test_subcommands():
    assert main.subcommands() == ["deploy", "version"]
