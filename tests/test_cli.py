"""Tests for the PurpleLab CLI (Milestone 6 behavior)."""

import pytest
from typer.testing import CliRunner

from purplelab import __version__
from purplelab.cli import app
from purplelab.lab import LabError
from purplelab.targets import DockerUnavailableError
from simulations import t1016_system_network_configuration_discovery as t1016
from simulations import t1057_process_discovery as t1057
from simulations import t1082_system_information_discovery as t1082
from simulations import t1087_account_discovery as t1087

runner = CliRunner()


def test_version_flag_prints_version_and_exits_cleanly() -> None:
    """`purplelab --version` should print the version and exit 0."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_list_shows_registered_simulations() -> None:
    """`purplelab list` should show all four built-in simulations."""
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "T1082" in result.stdout
    assert "System Information Discovery" in result.stdout
    assert "T1057" in result.stdout
    assert "Process Discovery" in result.stdout
    assert "T1087" in result.stdout
    assert "Account Discovery" in result.stdout
    assert "T1016" in result.stdout
    assert "System Network Configuration Discovery" in result.stdout


def test_info_shows_simulation_metadata() -> None:
    """`purplelab info T1082` should display key simulation metadata."""
    result = runner.invoke(app, ["info", "T1082"])

    assert result.exit_code == 0
    assert "T1082" in result.stdout
    assert "System Information Discovery" in result.stdout
    assert "Discovery" in result.stdout
    assert "Linux" in result.stdout
    assert "Not configured" in result.stdout


@pytest.mark.parametrize(
    ("technique_id", "expected_name"),
    [
        ("T1057", "Process Discovery"),
        ("T1087", "Account Discovery"),
        ("T1016", "System Network Configuration Discovery"),
    ],
)
def test_info_shows_metadata_for_each_new_simulation(
    technique_id: str, expected_name: str
) -> None:
    """`purplelab info <TECHNIQUE>` should work for each Milestone 6 simulation."""
    result = runner.invoke(app, ["info", technique_id])

    assert result.exit_code == 0
    assert technique_id in result.stdout
    assert expected_name in result.stdout


def test_info_reports_unknown_simulation_gracefully() -> None:
    """`purplelab info T9999` should fail cleanly with a non-zero exit code."""
    result = runner.invoke(app, ["info", "T9999"])

    assert result.exit_code != 0
    assert "T9999" in result.output
    # A controlled typer.Exit is expected; anything else means an unhandled traceback.
    assert isinstance(result.exception, SystemExit)


def test_run_reports_success_on_a_supported_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """`purplelab run T1082` should succeed and show collected system info."""
    monkeypatch.setattr(t1082.platform, "system", lambda: "Linux")
    monkeypatch.setattr(t1082.platform, "release", lambda: "6.8.0")
    monkeypatch.setattr(t1082.platform, "machine", lambda: "x86_64")

    result = runner.invoke(app, ["run", "T1082"])

    assert result.exit_code == 0
    assert "T1082" in result.stdout
    assert "Success" in result.stdout
    assert "x86_64" in result.stdout


def test_run_reports_failure_on_an_unsupported_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """`purplelab run T1082` should fail cleanly on an incompatible host platform."""
    monkeypatch.setattr(t1082.platform, "system", lambda: "Windows")

    result = runner.invoke(app, ["run", "T1082"])

    assert result.exit_code != 0
    assert "Failed" in result.stdout
    assert isinstance(result.exception, SystemExit)


@pytest.mark.parametrize(
    "module",
    [t1057, t1087, t1016],
)
def test_run_reports_failure_locally_for_linux_only_simulations(
    module, monkeypatch: pytest.MonkeyPatch
) -> None:
    """New Linux-only simulations should also fail predictably on a non-Linux host."""
    monkeypatch.setattr(module.platform, "system", lambda: "Windows")

    result = runner.invoke(app, ["run", module.SIMULATION.technique_id, "--target", "local"])

    assert result.exit_code != 0
    assert "Failed" in result.stdout


def test_run_renders_generic_result_label_not_technique_specific_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI output must use a generic 'Result:' label, not per-technique branching."""
    monkeypatch.setattr(t1057.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        t1057,
        "collect_process_information",
        lambda: {"process_count": "5", "sample_process_names": "bash, sshd"},
    )

    result = runner.invoke(app, ["run", "T1057", "--target", "local"])

    assert result.exit_code == 0
    assert "Result:" in result.stdout
    assert "Process count:" in result.stdout
    assert "bash, sshd" in result.stdout


