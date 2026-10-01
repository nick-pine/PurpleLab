"""Tests for PurpleLab's telemetry models and query correlation (Milestone 7)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from purplelab.telemetry import (
    MAX_PADDING_SECONDS,
    TelemetryCollectionStatus,
    TelemetryEvent,
    TelemetryProviderError,
    TelemetryQuery,
    build_query_for_execution,
    collect_telemetry,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_telemetry_event_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError):
        TelemetryEvent(
            provider="wazuh",
            observed_at=datetime.now(),  # naive
            source="agent-01",
            summary="test",
        )


def test_telemetry_event_bounds_summary_length() -> None:
    event = TelemetryEvent(
        provider="wazuh",
        observed_at=_now(),
        source="agent-01",
        summary="x" * 10_000,
    )

    assert len(event.summary) <= 500


def test_telemetry_event_is_immutable() -> None:
    event = TelemetryEvent(
        provider="wazuh", observed_at=_now(), source="agent-01", summary="test"
    )

    with pytest.raises(ValidationError):
        event.summary = "changed"


def test_telemetry_query_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(ValidationError):
        TelemetryQuery(
            execution_id="exec-1",
            simulation_id="sim-1",
            technique_id="T1082",
            window_start=datetime.now(),
            window_end=datetime.now(),
        )


def test_telemetry_query_rejects_end_before_start() -> None:
    start = _now()
    with pytest.raises(ValidationError):
        TelemetryQuery(
            execution_id="exec-1",
            simulation_id="sim-1",
            technique_id="T1082",
            window_start=start,
            window_end=start - timedelta(seconds=5),
        )


def test_telemetry_query_bounds_padding_seconds() -> None:
    start = _now()
    with pytest.raises(ValidationError):
        TelemetryQuery(
            execution_id="exec-1",
            simulation_id="sim-1",
            technique_id="T1082",
            window_start=start,
            window_end=start,
            padding_seconds=MAX_PADDING_SECONDS + 1,
        )


def test_telemetry_query_padded_bounds_apply_symmetric_padding() -> None:
    start = _now()
    end = start + timedelta(seconds=2)
    query = TelemetryQuery(
        execution_id="exec-1",
        simulation_id="sim-1",
        technique_id="T1082",
        window_start=start,
        window_end=end,
        padding_seconds=5,
    )

    assert query.padded_start == start - timedelta(seconds=5)
    assert query.padded_end == end + timedelta(seconds=5)


def test_build_query_for_execution_produces_a_bounded_window() -> None:
    started_at = _now()
    finished_at = started_at + timedelta(seconds=3)

    query = build_query_for_execution(
        execution_id="exec-123",
        simulation_id="t1082-system-information-discovery",
        technique_id="T1082",
        started_at=started_at,
        finished_at=finished_at,
    )

    assert query.execution_id == "exec-123"
    assert query.technique_id == "T1082"
    assert query.window_start == started_at
    assert query.window_end == finished_at
    # The query must never span more than the execution window plus bounded padding.
    total_span = query.padded_end - query.padded_start
    assert total_span <= (finished_at - started_at) + timedelta(seconds=2 * MAX_PADDING_SECONDS)


def test_collect_telemetry_represents_successful_zero_alerts_explicitly() -> None:
    query = TelemetryQuery(
        execution_id="exec-1",
        simulation_id="sim-1",
        technique_id="T1082",
        window_start=_now(),
        window_end=_now(),
    )

    class _EmptyProvider:
        def collect(self, received_query: TelemetryQuery) -> tuple[TelemetryEvent, ...]:
            assert received_query is query
            return ()

    result = collect_telemetry(_EmptyProvider(), query)

    assert result.status is TelemetryCollectionStatus.SUCCESS
    assert result.events == ()
    assert result.error is None


def test_collect_telemetry_preserves_provider_failure_without_swallowing_it() -> None:
    query = TelemetryQuery(
        execution_id="exec-1",
        simulation_id="sim-1",
        technique_id="T1082",
        window_start=_now(),
        window_end=_now(),
    )

    class _FailingProvider:
        def collect(self, received_query: TelemetryQuery) -> tuple[TelemetryEvent, ...]:
            raise TelemetryProviderError("provider unavailable")

    result = collect_telemetry(_FailingProvider(), query)

    assert result.status is TelemetryCollectionStatus.PROVIDER_ERROR
    assert result.events == ()
    assert result.error == "provider unavailable"
