"""
config.py — Central Configuration for the RAG Application
==========================================================

WHAT THIS FILE DOES:
    Holds every tunable setting in one place: model names, chunk sizes,
    database URLs, API keys, etc. No other file in the project should
    contain hardcoded "magic numbers" or service URLs — they all read
    from here.

WHY IT EXISTS:
    Without a central config, you'd have chunk_size=500 buried in one file,
    a model name string in another, and a database URL in a third. Changing
    anything means hunting through the whole codebase. With this file,
    you change one value and it propagates everywhere.

HOW IT FITS IN THE PIPELINE:
    Every module imports from this file. It's the first thing that loads.
    It also reads from a .env file (if present) for secrets like API keys,
    so you never hardcode passwords in source code.

DESIGN DECISION — Why a Python file instead of YAML/JSON/TOML config?
    - Python config files can have comments, defaults, and computed values.
    - No extra parser dependency needed.
    - Type hints work natively.
    - For a personal project, this is simpler than a full settings framework
      like dynaconf or pydantic-settings. If this were a team project with
      staging/production environments, we'd use pydantic-settings instead.
"""

import os                    # Access environment variables (for API keys, etc.)
from pathlib import Path     # Cross-platform file path handling
from dotenv import load_dotenv  # Load .env file into environment variables

# ── Load .env file if it exists ─────────────────────────────────────────────
# The .env file holds secrets (API keys) that should never be committed to git.
# load_dotenv() reads key=value pairs from .env and sets them as environment
# variables, so os.getenv("KEY") can find them.
load_dotenv()

# ── Project Paths ───────────────────────────────────────────────────────────
# All paths are relative to this file's location, so the project works
# regardless of where it's cloned or installed.

PROJECT_ROOT = Path(__file__).parent                # The RAG/ folder itself
DATA_DIR = PROJECT_ROOT / "data"                    # Where your documents live
INGESTION_INDEX_PATH = PROJECT_ROOT / ".ingestion_index.json"
    # ^ Tracks which files have been processed (Phase 10: incremental ingestion).
    #   Stored as a JSON file mapping file paths → content hashes + timestamps.

# ── Chunking Settings (Phase 3) ────────────────────────────────────────────
# These control how documents get split into pieces for embedding and search.

CHUNK_SIZE = 500
    # How many characters per chunk (roughly 100-125 words).
    # WHY 500: Small enough that each chunk is about one focused topic
    # (so search results are precise), but large enough to contain meaningful
    # context. Too small (100) → chunks are sentence fragments, losing meaning.
    # Too large (2000) → chunks cover multiple topics, reducing search precision.
    # 500 is a well-tested default for mixed document types.

CHUNK_OVERLAP = 50
    # How many characters of overlap between consecutive chunks.
    # WHY OVERLAP MATTERS: Without it, a sentence that spans a chunk boundary
    # gets cut in half — the first half is in chunk N, the second in chunk N+1.
    # Neither chunk has the full sentence, so neither matches a search about it.
    # Overlap means the boundary region appears in BOTH chunks, preventing
    # information loss at the edges.
    # WHY 50: ~10% of chunk_size is standard. Enough to capture boundary context
    # without bloating the total number of chunks (which costs more embeddings
    # and storage).

# ── Embedding Settings (Phase 4) ───────────────────────────────────────────

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
    # The neural network that converts text into vectors (lists of numbers).
    # WHY THIS MODEL:
    #   - ~130MB download, ~200MB in RAM — fits comfortably on 16GB with room
    #     for everything else.
    #   - 384-dimensional vectors — compact but high quality. (Dimensions =
    #     how many numbers per vector. More = more nuance but more storage/RAM.)
    #   - Top-ranked on the MTEB benchmark for its size class.
    #   - English-optimized, which matches typical personal notes/docs.
    # ALTERNATIVES CONSIDERED:
    #   - all-MiniLM-L6-v2: slightly smaller, slightly worse quality.
    #   - bge-base-en-v1.5: higher quality but ~420MB — still fits, but
    #     embedding is slower. Good upgrade path if you want better results later.
    #   - OpenAI text-embedding-3-small: excellent quality, but costs money
    #     and sends your data to the cloud. Against our constraints.

SPARSE_MODEL_NAME = "Qdrant/bm25"
    # Used for Hybrid Search (keyword matching). 
    # fastembed supports this directly. It generates sparse vectors containing
    # word frequencies, which allows us to find exact keyword matches that
    # the dense model (bge-small) might miss because it focuses on "meaning".

EMBEDDING_DIMENSION = 384
    # Must match the output dimension of the model above.
    # bge-small-en-v1.5 produces 384-dimensional vectors.
    # This is used when creating the Qdrant collection (it needs to know
    # the vector size upfront).

# ── Vector Database Settings (Phase 5) ─────────────────────────────────────

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_URL = os.getenv("QDRANT_URL", None)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

QDRANT_COLLECTION_NAME = "documents"
    # Name of the "collection" in Qdrant (like a table in a regular database).
    # All your document chunks and their vectors go into this one collection.

# ── Cloudflare R2 Settings ──────────────────────────────────────────────────

R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", None)
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", None)
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", None)
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "rag-pdfs")

    # You COULD create separate collections per document type, but one unified
    # collection with metadata filtering is simpler and more flexible —
    # you can filter by file_type, source, date, etc. at query time.

# ── Retrieval Settings (Phase 6) ───────────────────────────────────────────

RETRIEVAL_TOP_K = 5
    # How many chunks to retrieve for each query.
    # WHY 5: Enough to cover the question from multiple angles (in case the
    # best answer spans multiple chunks), but not so many that you flood the
    # LLM with irrelevant context (which confuses it and wastes token budget).
    # TUNING: If answers seem shallow, try 7-10. If answers seem unfocused
    # (rambling, mixing unrelated info), try 3.

SIMILARITY_THRESHOLD = 0.5
    # Minimum similarity score (0 to 1) for a chunk to be included.
    # Chunks below this score are considered irrelevant even if they're in
    # the top-k. This prevents the LLM from seeing garbage when your question
    # doesn't match anything in your data well.
    # WHY 0.5: Conservative default. Cosine similarity of 0.5 means "somewhat
    # related." Raise to 0.7 for stricter filtering (fewer but more relevant
    # chunks), lower to 0.3 if you're getting too few results.

# ── LLM / Generation Settings (Phase 7) ────────────────────────────────────

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()  # 'ollama', 'cloud', or 'groq'

# ---------------------------------------------------------
# OLLAMA CONFIGURATION (Local)
# ---------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3")

# ---------------------------------------------------------
# CLOUD LLM CONFIGURATION (Gemini)
# ---------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

# ---------------------------------------------------------
# GROQ LLM CONFIGURATION (Cloud Fast Inference)
# ---------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    # fast, and very capable. It does send your data to Google's servers.

# ── Prompt Settings ─────────────────────────────────────────────────────────

MAX_CONTEXT_LENGTH = 12000
    # Maximum total characters of retrieved chunks to include in the prompt.
    # WHY THIS MATTERS: LLMs have a "context window" — a maximum amount of
    # text they can read at once. 12,000 chars (approx 3,000 tokens) is the sweet 
    # spot for free-tier APIs like Groq, providing enough context without hitting limits.
    # 30000 chars ≈ 7500 tokens ≈ about 15 pages of text.
