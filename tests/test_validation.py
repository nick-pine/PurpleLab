"""Tests for deterministic detection validation (Milestone 8)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from purplelab.engine import ExecutionResult
from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.telemetry import (
    TelemetryCollectionResult,
    TelemetryCollectionStatus,
    TelemetryEvent,
)
from purplelab.validation import (
    DetectionStatus,
    DetectionValidationResult,
    DetectionValidator,
)


RULE_ID = "100201"


def _metadata(expected_rule: str | None = RULE_ID) -> SimulationMetadata:
    return SimulationMetadata(
        id="fake-simulation",
        technique_id="T1082",
        name="Fake Simulation",
        description="Fake metadata used for validator tests.",
        tactic=Tactic.DISCOVERY,
        platform=Platform.LINUX,
        risk=RiskLevel.LOW,
        expected_telemetry=("process creation",),
        expected_detection_rule=expected_rule,
    )


def _execution(success: bool = True) -> ExecutionResult:
    now = datetime.now(timezone.utc)
    return ExecutionResult(
        execution_id="execution-1",
        simulation_id="fake-simulation",
        technique_id="T1082",
        started_at=now,
        finished_at=now,
        success=success,
        data={} if success else {},
        error=None if success else "execution failed",
    )


def _event(
    rule_id: str | None,
    *,
    event_id: str = "event-1",
    description: str | None = None,
    summary: str = "summary",
    severity: int | None = None,
) -> TelemetryEvent:
    return TelemetryEvent(
        provider="wazuh",
        observed_at=datetime.now(timezone.utc),
        source="lab-target",
        event_id=event_id,
        rule_id=rule_id,
        rule_description=description,
        severity=severity,
        summary=summary,
    )


def _success(*events: TelemetryEvent) -> TelemetryCollectionResult:
    return TelemetryCollectionResult(
        status=TelemetryCollectionStatus.SUCCESS,
        events=events,
    )


def _provider_error(reason: str = "Wazuh unavailable") -> TelemetryCollectionResult:
    return TelemetryCollectionResult(
        status=TelemetryCollectionStatus.PROVIDER_ERROR,
        events=(),
        error=reason,
    )


def test_validation_result_accepts_each_explicit_status() -> None:
    now = datetime.now(timezone.utc)

    for status in DetectionStatus:
        result = DetectionValidationResult(
            execution_id="execution-1",
            simulation_id="fake-simulation",
            technique_id="T1082",
            status=status,
            evaluated_at=now,
            reason="test",
        )
        assert result.status is status


def test_validation_result_requires_timezone_aware_evaluated_at() -> None:
    with pytest.raises(ValidationError):
        DetectionValidationResult(
            execution_id="execution-1",
            simulation_id="fake-simulation",
            technique_id="T1082",
            status=DetectionStatus.NOT_EVALUATED,
            evaluated_at=datetime.now(),
            reason="test",
        )


def test_validation_result_is_immutable() -> None:
    result = DetectionValidationResult(
        execution_id="execution-1",
        simulation_id="fake-simulation",
        technique_id="T1082",
        status=DetectionStatus.NOT_EVALUATED,
        evaluated_at=datetime.now(timezone.utc),
        reason="test",
    )

    with pytest.raises(ValidationError):
        result.reason = "changed"


def test_failed_execution_is_not_evaluated() -> None:
    result = DetectionValidator().validate(
        execution=_execution(success=False),
        metadata=_metadata(),
        telemetry=_success(_event(RULE_ID)),
    )

    assert result.status is DetectionStatus.NOT_EVALUATED
    assert result.reason == "Simulation execution did not succeed."


def test_missing_detection_expectation_is_not_evaluated() -> None:
    result = DetectionValidator().validate(
        execution=_execution(),
        metadata=_metadata(expected_rule=None),
        telemetry=_success(_event(RULE_ID)),
    )

    assert result.status is DetectionStatus.NOT_EVALUATED
    assert "No expected detection rule is configured" in result.reason


def test_provider_failure_is_not_evaluated_not_not_detected() -> None:
    result = DetectionValidator().validate(
        execution=_execution(),
        metadata=_metadata(),
        telemetry=_provider_error("Wazuh authentication failed"),
    )

    assert result.status is DetectionStatus.NOT_EVALUATED
    assert result.reason == "Wazuh authentication failed"


def test_zero_alerts_with_expected_rule_is_not_detected() -> None:
    result = DetectionValidator().validate(
        execution=_execution(),
        metadata=_metadata(),
        telemetry=_success(),
    )

    assert result.status is DetectionStatus.NOT_DETECTED
    assert result.expected_rule_id == RULE_ID
    assert "no alert matching configured rule" in result.reason


def test_unrelated_alerts_are_not_detection_matches() -> None:
    result = DetectionValidator().validate(
        execution=_execution(),
        metadata=_metadata(),
        telemetry=_success(
            _event("5501"),
            _event("10020"),
            _event("1002010"),
            _event("9999", description=RULE_ID, summary=f"T1082 {RULE_ID}", severity=15),
        ),
    )

    assert result.status is DetectionStatus.NOT_DETECTED
    assert result.matched_event_ids == ()
    assert result.matched_rule_ids == ()


def test_exact_rule_id_match_is_detected() -> None:
    result = DetectionValidator().validate(
        execution=_execution(),
        metadata=_metadata(),
        telemetry=_success(_event(RULE_ID, event_id="matching-event")),
    )

    assert result.status is DetectionStatus.DETECTED
    assert result.matched_event_ids == ("matching-event",)
    assert result.matched_rule_ids == (RULE_ID,)
    assert RULE_ID in result.reason


def test_matching_and_unrelated_alerts_are_detected() -> None:
    result = DetectionValidator().validate(
        execution=_execution(),
        metadata=_metadata(),
        telemetry=_success(
            _event("5501", event_id="unrelated-event"),
            _event(RULE_ID, event_id="matching-event"),
        ),
    )

    assert result.status is DetectionStatus.DETECTED
    assert result.matched_event_ids == ("matching-event",)


def test_multiple_matching_alerts_have_bounded_identifiers() -> None:
    events = tuple(_event(RULE_ID, event_id=f"event-{index}") for index in range(100))

    result = DetectionValidator().validate(
        execution=_execution(),
        metadata=_metadata(),
        telemetry=_success(*events),
    )

    assert result.status is DetectionStatus.DETECTED
    assert len(result.matched_event_ids) == 50
    assert len(result.matched_rule_ids) == 1
