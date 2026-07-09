# Learning Notes — Personal RAG Application

> This is a running journal of every concept learned during the build.
> Each phase adds a new section explaining what was built, the key ideas,
> the design decisions and their alternatives, and how each choice
> affects behavior as the dataset grows.

---

## Phase 0 — Orientation: What is RAG?

### What was built
Nothing yet — this phase is about understanding the big picture before writing code.

### Key Concept: Retrieval-Augmented Generation (RAG)

**The problem RAG solves:**
Large Language Models (LLMs) like ChatGPT are trained on public data up to a cutoff
date. They cannot answer questions about *your* private documents — your notes, your
PDFs, your saved web pages. You could paste text into the chat window, but that hits
context-length limits fast, and you'd have to manually pick which documents to paste.

**What RAG does:**
RAG automates the process of "find the relevant parts of my data, then give them
to the LLM along with my question." It's two steps glued together:

1. **Retrieval** — search your own data for the pieces most relevant to your question.
2. **Augmented Generation** — feed those pieces into an LLM's prompt so it can
   write an answer *grounded in your data*, not just its training data.

**Why not just fine-tune the LLM on your data?**
Fine-tuning bakes knowledge into the model's weights. It's:
- Expensive (GPU hours, cloud costs)
- Slow (hours to days per training run)
- Hard to update (add one document → retrain the whole model)
- Lossy (the model may "forget" fine-tuning details over time)

RAG keeps your data *outside* the model, in a searchable database. Add a new
document? Just index it — seconds, not hours. Delete a document? Remove it from
the database. No retraining ever.

### Key Concept: The RAG Pipeline (6 stages)

Here's a mental model for what we'll build, using your use case:

| Stage | What happens | Analogy |
|-------|-------------|---------|
| **1. Ingestion** | Read PDFs, DOCX, HTML, MD, TXT into a common format | Like converting all your books into the same language |
| **2. Chunking** | Split each document into small overlapping pieces | Like cutting a book into paragraphs — small enough to search precisely |
| **3. Embedding** | Convert each chunk into a vector (list of numbers) capturing its meaning | Like assigning GPS coordinates to each paragraph — similar topics get nearby coordinates |
| **4. Vector Storage** | Store vectors + metadata in Qdrant | Like filing those GPS-tagged paragraphs in a fast-lookup index |
| **5. Retrieval** | When you ask a question, embed it too, then find the closest vectors | Like "find the paragraphs nearest to my question's GPS coordinates" |
| **6. Generation** | Feed question + closest chunks to an LLM → answer | Like handing a smart assistant the exact pages they need to answer you |

### Design Decision: Why build from scratch instead of using LangChain/LlamaIndex?

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **LangChain** | Fast to prototype, huge ecosystem | Hides critical details, heavy abstraction layers, hard to debug, changes API frequently | ❌ for learning |
| **LlamaIndex** | Great for document QA specifically | Same abstraction problem — you'd use it without understanding it | ❌ for learning |
| **Plain Python + focused libraries** | Every line is visible, debuggable, and yours to understand | More code to write | ✅ chosen |

**How this affects scaling:** Building from scratch actually helps scaling, because when
something breaks at 10x data, you know every line of your pipeline and can diagnose it.
Framework users often hit opaque errors deep in abstraction layers they never learned.

> **Side note for context:** In a production team setting where speed-to-ship matters
> more than learning, LangChain or LlamaIndex are perfectly reasonable choices.
> We're choosing plain Python because understanding the internals *is* a primary goal.

### Design Decision: Why these specific tools?

| Tool | Why chosen | Alternative considered | Why not |
|------|-----------|----------------------|---------|
| `sentence-transformers` + `bge-small-en-v1.5` | Free, ~130MB, fast on CPU | OpenAI `text-embedding-3-small` | Costs money, requires internet, sends your data to a third party |
| Qdrant (local Docker) | Free, production-grade, millions of vectors, metadata filtering, easy cloud migration | ChromaDB (in-process) | Simpler to start, but embeds in your Python process (RAM-hungry at scale), no standalone server mode for production |
| Ollama (local LLM) | Free, runs `llama3.2:3b` in ~4GB RAM | OpenAI GPT-4 API | Costs money, requires internet; we'll support it as a swappable option |
| FastAPI | Modern, fast, auto-generates API docs, async support | Flask | Older, no async, no auto-docs — FastAPI is the modern standard |

---

*Next: Phase 1 — Environment & Scaffolding*

---

## Phase 1 — Environment & Scaffolding

### What was built
- Python virtual environment (`venv/`)
- `requirements.txt` — every dependency explained with purpose and alternatives
- `docker-compose.yml` — Qdrant vector database, resource-limited for 16GB RAM
- `config.py` — central configuration with every setting documented
- `.env.example` — template for secrets (API keys)

