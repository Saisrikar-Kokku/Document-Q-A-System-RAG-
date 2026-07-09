"""
text_splitter.py — Structure-Aware Recursive Chunker
====================================================

WHAT THIS FILE DOES:
    Takes a single, potentially massive `Document` and splits it into a list
    of small, overlapping `Chunk` objects.

WHY IT'S DESIGNED THIS WAY:
    We use a "recursive" splitting strategy. We don't just blindly chop the text
    every 500 characters (which would cut sentences in half). Instead, we first
    try to split by paragraphs (\\n\\n). If a paragraph is still larger than our
    max size, we split it by single newlines (\\n). If that's too big, we split
    by periods (sentences), and finally by spaces (words).
    This ensures chunks stay as semantically complete as possible.

HOW IT FITS IN THE PIPELINE:
    Takes `Document` (from Ingestion layer).
    Produces `Chunk` objects (which are then sent to the Embeddings layer).
"""

from pydantic import BaseModel, Field
from typing import List
import re

from config import CHUNK_SIZE, CHUNK_OVERLAP
from ingestion.document import Document, DocumentMetadata

class Chunk(BaseModel):
    """
    Represents a small, searchable piece of a document.
    
    We inherit the metadata from the parent Document so that when we find this
    chunk in the database later, we know exactly which file it came from.
    """
    text: str = Field(description="The actual text content of this chunk")
    metadata: DocumentMetadata = Field(description="Metadata inherited from the parent document")
    chunk_index: int = Field(description="The sequential position of this chunk in the document")


class RecursiveCharacterTextSplitter:
    """
    Splits text recursively based on a list of separators.
    """
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # The order of separators matters! 
        # We prefer to split on paragraphs, then lines, then sentences, then spaces.
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def split_document(self, document: Document) -> List[Chunk]:
        """
        Takes a Document and returns a list of overlapping Chunks.
        """
        text = document.content
        # Clean any HTML artifacts that may have leaked from PDF/DOCX parsing
        text = self._clean_html(text)
        # Get the raw text pieces using our recursive logic
        text_chunks = self._split_text(text, self.separators)
        
        # Now we need to combine these small pieces into chunks of roughly `self.chunk_size`
        combined_chunks = self._combine_pieces(text_chunks)
        
        # Finally, wrap the text strings into proper `Chunk` objects
        final_chunks = []
        for i, text_content in enumerate(combined_chunks):
            # We skip empty chunks
            if not text_content.strip():
                continue
                
            chunk = Chunk(
                text=text_content.strip(),
                metadata=document.metadata,
                chunk_index=i
            )
            final_chunks.append(chunk)
            
        return final_chunks

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """
        Recursively splits the text using the provided separators.
        """
        if not text:
            return []

        # Find the first separator in our list that actually exists in the text
        separator = separators[-1] # Default to the last one (usually empty string "")
        new_separators = []
        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:] # If this one fails later, use the smaller ones
                break

        # Split the text
        if separator:
            splits = text.split(separator)
        else:
            # If separator is empty string, split by characters
            splits = list(text)

        # Now, check if any of the resulting splits are STILL too big.
        # If they are, recursively split them with the smaller separators.
        final_splits = []
        for split in splits:
            if len(split) <= self.chunk_size:
                # Add the separator back so we don't lose punctuation/formatting
                # (except for the last piece, which doesn't need a trailing separator)
                final_splits.append(split + (separator if split != splits[-1] else ""))
            else:
                if new_separators:
                    # Too big! Recurse with the remaining (smaller) separators
                    final_splits.extend(self._split_text(split, new_separators))
                else:
                    # We ran out of separators and it's still too big. 
                    # Just force a hard cut (this is rare).
                    final_splits.append(split)
                    
        return final_splits

    def _combine_pieces(self, pieces: List[str]) -> List[str]:
        """
        Combines small text pieces into chunks of up to chunk_size, accounting for overlap.
        """
        chunks = []
        current_chunk_pieces = []
        current_len = 0

        for piece in pieces:
            piece_len = len(piece)
            
            # If adding this piece pushes us over the limit, finalize the current chunk
            if current_len + piece_len > self.chunk_size and current_chunk_pieces:
                chunks.append("".join(current_chunk_pieces))
                
                # Now we need to start the next chunk, but keep some overlap from the previous one!
                # We remove pieces from the start of the list until our remaining pieces 
                # are small enough to fit within the `chunk_overlap` limit.
                while current_len > self.chunk_overlap and len(current_chunk_pieces) > 1:
                    popped_piece = current_chunk_pieces.pop(0)
                    current_len -= len(popped_piece)
            
            # Add the current piece
            current_chunk_pieces.append(piece)
            current_len += piece_len

        # Don't forget to add the very last chunk!
        if current_chunk_pieces:
            chunks.append("".join(current_chunk_pieces))
            
        return chunks

    def _clean_html(self, text: str) -> str:
        """
        Strips HTML tags, comments, and normalizes whitespace.
        
        WHY THIS IS NEEDED:
            pymupdf4llm sometimes outputs HTML artifacts like <br>, <!-- comments -->,
            and other markup that confuses embedding models and the cross-encoder
            reranker. Clean text produces dramatically better search results.
        """
        # Remove HTML comments <!-- ... -->
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        # Replace <br>, <br/>, <br /> with newlines
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode common HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"')
        # Collapse multiple blank lines into max 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Collapse multiple spaces into single space
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()
