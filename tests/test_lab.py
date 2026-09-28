"""Tests for PurpleLab Docker lab image lifecycle management (Milestone 5)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from purplelab.lab import (
    LabError,
    build_lab_image,
    docker_cli_available,
    docker_daemon_available,
    lab_image_built,
)


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def test_docker_cli_available_true_when_found() -> None:
    with patch("purplelab.lab.shutil.which", return_value="/usr/bin/docker"):
        assert docker_cli_available() is True


def test_docker_cli_available_false_when_missing() -> None:
    with patch("purplelab.lab.shutil.which", return_value=None):
        assert docker_cli_available() is False


def test_docker_daemon_available_false_when_cli_missing() -> None:
    with patch("purplelab.lab.shutil.which", return_value=None):
        assert docker_daemon_available() is False


def test_docker_daemon_available_true_on_success() -> None:
    with patch("purplelab.lab.shutil.which", return_value="/usr/bin/docker"), patch(
        "purplelab.lab.subprocess.run", return_value=_completed(returncode=0)
    ):
        assert docker_daemon_available() is True


def test_docker_daemon_available_false_on_failure() -> None:
    with patch("purplelab.lab.shutil.which", return_value="/usr/bin/docker"), patch(
        "purplelab.lab.subprocess.run", return_value=_completed(returncode=1)
    ):
        assert docker_daemon_available() is False


def test_lab_image_built_true_when_inspect_succeeds() -> None:
    with patch("purplelab.lab.shutil.which", return_value="/usr/bin/docker"), patch(
        "purplelab.lab.subprocess.run", return_value=_completed(returncode=0)
    ):
        assert lab_image_built() is True


def test_lab_image_built_false_when_inspect_fails() -> None:
    with patch("purplelab.lab.shutil.which", return_value="/usr/bin/docker"), patch(
        "purplelab.lab.subprocess.run", return_value=_completed(returncode=1)
    ):
        assert lab_image_built() is False


def test_build_lab_image_raises_when_docker_missing() -> None:
    with patch("purplelab.lab.shutil.which", return_value=None):
        with pytest.raises(LabError):
            build_lab_image()


def test_build_lab_image_raises_on_build_failure() -> None:
    with patch("purplelab.lab.shutil.which", return_value="/usr/bin/docker"), patch(
        "purplelab.lab.subprocess.run", return_value=_completed(returncode=1, stderr="boom")
    ):
        with pytest.raises(LabError):
            build_lab_image()


def test_build_lab_image_succeeds_when_docker_build_succeeds() -> None:
    with patch("purplelab.lab.shutil.which", return_value="/usr/bin/docker"), patch(
        "purplelab.lab.subprocess.run", return_value=_completed(returncode=0)
    ) as mock_run:
        build_lab_image()

    args, kwargs = mock_run.call_args
    command = args[0]
    assert command[:3] == ["docker", "build", "-t"]
    assert "shell" not in kwargs
