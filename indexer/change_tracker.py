"""
change_tracker.py — Incremental Ingestion Engine
================================================

WHAT THIS FILE DOES:
    Scans your `data/` directory. For each file, it checks if the file has been
    modified since it was last ingested. If it is new or changed, it runs the
    file through the entire pipeline (Parse -> Chunk -> Embed -> Vector DB).
    If it hasn't changed, it skips it.

WHY IT'S DESIGNED THIS WAY:
    As your dataset grows to hundreds or thousands of files, re-parsing and
    re-embedding everything takes a long time and wastes compute. By saving a
    tiny `.ingestion_index.json` file that maps `filepath -> hash`, we achieve
    O(1) incremental updates.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any

from config import DATA_DIR, INGESTION_INDEX_PATH
from ingestion.registry import load_document, PARSERS
from chunking.text_splitter import RecursiveCharacterTextSplitter
from embeddings.embedder import Embedder, SparseEmbedder
from vectorstore.qdrant_store import QdrantStore

class Indexer:
    """
    Manages the incremental ingestion of files into the vector database.
    """
    def __init__(self, embedder: Embedder, sparse_embedder: SparseEmbedder, qdrant_store: QdrantStore):
        self.embedder = embedder
        self.sparse_embedder = sparse_embedder
        self.qdrant_store = qdrant_store
        self.splitter = RecursiveCharacterTextSplitter()
        self.index_path = INGESTION_INDEX_PATH
        
        # Ensure the data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)

    def _load_index(self) -> Dict[str, Any]:
        """Loads the tracking file."""
        if not self.index_path.exists():
            return {}
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_index(self, index_data: Dict[str, Any]):
        """Saves the tracking file."""
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=4)

    def _compute_hash(self, file_path: Path) -> str:
        """
        Calculates an MD5 hash of the file's contents.
        We do this instead of just checking 'mtime' (modified time) because
        copying a file or changing its permissions can alter mtime without
        altering the actual text.
        """
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            buf = f.read(65536) # Read in 64kb chunks for memory safety
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()

    def ingest_all(self, progress_callback=None) -> Dict[str, int]:
        """
        Scans the R2 bucket and ingests any new or modified files.
        """
        index_data = self._load_index()
        stats = {"processed": 0, "skipped": 0, "failed": 0}
        
        from storage.s3_client import S3Client
        s3_client = S3Client()
        if not s3_client.client:
            print("S3 client not configured. Skipping ingestion.")
            return stats
            
        r2_files = s3_client.list_files_with_hashes()
        
        # Temp dir for processing
        temp_dir = Path(DATA_DIR) / "temp_ingest"
        os.makedirs(temp_dir, exist_ok=True)
        
        for key, current_hash in r2_files.items():
            file_name = key.split('/')[-1]
            ext = Path(file_name).suffix.lower()
            
            # Skip files we don't know how to parse
            if ext not in PARSERS:
                continue
                
            # Check if it's already indexed and hasn't changed
            if key in index_data and index_data[key] == current_hash:
                print(f"Skipping (unchanged): {key}")
                stats["skipped"] += 1
                continue
                
            # New or modified file found! Process it.
            print(f"Processing: {key}...")
            if progress_callback:
                progress_callback(f"Reading and splitting {file_name}...")
                
            temp_file_path = temp_dir / file_name
            try:
                # Download to temp
                s3_client.download_file(key, str(temp_file_path))
                
                # 1. Parse -> List[Document]
                docs = load_document(temp_file_path)
                
                # Update document metadata to point to the R2 key instead of temp path
                for doc in docs:
                    doc.metadata["source"] = key
                
                total_chars = sum(len(doc.content) for doc in docs)
                print(f"  Extracted {total_chars:,} characters.")
                if progress_callback:
                    progress_callback(f"Extracted {total_chars:,} characters from {file_name}. Chunking...")
                
                # 2. Document -> Chunks
                chunks = []
                for doc in docs:
                    chunks.extend(self.splitter.split_document(doc))
                if not chunks:
                    print(f"  Warning: No text extracted from {key}")
                    stats["failed"] += 1
                    continue
                    
                # 3 & 4. Embed and Upsert in batches
                if progress_callback:
                    progress_callback(f"Processing {len(chunks)} chunks in batches of 100...")
                    
                batch_size = 100
                for i in range(0, len(chunks), batch_size):
                    chunk_batch = chunks[i:i + batch_size]
                    text_batch = [c.text for c in chunk_batch]
                    
                    if progress_callback:
                        progress_callback(f"  Embedding & saving batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}...")
                        
                    dense_vectors = self.embedder.embed_batch(text_batch)
                    sparse_vectors = self.sparse_embedder.embed_batch(text_batch)
                    
                    self.qdrant_store.upsert_chunks(chunk_batch, dense_vectors, sparse_vectors)
                
                # 5. Mark as processed
                index_data[key] = current_hash
                stats["processed"] += 1
                
            except Exception as e:
                print(f"Failed to process {key}: {e}")
                stats["failed"] += 1
            finally:
                if temp_file_path.exists():
                    os.remove(temp_file_path)
                    
        # Save the updated index so we don't process these again next time
        self._save_index(index_data)
        return stats
