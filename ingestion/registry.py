"""
registry.py — The Ingestion Orchestrator
========================================

WHAT THIS FILE DOES:
    This is the "front door" for the ingestion layer. You give it a file path,
    it looks at the extension, calls the correct parser, and returns a unified
    `Document` object.

WHY IT'S DESIGNED THIS WAY:
    This hides all the complexity of parsing from the rest of the pipeline.
    The main pipeline just calls `load_document(path)` and doesn't care if it's
    a PDF or HTML file.

HOW IT FITS IN THE PIPELINE:
    This file is called by the `indexer` module (Phase 10) to process new files.
"""

from pathlib import Path
import os
from datetime import datetime

# Import our schemas and parsers
from typing import List
from .document import Document, DocumentMetadata
from .pdf_parser import parse_pdf
from .docx_parser import parse_docx
from .html_parser import parse_html
from .text_parser import parse_text

# A dictionary mapping file extensions to the function that parses them.
# Adding a new file type is as simple as adding an entry to this dictionary.
PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".html": parse_html,
    ".htm": parse_html,
    ".txt": parse_text,
    ".md": parse_text,
    ".markdown": parse_text,
}

def load_document(file_path: Path) -> List[Document]:
    """
    Reads a file, parses it based on its extension, and returns a list of unified Documents (one per page if applicable).
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    if ext not in PARSERS:
        raise ValueError(f"Unsupported file type: {ext}")
        
    parser_func = PARSERS[ext]
    content = parser_func(file_path)
    
    mtime = os.path.getmtime(file_path)
    base_metadata_dict = {
        "source_path": str(file_path.absolute()),
        "file_type": ext,
        "file_name": file_path.name,
        "last_modified": datetime.fromtimestamp(mtime)
    }
    
    if isinstance(content, str):
        metadata = DocumentMetadata(**base_metadata_dict)
        return [Document(content=content, metadata=metadata)]
    elif isinstance(content, list):
        documents = []
        for page_data in content:
            meta = DocumentMetadata(
                **base_metadata_dict,
                page_number=page_data.get("page_number")
            )
            documents.append(Document(content=page_data.get("text", ""), metadata=meta))
        return documents
    else:
        return []
