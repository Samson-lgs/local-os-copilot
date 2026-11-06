# Sam: Local OS Copilot

Sam is a privacy-first Windows desktop AI agent that runs with locally hosted language and embedding models. It can understand requests, retrieve context from local documents, read visible screen text, launch approved desktop applications, and type into the focused window.

The project demonstrates local inference, retrieval-augmented generation, function calling, OS automation, safety boundaries, and measurable engineering quality without sending application data to a cloud LLM.

## Why This Project

Cloud assistants are convenient, but sensitive screen content and private documents should not have to leave a user's computer. Sam uses Ollama as a local model server and keeps OCR, document parsing, embeddings, retrieval, and desktop actions on the local machine.

The result is a small but complete agent architecture:

```text
User request
    |
    v
Intent gate and bounded conversation history
    |
    v
Local Ollama chat model
    |
    +--> Normal response
    |
    +--> Local tool call
             |
             +--> Screen OCR with mss + Tesseract
             +--> RAG search with local embeddings
             +--> Allowlisted Windows application launch
             +--> Focused-window text entry
             |
             v
        Structured result and timing
             |
             v
        Final local model response
```

## Features

### Local LLM and agent behavior

- Ollama-hosted chat model, configured with `OLLAMA_MODEL`
- Local function calling for OS and knowledge-base tools
- Tool intent gating so casual messages such as `hi` do not trigger desktop actions
- Bounded tool execution with a maximum of four rounds per request
- Bounded conversation history to avoid unbounded context growth
- CLI and Tkinter desktop interfaces using the same execution layer
- Agent phases shown in the UI:
  - Planning
  - Acting
  - Verifying
- Tool success, failure, and execution duration shown in the CLI and UI
- Stop control for future tool rounds
- Local model selector and model refresh in the UI

### Local RAG

Sam supports retrieval-augmented generation over files placed in `docs/`.

Supported formats:

- Markdown: `.md`
- Text: `.txt`
- Python: `.py`
- JSON: `.json`
- reStructuredText: `.rst`
- PDF: `.pdf`
- Word documents: `.docx`

The RAG pipeline is:

```text
Local documents
    |
    v
Local text extraction
    |
    v
Chunking with overlap
    |
    v
Ollama embedding model
    |
    v
Persisted local index
    |
    v
Cosine similarity retrieval
    |
    v
Relevant chunks with source citations
    |
    v
Local chat model
```

PDF citations include page numbers. For example:

```text
Source: docs/manual.pdf (page 4)
Relevance: 0.8421
Relevant document content...
```

### Local operating-system tools

- Read visible text from the primary screen using local OCR
- Launch a strict allowlist of Windows applications:
  - Calculator
  - Notepad
  - Paint
  - WordPad
- Type bounded text into the currently focused window
- Export conversations to a local text file
- No arbitrary shell command tool is exposed to the model

## Technology Stack

- Python 3.10 to 3.12
- Ollama for local chat and embedding models
- Tkinter for the Windows desktop UI
- `mss` for screen capture
- Tesseract OCR through `pytesseract`
- `pypdf` for local PDF extraction
- `python-docx` for local DOCX extraction
- PyAutoGUI for bounded text entry
- pytest for automated tests
- Ruff for linting
- GitHub Actions for Windows CI

## Requirements

- Windows 10 or Windows 11
- Python 3.10, 3.11, or 3.12
- Ollama installed and running locally
- Tesseract OCR installed
- A local Ollama chat model
- The local embedding model `nomic-embed-text` for RAG

## Installation

From the project directory:

