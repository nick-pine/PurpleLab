"""Command-line interface for PurpleLab.

This module wires Typer commands to the (currently minimal) application
behavior. It intentionally contains no simulation logic itself -- future
milestones will delegate to an application/service layer so the same logic
can be reused by the web API.
"""

from __future__ import annotations

import typer

from purplelab import __version__
from purplelab.engine import SimulationEngine
from purplelab.registry import SimulationNotFoundError, create_default_registry

app = typer.Typer(
    name="purplelab",
    help="PurpleLab - a local adversary-emulation and detection-validation platform.",
    add_completion=False,
)


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

    typer.echo(f"{'TECHNIQUE':<12} {'NAME':<30} {'PLATFORM':<10} {'RISK':<8}")
    for simulation in simulations:
        metadata = simulation.metadata
        typer.echo(
            f"{metadata.technique_id:<12} {metadata.name:<30} "
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
def run_simulation(technique_id: str) -> None:
    """Execute a simulation and display its execution result."""
    registry = create_default_registry()

    try:
        simulation = registry.get(technique_id)
    except SimulationNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    result = SimulationEngine().run(simulation)
    metadata = simulation.metadata

    typer.echo("PurpleLab Simulation Execution\n")
    typer.echo(f"Technique:    {metadata.technique_id}")
    typer.echo(f"Name:         {metadata.name}")
    typer.echo(f"Status:       {'Success' if result.success else 'Failed'}")

    if not result.success:
        typer.echo(f"\nError:\n{result.error}", err=True)
        typer.echo(f"\nStarted:      {result.started_at.isoformat()}")
        typer.echo(f"Finished:     {result.finished_at.isoformat()}")
        raise typer.Exit(code=1)

    typer.echo("\nSystem Information:")
    for key, value in result.data.items():
        typer.echo(f"{key.capitalize() + ':':<13} {value}")
    typer.echo(f"\nStarted:      {result.started_at.isoformat()}")
    typer.echo(f"Finished:     {result.finished_at.isoformat()}")


if __name__ == "__main__":
    app()
