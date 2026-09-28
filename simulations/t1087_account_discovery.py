"""Metadata and execution behavior for T1087 - Account Discovery.

This simulation demonstrates account *discovery*, not credential access: it
reports the current user and local account names only. It never reads
`/etc/shadow`, password hashes, authentication tokens, or any other
credential material.
"""

import platform

from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic
from purplelab.platform_guard import require_host_platform
from purplelab.registry import Simulation
from simulations._stdlib_collectors import collect_account_information

SIMULATION = SimulationMetadata(
    id="t1087-account-discovery",
    technique_id="T1087",
    name="Account Discovery",
    description=(
        "Safely discovers the current user and local account names inside "
        "an authorized PurpleLab target. Read-only and credential-free: "
        "never accesses password hashes, /etc/shadow, or other secret "
        "material."
    ),
    tactic=Tactic.DISCOVERY,
    platform=Platform.LINUX,
    risk=RiskLevel.LOW,
    expected_telemetry=(
        "file access (/etc/passwd)",
        "command execution",
    ),
)


def run() -> dict[str, str]:
    """Collect the current user and a bounded sample of local account names."""
    require_host_platform(SIMULATION, platform.system())
    return collect_account_information()


EXECUTABLE = Simulation(metadata=SIMULATION, run=run)
