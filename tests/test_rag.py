from pathlib import Path

import pytest

from src.rag import LocalDocumentIndex, _chunks, _cosine


class FakeEmbeddingClient:
    def embed(self, *, model, input):
        return {"embeddings": [[float(len(input)), 1.0]]}


def test_chunks_normalize_and_split_text():
    assert _chunks("  hello   local   RAG  ", size=20, overlap=2) == ["hello local RAG"]


def test_cosine_similarity_is_one_for_equal_vectors():
    assert _cosine([1.0, 2.0], [1.0, 2.0]) == pytest.approx(1.0)


def test_local_index_builds_and_searches_documents(tmp_path: Path):
    (tmp_path / "notes.md").write_text("Sam runs entirely on a local computer.", encoding="utf-8")
    index = LocalDocumentIndex(FakeEmbeddingClient(), tmp_path, tmp_path / ".index.json")

    assert index.build() == 1
    result = index.search("local computer")

    assert "notes.md" in result
    assert "local computer" in result


def test_local_index_loads_saved_embeddings(tmp_path: Path):
    (tmp_path / "notes.md").write_text("Saved local context.", encoding="utf-8")
    index_path = tmp_path / ".index.json"
    first = LocalDocumentIndex(FakeEmbeddingClient(), tmp_path, index_path)
    first.build()

    second = LocalDocumentIndex(FakeEmbeddingClient(), tmp_path, index_path)
    assert "notes.md" in second.search("saved context")


def test_search_clamps_string_top_k_value(tmp_path: Path):
    (tmp_path / "notes.md").write_text("Bounded retrieval result.", encoding="utf-8")
    index = LocalDocumentIndex(FakeEmbeddingClient(), tmp_path, tmp_path / ".index.json")

    result = index.search("retrieval", top_k="10")

    assert "Bounded retrieval result" in result