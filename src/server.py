"""Local HTTP API and static frontend server for Sam."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import ollama

from src.audio import record_and_transcribe
from src.executor import execute_tool
from src.main import TOOLS_SCHEMA
from src.memory import recall_memory, remember
from src.settings import MAX_TOOL_ROUNDS, MODEL, OLLAMA_HOST, should_offer_tools, validate_local_endpoint
from src.speech import speak_text
from src.vision import read_screen_region, screenshot_payload

WEB_DIR = Path(__file__).parent.parent / "web"
SYSTEM_PROMPT = (
    "You are Sam, a concise local OS copilot. Use search_documents for local files and memory tools for preferences. "
    "Use read_screen only for visible screen content. Never claim an action succeeded unless its tool result says so."
)


def chat_request(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    validate_local_endpoint()
    client = ollama.Client(host=OLLAMA_HOST)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": message})
    events: list[dict[str, Any]] = []
    use_tools = should_offer_tools(message)
    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat(model=MODEL, messages=messages, tools=TOOLS_SCHEMA if use_tools else None)
        assistant = response["message"]
        messages.append(assistant)
        calls = assistant.get("tool_calls", [])
        if not calls:
            return {"reply": assistant.get("content", ""), "events": events, "messages": messages[-8:]}
        for call in calls:
            result = execute_tool(call)
            events.append({"name": result.name, "ok": result.succeeded, "duration_ms": result.duration_ms, "content": result.content})
            messages.append({"role": "tool", "content": result.content})
    return {"reply": "I stopped after reaching the tool-call limit.", "events": events, "messages": messages[-8:]}


class SamHandler(BaseHTTPRequestHandler):
    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            try:
                validate_local_endpoint()
                ollama.Client(host=OLLAMA_HOST).list()
                self._json({"online": True, "model": MODEL, "host": OLLAMA_HOST})
            except Exception as error:
                self._json({"online": False, "model": MODEL, "error": str(error)}, 503)
            return
        if parsed.path == "/api/screenshot":
            try:
                self._json(screenshot_payload())
            except Exception as error:
                self._json({"error": str(error)}, 500)
            return
        path = (WEB_DIR / ("index.html" if parsed.path == "/" else parsed.path.lstrip("/"))).resolve()
        if WEB_DIR not in path.parents or not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        try:
            body = self._body()
            if self.path == "/api/chat":
                self._json(chat_request(str(body.get("message", "")), body.get("history", [])))
            elif self.path == "/api/ocr-region":
                self._json({"text": read_screen_region(int(body["left"]), int(body["top"]), int(body["width"]), int(body["height"]))})
            elif self.path == "/api/voice":
                self._json({"text": record_and_transcribe(int(body.get("seconds", 8)))})
            elif self.path == "/api/memory":
                action = body.get("action", "recall")
                result = remember(str(body.get("content", ""))) if action == "remember" else recall_memory(str(body.get("query", "")))
                self._json({"result": result})
            elif self.path == "/api/speak":
                self._json({"result": speak_text(str(body.get("text", "")))})
            else:
                self._json({"error": "Not found"}, 404)
        except Exception as error:
            self._json({"error": str(error)}, 500)


def run_server(port: int = 8765) -> None:
    from src.rag import _index

    _index.start_watcher()
    server = ThreadingHTTPServer(("127.0.0.1", port), SamHandler)
    print(f"Sam web UI: http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