### Key Concept: Virtual Environments

A virtual environment is an isolated Python installation. Packages installed inside
it are invisible to the rest of your system, and vice versa. This prevents:
- **Dependency conflicts**: Project A needs `library v1`, Project B needs `library v2`
  — without venvs, they'd fight over the same installation.
- **Pollution**: Installing 50 packages globally makes it impossible to know which
  project needs what.

**Always activate the venv** (`venv\Scripts\activate` on Windows) before running
any Python command for this project.

### Key Concept: Docker Compose

Docker runs applications in "containers" — lightweight, isolated environments
(like virtual machines but much faster). Docker Compose lets you define multiple
services in one YAML file and start/stop them together.

We use it for Qdrant because:
- Qdrant runs as a separate server, not inside your Python process
- It persists data independently of your code
- Destroying and recreating it is one command
- The same setup works identically on any machine

### Design Decision: config.py vs. YAML/TOML config file

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Python file (config.py)** | Comments, defaults, computed values, type hints, no parser needed | Can't be read by non-Python tools | ✅ chosen |
| **YAML** | Language-agnostic, clean syntax | Needs a parser, no computed values, no type hints | ❌ |
| **pydantic-settings** | Validation, env var loading, multiple environments | Overkill for a single-developer project | ❌ for now |

**How this affects scaling:** If this grows into a team project with staging/production
environments, we'd migrate to `pydantic-settings`. For a personal app, `config.py`
+ `.env` is the simplest correct approach.

### Design Decision: Qdrant resource limits

Set to 1GB RAM max. Qdrant is efficient — 1GB handles ~100,000 vectors easily.
At 500-char chunks, that's roughly 50,000 pages of text. If you hit the limit,
just increase it in `docker-compose.yml`.

---

*Next: Phase 2 — Ingestion Layer*

---

## Phase 2 — Ingestion Layer

### What was built
- `document.py` — The unified schema (`Document` and `DocumentMetadata`) using Pydantic.
- `pdf_parser.py`, `docx_parser.py`, `html_parser.py`, `text_parser.py` — File-specific extraction scripts.
- `registry.py` — The orchestrator that maps extensions to parsers.

### Key Concept: The Unified Schema

Your data is messy. PDFs store text by coordinates. Word docs are zipped XML. HTML has tags.
If the rest of the RAG pipeline had to handle each of these differently, the code would be
unmaintainable.

**The Solution:** A unified schema.
Every parser takes its complex format and strips it down to two things:
1. `content`: The raw, human-readable text string.
2. `metadata`: Where it came from, its file type, and when it was modified.

By doing this, Phase 3 (Chunking) and Phase 4 (Embedding) only ever see `Document` objects.
They don't know or care what a PDF is.

### Design Decision: Hardcoded parsing vs. Framework-based parsing (like Langchain's DocumentLoaders)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Write our own parsers using base libraries** | Complete control over extraction (e.g., stripping bad HTML, detecting encoding) | More upfront code | ✅ chosen |
| **Langchain DocumentLoaders** | One-liners to load almost anything | Heavy abstraction, often pulls in unwanted dependencies | ❌ |

**How this affects scaling:** When (not if) you encounter a weirdly formatted PDF in the future
that breaks the parser, you know exactly where `pdf_parser.py` is to fix it. If a framework's
parser fails, you're usually stuck waiting for an upstream bug fix.

### Key Concept: Smart Encoding Detection

Text files aren't just "text" — they are binary bytes encoded using rules like UTF-8 or Windows-1252.
If you open a file with the wrong rules, you get garbled characters like .
We use the `chardet` library in `text_parser.py` to guess the encoding based on the bytes *before*
decoding it. This makes the ingestion layer extremely resilient to messy personal data.

---

*Next: Phase 3 — Chunking*

---

## Phase 3 — Chunking

### What was built
- `text_splitter.py` — The core logic for recursively splitting documents into chunks.
- `Chunk` schema — The data structure representing a searchable piece of text, inheriting metadata from its parent document.

### Key Concept: Why do we chunk?

1. **LLM Limits:** LLMs cannot read a 500-page book in one go (context limits). We need to feed them only the most relevant pages.
2. **Search Accuracy:** If you convert a whole book into a single vector (embedding), its "meaning" is incredibly diluted. A search for a specific fact will fail. Searching small paragraphs is highly precise.

### Key Concept: Why "Recursive" Splitting?

If we just cut text every 500 characters, we would chop sentences exactly in half, destroying their meaning. 
Instead, our chunker tries to respect the structure of human language. It attempts to split by:
1. Double newlines (`\n\n` - Paragraphs)
2. Single newlines (`\n` - Lines)
3. Periods (`. ` - Sentences)
4. Spaces (` ` - Words)

