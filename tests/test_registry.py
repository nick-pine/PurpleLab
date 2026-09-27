"""Tests for PurpleLab's simulation registry (Milestone 4 behavior)."""

import pytest

from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.registry import (
    DuplicateSimulationError,
    Simulation,
    SimulationNotFoundError,
    SimulationRegistry,
)


def _make_simulation(technique_id: str, name: str = "Example") -> Simulation:
    """Build a minimal valid, fake executable Simulation for registry tests."""
    slug = technique_id.lower().replace(".", "-")
    metadata = SimulationMetadata(
        id=f"{slug}-example",
        technique_id=technique_id,
        name=name,
        description="An example simulation used for registry tests.",
        tactic=Tactic.DISCOVERY,
        platform=Platform.LINUX,
        risk=RiskLevel.LOW,
        expected_telemetry=("process creation",),
    )
    return Simulation(metadata=metadata, run=lambda: {})


def test_register_stores_a_valid_simulation() -> None:
    """A valid Simulation can be registered without error."""
    registry = SimulationRegistry()

    registry.register(_make_simulation("T1082"))

    assert registry.get("T1082").metadata.technique_id == "T1082"


def test_get_retrieves_registered_simulation_by_technique_id() -> None:
    """A registered simulation can be retrieved by its technique ID."""
    registry = SimulationRegistry()
    simulation = _make_simulation("T1082")
    registry.register(simulation)

    assert registry.get("T1082") == simulation


def test_get_normalizes_technique_id_case() -> None:
    """Lookup is case-insensitive for convenience, not fuzzy matching."""
    registry = SimulationRegistry()
    registry.register(_make_simulation("T1082"))

    assert registry.get("t1082").metadata.technique_id == "T1082"


def test_list_all_includes_registered_simulations() -> None:
    """Registered simulations appear in the registry's list operation."""
    registry = SimulationRegistry()
    simulation = _make_simulation("T1082")
    registry.register(simulation)

    assert simulation in registry.list_all()


def test_duplicate_registration_is_rejected() -> None:
    """Registering the same technique ID twice raises DuplicateSimulationError."""
    registry = SimulationRegistry()
    registry.register(_make_simulation("T1082"))

    with pytest.raises(DuplicateSimulationError):
        registry.register(_make_simulation("T1082", name="Different Name"))


def test_unknown_lookup_raises_not_found_error() -> None:
    """Requesting an unregistered technique raises SimulationNotFoundError."""
    registry = SimulationRegistry()

    with pytest.raises(SimulationNotFoundError):
        registry.get("T9999")


def test_registry_can_contain_multiple_simulations() -> None:
    """The registry can hold more than one simulation."""
    registry = SimulationRegistry()
    first = _make_simulation("T1082")
    second = _make_simulation("T1059.001", name="Command and Scripting Interpreter")

    registry.register(first)
    registry.register(second)

    assert set(registry.list_all()) == {first, second}


def test_registries_do_not_share_state() -> None:
    """Each SimulationRegistry instance is isolated from others."""
    first_registry = SimulationRegistry()
    second_registry = SimulationRegistry()

    first_registry.register(_make_simulation("T1082"))

    assert second_registry.list_all() == ()
