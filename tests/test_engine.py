"""Tests for PurpleLab's simulation execution engine (Milestone 5 behavior)."""

import pytest

from purplelab.engine import SimulationEngine, SimulationExecutionError
from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.registry import Simulation
from purplelab.targets import LocalTarget


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

    result = SimulationEngine().run(simulation, LocalTarget())

    assert result.success is True
    assert result.simulation_id == "fake-simulation"
    assert result.technique_id == "T1234"
    assert result.data == {"os": "Linux"}
    assert result.error is None


def test_engine_generates_a_unique_execution_id_per_run() -> None:
    """Each execution gets its own unique execution_id, not a timestamp-derived value."""
    simulation = Simulation(metadata=_make_metadata(), run=lambda: {})

    first = SimulationEngine().run(simulation, LocalTarget())
    second = SimulationEngine().run(simulation, LocalTarget())

    assert first.execution_id
    assert second.execution_id
    assert first.execution_id != second.execution_id


def test_engine_populates_timezone_aware_timestamps() -> None:
    """started_at and finished_at should be timezone-aware and ordered."""
    simulation = Simulation(metadata=_make_metadata(), run=lambda: {})

    result = SimulationEngine().run(simulation, LocalTarget())

    assert result.started_at.tzinfo is not None
    assert result.finished_at.tzinfo is not None
    assert result.finished_at >= result.started_at


def test_engine_returns_failed_result_on_execution_error() -> None:
    """A SimulationExecutionError raised during run() becomes a failed result."""

    def _failing_run() -> dict[str, str]:
        raise SimulationExecutionError("boom")

    simulation = Simulation(metadata=_make_metadata(), run=_failing_run)

    result = SimulationEngine().run(simulation, LocalTarget())

    assert result.success is False
    assert result.data == {}
    assert result.error == "boom"


def test_engine_lets_unexpected_errors_propagate() -> None:
    """Programming errors are not silently swallowed by the engine."""

    def _buggy_run() -> dict[str, str]:
        raise ValueError("programming error")

    simulation = Simulation(metadata=_make_metadata(), run=_buggy_run)

    with pytest.raises(ValueError):
        SimulationEngine().run(simulation, LocalTarget())


def test_engine_uses_target_run_instead_of_simulation_run_directly() -> None:
    """The engine delegates to the target, not directly to simulation.run()."""

    class _RecordingTarget:
        def __init__(self) -> None:
            self.received: Simulation | None = None

        def run(self, simulation: Simulation) -> dict[str, str]:
            self.received = simulation
            return {"source": "target"}

    simulation = Simulation(metadata=_make_metadata(), run=lambda: {"source": "simulation"})
    target = _RecordingTarget()

    result = SimulationEngine().run(simulation, target)

    assert target.received is simulation
    assert result.data == {"source": "target"}