It only moves to a smaller separator if the larger one results in a piece that is still over 500 characters.

### Key Concept: Why Overlap?

If Chunk 1 ends at character 500 and Chunk 2 starts at character 501, any information sitting right on that boundary is split in half. Neither chunk has the full context. 
By adding an `overlap` (e.g., 50 characters), the end of Chunk 1 is duplicated at the start of Chunk 2. This prevents information loss at the edges.

### Design Decision: Hardcoding the logic vs. Langchain's RecursiveCharacterTextSplitter

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Write our own recursive splitter** | 100% visibility into the logic. Easy to debug if a specific document splits weirdly. | Need to write the recursion loop ourselves. | ✅ chosen |
| **Langchain TextSplitter** | Standard industry tool, robust. | You have to read Langchain's source code to understand *how* it's splitting your text. | ❌ |

**How this affects scaling:** When your dataset grows and you start adding markdown tables or code blocks, you can easily tweak `separators` in our class to handle them without waiting for a library update.

---

*Next: Phase 4 — Embeddings*

---

## Phase 4 — Embeddings

### What was built
- `embedder.py` — A wrapper around `sentence-transformers` that loads our model and provides batch encoding.

### Key Concept: What is an Embedding?

Computers don't understand what a "dog" is. To a computer, "dog" is just three characters. If you search for "puppy", a basic search will not find a document about a "small dog".

An embedding solves this by converting a chunk of text into a long list of numbers (a "vector"). You can think of this vector as a coordinate on a giant, multi-dimensional map of human language. 
On this map, the coordinate for "puppy" is located right next to the coordinate for "small dog". 
Semantic search just asks: *"Find me the chunks whose coordinates are closest to my question's coordinate."*

### Key Concept: Why Batching?

In Python, writing a `for` loop that calls `model.encode(text)` 50 times is slow. 
Neural networks are designed to process massive arrays of data at once (using underlying C++ libraries). By passing a `List[str]` of 50 chunks into `model.encode(texts)`, the library processes them in parallel, resulting in massive speedups during ingestion.

### Design Decision: BAAI/bge-small-en-v1.5 vs OpenAI Embeddings

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **bge-small-en-v1.5** | Free, runs locally, privacy-preserving, very fast on CPU (~130MB). | Slightly less accurate on very complex nuance than OpenAI. | ✅ chosen |
| **OpenAI text-embedding-3** | Highest quality, fast (runs on their servers). | Costs money, requires internet, sends personal data to cloud. | ❌ |

**How this affects scaling:** When your data grows, local embeddings cost you exactly $0. If you used an API, you'd pay for every document you ingest, and pay again if you ever have to re-index your database.

---

*Next: Phase 5 — Vector Store*

---

## Phase 5 — Vector Store

### What was built
- `qdrant_store.py` — The interface for connecting to Qdrant, ensuring the collection exists, upserting chunks + vectors, and searching.

### Key Concept: Vector Database vs Relational Database

A standard database (like Postgres) looks for exact string matches (`word = 'puppy'`). 
A Vector Database is built for math. It takes a query vector and calculates the "distance" between it and millions of other vectors in milliseconds. The metric we use is `Cosine Distance`, which measures the angle between two vectors. A smaller angle means the meaning is more similar.

### Key Concept: Why Metadata Filtering is the Key to Scaling

If you have 100 documents, standard semantic search works great.
If you have 100,000 documents, semantic search might accidentally return a completely unrelated paragraph just because some of the words aligned with your query's vector.
By storing metadata (file type, date, source path) alongside the vector (the "payload"), you can tell Qdrant: *"Find the closest vectors, BUT ONLY IF they come from a `.pdf` file."*
This pre-filters the math problem, ensuring perfect precision at scale.

### Key Concept: Incremental Upserts vs Duplication

When you edit a document and re-ingest it, how does the database know not to create duplicate chunks?
We generate a deterministic ID for every chunk by hashing its `source_path + chunk_index` (e.g., `C:/notes.md_0`). 
When Qdrant receives an upsert command with an ID that already exists, it silently overwrites the old vector and payload. 
If we didn't do this, running ingestion twice would double your database size and return duplicate results to the LLM.

---

*Next: Phase 6 — Retrieval*

---

## Phase 6 — Retrieval

### What was built
- `retriever.py` — Coordinates taking a user's question, embedding it, asking Qdrant for matches, and filtering out bad results.

### Key Concept: Relevance Threshold

