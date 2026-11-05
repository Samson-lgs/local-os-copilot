from src.executor import execute_tool, parse_arguments


def test_executor_rejects_unknown_tool():
    result = execute_tool({"function": {"name": "delete_files", "arguments": {}}})

    assert not result.succeeded
    assert result.name == "delete_files"


def test_executor_rejects_malformed_arguments():
    result = execute_tool({"function": {"name": "read_screen", "arguments": "not-json"}})

    assert not result.succeeded
    assert "Invalid arguments" in result.content


def test_parse_arguments_accepts_json_objects():
    tool_call = {"function": {"arguments": '{"app_name": "Calculator"}'}}

    assert parse_arguments(tool_call) == {"app_name": "Calculator"}