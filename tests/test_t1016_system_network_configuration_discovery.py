"""Tests for T1016's executable behavior (Milestone 6 behavior)."""

import pytest

from purplelab.engine import SimulationExecutionError
from simulations import t1016_system_network_configuration_discovery as t1016


def test_run_returns_network_collector_output_on_a_matching_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On a matching host platform, run() delegates to the network collector."""
    monkeypatch.setattr(t1016.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        t1016,
        "collect_network_configuration",
        lambda: {
            "hostname": "lab-target",
            "local_ip": "172.17.0.2",
            "interface_count": "2",
            "sample_interfaces": "eth0, lo",
        },
    )

    result = t1016.run()

    assert result["hostname"] == "lab-target"


def test_run_rejects_incompatible_host_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() refuses to execute on a host that doesn't match its declared platform."""
    monkeypatch.setattr(t1016.platform, "system", lambda: "Windows")

    with pytest.raises(SimulationExecutionError):
        t1016.run()


def test_executable_wraps_metadata_and_run() -> None:
    """The exported EXECUTABLE pairs SIMULATION metadata with the run callable."""
    assert t1016.EXECUTABLE.metadata is t1016.SIMULATION
    assert t1016.EXECUTABLE.run is t1016.run
