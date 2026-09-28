"""Tests for T1057's executable behavior (Milestone 6 behavior)."""

import pytest

from purplelab.engine import SimulationExecutionError
from simulations import t1057_process_discovery as t1057


def test_run_returns_process_collector_output_on_a_matching_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On a matching host platform, run() delegates to the process collector."""
    monkeypatch.setattr(t1057.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        t1057,
        "collect_process_information",
        lambda: {"process_count": "3", "sample_process_names": "bash, sshd, cron"},
    )

    result = t1057.run()

    assert result == {"process_count": "3", "sample_process_names": "bash, sshd, cron"}


def test_run_rejects_incompatible_host_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() refuses to execute on a host that doesn't match its declared platform."""
    monkeypatch.setattr(t1057.platform, "system", lambda: "Windows")

    with pytest.raises(SimulationExecutionError):
        t1057.run()


def test_executable_wraps_metadata_and_run() -> None:
    """The exported EXECUTABLE pairs SIMULATION metadata with the run callable."""
    assert t1057.EXECUTABLE.metadata is t1057.SIMULATION
    assert t1057.EXECUTABLE.run is t1057.run
