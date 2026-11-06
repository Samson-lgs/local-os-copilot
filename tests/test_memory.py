from pathlib import Path

from src.memory import MemoryStore


def test_memory_store_saves_and_recalls_local_facts(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.sqlite3")

    assert store.remember("User prefers concise answers.").startswith("Success")
    result = store.recall("concise")

    assert "User prefers concise answers." in result


def test_memory_store_rejects_empty_content(tmp_path: Path):
    assert MemoryStore(tmp_path / "memory.sqlite3").remember(" ").startswith("Error")
