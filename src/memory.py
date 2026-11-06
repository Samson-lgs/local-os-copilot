"""Small local SQLite memory store for user-approved facts and preferences."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MEMORY_PATH = Path("sam-memory.sqlite3")


class MemoryStore:
    def __init__(self, path: Path = MEMORY_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, content TEXT NOT NULL, created_at TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def remember(self, content: str) -> str:
        content = content.strip()
        if not content:
            return "Error: Memory cannot be empty."
        if len(content) > 2_000:
            return "Error: Memory is too long."
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO memories(content, created_at) VALUES (?, ?)",
                (content, datetime.now(timezone.utc).isoformat()),
            )
        return "Success: Memory saved locally."

    def recall(self, query: str = "", limit: int = 5) -> str:
        query = query.strip()
        limit = max(1, min(int(limit), 10))
        with self._connect() as connection:
            if query:
                rows = connection.execute(
                    "SELECT content, created_at FROM memories WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                    (f"%{query}%", limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT content, created_at FROM memories ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
        if not rows:
            return "No matching local memories found."
        return "\n".join(f"- {content} ({created_at})" for content, created_at in rows)


_store = MemoryStore()


def remember(content: str) -> str:
    return _store.remember(content)


def recall_memory(query: str = "", limit: int = 5) -> str:
    return _store.recall(query, limit)
