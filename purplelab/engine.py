"""Execution orchestration for PurpleLab simulations.

The engine knows how to run a resolved `Simulation` and capture the
outcome. It has no knowledge of any particular technique's behavior --
that lives in each simulation module.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from purplelab.registry import Simulation


class SimulationExecutionError(Exception):
    """Raised when a simulation cannot be executed successfully."""


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
    """Orchestrates execution of a resolved `Simulation`."""

    def run(self, simulation: Simulation) -> ExecutionResult:
        """Execute `simulation`, always returning a structured result."""
        started_at = datetime.now(timezone.utc)

        try:
            data = simulation.run()
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
