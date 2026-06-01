from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


class ConfigError(Exception):
    """Raised when mcpdrift.toml cannot be used."""


@dataclass(frozen=True)
class ServerConfig:
    command: str
    args: list[str]
    env: dict[str, str] | None
    cwd: Path


def load_config(path: Path) -> ServerConfig:
    config_path = path.expanduser().resolve()
    if not config_path.exists():
        raise ConfigError(f"config not found: {config_path}")

    data = tomllib.loads(config_path.read_text())
    server = _table(data, "server")

    transport = str(server.get("transport", "stdio"))
    if transport != "stdio":
        raise ConfigError(f'transport "{transport}" is not yet supported in v0.1; use stdio')

    command = server.get("command")
    if not isinstance(command, str) or not command:
        raise ConfigError('[server].command must be a non-empty string')

    args = server.get("args", [])
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        raise ConfigError("[server].args must be a list of strings")

    env = server.get("env")
    if env is not None:
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
            raise ConfigError("[server].env must be a table of string values")

    return ServerConfig(command=_resolve_command(command), args=args, env=env, cwd=config_path.parent)


def _resolve_command(command: str) -> str:
    # A bare `python`/`python3` (common in samples/quickstarts) is often not on
    # PATH — stock macOS ships only `python3`, and you may run mcpdrift without an
    # activated venv. Fall back to the interpreter running mcpdrift, which has the
    # deps installed. An explicit path or any other command is left untouched.
    if command in {"python", "python3"} and shutil.which(command) is None:
        return sys.executable
    return command


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"[{key}] table is required")
    return value
