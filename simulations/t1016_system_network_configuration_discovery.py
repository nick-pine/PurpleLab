"""Metadata and execution behavior for T1016 - System Network Configuration
Discovery.

This simulation reports the target's own network configuration only. It
never scans, probes, or otherwise contacts any other host, and never
performs reconnaissance against external infrastructure.
"""

import platform

from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.platform_guard import require_host_platform
from purplelab.registry import Simulation
from simulations._stdlib_collectors import collect_network_configuration

SIMULATION = SimulationMetadata(
    id="t1016-system-network-configuration-discovery",
    technique_id="T1016",
    name="System Network Configuration Discovery",
    description=(
        "Safely inspects the authorized PurpleLab target's own hostname, "
        "local IP, and network interfaces. Read-only and self-contained: "
        "never scans, probes, or contacts any other host."
    ),
    tactic=Tactic.DISCOVERY,
    platform=Platform.LINUX,
    risk=RiskLevel.LOW,
    expected_telemetry=(
        "command execution",
        "process creation",
    ),
)


def run() -> dict[str, str]:
    """Collect the local host's own network configuration."""
    require_host_platform(SIMULATION, platform.system())
    return collect_network_configuration()


EXECUTABLE = Simulation(metadata=SIMULATION, run=run)
