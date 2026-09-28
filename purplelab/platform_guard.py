"""Shared host-platform compatibility check for local simulation execution.

Centralizes the "does this host match what the simulation declares" rule so
individual simulation modules don't each repeat the same comparison/error
logic. This has nothing to do with Docker execution -- the Docker lab is
always Linux, so this check only matters for `LocalTarget`.
"""

from __future__ import annotations

from purplelab.engine import SimulationExecutionError
from purplelab.models import Platform, SimulationMetadata

_HOST_PLATFORM_NAMES: dict[Platform, str] = {
    Platform.LINUX: "Linux",
    Platform.WINDOWS: "Windows",
    Platform.MACOS: "Darwin",
}


def require_host_platform(metadata: SimulationMetadata, actual_host: str) -> None:
    """Raise SimulationExecutionError if `actual_host` doesn't match `metadata.platform`."""
    expected_host = _HOST_PLATFORM_NAMES[metadata.platform]
    if actual_host != expected_host:
        raise SimulationExecutionError(
            f"{metadata.technique_id} requires a {expected_host} host, "
            f"but this host is running {actual_host}."
        )
