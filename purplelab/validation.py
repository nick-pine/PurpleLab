"""Deterministic detection validation (Milestone 8).

This module answers "did the monitoring stack produce relevant detection
evidence for this specific simulation execution?" -- it never asks or
answers "did any Wazuh alert occur nearby?". An unrelated alert during the
execution window is not proof of detection.

`DetectionValidator` evaluates already-collected, structured evidence only.
It never executes simulations, calls Docker, makes HTTP requests, performs
Wazuh authentication, or looks anything up in the registry -- that keeps
detection logic deterministic and trivial to unit test.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from purplelab.engine import ExecutionResult
from purplelab.models import SimulationMetadata
from purplelab.telemetry import TelemetryCollectionResult, TelemetryCollectionStatus, TelemetryEvent

MAX_MATCHED_IDENTIFIERS = 50


class DetectionStatus(str, Enum):
    """The three possible outcomes of detection validation.

    A boolean is deliberately insufficient here: PurpleLab must be able to
    say "we could not legitimately assess this" separately from "we assessed
    it and found no matching evidence".
    """

    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    NOT_EVALUATED = "not_evaluated"


class DetectionValidationResult(BaseModel):
    """The structured outcome of evaluating one execution's detection evidence."""

    model_config = ConfigDict(frozen=True)

    execution_id: str
    simulation_id: str
    technique_id: str
    status: DetectionStatus
    expected_rule_id: str | None = None
    matched_event_ids: tuple[str, ...] = Field(
        default_factory=tuple, max_length=MAX_MATCHED_IDENTIFIERS
    )
    matched_rule_ids: tuple[str, ...] = Field(
        default_factory=tuple, max_length=MAX_MATCHED_IDENTIFIERS
    )
    evaluated_at: datetime
    reason: str = Field(description="Explains WHY validation reached this status.")

    @field_validator("evaluated_at")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware (UTC)")
        return value


class DetectionValidator:
    """Evaluates an execution's evidence against its configured detection expectation."""

    def validate(
        self,
        *,
        execution: ExecutionResult,
        metadata: SimulationMetadata,
        telemetry: TelemetryCollectionResult,
    ) -> DetectionValidationResult:
        """Determine DETECTED / NOT_DETECTED / NOT_EVALUATED for one execution.

        Evaluation order (each step short-circuits to NOT_EVALUATED):
        1. Did the simulation execution succeed?
        2. Is a detection expectation configured for this simulation?
        3. Did telemetry retrieval succeed?
        4. Does any observed alert's rule_id exactly match the expected rule?
        """
        evaluated_at = datetime.now(timezone.utc)

        if not execution.success:
            return self._not_evaluated(
                execution,
                evaluated_at,
                reason="Simulation execution did not succeed.",
            )

        expected_rule_id = metadata.expected_detection_rule
        if expected_rule_id is None:
            return self._not_evaluated(
                execution,
                evaluated_at,
                reason=f"No expected detection rule is configured for {metadata.technique_id}.",
            )

        if telemetry.status is not TelemetryCollectionStatus.SUCCESS:
            reason = telemetry.error or "Telemetry retrieval did not succeed."
            return self._not_evaluated(
                execution,
                evaluated_at,
                reason=reason,
                expected_rule_id=expected_rule_id,
            )

        matched_events = tuple(
            event for event in telemetry.events if event.rule_id == expected_rule_id
        )

        if matched_events:
            return DetectionValidationResult(
                execution_id=execution.execution_id,
                simulation_id=execution.simulation_id,
                technique_id=execution.technique_id,
                status=DetectionStatus.DETECTED,
                expected_rule_id=expected_rule_id,
                matched_event_ids=self._bounded_event_ids(matched_events),
                matched_rule_ids=(expected_rule_id,),
                evaluated_at=evaluated_at,
                reason=f"Observed Wazuh alert matching configured rule {expected_rule_id}.",
            )

        return DetectionValidationResult(
            execution_id=execution.execution_id,
            simulation_id=execution.simulation_id,
            technique_id=execution.technique_id,
            status=DetectionStatus.NOT_DETECTED,
            expected_rule_id=expected_rule_id,
            evaluated_at=evaluated_at,
            reason=(
                f"Wazuh query succeeded, but no alert matching configured rule "
                f"{expected_rule_id} was observed."
            ),
        )

    def _not_evaluated(
        self,
        execution: ExecutionResult,
        evaluated_at: datetime,
        *,
        reason: str,
        expected_rule_id: str | None = None,
    ) -> DetectionValidationResult:
        return DetectionValidationResult(
            execution_id=execution.execution_id,
            simulation_id=execution.simulation_id,
            technique_id=execution.technique_id,
            status=DetectionStatus.NOT_EVALUATED,
            expected_rule_id=expected_rule_id,
            evaluated_at=evaluated_at,
            reason=reason,
        )

    @staticmethod
    def _bounded_event_ids(events: tuple[TelemetryEvent, ...]) -> tuple[str, ...]:
        ids = [event.event_id for event in events if event.event_id is not None]
        return tuple(ids[:MAX_MATCHED_IDENTIFIERS])
