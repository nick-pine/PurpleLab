"""Command-line interface for PurpleLab.

This module wires Typer commands to the (currently minimal) application
behavior. It intentionally contains no simulation logic itself -- future
milestones will delegate to an application/service layer so the same logic
can be reused by the web API.
"""

from __future__ import annotations

import typer

from purplelab import __version__
from purplelab.engine import ExecutionResult, ExecutionTarget, SimulationEngine
from purplelab.integrations.wazuh import WazuhConfig, WazuhTelemetryProvider
from purplelab.lab import (
    LabError,
    build_lab_image,
    docker_cli_available,
    docker_daemon_available,
    lab_image_built,
)
from purplelab.registry import SimulationNotFoundError, create_default_registry
from purplelab.targets import LAB_IMAGE, DockerTarget, LocalTarget, TargetType
from purplelab.telemetry import TelemetryProviderError, build_query_for_execution

app = typer.Typer(
    name="purplelab",
    help="PurpleLab - a local adversary-emulation and detection-validation platform.",
    add_completion=False,
)

lab_app = typer.Typer(help="Manage the PurpleLab Docker lab environment.")
app.add_typer(lab_app, name="lab")


def _version_callback(show_version: bool) -> None:
    """Print the installed PurpleLab version and exit early if requested."""
    if show_version:
        typer.echo(f"PurpleLab {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the PurpleLab version and exit.",
    ),
) -> None:
    """PurpleLab: local adversary-emulation and detection-validation platform."""


@app.command("list")
def list_simulations() -> None:
    """List available simulations."""
    registry = create_default_registry()
    simulations = registry.list_all()

    if not simulations:
        typer.echo("No simulations installed.")
        raise typer.Exit()

    typer.echo(f"{'TECHNIQUE':<12} {'NAME':<42} {'PLATFORM':<10} {'RISK':<8}")
    for simulation in simulations:
        metadata = simulation.metadata
        typer.echo(
            f"{metadata.technique_id:<12} {metadata.name:<42} "
            f"{metadata.platform.value:<10} {metadata.risk.value:<8}"
        )


@app.command("info")
def simulation_info(technique_id: str) -> None:
    """Show detailed metadata for a single simulation."""
    registry = create_default_registry()

    try:
        metadata = registry.get(technique_id).metadata
    except SimulationNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    telemetry = "\n".join(f"- {entry}" for entry in metadata.expected_telemetry)
    detection = metadata.expected_detection_rule or "Not configured"

    typer.echo("PurpleLab Simulation\n")
    typer.echo(f"Technique:    {metadata.technique_id}")
    typer.echo(f"Name:         {metadata.name}")
    typer.echo(f"Tactic:       {metadata.tactic.value}")
    typer.echo(f"Platform:     {metadata.platform.value}")
    typer.echo(f"Risk:         {metadata.risk.value}")
    typer.echo(f"\nDescription:\n{metadata.description}")
    typer.echo(f"\nExpected Telemetry:\n{telemetry}")
    typer.echo(f"\nExpected Detection:\n{detection}")


@app.command("run")
def run_simulation(
    technique_id: str,
    target: TargetType = typer.Option(
        TargetType.LOCAL,
        "--target",
        help="Where to execute the simulation: 'local' or 'docker'.",
    ),
    telemetry: bool = typer.Option(
        False,
        "--telemetry",
        help="After a successful run, query Wazuh for telemetry observed during execution.",
    ),
) -> None:
    """Execute a simulation and display its execution result."""
    registry = create_default_registry()

    try:
        simulation = registry.get(technique_id)
    except SimulationNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    execution_target: ExecutionTarget = (
        LocalTarget() if target is TargetType.LOCAL else DockerTarget()
    )

    result = SimulationEngine().run(simulation, execution_target)
    metadata = simulation.metadata

    typer.echo("PurpleLab Simulation Execution\n")
    typer.echo(f"Technique:    {metadata.technique_id}")
    typer.echo(f"Name:         {metadata.name}")
    typer.echo(f"Target:       {target.value.capitalize()}")
    typer.echo(f"Status:       {'Success' if result.success else 'Failed'}")

    if not result.success:
        typer.echo(f"\nError:\n{result.error}", err=True)
        typer.echo(f"\nStarted:      {result.started_at.isoformat()}")
        typer.echo(f"Finished:     {result.finished_at.isoformat()}")
        raise typer.Exit(code=1)

    typer.echo("\nResult:")
    for key, value in result.data.items():
        label = key.replace("_", " ").capitalize()
        typer.echo(f"{label + ':':<24} {value}")
    typer.echo(f"\nStarted:      {result.started_at.isoformat()}")
    typer.echo(f"Finished:     {result.finished_at.isoformat()}")

    if telemetry:
        _display_telemetry(result)


def _display_telemetry(result: ExecutionResult) -> None:
    """Query Wazuh for telemetry observed during `result`'s execution window."""
    try:
        config = WazuhConfig.from_env()
    except TelemetryProviderError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    query = build_query_for_execution(
        execution_id=result.execution_id,
        simulation_id=result.simulation_id,
        technique_id=result.technique_id,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )

    try:
        events = WazuhTelemetryProvider(config).collect(query)
    except TelemetryProviderError as error:
        typer.echo(f"\nTelemetry (Wazuh):\n{error}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo("\nTelemetry (Wazuh):")
    if not events:
        typer.echo("No telemetry events observed in the query window.")
        return

    for event in events:
        rule = event.rule_id or "unknown"
        description = event.rule_description or event.summary
        typer.echo(f"- [severity {event.severity}] rule {rule}: {description}")


@lab_app.command("build")
def lab_build() -> None:
    """Build the PurpleLab Docker lab image."""
    try:
        build_lab_image()
    except LabError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Built PurpleLab lab image: {LAB_IMAGE}")


@lab_app.command("status")
def lab_status() -> None:
    """Report whether Docker and the PurpleLab lab image are ready to use."""
    if not docker_cli_available():
        typer.echo(
            "Docker CLI was not found. Install/start Docker before using the Docker lab.",
            err=True,
        )
        raise typer.Exit(code=1)

    if not docker_daemon_available():
        typer.echo(
            "Docker is installed, but the Docker engine is not reachable.", err=True
        )
        raise typer.Exit(code=1)

    if not lab_image_built():
        typer.echo(
            f"Docker is available, but the lab image ({LAB_IMAGE}) has not been built.\n"
            "Run `purplelab lab build` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Docker is available and the lab image ({LAB_IMAGE}) is built.")


if __name__ == "__main__":
    app()