def test_run_reports_unknown_simulation_gracefully() -> None:
    """`purplelab run T9999` should fail cleanly with a non-zero exit code."""
    result = runner.invoke(app, ["run", "T9999"])

    assert result.exit_code != 0
    assert "T9999" in result.output
    assert isinstance(result.exception, SystemExit)


def test_run_docker_target_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """`purplelab run T1082 --target docker` should succeed when Docker is mocked."""
    monkeypatch.setattr(
        "purplelab.cli.DockerTarget.run",
        lambda self, simulation: {"os": "Linux", "release": "6.8.0", "architecture": "x86_64"},
    )

    result = runner.invoke(app, ["run", "T1082", "--target", "docker"])

    assert result.exit_code == 0
    assert "T1082" in result.stdout
    assert "Docker" in result.stdout
    assert "Linux" in result.stdout


def test_run_docker_target_reports_infrastructure_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mocked Docker infrastructure failure should exit non-zero with no traceback."""

    def _raise(self, simulation):
        raise DockerUnavailableError("Docker is installed, but the Docker engine is not reachable.")

    monkeypatch.setattr("purplelab.cli.DockerTarget.run", _raise)

    result = runner.invoke(app, ["run", "T1082", "--target", "docker"])

    assert result.exit_code != 0
    assert "Failed" in result.stdout
    assert isinstance(result.exception, SystemExit)


@pytest.mark.parametrize(
    ("technique_id", "fake_data"),
    [
        ("T1057", {"process_count": "5", "sample_process_names": "bash, sshd"}),
        (
            "T1087",
            {"current_user": "root", "local_account_count": "2", "sample_local_accounts": "root, ci"},
        ),
        (
            "T1016",
            {"hostname": "lab-target", "local_ip": "172.17.0.2", "interface_count": "1"},
        ),
    ],
)
def test_run_docker_target_reports_success_for_new_simulations(
    technique_id: str, fake_data: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each new Milestone 6 simulation should render generically over Docker."""
    monkeypatch.setattr("purplelab.cli.DockerTarget.run", lambda self, simulation: fake_data)

    result = runner.invoke(app, ["run", technique_id, "--target", "docker"])

    assert result.exit_code == 0
    assert technique_id in result.stdout
    assert "Docker" in result.stdout
    for value in fake_data.values():
        assert value in result.stdout


def test_lab_build_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """`purplelab lab build` should report success when the build is mocked."""
    monkeypatch.setattr("purplelab.cli.build_lab_image", lambda: None)

    result = runner.invoke(app, ["lab", "build"])

    assert result.exit_code == 0
    assert "Built" in result.stdout


def test_lab_build_reports_failure_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    """`purplelab lab build` should fail cleanly when Docker is unavailable."""

    def _raise():
        raise LabError("Docker CLI was not found.")

    monkeypatch.setattr("purplelab.cli.build_lab_image", _raise)

    result = runner.invoke(app, ["lab", "build"])

    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit)


def test_lab_status_reports_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """`purplelab lab status` should report readiness when everything is mocked available."""
    monkeypatch.setattr("purplelab.cli.docker_cli_available", lambda: True)
    monkeypatch.setattr("purplelab.cli.docker_daemon_available", lambda: True)
    monkeypatch.setattr("purplelab.cli.lab_image_built", lambda: True)

    result = runner.invoke(app, ["lab", "status"])

    assert result.exit_code == 0
    assert "available" in result.stdout.lower()


def test_lab_status_reports_missing_docker_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """`purplelab lab status` should fail cleanly when Docker CLI is missing."""
    monkeypatch.setattr("purplelab.cli.docker_cli_available", lambda: False)

    result = runner.invoke(app, ["lab", "status"])

    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit)
