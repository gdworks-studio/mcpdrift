# MCPFlight

Catch MCP tool and schema regressions before your users' agents do.

MCPFlight is a local-first CLI for MCP servers. It connects to a server over stdio, snapshots the server contract, then diffs future runs against that snapshot. v0.1 captures structural metadata only: tool names, descriptions, input schemas, output schemas, resources, and prompts. It does not call tools, collect user data, send telemetry, or require a hosted backend.

## 5-minute quickstart

Requires Python 3.10 or newer.

```bash
git clone https://github.com/your-org/mcpflight.git
cd mcpflight
python -m pip install -e .
```

Create `mcpflight.toml` in the repo that owns your MCP server:

```toml
[server]
command = "python"
args = ["-m", "my_server"]
# env = { KEY = "value" }
```

Capture the baseline contract:

```bash
mcpflight init
git add mcpflight.toml .mcpflight/contract.json
git commit -m "test: add MCP contract snapshot"
```

Check for drift in CI or before a release:

```bash
mcpflight diff
```

Exit codes:

- `0`: no breaking drift detected
- `1`: breaking drift detected
- `2`: setup/configuration problem

## Try the bundled sample server

```bash
python -m pip install -e '.[test]'
mcpflight init --config examples/sample_server/mcpflight.toml
mcpflight diff --config examples/sample_server/mcpflight.toml
```

The snapshot is written to `.mcpflight/contract.json` in your current working directory. Commit that file with your server so future diffs have a baseline.

## What MCPFlight classifies

Breaking changes:

- tool removed
- tool renamed
- required input parameter added, removed, or retyped
- input schema made stricter
- output schema shape changed
- resource or prompt removed
- prompt arguments changed

Non-breaking changes:

- tool added
- description changed
- optional input parameter added
- resource or prompt added

## Badge

After a diff run, emit shields.io endpoint JSON:

```bash
mcpflight badge > .mcpflight/status.json
```

Or print a Markdown snippet:

```bash
mcpflight badge --markdown --url https://example.com/mcpflight/status.json
```

## GitHub Action

This repo includes a composite action that installs MCPFlight, runs `mcpflight diff`, comments the report on pull requests, and fails the check when breaking drift is detected.

```yaml
name: MCP contract

on:
  pull_request:
  push:
    branches: [main]

jobs:
  mcpflight:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: gdworks/mcpflight@v0.1
        with:
          config: mcpflight.toml
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

For local development of this repo, use:

```yaml
- uses: ./
  with:
    config: examples/sample_server/mcpflight.toml
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

## v0.1 scope

MCPFlight v0.1 is stdio-only. If `transport = "http"` or another future transport appears in config, the CLI exits with a clear unsupported-transport message.

Out of scope for v0.1: streamable HTTP, record/replay testing, risk/security checks, TypeScript/npm packaging, hosted history, telemetry, and any backend service.
