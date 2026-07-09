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
    
    print(f"Deleting collection '{store.collection_name}'...")
    store.client.delete_collection(store.collection_name)
    
    print("Recreating collection...")
    store._ensure_collection()

    print("Wiping local ingestion tracker...")
    if os.path.exists(".ingestion_index.json"):
        os.remove(".ingestion_index.json")

    print("Initializing embedders (this might take a second)...")
    embedder = Embedder()
    sparse_embedder = SparseEmbedder()
    
    indexer = Indexer(embedder, sparse_embedder, store)

    def progress_callback(msg):
        print(f"PROGRESS: {msg}")

    print("\nStarting full re-ingestion of all files in data/...")
    indexer.ingest_all(progress_callback=progress_callback)
    print("\nSUCCESS! All data has been successfully re-ingested.")

if __name__ == "__main__":
    main()
