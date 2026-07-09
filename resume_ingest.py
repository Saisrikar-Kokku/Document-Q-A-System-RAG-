import os
import sys

# Add the current directory to python path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vectorstore.qdrant_store import QdrantStore
from indexer.change_tracker import Indexer
from embeddings.embedder import Embedder, SparseEmbedder

def main():
    print("Connecting to Qdrant...")
    store = QdrantStore()
    
    # Do NOT wipe the collection or the ingestion tracker!
    print("Ensuring collection exists...")
    store._ensure_collection()

    print("Initializing embedders (this might take a second)...")
    embedder = Embedder()
    sparse_embedder = SparseEmbedder()
    
    indexer = Indexer(embedder, sparse_embedder, store)

    def progress_callback(msg):
        print(f"PROGRESS: {msg}")

    print("\nResuming ingestion of remaining files in data/...")
    indexer.ingest_all(progress_callback=progress_callback)
    print("\nSUCCESS! All data has been successfully re-ingested.")

if __name__ == "__main__":
    main()
