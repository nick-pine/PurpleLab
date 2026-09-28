"""Tests for the shared host-platform compatibility guard (Milestone 6)."""

import pytest

from purplelab.engine import SimulationExecutionError
from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.platform_guard import require_host_platform


def _make_metadata(platform: Platform) -> SimulationMetadata:
    return SimulationMetadata(
        id="fake-simulation",
        technique_id="T1234",
        name="Fake Simulation",
        description="A fake simulation used for platform guard tests.",
        tactic=Tactic.DISCOVERY,
        platform=platform,
        risk=RiskLevel.LOW,
        expected_telemetry=("process creation",),
    )


def test_require_host_platform_passes_on_a_matching_host() -> None:
    """No error is raised when the actual host matches the declared platform."""
    require_host_platform(_make_metadata(Platform.LINUX), "Linux")


def test_require_host_platform_rejects_a_mismatched_host() -> None:
    """A SimulationExecutionError is raised when the host doesn't match."""
    with pytest.raises(SimulationExecutionError, match="T1234"):
        require_host_platform(_make_metadata(Platform.LINUX), "Windows")


@pytest.mark.parametrize(
    ("platform", "expected_host"),
    [
        (Platform.LINUX, "Linux"),
        (Platform.WINDOWS, "Windows"),
        (Platform.MACOS, "Darwin"),
    ],
)
def test_require_host_platform_maps_each_platform_to_its_host_name(
    platform: Platform, expected_host: str
) -> None:
    """Each declared Platform value maps to the correct platform.system() name."""
    require_host_platform(_make_metadata(platform), expected_host)
