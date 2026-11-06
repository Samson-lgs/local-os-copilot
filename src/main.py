from typing import Any

import ollama

from src.executor import execute_tool, parse_arguments
from src.settings import MAX_TOOL_ROUNDS, MODEL, OLLAMA_HOST, should_offer_tools, trim_history, validate_local_endpoint

ollama_client = ollama.Client(host=OLLAMA_HOST)
TOOLS_SCHEMA = [
    {"type": "function", "function": {"name": "open_application", "description": "Open a desktop application by name.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "type_text", "description": "Type text into the currently focused local window.", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "read_screen", "description": "Capture the primary screen and extract visible text locally.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "read_screen_region", "description": "Extract text from a selected screen rectangle locally.", "parameters": {"type": "object", "properties": {"left": {"type": "integer"}, "top": {"type": "integer"}, "width": {"type": "integer"}, "height": {"type": "integer"}}, "required": ["left", "top", "width", "height"]}}},
    {"type": "function", "function": {"name": "search_documents", "description": "Search files in the local docs folder using embeddings. Use this for questions about project notes or documents. Do not use read_screen for document questions.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "minimum": 1, "maximum": 5}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "remember", "description": "Save a user-approved preference or fact in local SQLite memory.", "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}}},
    {"type": "function", "function": {"name": "recall_memory", "description": "Retrieve relevant facts from Sam's local SQLite memory.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}}}}},
    {"type": "function", "function": {"name": "record_and_transcribe", "description": "Record a short microphone clip and transcribe it locally with Whisper.", "parameters": {"type": "object", "properties": {"seconds": {"type": "integer", "minimum": 1, "maximum": 30}}, "required": []}}},
]
CONFIRMATION_REQUIRED: set[str] = set()


def _arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    return parse_arguments(tool_call)


def _run_tool(tool_call: dict[str, Any]) -> str:
    return execute_tool(tool_call).content


def _chat(messages: list[dict[str, Any]], use_tools: bool = True) -> dict[str, Any] | None:
    try:
        validate_local_endpoint()
        return ollama_client.chat(model=MODEL, messages=messages, tools=TOOLS_SCHEMA if use_tools else None)
    except Exception as error:
        print(f"\nOllama is unavailable locally: {error}")
        print(f"Start Ollama and make sure the model exists: ollama pull {MODEL}")
        return None


def run_copilot() -> None:
    print(f"Local OS Copilot ready ({MODEL}). Type 'exit' to quit.")
    print("Privacy: requests are sent only to the local Ollama server.")
    messages: list[dict[str, Any]] = [{"role": "system", "content": "You are a local OS copilot. Use search_documents for questions about files, notes, or the project knowledge base. Use read_screen only for text visible on the computer screen. Use tools only when needed. Never claim an action succeeded unless its tool result says so. Keep responses concise."}]
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nShutting down Copilot...")
            return
        if user_input.lower() in {"exit", "quit"}:
            print("Shutting down Copilot...")
            return
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        messages = trim_history(messages)
        use_tools = should_offer_tools(user_input)
        for _ in range(MAX_TOOL_ROUNDS):
            response = _chat(messages, use_tools=use_tools)
            if response is None:
                return
            assistant_message = response["message"]
            messages.append(assistant_message)
            tool_calls = assistant_message.get("tool_calls", [])
            if not tool_calls:
                print(f"\nCopilot: {assistant_message.get('content', '')}")
                break
            for tool_call in tool_calls:
                name = tool_call["function"]["name"]
                print(f"Running local tool: {name}")
                try:
                    tool_result = execute_tool(tool_call)
                    result = tool_result.content
                    print(f"Tool {tool_result.name}: {'ok' if tool_result.succeeded else 'failed'} ({tool_result.duration_ms} ms)")
                except Exception as error:
                    result = f"Error: {error}"
                messages.append({"role": "tool", "content": result})
        else:
            print("Copilot: I stopped after reaching the tool-call limit.")


if __name__ == "__main__":
    run_copilot()