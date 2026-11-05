import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any
from uuid import uuid4

import ollama

from src.executor import AVAILABLE_FUNCTIONS, execute_tool
from src.main import MODEL, TOOLS_SCHEMA
from src.settings import (
    MAX_TOOL_ROUNDS,
    OLLAMA_HOST,
    build_task_plan,
    should_offer_tools,
    trim_history,
    validate_local_endpoint,
)


class SamApp(tk.Tk):
    """A local-only desktop interface for the OS Copilot."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Sam | Private AI Workspace")
        self.geometry("920x680")
        self.minsize(720, 520)
        self.configure(bg="#0b1117")
        self.model = MODEL
        self.ollama_client = ollama.Client(host=OLLAMA_HOST)
        self.stop_event = threading.Event()
        self.session_id = uuid4().hex[:8].upper()
        self.activity_items: list[str] = []
        self.messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are Sam, a concise local OS copilot. Use search_documents for questions about files, notes, or the project knowledge base. "
                    "Use read_screen only for text visible on the computer screen. Use tools only when needed. "
                    "Never claim an action succeeded unless its tool result says so."
                ),
            }
        ]
        self._build_ui()
        self.after(150, self._check_connection)
        self._append_message(
            "Sam",
            "Ready. I can read your screen, search local documents, and control local apps.",
            "assistant",
        )

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg="#111820", width=242)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        tk.Label(
            sidebar,
            text="SAM",
            bg="#111820",
            fg="#f2f7f5",
            font=("Segoe UI", 26, "bold"),
        ).pack(anchor="w", padx=24, pady=(28, 2))
        tk.Label(
            sidebar,
            text="LOCAL OS COPILOT",
            bg="#111820",
            fg="#72d6aa",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=26)

        status = tk.Frame(sidebar, bg="#18242d", highlightthickness=1, highlightbackground="#263540")
        status.pack(fill="x", padx=18, pady=(42, 18))
        tk.Label(status, text="RUNTIME", bg="#18242d", fg="#8fa0ad", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        self.connection_label = tk.Label(status, text="●  Checking Ollama...", bg="#18242d", fg="#e5c27b", font=("Segoe UI", 10))
        self.connection_label.pack(anchor="w", padx=14, pady=(0, 12))

        tk.Label(sidebar, text="TOOLS", bg="#111820", fg="#71818d", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=26, pady=(12, 8))
        for capability in ("Read visible screen text", "Open desktop applications", "Type into focused windows"):
            tk.Label(sidebar, text=f"  {capability}", bg="#111820", fg="#c0ccd4", font=("Segoe UI", 9), wraplength=195, justify="left").pack(anchor="w", padx=20, pady=5)

        tk.Label(sidebar, text="MODEL", bg="#111820", fg="#71818d", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=24, pady=(18, 4))
        model_row = tk.Frame(sidebar, bg="#111820")
        model_row.pack(fill="x", padx=20)
        self.model_box = ttk.Combobox(model_row, values=(MODEL,), state="normal", font=("Consolas", 8))
        self.model_box.set(MODEL)
        self.model_box.pack(side="left", fill="x", expand=True)
        tk.Button(model_row, text="↻", command=self._refresh_models, bg="#22303a", fg="#d9e7df", activebackground="#30424e", relief="flat", padx=7, cursor="hand2").pack(side="right", padx=(5, 0))
        tk.Label(sidebar, text="Installed models only", bg="#111820", fg="#71818d", font=("Segoe UI", 8), wraplength=195, justify="left").pack(anchor="w", padx=24, pady=(5, 22))

        activity_card = tk.Frame(sidebar, bg="#18242d", highlightthickness=1, highlightbackground="#263540")
        activity_card.pack(fill="both", expand=True, padx=18, pady=(0, 20))
        tk.Label(activity_card, text="AGENT TRACE", bg="#18242d", fg="#8fa0ad", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        self.activity_list = tk.Listbox(activity_card, height=6, bg="#18242d", fg="#b8c5c0", selectbackground="#245644", relief="flat", bd=0, highlightthickness=0, font=("Consolas", 8), activestyle="none")
        self.activity_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        content = tk.Frame(self, bg="#0b1117")
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)

        header = tk.Frame(content, bg="#0b1117")
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 12))
        header.columnconfigure(0, weight=1)
        tk.Label(header, text="Sam", bg="#0b1117", fg="#f2f7f5", font=("Segoe UI", 21, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(header, text="Private AI workspace  ·  local model  ·  bounded tools", bg="#0b1117", fg="#84939d", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=(3, 0))
        actions = tk.Frame(header, bg="#0b1117")
        actions.grid(row=0, column=1, rowspan=2, sticky="e")
        self.export_button = tk.Button(actions, text="Export", command=self._export_chat, bg="#1b2731", fg="#dbe7e2", activebackground="#263843", relief="flat", padx=10, pady=6, cursor="hand2")
        self.export_button.pack(side="left", padx=(0, 6))
        self.clear_button = tk.Button(actions, text="New chat", command=self._clear_chat, bg="#176b55", fg="#ffffff", activebackground="#208568", relief="flat", padx=10, pady=6, cursor="hand2")
        self.clear_button.pack(side="left")
        self.activity_label = tk.Label(header, text="READY", bg="#0b1117", fg="#72d6aa", font=("Consolas", 8, "bold"))
        self.activity_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.session_label = tk.Label(header, text=f"SESSION {self.session_id}", bg="#0b1117", fg="#71818d", font=("Consolas", 8))
        self.session_label.grid(row=2, column=1, sticky="e", pady=(10, 0))

        quick_actions = tk.Frame(content, bg="#0b1117")
        quick_actions.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 12))
        tk.Label(quick_actions, text="START WITH", bg="#0b1117", fg="#71818d", font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 10))
        for label, prompt in (("Read screen", "Read the text currently visible on my screen"), ("Search knowledge", "Search my local documents for relevant context"), ("Explain screen", "Read my screen and briefly explain what is visible")):
            tk.Button(quick_actions, text=label, command=lambda value=prompt: self._quick_prompt(value), bg="#17232d", fg="#c3d6cf", activebackground="#243b35", relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=3)

        self.chat = scrolledtext.ScrolledText(content, wrap="word", state="disabled", bg="#111a23", fg="#e1e9ee", relief="flat", bd=0, padx=22, pady=18, font=("Segoe UI", 11), insertbackground="#e1e9ee")
        self.chat.grid(row=2, column=0, sticky="nsew", padx=32, pady=(0, 16))
        self.chat.tag_configure("assistant", foreground="#e1e9ee", spacing1=5, spacing3=12)
        self.chat.tag_configure("user", foreground="#72d6aa", spacing1=5, spacing3=12)
        self.chat.tag_configure("event", foreground="#e5c27b", spacing1=5, spacing3=12)

        composer = tk.Frame(content, bg="#0b1117")
        composer.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 28))
        composer.columnconfigure(0, weight=1)
        self.entry = tk.Entry(composer, bg="#17232d", fg="#e1e9ee", relief="flat", bd=0, font=("Segoe UI", 11), insertbackground="#e1e9ee")
        self.entry.grid(row=0, column=0, sticky="ew", ipady=11, padx=(0, 10))
        self.entry.bind("<Return>", self._submit)
        self.send_button = tk.Button(composer, text="Send", command=self._submit, bg="#176b55", fg="#ffffff", activebackground="#0f5845", relief="flat", padx=18, pady=9, cursor="hand2")
        self.send_button.grid(row=0, column=1)
        self.stop_button = tk.Button(composer, text="Stop", command=self._stop_response, state="disabled", bg="#3a2528", fg="#f1b1a6", activebackground="#503033", relief="flat", padx=12, pady=9, cursor="hand2")
        self.stop_button.grid(row=0, column=2, padx=(6, 0))
        self.entry.focus_set()

    def _append_message(self, speaker: str, text: str, tag: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{speaker}\n", tag)
        self.chat.insert("end", f"{text}\n\n", tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")
        if speaker in {"Local activity", "Local result"}:
            self._add_activity(text.splitlines()[0])

    def _add_activity(self, text: str) -> None:
        self.activity_items.append(text[:58])
        self.activity_items = self.activity_items[-8:]
        self.activity_list.delete(0, "end")
        for item in self.activity_items:
            self.activity_list.insert("end", f"• {item}")

    def _check_connection(self) -> None:
        threading.Thread(target=self._check_connection_worker, daemon=True).start()

    def _check_connection_worker(self) -> None:
        try:
            validate_local_endpoint()
            self.ollama_client.list()
            self.after(0, self.connection_label.configure, {"text": "●  Ollama online", "fg": "#86d9ab"})
        except Exception:
            self.after(0, self.connection_label.configure, {"text": "●  Ollama offline", "fg": "#d98572"})

    def _clear_chat(self) -> None:
        self.messages = [self.messages[0]]
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self._append_message("Sam", "Ready. What should we do locally?", "assistant")
        self._set_activity("READY")

    def _refresh_models(self) -> None:
        self._set_activity("CHECKING LOCAL MODELS")
        threading.Thread(target=self._load_models, daemon=True).start()

    def _load_models(self) -> None:
        try:
            validate_local_endpoint()
            models = self.ollama_client.list().get("models", [])
            names = [item.get("name", "") for item in models if item.get("name")]
            self.after(0, self._apply_models, names)
        except Exception as error:
            self.after(0, self._finish_response, f"Could not list local models: {error}")

    def _apply_models(self, names: list[str]) -> None:
        values = names or [MODEL]
        self.model_box["values"] = values
        if self.model not in values:
            self.model_box.set(values[0])
        self._set_activity(f"{len(names)} LOCAL MODELS FOUND")

    def _export_chat(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Sam conversation",
            defaultextension=".txt",
            filetypes=(("Text file", "*.txt"), ("All files", "*.*")),
        )
        if not path:
            return
        transcript = self.chat.get("1.0", "end-1c")
        with open(path, "w", encoding="utf-8") as output:
            output.write(f"Sam conversation exported {datetime.now():%Y-%m-%d %H:%M}\n\n{transcript}")
        self._set_activity("CONVERSATION EXPORTED")

    def _stop_response(self) -> None:
        self.stop_event.set()
        self._set_activity("STOPPING")

    def _quick_prompt(self, prompt: str) -> None:
        if str(self.send_button["state"]) == "disabled":
            return
        self.entry.delete(0, "end")
        self.entry.insert(0, prompt)
        self._submit()

    def _set_activity(self, text: str) -> None:
        self.activity_label.configure(text=text.upper())

    def _submit(self, _event: object = None) -> str:
        prompt = self.entry.get().strip()
        if not prompt or str(self.send_button["state"]) == "disabled":
            return "break"
        self.entry.delete(0, "end")
        selected_model = self.model_box.get().strip()
        if selected_model:
            self.model = selected_model
        self._append_message("You", prompt, "user")
        self.messages.append({"role": "user", "content": prompt})
        self.messages = trim_history(self.messages)
        self.use_tools = should_offer_tools(prompt)
        self.task_plan = build_task_plan(prompt)
        self._show_plan()
        self.stop_event.clear()
        self.send_button.configure(state="disabled", text="Working...")
        self.stop_button.configure(state="normal")
        self._set_activity("THINKING LOCALLY")
        threading.Thread(target=self._respond, daemon=True).start()
        return "break"

    def _show_plan(self) -> None:
        self._add_activity("PLANNING · " + " → ".join(self.task_plan))
        self._set_activity("PLANNING")

    def _respond(self) -> None:
        try:
            validate_local_endpoint()
            for _ in range(MAX_TOOL_ROUNDS):
                if self.stop_event.is_set():
                    self.after(0, self._finish_response, "Stopped.")
                    return
                self.after(0, self._set_activity, "ACTING")
                response = self.ollama_client.chat(model=self.model, messages=self.messages, tools=TOOLS_SCHEMA if self.use_tools else None)
                assistant = response["message"]
                self.messages.append(assistant)
                tool_calls = assistant.get("tool_calls", [])
                if not tool_calls:
                    self.after(0, self._finish_response, assistant.get("content", ""))
                    return
                for tool_call in tool_calls:
                    if self.stop_event.is_set():
                        self.after(0, self._finish_response, "Stopped before the next local action.")
                        return
                    result = self._run_tool_with_confirmation(tool_call)
                    self.messages.append({"role": "tool", "content": result.content})
                    self.after(0, self._set_activity, "VERIFYING")
                    self.after(0, self._add_activity, f"VERIFIED · {result.name} · {'ok' if result.succeeded else 'failed'}")
                    self.after(
                        0,
                        self._append_message,
                        "Local result",
                        f"{result.name}: {'completed' if result.succeeded else 'failed'} in {result.duration_ms} ms\n{result.content}",
                        "event",
                    )
            self.after(0, self._finish_response, "I stopped after reaching the tool-call limit.")
        except Exception as error:
            self.after(0, self._finish_response, f"Ollama is unavailable locally: {error}\n\nStart Ollama and run: ollama pull {self.model}")

    def _run_tool_with_confirmation(self, tool_call: dict[str, Any]) -> Any:
        name = tool_call["function"]["name"]
        self.after(0, self._append_message, "Local activity", f"Running {name}...", "event")
        self.after(0, self._set_activity, f"RUNNING {name}")
        function = AVAILABLE_FUNCTIONS.get(name)
        if function is None:
            return execute_tool(tool_call)
        return execute_tool(tool_call)

    def _ask_confirmation(self, name: str, arguments: dict[str, Any]) -> bool:
        answer: list[bool] = []
        event = threading.Event()

        def ask() -> None:
            answer.append(messagebox.askyesno("Approve local action", f"Allow Sam to run:\n\n{name}({arguments})"))
            event.set()

        self.after(0, ask)
        event.wait()
        return answer[0]

    def _finish_response(self, text: str) -> None:
        self._append_message("Sam", text, "assistant")
        self.send_button.configure(state="normal", text="Send")
        self.stop_button.configure(state="disabled")
        self._set_activity("READY")
        self.entry.focus_set()


def run_ui() -> None:
    app = SamApp()
    app.mainloop()


if __name__ == "__main__":
    run_ui()
