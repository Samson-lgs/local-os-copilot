import os
import re
from urllib.parse import urlparse

MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MAX_TOOL_ROUNDS = 4
MAX_MESSAGES = 40
TOOL_INTENT_PATTERN = re.compile(
    r"\b(screen|screenshot|visible|see|document|docs|file|notes|knowledge|search|open|launch|start|type|write|enter|fill|calculator|notepad|paint|remember|recall|memory|voice|microphone|record|transcribe)\b",
    re.IGNORECASE,
)


def validate_local_endpoint(host: str = OLLAMA_HOST) -> str:
    candidate = host if "://" in host else f"http://{host}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError(
            "OLLAMA_HOST must point to a local endpoint (localhost, 127.0.0.1, or ::1)."
        )
    return candidate.rstrip("/")


def trim_history(messages: list[dict], limit: int = MAX_MESSAGES) -> list[dict]:
    if len(messages) <= limit:
        return messages
    return [messages[0], *messages[-(limit - 1):]]


def should_offer_tools(prompt: str) -> bool:
    """Only expose desktop tools when the request expresses a tool intent."""
    return bool(TOOL_INTENT_PATTERN.search(prompt))


def build_task_plan(prompt: str) -> list[str]:
    """Build a small deterministic plan for the visible agent trace."""
    lowered = prompt.casefold()
    plan = ["Understand request"]
    if any(word in lowered for word in ("screen", "screenshot", "visible", "see")):
        plan.append("Read visible screen")
    if any(word in lowered for word in ("document", "docs", "file", "notes", "knowledge", "search")):
        plan.append("Search local knowledge")
    if any(word in lowered for word in ("open", "launch", "start", "calculator", "notepad", "paint")):
        plan.append("Run desktop action")
    if any(word in lowered for word in ("type", "write", "enter", "fill")):
        plan.append("Enter requested text")
    plan.append("Verify result")
    return plan