```powershell
python -m venv ..\venv
..\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install Ollama models:

```powershell
ollama pull llama3.1
ollama pull nomic-embed-text
```

Install Tesseract OCR and make sure `tesseract.exe` is on `PATH`. If it is installed in another location, configure it with:

```powershell
$env:TESSERACT_CMD = "C:\Path\To\tesseract.exe"
```

## Running Sam

### Desktop UI

```powershell
..\venv\Scripts\python.exe -m src.ui
```

The UI includes:

- Local Ollama connection status
- Model selection
- Chat workspace
- Agent activity trace
- Planning, acting, and verification states
- Screen-reading and knowledge-search shortcuts
- Stop response control
- Conversation export

### CLI

```powershell
..\venv\Scripts\python.exe -m src.main
```

Example requests:

```text
hi
Read my screen
Search my local documents for the setup steps
Open Calculator
Type hello into the focused window
```

## Using Local RAG

Put private files in the `docs/` folder:

```powershell
New-Item -ItemType Directory -Force docs
Copy-Item .\README.md .\docs\project-notes.md
```

Then start Sam and ask:

```text
What does the project documentation say about local embeddings?
```

On the first search, Sam creates `docs/.sam-index.json`. This file contains local embeddings and is ignored by Git. Document extraction, embedding, retrieval, and response generation remain local.

Configuration options:

```powershell
$env:OLLAMA_MODEL = "llama3.1"
$env:OLLAMA_EMBED_MODEL = "nomic-embed-text"
$env:OLLAMA_HOST = "http://127.0.0.1:11434"
$env:SAM_DOCUMENTS_DIR = "docs"
```

`OLLAMA_HOST` must resolve to a loopback address such as `localhost`, `127.0.0.1`, or `::1`. Remote endpoints are rejected before model requests are sent.

## Safety and Privacy Model

Sam has a local trust boundary and several execution controls:

- The application defaults to `http://127.0.0.1:11434`.
- Non-loopback Ollama endpoints are rejected.
- Screen capture occurs only when a screen-related request enables the tool path.
- Document contents are parsed and embedded locally.
- Unknown tools are rejected by the shared executor.
- Windows application names are restricted to an allowlist.
- Windows launching does not pass model-generated text through a shell command string.
- Typed text has a maximum length.
- Tool execution is bounded to four rounds per request.
- Conversation history is bounded in memory.
- Tool results include success/failure status and duration.
- Conversation export is manual and writes only to a user-selected local path.

Important limitations:

- `type_text` operates on whichever window currently has focus.
- The current release does not implement voice input or output.
- The current release does not provide arbitrary shell access.
- Exported conversations are plain text.
- Users should review tool activity before allowing desktop actions.

## Testing and Quality Checks

Install development tools:

```powershell
pip install -e ".[dev]"
```

Run the test suite:

```powershell
python -m pytest -q
```

Run linting:

```powershell
ruff check src tests
```

Run compilation and whitespace checks:

```powershell
python -m compileall -q src tests
git diff --check
```

The automated tests use fakes and mocks where appropriate. They do not require:

- A running Ollama server
- A microphone
- Tesseract OCR
- A real desktop application launch
- Real typing into a focused window

## Benchmarking Local Models

Sam includes a side-effect-free benchmark for comparing local Ollama models:

```powershell
python -m src.benchmark --models llama3.1 --rounds 3 --output benchmark.json
```

The benchmark records:

- Average response latency
- Number of tool selections
- Expected tool selections
- Exact tool-selection accuracy

The benchmark never executes desktop tools or sends data to a remote endpoint.

## Repository Structure

```text
local-os-copilot/
|-- .github/workflows/quality.yml  Windows CI for tests and lint
|-- docs/                          Local RAG knowledge base
|-- src/
|   |-- benchmark.py                Local model benchmark
|   |-- executor.py                 Shared validated tool executor
|   |-- main.py                     CLI and Ollama orchestration
|   |-- rag.py                      Local document indexing and retrieval
|   |-- settings.py                 Endpoint, intent, and history policy
|   |-- tools.py                    Windows tools and input limits
|   |-- ui.py                       Tkinter agent workspace
|   |-- vision.py                   Screen capture and OCR
|-- tests/                          Deterministic unit tests
|-- pyproject.toml                  Metadata and development configuration
|-- requirements.txt                Runtime dependencies
|-- README.md                       Project documentation
```



## Future Work

- Push-to-talk local Whisper voice input
- Incremental file watching and index rebuilds
- Screenshot preview and selectable OCR regions
- Local SQLite preferences and memory
- Windows executable packaging

## License

This project is currently intended as a personal portfolio project. Add a license before redistributing it publicly.
