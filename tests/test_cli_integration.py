from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "mcpdrift.cli", *args]
    return subprocess.run(command, cwd=repo, text=True, capture_output=True)


def test_init_then_diff_detects_required_input_mutation(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    server_dir = repo / "sample_server"
    shutil.copytree(Path("examples/sample_server"), server_dir)
    config = server_dir / "mcpdrift.toml"
    # Make the test hermetic: launch the sample server with the same interpreter
    # running the tests (which has `mcp` installed), not a bare `python` that may
    # be absent or lack deps on the host PATH.
    config.write_text(config.read_text().replace('command = "python"', f'command = "{sys.executable}"'))

    init = run_cli(repo, "init", "--config", str(config))

    assert init.returncode == 0, init.stderr
    snapshot = json.loads((repo / ".mcpdrift" / "contract.json").read_text())
    assert [tool["name"] for tool in snapshot["tools"]] == ["lookup_issue", "search_docs"]

    server_file = server_dir / "server.py"
    server_file.write_text(
        server_file.read_text().replace(
            'def search_docs(query: str, limit: int = 5) -> SearchDocsResult:',
            'def search_docs(query: str, region: str, limit: int = 5) -> SearchDocsResult:',
        )
    )

    diff = run_cli(repo, "diff", "--config", str(config))

    assert diff.returncode == 1
    assert "required input added on search_docs: region" in diff.stdout
