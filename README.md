# Local OS Copilot

A privacy-first Windows desktop assistant. The Python process talks to an Ollama server on `localhost`, captures screen text with local OCR, and runs validated desktop actions locally. No cloud API is used by this project.

## Setup

1. Install Python dependencies:

	 ```powershell
	 pip install -r requirements.txt
	 ```

2. Install Ollama, then pull a local tool-capable model:

	 ```powershell
	 ollama pull llama3.1
	 ollama pull nomic-embed-text
	 ```

3. Install Tesseract OCR and make sure `tesseract.exe` is on `PATH`. If it is elsewhere, set `TESSERACT_CMD`.

4. Start the assistant from this directory:

	 ```powershell
	 python -m src.main
	 ```

	Or launch the Sam desktop UI:

	```powershell
	python -m src.ui
	```

Set `OLLAMA_MODEL` to use another model, for example `$env:OLLAMA_MODEL = "qwen2.5:7b"`.
Sam defaults to `http://127.0.0.1:11434`. Set `OLLAMA_HOST` only to another loopback address such as `http://localhost:11434`.

## Development checks

Install development tools and run the deterministic checks:

```powershell
pip install -e ".[dev]"
python -m pytest -q
ruff check src tests
```

The tests do not require Ollama, Tesseract, or a live desktop action. External dependencies are mocked where needed.

## Local model benchmark

Run the fixed, side-effect-free benchmark against installed Ollama models:

```powershell
python -m src.benchmark --models llama3.1 --rounds 3 --output benchmark.json
```

It records average response latency and exact tool-selection accuracy across an ordinary response and an expected `read_screen` request. The benchmark never executes a desktop tool or sends data to a remote endpoint.

## Local RAG

Sam supports retrieval-augmented generation over files in `docs/`. Add `.md`, `.txt`, `.py`, `.json`, `.rst`, `.pdf`, or `.docx` files, then ask Sam a question about them. Sam will call `search_documents`, extract text locally, create embeddings with `nomic-embed-text`, and return the most relevant chunks to the local chat model with source citations. PDF citations include page numbers.

```powershell
mkdir docs
Copy-Item .\README.md .\docs\project-notes.md
python -m src.main
```

The first document search builds `docs/.sam-index.json`; it is generated locally and ignored by Git. Set `OLLAMA_EMBED_MODEL` or `SAM_DOCUMENTS_DIR` to customize the local embedding model or document directory. PDF and DOCX parsing happens locally; document contents are never uploaded to a cloud parser.

## Architecture

```text
Tkinter UI / CLI
	|
	v
Ollama tool-calling loop
	|
	v
Shared validated executor
   |         |          |
 OCR     App allowlist  Typing limits
```

The shared executor rejects unknown tools, malformed arguments, disallowed Windows applications, and oversized text before invoking desktop side effects.

## Safety and privacy

- `read_screen` captures only when the model requests it.
- Local actions run directly after Sam requests them and are shown in the activity log.
- Tool execution is bounded to four rounds per user request.
- Windows app launching does not pass model text through a shell command string.
- Conversation history stays in process memory and is not written to disk by this project.
- The Sam UI can switch between models already installed in local Ollama.
- Conversations can be exported manually to a local text file.
- Stop cancels future tool rounds without sending data outside the machine.
- Remote Ollama hosts are rejected before a model request is sent.
- Conversation history is bounded to prevent unbounded memory/context growth.
- Tool execution reports success/failure and duration in both the CLI and desktop UI.

The current release is Windows-focused. Audio is not implemented yet, and the application currently trusts the configured Ollama endpoint; use a loopback endpoint for the intended local-only setup.

Ollama itself must be running locally. Review the model and tool output before approving actions that affect the desktop.
