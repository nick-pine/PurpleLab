"""Telemetry evidence models and provider abstraction (Milestone 7/8).

This module has no knowledge of Wazuh specifically -- `purplelab.integrations.wazuh`
implements a concrete provider. The rest of PurpleLab only depends on this
module's `TelemetryProvider` Protocol and models, keeping `SimulationEngine`
and the CLI independent of any particular SIEM.

Terminology matters here:

- EXPECTED telemetry (`SimulationMetadata.expected_telemetry`) is conceptual
  metadata describing what a simulation is designed to produce.
- OBSERVED telemetry (`TelemetryEvent`) is real evidence retrieved from a
  provider. With the current `WazuhTelemetryProvider`, that means Wazuh
  ALERTS (from `wazuh-alerts-*`), which is not necessarily a complete
  representation of all raw endpoint telemetry -- an empty alert search does
  not prove no underlying activity occurred.

This module never overwrites one of these concepts with another.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_PADDING_SECONDS = 60
MAX_SUMMARY_LENGTH = 500
MAX_EVENTS_RETURNED = 50


class TelemetryProviderError(Exception):
    """Base class for all telemetry-provider failures.

    A provider must never collapse a failure into an empty result tuple --
    "zero events observed" and "the provider is unavailable" are always
    distinguishable: the former is a return value, the latter is always one
    of these exceptions (or a subclass).
    """


class TelemetryUnavailableError(TelemetryProviderError):
    """Raised when the telemetry provider cannot be reached (network/timeout)."""


class TelemetryAuthenticationError(TelemetryProviderError):
    """Raised when the telemetry provider rejects PurpleLab's credentials."""


class TelemetryMalformedResponseError(TelemetryProviderError):
    """Raised when the telemetry provider returns an unexpected response shape."""


class TelemetryEvent(BaseModel):
    """A single, bounded piece of OBSERVED telemetry evidence."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(description="Identifies which telemetry provider produced this event.")
    observed_at: datetime
    source: str = Field(description="Agent/host identity that reported this event.")
    event_id: str | None = None
    rule_id: str | None = None
    rule_description: str | None = None
    severity: int | None = None
    summary: str = Field(description="Bounded, human-readable event summary.")

    @field_validator("observed_at")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware (UTC)")
        return value

    @field_validator("summary")
    @classmethod
    def _bound_summary_length(cls, value: str) -> str:
        return value[:MAX_SUMMARY_LENGTH]


class TelemetryQuery(BaseModel):
    """A bounded, structured request for telemetry evidence tied to one execution.

    This is the only shape a provider ever receives. PurpleLab never accepts
    arbitrary SIEM query strings/bodies from the CLI or elsewhere.
    """

    model_config = ConfigDict(frozen=True)

    execution_id: str
    simulation_id: str
    technique_id: str
    window_start: datetime
    window_end: datetime
    agent_identity: str | None = None
    padding_seconds: int = Field(default=5, ge=0, le=MAX_PADDING_SECONDS)

    @field_validator("window_start", "window_end")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("window_start/window_end must be timezone-aware (UTC)")
        return value

    @model_validator(mode="after")
    def _require_ordered_window(self) -> "TelemetryQuery":
        if self.window_end < self.window_start:
            raise ValueError("window_end must not be before window_start")
        return self

    @property
    def padded_start(self) -> datetime:
        """The query window's lower bound, including padding."""
        return self.window_start - timedelta(seconds=self.padding_seconds)

    @property
    def padded_end(self) -> datetime:
        """The query window's upper bound, including padding."""
        return self.window_end + timedelta(seconds=self.padding_seconds)


class TelemetryProvider(Protocol):
    """Retrieves bounded, OBSERVED telemetry evidence for a given query."""

    def collect(self, query: TelemetryQuery) -> tuple[TelemetryEvent, ...]:
        """Return observed telemetry events, or raise a `TelemetryProviderError`."""
        ...


class TelemetryCollectionStatus(str, Enum):
    """Whether a telemetry-collection attempt itself succeeded."""

    SUCCESS = "success"
    PROVIDER_ERROR = "provider_error"


class TelemetryCollectionResult(BaseModel):
    """The structured outcome of one telemetry-collection attempt.

    Consumers such as `DetectionValidator` depend on this plain data model
    instead of catching provider-specific exceptions (e.g. Wazuh HTTP errors)
    themselves, so validation logic stays independent of any one provider.
    """

    model_config = ConfigDict(frozen=True)

    status: TelemetryCollectionStatus
    events: tuple[TelemetryEvent, ...] = Field(default_factory=tuple)
    error: str | None = Field(
        default=None,
        description="Human-readable failure reason, present only when status is PROVIDER_ERROR.",
    )


def collect_telemetry(
    provider: TelemetryProvider, query: TelemetryQuery
) -> TelemetryCollectionResult:
    """Call `provider.collect(query)`, converting any provider error into a result.

    The provider contract itself still raises `TelemetryProviderError` (it
    must never silently swallow a failure into an empty tuple) -- this is the
    orchestration-boundary helper that converts that exception into a plain,
    inspectable `TelemetryCollectionResult` for consumers that shouldn't need
    to catch provider-specific exceptions themselves.
    """
    try:
        events = provider.collect(query)
    except TelemetryProviderError as error:
        return TelemetryCollectionResult(
            status=TelemetryCollectionStatus.PROVIDER_ERROR, events=(), error=str(error)
        )

    return TelemetryCollectionResult(status=TelemetryCollectionStatus.SUCCESS, events=events)


def build_query_for_execution(
    *,
    execution_id: str,
    simulation_id: str,
    technique_id: str,
    started_at: datetime,
    finished_at: datetime,
    agent_identity: str | None = None,
    padding_seconds: int = 5,
) -> TelemetryQuery:
    """Build a correlation query bounded to one execution's time window.

    The window is always `[started_at, finished_at]` (plus small, bounded
    padding) -- never an open-ended or unbounded historical query.
    """
    return TelemetryQuery(
        execution_id=execution_id,
        simulation_id=simulation_id,
        technique_id=technique_id,
        window_start=started_at,
        window_end=finished_at,
        agent_identity=agent_identity,
        padding_seconds=padding_seconds,
    )
