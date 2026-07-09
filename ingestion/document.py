"""
document.py — Unified Document Schema
=====================================

WHAT THIS FILE DOES:
    Defines the single data structure that represents ANY document in our system,
    whether it started as a PDF, Word doc, or HTML page.

WHY IT EXISTS:
    If chunking, embedding, and vector storage had to understand every file
    format, our code would be an unmaintainable mess. By enforcing a single
    schema here, the rest of the pipeline only ever deals with `Document` objects.
    This makes adding a new format later (like CSVs) as easy as writing a new
    parser without touching the rest of the pipeline.

HOW IT FITS IN THE PIPELINE:
    Parsers in `ingestion/` produce these.
    The chunker in `chunking/` consumes these and produces smaller `Chunk` objects.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class DocumentMetadata(BaseModel):
    """
    Metadata about the document.
    
    WHY IT'S IMPORTANT: When we store chunks in the vector database, we attach
    this metadata. This allows us to do "metadata filtering" during retrieval
    (e.g., "only search PDFs" or "only search notes from 2024").
    """
    source_path: str = Field(description="The absolute path to the original file")
    file_type: str = Field(description="The file extension (e.g., '.pdf', '.md')")
    file_name: str = Field(description="The name of the file (e.g., 'notes.docx')")
    last_modified: datetime = Field(description="When the file was last modified on disk")
    page_number: Optional[int] = Field(default=None, description="The page number this chunk came from, if applicable")
    
    # We can easily add more fields here later without breaking existing code
    # (e.g., author, title, tags).

class Document(BaseModel):
    """
    The unified representation of a document.
    
    We use Pydantic (BaseModel) instead of standard Python classes because it
    automatically validates data types. If a parser accidentally tries to set
    `content` to an integer, Pydantic will catch the error immediately.
    """
    content: str = Field(description="The extracted raw text of the entire document")
    metadata: DocumentMetadata = Field(description="Information about where the text came from")
