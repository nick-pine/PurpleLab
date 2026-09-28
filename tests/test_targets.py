"""Tests for PurpleLab execution targets (Milestone 5 behavior).

Docker interactions are always mocked at the `subprocess.run` boundary --
these tests must never require a real Docker daemon.
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from purplelab.engine import SimulationExecutionError
from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.registry import Simulation
from purplelab.targets import (
    LAB_IMAGE,
    DockerLabImageMissingError,
    DockerTarget,
    DockerUnavailableError,
    LocalTarget,
)


def _make_simulation(technique_id: str = "T1082") -> Simulation:
    metadata = SimulationMetadata(
        id="fake-simulation",
        technique_id=technique_id,
        name="Fake Simulation",
        description="A fake simulation used for target tests.",
        tactic=Tactic.DISCOVERY,
        platform=Platform.LINUX,
        risk=RiskLevel.LOW,
        expected_telemetry=("process creation",),
    )
    return Simulation(metadata=metadata, run=lambda: {"os": "Linux"})


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def test_local_target_calls_simulation_run() -> None:
    """LocalTarget delegates directly to the simulation's run callable."""
    simulation = _make_simulation()

    result = LocalTarget().run(simulation)

    assert result == {"os": "Linux"}


def test_docker_target_builds_safe_argument_list() -> None:
    """The Docker command must be a fixed argv list, never a shell string."""
    simulation = _make_simulation("T1082")

    with patch("purplelab.targets.subprocess.run") as mock_run:
        mock_run.return_value = _completed(stdout=json.dumps({"os": "Linux"}))

        DockerTarget().run(simulation)

    args, kwargs = mock_run.call_args
    command = args[0]

    assert command[0] == "docker"
    assert command[1] == "run"
    assert command[-2:] == [LAB_IMAGE, "T1082"]
    assert "--rm" in command
    assert "--network" in command and command[command.index("--network") + 1] == "none"
    assert "--cap-drop" in command and command[command.index("--cap-drop") + 1] == "ALL"
    assert "--security-opt" in command
    assert command[command.index("--security-opt") + 1] == "no-new-privileges"
    assert "--read-only" in command
    assert "--privileged" not in command
    assert "-v" not in command and "--volume" not in command
    assert "--network" in command  # never host networking
    assert "host" not in command
    assert "shell" not in kwargs
    assert kwargs["timeout"] > 0
    assert kwargs["capture_output"] is True


def test_docker_target_returns_structured_data_on_success() -> None:
    """A successful container run parses JSON stdout into structured data."""
    simulation = _make_simulation()

    with patch("purplelab.targets.subprocess.run") as mock_run:
        mock_run.return_value = _completed(
            stdout=json.dumps({"os": "Linux", "release": "6.8.0", "architecture": "x86_64"})
        )

        result = DockerTarget().run(simulation)

    assert result == {"os": "Linux", "release": "6.8.0", "architecture": "x86_64"}


def test_docker_target_raises_when_docker_cli_missing() -> None:
    """A missing `docker` executable becomes a clean DockerUnavailableError."""
    simulation = _make_simulation()

    with patch("purplelab.targets.subprocess.run", side_effect=FileNotFoundError()):
        with pytest.raises(DockerUnavailableError):
            DockerTarget().run(simulation)


def test_docker_target_raises_when_daemon_unavailable() -> None:
    """A Docker-daemon-unreachable error is surfaced cleanly."""
    simulation = _make_simulation()

    with patch("purplelab.targets.subprocess.run") as mock_run:
        mock_run.return_value = _completed(
            returncode=1, stderr="Cannot connect to the Docker daemon at unix:///var/run/docker.sock"
        )

        with pytest.raises(DockerUnavailableError):
            DockerTarget().run(simulation)


def test_docker_target_raises_when_image_missing() -> None:
    """A missing lab image is surfaced as DockerLabImageMissingError."""
    simulation = _make_simulation()

    with patch("purplelab.targets.subprocess.run") as mock_run:
        mock_run.return_value = _completed(
            returncode=125, stderr=f"Unable to find image '{LAB_IMAGE}' locally"
        )

        with pytest.raises(DockerLabImageMissingError):
            DockerTarget().run(simulation)


def test_docker_target_raises_on_generic_nonzero_exit() -> None:
    """An unrecognized non-zero exit becomes a generic SimulationExecutionError."""
    simulation = _make_simulation()

    with patch("purplelab.targets.subprocess.run") as mock_run:
        mock_run.return_value = _completed(returncode=1, stderr="boom")

        with pytest.raises(SimulationExecutionError):
            DockerTarget().run(simulation)


def test_docker_target_raises_on_malformed_stdout() -> None:
    """Non-JSON stdout is treated as malformed result data."""
    simulation = _make_simulation()

    with patch("purplelab.targets.subprocess.run") as mock_run:
        mock_run.return_value = _completed(stdout="not json")

        with pytest.raises(SimulationExecutionError):
            DockerTarget().run(simulation)


def test_docker_target_raises_on_unexpected_result_shape() -> None:
    """Valid JSON that isn't a flat string-keyed/valued mapping is rejected."""
    simulation = _make_simulation()

    with patch("purplelab.targets.subprocess.run") as mock_run:
        mock_run.return_value = _completed(stdout=json.dumps({"os": ["Linux"]}))

        with pytest.raises(SimulationExecutionError):
            DockerTarget().run(simulation)


def test_docker_target_raises_on_timeout() -> None:
    """A container that never completes raises a SimulationExecutionError."""
    simulation = _make_simulation()

    with patch(
        "purplelab.targets.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=30),
    ):
        with pytest.raises(SimulationExecutionError):
            DockerTarget().run(simulation)
