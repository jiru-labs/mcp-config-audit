"""Typer entrypoint for the mcp-scan CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from mcp_scan import __version__
from mcp_scan.discovery import ConfigLocation, find_claude_desktop_config
from mcp_scan.parsers import MCPServer, parse_config_file

app = typer.Typer(
    name="mcp-scan",
    help="Scan local MCP configurations for security risks.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.callback()
def main() -> None:
    """Keep mcp-scan a command group even while only one command exists."""


@app.command()
def version() -> None:
    """Print the mcp-scan version."""
    console.print(f"mcp-scan {__version__}")


@app.command("list")
def list_servers(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Parse this config file instead of discovering the installed hosts.",
        ),
    ] = None,
) -> None:
    """List the MCP servers declared in your local host configs.

    Environment variables are reported by name only; their values are never
    read into the report.
    """
    paths = [config] if config is not None else _discovered_config_paths()

    servers: list[MCPServer] = []
    warnings: list[str] = []
    for path in paths:
        result = parse_config_file(path)
        servers.extend(result.servers)
        warnings.extend(result.warnings)

    if servers:
        console.print(_servers_table(servers))

    for warning in warnings:
        console.print(f"[yellow]warning:[/yellow] {warning}")

    # Only explain an empty result that the warnings above have not already
    # explained.
    if not servers and not warnings:
        message = (
            "No MCP servers declared in any config file."
            if paths
            else "No MCP config files found."
        )
        console.print(f"[yellow]{message}[/yellow]")


def _discovered_config_paths() -> list[Path]:
    """Paths of the config files that actually exist on this machine."""
    locations: list[ConfigLocation] = [find_claude_desktop_config()]
    return [location.path for location in locations if location.exists]


def _servers_table(servers: list[MCPServer]) -> Table:
    table = Table(title="MCP servers")
    table.add_column("Server", style="bold")
    table.add_column("Transport")
    table.add_column("Command / URL", overflow="fold")
    table.add_column("Env keys", overflow="fold")
    table.add_column("Source", overflow="fold", style="dim")

    for server in servers:
        table.add_row(
            server.name,
            server.transport,
            server.endpoint or "-",
            ", ".join(server.env_keys) or "-",
            str(server.source),
        )

    return table
