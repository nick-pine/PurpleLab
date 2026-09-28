"""Lifecycle management for the PurpleLab Docker lab image.

This module knows how to check Docker availability and build/verify the
lab image. It does not execute simulations -- that is `purplelab.targets`'s
responsibility.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from purplelab.targets import LAB_IMAGE

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE_PATH = REPO_ROOT / "docker" / "target" / "Dockerfile"
DOCKER_INFO_TIMEOUT_SECONDS = 10
DOCKER_BUILD_TIMEOUT_SECONDS = 300


class LabError(Exception):
    """Raised when a lab lifecycle operation cannot complete."""


def docker_cli_available() -> bool:
    """Return True if the `docker` executable is on PATH."""
    return shutil.which("docker") is not None


def docker_daemon_available() -> bool:
    """Return True if the Docker engine responds to a basic query."""
    if not docker_cli_available():
        return False

    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=DOCKER_INFO_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    return completed.returncode == 0


def lab_image_built() -> bool:
    """Return True if the PurpleLab lab image has already been built."""
    if not docker_cli_available():
        return False

    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["docker", "image", "inspect", LAB_IMAGE],
            capture_output=True,
            text=True,
            timeout=DOCKER_INFO_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    return completed.returncode == 0


def build_lab_image() -> None:
    """Build the PurpleLab lab image from `docker/target/Dockerfile`.

    The build context is the repository root (not `docker/target/`) so the
    Dockerfile can copy the shared `simulations/_stdlib_collectors.py`
    module without duplicating it inside the image build directory.
    """
    if not docker_cli_available():
        raise LabError(
            "Docker CLI was not found. Install/start Docker before building the lab image."
        )

    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [
                "docker",
                "build",
                "-t",
                LAB_IMAGE,
                "-f",
                str(DOCKERFILE_PATH),
                str(REPO_ROOT),
            ],
            capture_output=True,
            text=True,
            timeout=DOCKER_BUILD_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise LabError("Building the PurpleLab lab image timed out.") from error

    if completed.returncode != 0:
        raise LabError(
            f"Failed to build the PurpleLab lab image:\n{completed.stderr.strip()}"
        )
