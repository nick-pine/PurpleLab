"""Tests for PurpleLab's simulation metadata model (Milestone 2.5 behavior)."""

import pytest
from pydantic import ValidationError

from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from simulations.t1082_system_information_discovery import SIMULATION as T1082


def _valid_kwargs(**overrides: object) -> dict[str, object]:
    """Build valid SimulationMetadata constructor kwargs, with overrides applied."""
    kwargs: dict[str, object] = {
        "id": "t1082-system-information-discovery",
        "technique_id": "T1082",
        "name": "System Information Discovery",
        "description": "Collects basic OS information.",
        "tactic": Tactic.DISCOVERY,
        "platform": Platform.LINUX,
        "risk": RiskLevel.LOW,
        "expected_telemetry": ("Process execution logs.",),
    }
    kwargs.update(overrides)
    return kwargs


def test_valid_metadata_constructs_successfully() -> None:
    """A well-formed SimulationMetadata should construct without error."""
    metadata = SimulationMetadata(**_valid_kwargs())

    assert metadata.technique_id == "T1082"
    assert metadata.expected_detection_rule is None


def test_valid_standard_technique_id_is_accepted() -> None:
    """A standard 'T####' technique ID should be accepted."""
    metadata = SimulationMetadata(**_valid_kwargs(technique_id="T1082"))

    assert metadata.technique_id == "T1082"


def test_valid_sub_technique_id_is_accepted() -> None:
    """A sub-technique 'T####.###' ID should be accepted."""
    metadata = SimulationMetadata(**_valid_kwargs(technique_id="T1059.001"))

    assert metadata.technique_id == "T1059.001"


@pytest.mark.parametrize(
    "technique_id",
    ["1082", "TABC", "T10", "T1059.1", "T1059.0001", "T1059.", "banana"],
)
def test_invalid_technique_id_is_rejected(technique_id: str) -> None:
    """Malformed technique IDs must be rejected by Pydantic validation."""
    with pytest.raises(ValidationError):
        SimulationMetadata(**_valid_kwargs(technique_id=technique_id))


def test_invalid_id_slug_is_rejected() -> None:
    """The internal id must be a lowercase kebab-case slug."""
    with pytest.raises(ValidationError):
        SimulationMetadata(**_valid_kwargs(id="T1082 System Info"))


def test_invalid_platform_is_rejected() -> None:
    """Platforms outside the supported enum must be rejected."""
    with pytest.raises(ValidationError):
        SimulationMetadata(**_valid_kwargs(platform="Solaris"))


def test_invalid_risk_level_is_rejected() -> None:
    """Risk levels outside the supported enum must be rejected."""
    with pytest.raises(ValidationError):
        SimulationMetadata(**_valid_kwargs(risk="Extreme"))


def test_missing_required_field_is_rejected() -> None:
    """Required fields, such as 'name', must not be omittable."""
    kwargs = _valid_kwargs()
    del kwargs["name"]

    with pytest.raises(ValidationError):
        SimulationMetadata(**kwargs)


def test_expected_telemetry_supports_multiple_entries() -> None:
    """A simulation can declare more than one expected telemetry entry."""
    metadata = SimulationMetadata(
        **_valid_kwargs(expected_telemetry=("process creation", "command execution"))
    )

    assert metadata.expected_telemetry == ("process creation", "command execution")


def test_expected_detection_rule_defaults_to_none() -> None:
    """Metadata can be created without an expected detection rule."""
    metadata = SimulationMetadata(**_valid_kwargs())

    assert metadata.expected_detection_rule is None


def test_metadata_is_immutable() -> None:
    """SimulationMetadata instances should be frozen (immutable) value objects."""
    metadata = SimulationMetadata(**_valid_kwargs())

    with pytest.raises(ValidationError):
        metadata.name = "Changed"


def test_t1082_simulation_metadata_is_well_formed() -> None:
    """The first real simulation (T1082) should match its expected shape."""
    assert T1082.technique_id == "T1082"
    assert T1082.tactic == Tactic.DISCOVERY
    assert T1082.platform == Platform.LINUX
    assert T1082.risk == RiskLevel.LOW
    assert T1082.expected_telemetry == (
        "process creation",
        "command execution",
        "endpoint events",
    )
    assert T1082.expected_detection_rule is None
