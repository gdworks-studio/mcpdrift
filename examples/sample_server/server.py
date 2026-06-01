from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP("mcpdrift Sample")


class SearchDocsResult(BaseModel):
    results: list[str]


class LookupIssueResult(BaseModel):
    issue_id: int
    status: str


@mcp.tool(structured_output=True)
def search_docs(query: str, limit: int = 5) -> SearchDocsResult:
    """Search documentation snippets."""
    return SearchDocsResult(results=[f"{query} result {index}" for index in range(limit)])


@mcp.tool(structured_output=True)
def lookup_issue(issue_id: int) -> LookupIssueResult:
    """Look up an issue by numeric ID."""
    return LookupIssueResult(issue_id=issue_id, status="open")


@mcp.resource("docs://status", name="status", description="Sample status resource")
def status_resource() -> str:
    return "mcpdrift sample server is healthy."


@mcp.prompt(description="Create a short triage plan for a documentation area.")
def triage_docs(area: str) -> str:
    return f"Review {area}, list contract changes, and note compatibility risks."


if __name__ == "__main__":
    mcp.run("stdio")
