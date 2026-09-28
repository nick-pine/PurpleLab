"""Execution targets for PurpleLab simulations.

A target answers WHERE and HOW a simulation's already-known behavior is
executed. Simulations answer WHAT that behavior is. Targets never accept
arbitrary user-supplied commands -- `DockerTarget` only ever forwards a
simulation's already-validated `technique_id` to a fixed container
entrypoint that maps known technique IDs to known collection logic.
"""

from __future__ import annotations

import json
import subprocess
from enum import Enum

from purplelab.engine import SimulationExecutionError
from purplelab.registry import Simulation

LAB_IMAGE = "purplelab-lab-target:latest"
DOCKER_RUN_TIMEOUT_SECONDS = 30


class TargetType(str, Enum):
    """The constrained set of execution targets PurpleLab supports."""

    LOCAL = "local"
    DOCKER = "docker"


class DockerUnavailableError(SimulationExecutionError):
    """Raised when the Docker CLI or engine cannot be reached."""


class DockerLabImageMissingError(SimulationExecutionError):
    """Raised when the PurpleLab lab image has not been built."""


class LocalTarget:
    """Executes a simulation's `run()` callable directly in this process."""

    def run(self, simulation: Simulation) -> dict[str, str]:
        return simulation.run()


class DockerTarget:
    """Executes a simulation inside a disposable, isolated Linux container.

    Only the simulation's already-validated `technique_id` is passed to the
    container; the container's fixed runner decides how to collect that
    technique's data. No user-supplied command ever reaches `subprocess`.
    """

    def __init__(
        self,
        image: str = LAB_IMAGE,
        timeout: int = DOCKER_RUN_TIMEOUT_SECONDS,
    ) -> None:
        self._image = image
        self._timeout = timeout

    def run(self, simulation: Simulation) -> dict[str, str]:
        technique_id = simulation.metadata.technique_id
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--read-only",
            self._image,
            technique_id,
        ]

        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, no user commands
                command,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except FileNotFoundError as error:
            raise DockerUnavailableError(
                "Docker CLI was not found. Install/start Docker before using the Docker lab."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise SimulationExecutionError(
                f"{technique_id} timed out after {self._timeout} seconds inside the Docker lab."
            ) from error

        if completed.returncode != 0:
            raise self._error_for_failed_run(technique_id, completed.stderr)

        return self._parse_result(technique_id, completed.stdout)

    def _error_for_failed_run(
        self, technique_id: str, stderr: str
    ) -> SimulationExecutionError:
        message = stderr.strip()
        lowered = message.lower()

        if "cannot connect to the docker daemon" in lowered or "docker daemon" in lowered:
            return DockerUnavailableError(
                "Docker is installed, but the Docker engine is not reachable."
            )
        if "no such image" in lowered or "unable to find image" in lowered:
            return DockerLabImageMissingError(
                f"The PurpleLab lab image ({self._image}) was not found. "
                "Run `purplelab lab build` first."
            )
        return SimulationExecutionError(
            f"Docker execution of {technique_id} failed: {message or 'unknown error'}"
        )

    def _parse_result(self, technique_id: str, stdout: str) -> dict[str, str]:
        try:
            data = json.loads(stdout.strip())
        except json.JSONDecodeError as error:
            raise SimulationExecutionError(
                f"Docker execution of {technique_id} returned malformed result data."
            ) from error

        if not isinstance(data, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in data.items()
        ):
            raise SimulationExecutionError(
                f"Docker execution of {technique_id} returned unexpected result data."
            )

        return data
