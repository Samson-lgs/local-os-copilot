import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from src.audio import record_and_transcribe
from src.memory import recall_memory, remember
from src.rag import search_documents
from src.tools import open_application, type_text
from src.vision import read_screen, read_screen_region


@dataclass(frozen=True)
class ToolResult:
    name: str
    content: str
    succeeded: bool
    duration_ms: int = 0


AVAILABLE_FUNCTIONS: dict[str, Callable[..., str]] = {
    "open_application": open_application,
    "type_text": type_text,
    "read_screen": read_screen,
    "read_screen_region": read_screen_region,
    "search_documents": search_documents,
    "remember": remember,
    "recall_memory": recall_memory,
    "record_and_transcribe": record_and_transcribe,
}


def parse_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    function = tool_call.get("function", {})
    arguments = function.get("arguments", {})
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object.")
    return arguments


def execute_tool(tool_call: dict[str, Any]) -> ToolResult:
    started = time.perf_counter()
    function = tool_call.get("function", {})
    name = function.get("name")
    if not isinstance(name, str) or name not in AVAILABLE_FUNCTIONS:
        return ToolResult(str(name or "unknown"), "Error: Unknown tool.", False, _duration_ms(started))
    try:
        result = AVAILABLE_FUNCTIONS[name](**parse_arguments(tool_call))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return ToolResult(name, f"Error: Invalid arguments. {error}", False, _duration_ms(started))
    except Exception as error:
        return ToolResult(name, f"Error: Tool failed. {error}", False, _duration_ms(started))
    return ToolResult(name, result, not result.startswith("Error:"), _duration_ms(started))


def _duration_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)