"""Metadata and execution behavior for T1082 - System Information Discovery."""

import platform

from purplelab.engine import SimulationExecutionError
from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.registry import Simulation

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

# Maps our declared Platform enum to the string platform.system() returns.
_HOST_PLATFORM_NAMES = {
    Platform.LINUX: "Linux",
    Platform.WINDOWS: "Windows",
    Platform.MACOS: "Darwin",
}


def run() -> dict[str, str]:
    """Collect basic OS/kernel/architecture info from the local host.

    Refuses to run on a host that doesn't match the simulation's declared
    platform, rather than silently pretending compatibility.
    """
    expected_host = _HOST_PLATFORM_NAMES[SIMULATION.platform]
    actual_host = platform.system()

    if actual_host != expected_host:
        raise SimulationExecutionError(
            f"{SIMULATION.technique_id} requires a {expected_host} host, "
            f"but this host is running {actual_host}."
        )

    return {
        "os": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
    }


EXECUTABLE = Simulation(metadata=SIMULATION, run=run)

