"""Tests for the PurpleLab CLI (Milestone 3 behavior)."""

from typer.testing import CliRunner

from purplelab import __version__
from purplelab.cli import app

runner = CliRunner()


def test_version_flag_prints_version_and_exits_cleanly() -> None:
    """`purplelab --version` should print the version and exit 0."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_list_shows_registered_simulations() -> None:
    """`purplelab list` should show T1082 sourced from the registry."""
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "T1082" in result.stdout
    assert "System Information Discovery" in result.stdout


def test_info_shows_simulation_metadata() -> None:
    """`purplelab info T1082` should display key simulation metadata."""
    result = runner.invoke(app, ["info", "T1082"])

    assert result.exit_code == 0
    assert "T1082" in result.stdout
    assert "System Information Discovery" in result.stdout
    assert "Discovery" in result.stdout
    assert "Linux" in result.stdout
    assert "Not configured" in result.stdout


def test_info_reports_unknown_simulation_gracefully() -> None:
    """`purplelab info T9999` should fail cleanly with a non-zero exit code."""
    result = runner.invoke(app, ["info", "T9999"])

    assert result.exit_code != 0
    assert "T9999" in result.output
    # A controlled typer.Exit is expected; anything else means an unhandled traceback.
    assert isinstance(result.exception, SystemExit)
