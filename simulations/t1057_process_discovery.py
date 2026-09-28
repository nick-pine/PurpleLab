"""Metadata and execution behavior for T1057 - Process Discovery.

This is strictly read-only enumeration of process names. It never
terminates, injects into, or inspects the memory of any process.
"""

import platform

from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.platform_guard import require_host_platform
from purplelab.registry import Simulation
from simulations._stdlib_collectors import collect_process_information

SIMULATION = SimulationMetadata(
    id="t1057-process-discovery",
    technique_id="T1057",
    name="Process Discovery",
    description=(
        "Safely enumerates running process names via the /proc filesystem "
        "inside an authorized PurpleLab target. Read-only: does not "
        "terminate, inject into, or inspect the memory of any process."
    ),
    tactic=Tactic.DISCOVERY,
    platform=Platform.LINUX,
    risk=RiskLevel.LOW,
    expected_telemetry=(
        "process creation",
        "file access (/proc)",
    ),
)


def run() -> dict[str, str]:
    """Collect a bounded sample of running process names from the local host."""
    require_host_platform(SIMULATION, platform.system())
    return collect_process_information()


EXECUTABLE = Simulation(metadata=SIMULATION, run=run)
