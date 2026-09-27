"""A simple in-memory registry of installed PurpleLab simulations.

The registry stores and retrieves `SimulationMetadata`. It knows nothing
about the CLI, execution, or any other consumer -- it is the single place
where "what simulations exist" is answered.
"""

from __future__ import annotations

from purplelab.models import SimulationMetadata


class DuplicateSimulationError(Exception):
    """Raised when a technique ID is registered more than once."""


class SimulationNotFoundError(Exception):
    """Raised when a requested technique ID has no registered simulation."""


class SimulationRegistry:
    """Stores `SimulationMetadata`, keyed by ATT&CK technique ID."""

    def __init__(self) -> None:
        self._simulations: dict[str, SimulationMetadata] = {}

    def register(self, metadata: SimulationMetadata) -> None:
        """Register a simulation, rejecting duplicate technique IDs."""
        technique_id = metadata.technique_id.upper()
        if technique_id in self._simulations:
            raise DuplicateSimulationError(
                f"A simulation for {technique_id} is already registered."
            )
        self._simulations[technique_id] = metadata

    def get(self, technique_id: str) -> SimulationMetadata:
        """Retrieve a simulation by technique ID, raising if it is unknown."""
        try:
            return self._simulations[technique_id.upper()]
        except KeyError:
            raise SimulationNotFoundError(
                f"Simulation {technique_id} was not found."
            ) from None

    def list_all(self) -> tuple[SimulationMetadata, ...]:
        """Return all registered simulations."""
        return tuple(self._simulations.values())


def create_default_registry() -> SimulationRegistry:
    """Build the registry containing PurpleLab's built-in simulations."""
    from simulations.t1082_system_information_discovery import (
        SIMULATION as T1082_SIMULATION,
    )

    registry = SimulationRegistry()
    registry.register(T1082_SIMULATION)
    return registry
