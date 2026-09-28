"""A simple in-memory registry of installed PurpleLab simulations.

The registry stores and retrieves executable `Simulation` objects. It knows
nothing about the CLI, execution orchestration details, or any other
consumer -- it is the single place where "what simulations exist" is
answered.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from purplelab.models import SimulationMetadata


@dataclass(frozen=True)
class Simulation:
    """Pairs a simulation's metadata with the callable that executes it."""

    metadata: SimulationMetadata
    run: Callable[[], dict[str, str]]


class DuplicateSimulationError(Exception):
    """Raised when a technique ID is registered more than once."""


class SimulationNotFoundError(Exception):
    """Raised when a requested technique ID has no registered simulation."""


class SimulationRegistry:
    """Stores executable `Simulation` objects, keyed by ATT&CK technique ID."""

    def __init__(self) -> None:
        self._simulations: dict[str, Simulation] = {}

    def register(self, simulation: Simulation) -> None:
        """Register a simulation, rejecting duplicate technique IDs."""
        technique_id = simulation.metadata.technique_id.upper()
        if technique_id in self._simulations:
            raise DuplicateSimulationError(
                f"A simulation for {technique_id} is already registered."
            )
        self._simulations[technique_id] = simulation

    def get(self, technique_id: str) -> Simulation:
        """Retrieve a simulation by technique ID, raising if it is unknown."""
        try:
            return self._simulations[technique_id.upper()]
        except KeyError:
            raise SimulationNotFoundError(
                f"Simulation {technique_id} was not found."
            ) from None

    def list_all(self) -> tuple[Simulation, ...]:
        """Return all registered simulations."""
        return tuple(self._simulations.values())


def create_default_registry() -> SimulationRegistry:
    """Build the registry containing PurpleLab's built-in simulations."""
    from simulations.t1016_system_network_configuration_discovery import (
        EXECUTABLE as T1016_EXECUTABLE,
    )
    from simulations.t1057_process_discovery import EXECUTABLE as T1057_EXECUTABLE
    from simulations.t1082_system_information_discovery import (
        EXECUTABLE as T1082_EXECUTABLE,
    )
    from simulations.t1087_account_discovery import EXECUTABLE as T1087_EXECUTABLE

    registry = SimulationRegistry()
    registry.register(T1082_EXECUTABLE)
    registry.register(T1057_EXECUTABLE)
    registry.register(T1087_EXECUTABLE)
    registry.register(T1016_EXECUTABLE)
    return registry
