"""Local document retrieval using Ollama embeddings and cosine similarity."""

import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import ollama
from docx import Document
from pypdf import PdfReader

from src.settings import OLLAMA_HOST, validate_local_endpoint

EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
DOCUMENTS_DIR = Path(os.getenv("SAM_DOCUMENTS_DIR", "docs"))
INDEX_PATH = DOCUMENTS_DIR / ".sam-index.json"
SUPPORTED_SUFFIXES = {".md", ".txt", ".py", ".json", ".rst", ".pdf", ".docx"}


class EmbeddingClient(Protocol):
    def embed(self, *, model: str, input: str) -> Any:
        ...


@dataclass(frozen=True)
class DocumentChunk:
    source: str
    text: str
    embedding: list[float]
    page: int | None = None


def _chunks(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    return [normalized[start:start + size] for start in range(0, len(normalized), size - overlap)]


def _embedding(response: Any) -> list[float]:
    embeddings = response.get("embeddings") if isinstance(response, dict) else getattr(response, "embeddings", None)
    if not embeddings:
        raise ValueError("Embedding response did not contain embeddings.")
    return [float(value) for value in embeddings[0]]


def _cosine(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def _read_document(path: Path) -> str:
    return "\n".join(text for text, _ in _read_document_sections(path))


def _read_document_sections(path: Path) -> list[tuple[str, int | None]]:
    if path.suffix.lower() == ".pdf":
        return [(page.extract_text() or "", page_number) for page_number, page in enumerate(PdfReader(str(path)).pages, 1)]
    if path.suffix.lower() == ".docx":
        document = Document(str(path))
        return [("\n".join(paragraph.text for paragraph in document.paragraphs), None)]
    return [(path.read_text(encoding="utf-8", errors="ignore"), None)]


class LocalDocumentIndex:
    def __init__(self, client: EmbeddingClient, documents_dir: Path = DOCUMENTS_DIR, index_path: Path = INDEX_PATH):
        self.client = client
        self.documents_dir = documents_dir
        self.index_path = index_path
        self.chunks: list[DocumentChunk] = []

    def _load_saved(self) -> bool:
        if not self.index_path.exists():
            return False
        try:
            saved = json.loads(self.index_path.read_text(encoding="utf-8"))
            self.chunks = [DocumentChunk(**item) for item in saved]
        except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError):
            return False
        return bool(self.chunks)

    def build(self) -> int:
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.chunks = []
        for path in sorted(self.documents_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES or path.name == self.index_path.name:
                continue
            for text, page in _read_document_sections(path):
                for chunk in _chunks(text):
                    self.chunks.append(DocumentChunk(str(path), chunk, _embedding(self.client.embed(model=EMBED_MODEL, input=chunk)), page))
        self.index_path.write_text(json.dumps([asdict(chunk) for chunk in self.chunks]), encoding="utf-8")
        return len(self.chunks)

    def search(self, query: str, top_k: int = 3) -> str:
        query = query.strip()
        if not query:
            return "Error: Search query cannot be empty."
        if not self.chunks:
            if not self._load_saved():
                self.build()
        if not self.chunks:
            return "No local documents found. Add .md, .txt, .py, .json, .rst, .pdf, or .docx files to the docs folder."
        try:
            requested_top_k = int(top_k)
        except (TypeError, ValueError):
            requested_top_k = 3
        query_embedding = _embedding(self.client.embed(model=EMBED_MODEL, input=query))
        limit = max(1, min(requested_top_k, 5))
        matches = sorted(((round(_cosine(query_embedding, chunk.embedding), 4), chunk) for chunk in self.chunks), reverse=True, key=lambda item: item[0])[:limit]
        return "\n\n".join(
            f"Source: {chunk.source}{f' (page {chunk.page})' if chunk.page else ''}\n"
            f"Relevance: {score}\n{chunk.text}"
            for score, chunk in matches
        )


_client = ollama.Client(host=OLLAMA_HOST)
_index = LocalDocumentIndex(_client)


def search_documents(query: str, top_k: int = 3) -> str:
    validate_local_endpoint()
    return _index.search(query, top_k)