"""Command-line interface for PurpleLab.

This module wires Typer commands to the (currently minimal) application
behavior. It intentionally contains no simulation logic itself -- future
milestones will delegate to an application/service layer so the same logic
can be reused by the web API.
"""

from __future__ import annotations

import typer

from purplelab import __version__
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
        typer.echo(
            f"{simulation.technique_id:<12} {simulation.name:<30} "
            f"{simulation.platform.value:<10} {simulation.risk.value:<8}"
        )


@app.command("info")
def simulation_info(technique_id: str) -> None:
    """Show detailed metadata for a single simulation."""
    registry = create_default_registry()

    try:
        simulation = registry.get(technique_id)
    except SimulationNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    telemetry = "\n".join(f"- {entry}" for entry in simulation.expected_telemetry)
    detection = simulation.expected_detection_rule or "Not configured"

    typer.echo("PurpleLab Simulation\n")
    typer.echo(f"Technique:    {simulation.technique_id}")
    typer.echo(f"Name:         {simulation.name}")
    typer.echo(f"Tactic:       {simulation.tactic.value}")
    typer.echo(f"Platform:     {simulation.platform.value}")
    typer.echo(f"Risk:         {simulation.risk.value}")
    typer.echo(f"\nDescription:\n{simulation.description}")
    typer.echo(f"\nExpected Telemetry:\n{telemetry}")
    typer.echo(f"\nExpected Detection:\n{detection}")


if __name__ == "__main__":
    app()
