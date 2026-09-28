"""Execution orchestration for PurpleLab simulations.

The engine knows how to run a resolved `Simulation` against a chosen
`ExecutionTarget` and capture the outcome. It has no knowledge of any
particular technique's behavior (that lives in each simulation module) or
of any particular target's implementation details (that lives in
`purplelab.targets`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from purplelab.registry import Simulation


class SimulationExecutionError(Exception):
    """Raised when a simulation cannot be executed successfully."""


class ExecutionTarget(Protocol):
    """Executes a known simulation's behavior somewhere, returning its data.

    A target defines WHERE and HOW a simulation runs (e.g. locally, or
    inside a Docker container). It never accepts arbitrary user-supplied
    commands -- it only knows how to run the fixed, known behavior a
    `Simulation` already represents.
    """

    def run(self, simulation: Simulation) -> dict[str, str]:
        """Execute `simulation` on this target, returning its structured data.

        Raises `SimulationExecutionError` (or a subclass) on any failure.
        """
        ...


class ExecutionResult(BaseModel):
    """The structured outcome of a single simulation execution."""

    model_config = ConfigDict(frozen=True)

    simulation_id: str
    technique_id: str
    started_at: datetime
    finished_at: datetime
    success: bool
    data: dict[str, str] = Field(
        default_factory=dict,
        description="Structured output produced by the simulation, if any.",
    )
    error: str | None = Field(
        default=None,
        description="Human-readable failure reason, present only when success is False.",
    )

    @field_validator("started_at", "finished_at")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (UTC)")
        return value


class SimulationEngine:
    """Orchestrates execution of a resolved `Simulation` against a target."""

    def run(self, simulation: Simulation, target: ExecutionTarget) -> ExecutionResult:
        """Execute `simulation` on `target`, always returning a structured result."""
        started_at = datetime.now(timezone.utc)

        try:
            data = target.run(simulation)
        except SimulationExecutionError as error:
            return ExecutionResult(
                simulation_id=simulation.metadata.id,
                technique_id=simulation.metadata.technique_id,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                success=False,
                data={},
                error=str(error),
            )

        return ExecutionResult(
            simulation_id=simulation.metadata.id,
            technique_id=simulation.metadata.technique_id,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            success=True,
            data=data,
            error=None,
        )
