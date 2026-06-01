from __future__ import annotations

from mcpdrift.diffing import compare_contracts


def contract(tools):
    return {
        "snapshot_schema_version": 1,
        "mcp_protocol_version": "2025-06-18",
        "tools": tools,
        "resources": [],
        "prompts": [],
    }


def tool(name="search_docs", description="Search docs", input_schema=None, output_schema=None):
    return {
        "name": name,
        "description": description,
        "inputSchema": input_schema
        or {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        "outputSchema": output_schema
        or {
            "type": "object",
            "properties": {"results": {"type": "array"}},
            "required": ["results"],
        },
    }


def messages(result, severity):
    return [change.message for change in result.changes if change.severity == severity]


def test_tool_removed_is_breaking():
    result = compare_contracts(contract([tool()]), contract([]))

    assert result.has_breaking
    assert "tool removed: search_docs" in messages(result, "BREAKING")


def test_required_input_added_is_breaking():
    after = tool(
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "region": {"type": "string"},
            },
            "required": ["query", "region"],
        }
    )

    result = compare_contracts(contract([tool()]), contract([after]))

    assert result.has_breaking
    assert "required input added on search_docs: region" in messages(result, "BREAKING")


def test_required_input_removed_is_breaking():
    after = tool(
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": [],
        }
    )

    result = compare_contracts(contract([tool()]), contract([after]))

    assert result.has_breaking
    assert "required input removed on search_docs: query" in messages(result, "BREAKING")


def test_required_input_retyped_is_breaking():
    after = tool(
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
    )

    result = compare_contracts(contract([tool()]), contract([after]))

    assert result.has_breaking
    assert "required input retyped on search_docs.query: string -> array" in messages(result, "BREAKING")


def test_input_schema_made_stricter_is_breaking():
    after = tool(
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 3},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
    )

    result = compare_contracts(contract([tool()]), contract([after]))

    assert result.has_breaking
    assert "input schema stricter on search_docs.query: minLength added as 3" in messages(result, "BREAKING")


def test_output_schema_change_is_breaking():
    after = tool(
        output_schema={
            "type": "object",
            "properties": {"items": {"type": "array"}},
            "required": ["items"],
        }
    )

    result = compare_contracts(contract([tool()]), contract([after]))

    assert result.has_breaking
    assert "output schema changed on search_docs" in messages(result, "BREAKING")


def test_tool_rename_is_breaking_when_contract_matches_new_name():
    before = tool(name="search_docs")
    after = tool(name="find_docs")

    result = compare_contracts(contract([before]), contract([after]))

    assert result.has_breaking
    assert "tool renamed: search_docs -> find_docs" in messages(result, "BREAKING")


def test_tool_added_description_changed_and_optional_param_added_are_non_breaking():
    after_existing = tool(
        description="Search docs quickly",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "locale": {"type": "string"},
            },
            "required": ["query"],
        },
    )
    after_new = tool(name="summarize_doc")

    result = compare_contracts(contract([tool()]), contract([after_existing, after_new]))

    assert not result.has_breaking
    assert "tool added: summarize_doc" in messages(result, "NON-BREAKING")
    assert "description changed on search_docs" in messages(result, "NON-BREAKING")
    assert "optional input added on search_docs: locale" in messages(result, "NON-BREAKING")
