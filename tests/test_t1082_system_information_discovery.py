"""Tests for T1082's executable behavior (Milestone 4 behavior)."""

import pytest

from purplelab.engine import SimulationExecutionError
from simulations import t1082_system_information_discovery as t1082


def test_run_returns_structured_system_information(monkeypatch: pytest.MonkeyPatch) -> None:
    """On a matching host platform, run() returns the collected fields."""
    monkeypatch.setattr(t1082.platform, "system", lambda: "Linux")
    monkeypatch.setattr(t1082.platform, "release", lambda: "6.8.0")
    monkeypatch.setattr(t1082.platform, "machine", lambda: "x86_64")

    result = t1082.run()

    assert result == {"os": "Linux", "release": "6.8.0", "architecture": "x86_64"}


def test_run_rejects_incompatible_host_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() refuses to execute on a host that doesn't match its declared platform."""
    monkeypatch.setattr(t1082.platform, "system", lambda: "Windows")

    with pytest.raises(SimulationExecutionError):
        t1082.run()


def test_executable_wraps_metadata_and_run() -> None:
    """The exported EXECUTABLE pairs SIMULATION metadata with the run callable."""
    assert t1082.EXECUTABLE.metadata is t1082.SIMULATION
    assert t1082.EXECUTABLE.run is t1082.run
