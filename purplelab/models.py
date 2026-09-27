"""Domain models describing PurpleLab simulations.

These models describe *what a simulation is* (metadata) - not how it runs.
Execution behavior is added in a later milestone once the simulation engine
exists.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Tactic(str, Enum):
    """MITRE ATT&CK tactic a simulation falls under."""

    DISCOVERY = "Discovery"


class Platform(str, Enum):
    """Operating system a simulation is designed to run on."""

    LINUX = "Linux"
    WINDOWS = "Windows"
    MACOS = "macOS"


class RiskLevel(str, Enum):
    """How risky a simulation is to execute, even in an isolated lab."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class SimulationMetadata(BaseModel):
    """Metadata describing a single PurpleLab adversary-emulation simulation."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        description="Unique internal identifier, e.g. 't1082-system-information-discovery'.",
    )
    technique_id: str = Field(
        pattern=r"^T\d{4}(?:\.\d{3})?$",
        description=(
            "MITRE ATT&CK technique ID, e.g. 'T1082' or sub-technique 'T1059.001'."
        ),
    )
    name: str
    description: str
    tactic: Tactic
    platform: Platform
    risk: RiskLevel
    expected_telemetry: tuple[str, ...] = Field(
        description="The forms of telemetry this simulation is expected to generate."
    )
    expected_detection_rule: str | None = Field(
        default=None,
        description="Identifier of the detection rule expected to fire, if known.",
    )
