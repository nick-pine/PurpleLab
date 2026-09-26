"""Command-line interface for PurpleLab.

This module wires Typer commands to the (currently minimal) application
behavior. It intentionally contains no simulation logic itself -- future
milestones will delegate to an application/service layer so the same logic
can be reused by the web API.
"""

from __future__ import annotations

import typer

from purplelab import __version__

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
    # No simulation registry exists yet (Milestone 3).
    typer.echo("No simulations installed.")


if __name__ == "__main__":
    app()
