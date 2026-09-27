"""Tests for PurpleLab's simulation execution engine (Milestone 4 behavior)."""

import pytest

from purplelab.engine import SimulationEngine, SimulationExecutionError
from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.registry import Simulation


def _make_metadata(technique_id: str = "T1234") -> SimulationMetadata:
    """Build a minimal valid SimulationMetadata for engine tests."""
    return SimulationMetadata(
        id="fake-simulation",
        technique_id=technique_id,
        name="Fake Simulation",
        description="A fake simulation used for engine tests.",
        tactic=Tactic.DISCOVERY,
        platform=Platform.LINUX,
        risk=RiskLevel.LOW,
        expected_telemetry=("process creation",),
    )


def test_engine_returns_execution_result_on_success() -> None:
    """A successful run returns an ExecutionResult with the simulation's output."""
    metadata = _make_metadata()
    simulation = Simulation(metadata=metadata, run=lambda: {"os": "Linux"})

    result = SimulationEngine().run(simulation)

    assert result.success is True
    assert result.simulation_id == "fake-simulation"
    assert result.technique_id == "T1234"
    assert result.data == {"os": "Linux"}
    assert result.error is None


def test_engine_populates_timezone_aware_timestamps() -> None:
    """started_at and finished_at should be timezone-aware and ordered."""
    simulation = Simulation(metadata=_make_metadata(), run=lambda: {})

    result = SimulationEngine().run(simulation)

    assert result.started_at.tzinfo is not None
    assert result.finished_at.tzinfo is not None
    assert result.finished_at >= result.started_at


def test_engine_returns_failed_result_on_execution_error() -> None:
    """A SimulationExecutionError raised during run() becomes a failed result."""

    def _failing_run() -> dict[str, str]:
        raise SimulationExecutionError("boom")

    simulation = Simulation(metadata=_make_metadata(), run=_failing_run)

    result = SimulationEngine().run(simulation)

    assert result.success is False
    assert result.data == {}
    assert result.error == "boom"


def test_engine_lets_unexpected_errors_propagate() -> None:
    """Programming errors are not silently swallowed by the engine."""

    def _buggy_run() -> dict[str, str]:
        raise ValueError("programming error")

    simulation = Simulation(metadata=_make_metadata(), run=_buggy_run)

    with pytest.raises(ValueError):
        SimulationEngine().run(simulation)
