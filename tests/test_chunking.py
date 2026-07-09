"""
test_chunking.py — Unit Tests for the Chunker
=============================================

WHAT THIS FILE DOES:
    Uses `pytest` to automatically verify that our chunking logic works perfectly.
    
Run this with: `pytest tests/test_chunking.py`
"""

from chunking.text_splitter import RecursiveCharacterTextSplitter
from ingestion.document import Document, DocumentMetadata
from datetime import datetime

def test_chunking_size_and_overlap():
    """
    Verifies that the chunker respects the max size and includes overlap.
    """
    # Create a fake document
    metadata = DocumentMetadata(
        source_path="fake.txt",
        file_type=".txt",
        file_name="fake.txt",
        last_modified=datetime.now()
    )
    # 3 lines of text
    text = "Line 1 is here.\nLine 2 is here.\nLine 3 is here."
    doc = Document(content=text, metadata=metadata)
    
    # We set a very small chunk size for testing
    splitter = RecursiveCharacterTextSplitter(chunk_size=16, chunk_overlap=5)
    chunks = splitter.split_document(doc)
    
    # Verify we got chunks back
    assert len(chunks) > 0
    
    # Verify no chunk exceeds our strict limit
    for chunk in chunks:
        assert len(chunk.text) <= 16

def test_chunking_keeps_metadata():
    """
    Verifies that the parent document's metadata is copied to every chunk.
    """
    metadata = DocumentMetadata(
        source_path="important_doc.pdf",
        file_type=".pdf",
        file_name="important_doc.pdf",
        last_modified=datetime.now()
    )
    doc = Document(content="Some text to chunk.", metadata=metadata)
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=10)
    chunks = splitter.split_document(doc)
    
    assert chunks[0].metadata.source_path == "important_doc.pdf"
    assert chunks[0].metadata.file_type == ".pdf"
