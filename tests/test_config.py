from __future__ import annotations

import sys
from pathlib import Path

import mcpdrift.config as config_mod
from mcpdrift.config import load_config


def _write_config(tmp_path: Path, command: str) -> Path:
    cfg = tmp_path / "mcpdrift.toml"
    cfg.write_text(f'[server]\ncommand = "{command}"\nargs = ["server.py"]\n')
    return cfg


def test_bare_python_falls_back_to_sys_executable_when_not_on_path(tmp_path, monkeypatch):
    cfg = _write_config(tmp_path, "python")
    monkeypatch.setattr(config_mod.shutil, "which", lambda _name: None)
    assert load_config(cfg).command == sys.executable


def test_resolvable_python_is_left_unchanged(tmp_path, monkeypatch):
    cfg = _write_config(tmp_path, "python")
    monkeypatch.setattr(config_mod.shutil, "which", lambda _name: "/usr/bin/python")
    assert load_config(cfg).command == "python"


def test_explicit_command_is_never_rewritten(tmp_path, monkeypatch):
    cfg = _write_config(tmp_path, "/opt/custom/bin/myserver")
    monkeypatch.setattr(config_mod.shutil, "which", lambda _name: None)
    assert load_config(cfg).command == "/opt/custom/bin/myserver"
