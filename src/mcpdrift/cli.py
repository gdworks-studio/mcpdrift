from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
import asyncio
import json

import typer

from .capture import capture_contract
from .config import ConfigError, load_config
from .diffing import compare_contracts, format_diff
from .snapshot import read_snapshot, write_snapshot
from .status import read_status, write_status

app = typer.Typer(help="Snapshot and diff MCP server contracts.")

DEFAULT_CONFIG = Path("mcpdrift.toml")
SNAPSHOT_PATH = Path(".mcpdrift/contract.json")
STATUS_PATH = Path(".mcpdrift/status.json")


@app.command()
def init(
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", help="Path to mcpdrift.toml."),
) -> None:
    """Capture the current MCP contract."""
    try:
        contract = asyncio.run(capture_contract(load_config(config)))
    except ConfigError as exc:
        _fail(str(exc))
    write_snapshot(SNAPSHOT_PATH, contract)
    write_status(STATUS_PATH, 0, 0)
    typer.echo(_summary("Snapshot written to .mcpdrift/contract.json", contract))


@app.command()
def diff(
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", help="Path to mcpdrift.toml."),
    update: bool = typer.Option(False, "--update", help="Overwrite the saved snapshot after diffing."),
) -> None:
    """Compare the saved snapshot with the current MCP contract."""
    if not SNAPSHOT_PATH.exists():
        _fail("no saved snapshot found; run mcpdrift init first")

    try:
        current = asyncio.run(capture_contract(load_config(config)))
    except ConfigError as exc:
        _fail(str(exc))

    previous = read_snapshot(SNAPSHOT_PATH)
    result = compare_contracts(previous, current)
    write_status(STATUS_PATH, result.breaking_count, result.non_breaking_count)
    typer.echo(format_diff(result))

    if update:
        write_snapshot(SNAPSHOT_PATH, current)
        typer.echo("Snapshot updated.")

    if result.has_breaking:
        raise typer.Exit(1)


@app.command()
def badge(
    markdown: bool = typer.Option(False, "--markdown", help="Emit a Markdown badge snippet."),
    url: str = typer.Option(
        "https://example.com/mcpdrift/status.json",
        "--url",
        help="Public URL where the shields.io endpoint JSON will be hosted.",
    ),
) -> None:
    """Emit shields.io endpoint JSON for the last diff status."""
    payload = read_status(STATUS_PATH)
    if markdown:
        badge_url = f"https://img.shields.io/endpoint?url={quote(url, safe='')}"
        typer.echo(f"![MCP contract]({badge_url})")
        return
    typer.echo(json.dumps(payload, sort_keys=True))


def _summary(prefix: str, contract: dict) -> str:
    return (
        f"{prefix}\n"
        f"Summary: {len(contract.get('tools', []))} tools, "
        f"{len(contract.get('resources', []))} resources, "
        f"{len(contract.get('prompts', []))} prompts."
    )


def _fail(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(2)


if __name__ == "__main__":
    app()
