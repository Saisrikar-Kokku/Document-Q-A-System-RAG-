# Personal RAG Application

> Ask questions about your own documents (PDFs, Word files, notes, web pages)
> and get accurate, grounded answers — running entirely on your laptop, for free.

## What is this?

A **Retrieval-Augmented Generation (RAG)** system built from scratch in Python.
It reads your documents, understands their meaning, and lets you ask natural-language
questions that get answered using *your* data — not generic internet knowledge.

**Everything runs locally.** No API keys required (cloud LLM support is optional).
No data leaves your machine unless you choose to use a cloud model.

## Quick Start

> ⚠️ Detailed setup instructions will be added as each phase is built.
> This section will grow with the project.

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for the Qdrant vector database)
- Ollama (for the local LLM) — [install from ollama.com](https://ollama.com)
- ~4GB free disk space (for models and the vector database)

### Installation

```bash
# 1. Clone / navigate to this project
cd RAG

# 2. Create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the vector database
docker-compose up -d

# 5. Pull a local LLM model (first time only, ~2GB download)
ollama pull llama3.2:3b

# 6. Start the API server
# (instructions will be added in Phase 9)
```

### Usage

**1. Start the API Server**
Open a terminal, activate your virtual environment, and run:
```bash
python -m api.main
```
*The server will start on http://localhost:8000. Leave this terminal running.*

**2. Start the Interactive CLI**
Open a SECOND terminal, activate your virtual environment, and run:
```bash
python -m ui.cli
```

From the CLI, you can:
- **Ingest Documents:** Press `1` to scan your `data/` folder and embed any new or modified files. (Make sure you've put some PDFs or notes in `data/` first!)
- **Ask a Question:** Press `2` to chat with your documents.

*Developer Tip: You can view the interactive API documentation at http://localhost:8000/docs*

## Project Structure

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full pipeline diagram and design decisions.

## Learning Journey

See [LEARNING_NOTES.md](./LEARNING_NOTES.md) for a running log of every concept
learned during the build, with design decisions and their alternatives.

## Tech Stack

| Component | Tool | Why |
|-----------|------|-----|
| Language | Python 3.11+ | Industry standard for ML/AI pipelines |
| Document parsing | `PyPDF2`, `python-docx`, `beautifulsoup4` | Format-specific, lightweight parsers |
| Chunking | Custom recursive splitter | Structure-aware, with overlap for context preservation |
| Embeddings | `sentence-transformers` + `bge-small-en-v1.5` | Free, ~130MB, fast on CPU |
| Vector DB | Qdrant (local Docker) | Production-grade, supports millions of vectors |
| Local LLM | Ollama (`llama3.2:3b`) | Free, runs in ~4GB RAM |
| Cloud LLM (optional) | Gemini free tier | Swappable via config, no code changes |
| API | FastAPI | Modern, async, auto-documentation |

## License

This is a personal learning project. Use it however you like.
