"""Metadata for T1082 - System Information Discovery."""

from purplelab.models import Platform, RiskLevel, SimulationMetadata, Tactic

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
