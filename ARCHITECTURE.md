# Personal RAG Application — Architecture

> This document is a living reference. It's updated at each phase of the build
> so you can always see how the pieces connect.

## High-Level Pipeline (Phase 0)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        YOUR DOCUMENTS                                   │
│   PDFs · Word docs · Markdown notes · HTML pages · Plain text           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   1. INGESTION LAYER   │
                    │  (format-specific       │
                    │   parsers → unified     │
                    │   Document schema)      │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   2. CHUNKING          │
                    │  (split into small,     │
                    │   overlapping pieces    │
                    │   with metadata)        │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   3. EMBEDDINGS        │
                    │  (convert each chunk    │
                    │   into a vector of      │
                    │   numbers that capture  │
                    │   its meaning)          │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   4. VECTOR DATABASE   │
                    │  (Qdrant — stores       │
                    │   vectors + metadata,   │
                    │   enables fast semantic │
                    │   search)               │
                    └───────────┬────────────┘
                                │
                                │  At query time:
                                ▼
                    ┌────────────────────────┐
                    │   5. RETRIEVAL         │
                    │  (find chunks whose     │
                    │   meaning is closest    │
                    │   to your question)     │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   6. LLM GENERATION    │
                    │  (feed question +       │
                    │   retrieved chunks to   │
                    │   a local LLM, get a   │
                    │   grounded answer)      │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   7. API LAYER         │
                    │  (FastAPI — exposes     │
                    │   /ingest and /query    │
                    │   endpoints for any     │
                    │   client to use)        │
                    └────────────────────────┘
```

## Key Design Decisions (so far)

| Decision | Choice | Why |
|----------|--------|-----|
| No LangChain/LlamaIndex | Build pipeline with plain Python | Every step stays visible and explainable — this is a learning project as much as a product |
| Local embeddings | `sentence-transformers` + `bge-small-en-v1.5` | Free, ~130MB, runs on CPU, no GPU needed — fits 16GB RAM constraint |
| Local vector DB | Qdrant via Docker | Free, production-grade, supports millions of vectors, trivial migration path to cloud |
| Local LLM | Ollama (`llama3.2:3b` or similar) | Free, runs on 16GB RAM, no API keys needed |
| Swappable LLM interface | Abstraction layer with local + cloud implementations | One-line config switch, no code rewrites ever |
| Incremental ingestion | Content hash + mtime tracking | Only re-processes changed files — scales gracefully as data grows |

## Folder Structure

```
RAG/
├── ARCHITECTURE.md          ← You are here
├── LEARNING_NOTES.md        ← Running log of concepts learned
├── README.md                ← Setup & usage instructions
├── requirements.txt         ← Python dependencies
├── docker-compose.yml       ← Qdrant vector database
├── config.py                ← Central configuration (model names, chunk sizes, etc.)
│
├── ingestion/               ← Phase 2: reads PDFs, DOCX, HTML, TXT/MD → Document schema
│   ├── __init__.py
│   ├── document.py          ← The unified Document data class
│   ├── pdf_parser.py
│   ├── docx_parser.py
│   ├── html_parser.py
│   ├── text_parser.py       ← Handles .txt and .md
│   └── registry.py          ← Maps file extensions → parser functions
│
├── chunking/                ← Phase 3: splits documents into overlapping chunks
│   ├── __init__.py
│   └── text_splitter.py
│
├── embeddings/              ← Phase 4: converts text chunks into vectors
│   ├── __init__.py
│   └── embedder.py
│
├── vectorstore/             ← Phase 5: stores/queries vectors in Qdrant
│   ├── __init__.py
│   └── qdrant_store.py
│
├── retrieval/               ← Phase 6: semantic search + filtering
│   ├── __init__.py
│   └── retriever.py
│
├── generation/              ← Phase 7: LLM abstraction + prompt construction
│   ├── __init__.py
│   ├── llm_interface.py     ← Abstract base class
│   ├── ollama_llm.py        ← Local implementation
│   ├── cloud_llm.py         ← Cloud fallback (e.g., Gemini free tier)
│   └── prompt_builder.py    ← Constructs the final prompt from chunks + question
│
├── pipeline/                ← Phase 8: ties retrieval + generation together
│   ├── __init__.py
│   └── rag_pipeline.py
│
├── api/                     ← Phase 9: FastAPI endpoints
│   ├── __init__.py
│   └── main.py
│
├── indexer/                 ← Phase 10: incremental ingestion (hash-based tracking)
│   ├── __init__.py
│   └── change_tracker.py
│
├── tests/                   ← Phase 11: pytest tests
│   ├── __init__.py
│   ├── test_chunking.py
│   └── test_retrieval.py
│
├── ui/                      ← Phase 12 (optional): simple chat interface
│
└── data/                    ← Your documents go here (not committed to git)
    └── .gitkeep
```
