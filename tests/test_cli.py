"""Tests for the PurpleLab CLI (Milestone 1 behavior)."""

from typer.testing import CliRunner

from purplelab import __version__
from purplelab.cli import app

runner = CliRunner()


def test_version_flag_prints_version_and_exits_cleanly() -> None:
    """`purplelab --version` should print the version and exit 0."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_list_reports_no_simulations_installed() -> None:
    """`purplelab list` should report no simulations exist yet."""
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No simulations installed." in result.stdout