If your database only contains recipes, and you ask "How do I fix a car?", Qdrant will still dutifully return the 5 "closest" chunks it has. But their similarity scores will be very low (e.g., 0.2 out of 1.0). 
If we feed those chunks to the LLM, the LLM gets confused and might try to answer a car question using a cake recipe. 
By setting a `SIMILARITY_THRESHOLD` (e.g., 0.5), we drop chunks that aren't actually relevant. If all 5 chunks are dropped, the LLM gets an empty context and correctly states: "I don't know based on your documents."

---

## Phase 7 — LLM Generation

### What was built
- `llm_interface.py` — The Abstract Base Class that standardizes how our app talks to AI models.
- `ollama_llm.py` — The client for your local, private LLM.
- `cloud_llm.py` — The client for Gemini (free tier) if you want cloud power.
- `prompt_builder.py` — Safely builds the prompt string without exceeding context limits.

### Key Concept: Why an Interface (Abstraction)?

If we hardcode the Ollama API directly into the RAG pipeline, we are locked in. If you want to switch to Gemini tomorrow, you'd have to rewrite the core app.
By defining `LLMInterface`, the core app just calls `.generate(prompt)`. It doesn't know or care if the model is on your laptop or in Google's cloud. Switching is just changing one line in `config.py`.

### Key Concept: Guarding the Context Limit

LLMs have a maximum amount of text they can read at once. If we retrieve 5 huge chunks and blindly paste them into the prompt, the prompt might be 15,000 characters. If the model's limit is 10,000 characters, it will either crash or truncate the prompt (losing your actual question!).
`PromptBuilder` tracks the length as it adds chunks. If adding the next chunk would exceed the `MAX_CONTEXT_LENGTH`, it stops adding chunks, ensuring the prompt is always safe to send.

---

*Next: Phase 8 — RAG Orchestration*

---

## Phase 8 — RAG Orchestration

### What was built
- `rag_pipeline.py` — The Master Class that wires `Retriever`, `PromptBuilder`, and `LLMInterface` together into a single `.answer_question()` method.

### Key Concept: Single Responsibility & Orchestration
Up until now, every file we wrote did exactly ONE thing (parsing, chunking, or embedding). This makes them easy to test and replace.
The orchestrator's only job is to be the "glue". It doesn't know *how* to chunk or *how* to call the LLM; it just knows *when* to call them. This allows our final API to be incredibly clean.

---

## Phase 9 — API Layer

### What was built
- `main.py` — A FastAPI server with `/query` (ask a question) and `/ingest` (scan for new files) endpoints.

### Key Concept: Why an API instead of a script?
If you build this as a python script, you have to open the terminal every time you want to ask a question. 
By wrapping it in FastAPI, your RAG brain becomes a "Service". 
- You can build a React frontend for it.
- You can build an iOS app that talks to it.
- You can leave it running in the background and use it from anywhere.
- FastAPI automatically generates interactive docs at `http://localhost:8000/docs`, making testing trivial.

---

## Phase 10 — Incremental Ingestion

### What was built
- `change_tracker.py` — Scans the `data/` folder, hashes files, and only processes ones that are new or changed.

### Key Concept: Hashing vs Modified Time (mtime)
To know if a file changed, we could just check its "Last Modified" timestamp. But if you copy a file from a USB drive, its timestamp might update even though the text is identical.
Instead, we calculate an MD5 hash of the file's raw bytes. If the hash hasn't changed, the text hasn't changed, and we can safely skip the expensive parsing and embedding steps. 
This is what allows you to dump a 10,000-file folder into `data/` and update it instantly.

---

*Next: Phase 11 & 12 — Testing and Interfaces*

---

## Phase 11 — Testing & Evaluation

### What was built
- `test_chunking.py` — Automated verification that text splits correctly without violating size limits or losing metadata.
- `test_retrieval.py` — Automated verification that the threshold filter drops bad search results.

### Key Concept: Why Automated Tests?
If you manually test the app by asking it a question, and it gives a good answer, that's great. 
But what if next month you change `CHUNK_SIZE` from 500 to 200, and suddenly the chunker breaks and starts returning empty chunks? You might not notice until you ask a question and get garbage back.
Automated unit tests run in milliseconds and verify that the *core logic* still holds true after any code changes.

---

## Phase 12 — The CLI Chat Interface

### What was built
- `ui/cli.py` — A terminal application using `rich` to provide a beautiful, interactive chat experience.

### Key Concept: Decoupling the Backend from the Frontend
Notice how the CLI does *not* import `Retriever` or `LLMInterface`. It strictly talks to the FastAPI server via HTTP requests (`httpx.post`).
This is called "Decoupling". The UI is completely independent of the AI logic. If you decide to build a React web app tomorrow, you don't have to touch a single line of your Python RAG logic — you just point your React app at `http://localhost:8000`.

---

# 🎉 Build Complete!
We have successfully built a production-grade, local, incremental RAG pipeline from scratch.
