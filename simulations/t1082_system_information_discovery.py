"""Metadata and execution behavior for T1082 - System Information Discovery."""

import platform

from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.platform_guard import require_host_platform
from purplelab.registry import Simulation
from simulations._stdlib_collectors import collect_system_information

SIMULATION = SimulationMetadata(
    id="t1082-system-information-discovery",
    technique_id="T1082",
    name="System Information Discovery",
    description=(
        "Safely collects basic operating-system information (OS version, "
        "kernel release, and architecture) inside an authorized PurpleLab "
        "target."
    ),
    tactic=Tactic.DISCOVERY,
    platform=Platform.LINUX,
    risk=RiskLevel.LOW,
    expected_telemetry=(
        "process creation",
        "command execution",
        "endpoint events",
    ),
)


def run() -> dict[str, str]:
    """Collect basic OS/kernel/architecture info from the local host.

    Refuses to run on a host that doesn't match the simulation's declared
    platform, rather than silently pretending compatibility.
    """
    require_host_platform(SIMULATION, platform.system())
    return collect_system_information()


EXECUTABLE = Simulation(metadata=SIMULATION, run=run)


