"""Tests for T1087's executable behavior (Milestone 6 behavior)."""

import pytest

from purplelab.engine import SimulationExecutionError
from simulations import t1087_account_discovery as t1087


def test_run_returns_account_collector_output_on_a_matching_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On a matching host platform, run() delegates to the account collector."""
    monkeypatch.setattr(t1087.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        t1087,
        "collect_account_information",
        lambda: {
            "current_user": "alice",
            "local_account_count": "3",
            "sample_local_accounts": "root, alice, bob",
        },
    )

    result = t1087.run()

    assert result["current_user"] == "alice"
    assert "password" not in result
    assert "hash" not in result


def test_run_rejects_incompatible_host_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() refuses to execute on a host that doesn't match its declared platform."""
    monkeypatch.setattr(t1087.platform, "system", lambda: "Windows")

    with pytest.raises(SimulationExecutionError):
        t1087.run()


def test_executable_wraps_metadata_and_run() -> None:
    """The exported EXECUTABLE pairs SIMULATION metadata with the run callable."""
    assert t1087.EXECUTABLE.metadata is t1087.SIMULATION
    assert t1087.EXECUTABLE.run is t1087.run
