"""
qdrant_store.py — The Vector Database Interface
===============================================

WHAT THIS FILE DOES:
    Connects to our local Qdrant Docker container. It creates the database collection
    (if it doesn't exist), allows us to `upsert` (insert/update) chunk vectors with
    their metadata, and allows us to `search` for similar vectors.

WHY IT'S DESIGNED THIS WAY:
    We abstract the Qdrant client into this class. If we ever want to switch to
    Qdrant Cloud in the future, we only have to change the connection URL here.
    The rest of the RAG pipeline doesn't care *how* things are stored, only that
    it can call `.upsert()` and `.search()`.
"""

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter
from typing import List, Dict, Any
import hashlib

from config import (
    QDRANT_HOST, 
    QDRANT_PORT, 
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME, 
    EMBEDDING_DIMENSION
)
from chunking.text_splitter import Chunk

class QdrantStore:
    """
    Handles all interactions with the Qdrant vector database.
    """
    def __init__(self):
        # Connect to the local Qdrant instance running in Docker or Qdrant Cloud
        if QDRANT_URL and QDRANT_API_KEY:
            print("Connecting to Qdrant Cloud...")
            self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        else:
            print("Connecting to local Qdrant...")
            self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            
        self.collection_name = QDRANT_COLLECTION_NAME
        
        # Ensure the collection exists when this class is instantiated
        self._ensure_collection()

    def _ensure_collection(self):
        """
        Creates the Qdrant collections if they don't already exist.
        A collection in Qdrant is like a table in a relational database.
        """
        collections = self.client.get_collections().collections
        existing_names = [c.name for c in collections]
        
        # We ensure both the main document collection and the chat_history collection exist.
        for col_name in [self.collection_name, "chat_history"]:
            exists = col_name in existing_names
            
            if exists:
                # Check if this collection was built with named vectors (Hybrid Search)
                col_info = self.client.get_collection(col_name)
                if not isinstance(col_info.config.params.vectors, dict) or "dense" not in col_info.config.params.vectors:
                    print(f"Upgrading Qdrant collection {col_name} to Hybrid Search...")
                    self.client.delete_collection(col_name)
                    exists = False
                    
                    if col_name == self.collection_name:
                        # We also need to wipe the ingestion index so the files get re-processed
                        import os
                        if os.path.exists(".ingestion_index.json"):
                            os.remove(".ingestion_index.json")
                            print("Cleared ingestion index to force re-indexing of all files with sparse vectors.")
            
            if not exists:
                print(f"Creating Qdrant collection: {col_name} (Hybrid Search enabled)...")
                self.client.create_collection(
                    collection_name=col_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=EMBEDDING_DIMENSION, 
                            distance=models.Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "sparse": models.SparseVectorParams(
                            index=models.SparseIndexParams(on_disk=False)
                        )
                    }
                )
                
                # Create payload indices for filtering
                if col_name == self.collection_name:
                    for field in ["file_name", "source_path", "file_type"]:
                        self.client.create_payload_index(
                            collection_name=col_name,
                            field_name=field,
                            field_schema=models.PayloadSchemaType.KEYWORD,
                        )

    def _generate_point_id(self, source_path: str, chunk_index: int, page_number: int = None) -> str:
        """
        Generates a unique ID for a chunk.
        """
        if page_number is not None:
            unique_string = f"{source_path}_page{page_number}_{chunk_index}"
        else:
            unique_string = f"{source_path}_{chunk_index}"
            
        md5_hash = hashlib.md5(unique_string.encode('utf-8')).hexdigest()
        return f"{md5_hash[:8]}-{md5_hash[8:12]}-{md5_hash[12:16]}-{md5_hash[16:20]}-{md5_hash[20:32]}"

    def upsert_chunks(self, chunks: List[Chunk], dense_vectors: List[List[float]], sparse_vectors: List[Dict[str, List[Any]]]):
        """
        Uploads chunks, their dense vectors, and their sparse vectors to Qdrant.
        """
        if len(chunks) != len(dense_vectors) or len(chunks) != len(sparse_vectors):
            raise ValueError("Number of chunks, dense vectors, and sparse vectors must match.")
            
        if not chunks:
            return

        points = []
        for chunk, dense_vec, sparse_vec in zip(chunks, dense_vectors, sparse_vectors):
            point_id = self._generate_point_id(
                chunk.metadata.source_path, 
                chunk.chunk_index,
                chunk.metadata.page_number
            )
            
            # The "payload" is where we store the actual text and metadata.
            # Qdrant stores the vector for math, and the payload for us to read later.
            payload = {
                "text": chunk.text,
                "source_path": chunk.metadata.source_path,
                "file_type": chunk.metadata.file_type,
                "file_name": chunk.metadata.file_name,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.metadata.page_number,
                # Convert datetime to ISO string for JSON serialization
                "last_modified": chunk.metadata.last_modified.isoformat() 
            }
            
            # Since we have named vectors, we pass them as a dictionary
            vectors_dict = {
                "dense": dense_vec,
                "sparse": models.SparseVector(
                    indices=sparse_vec["indices"], 
                    values=sparse_vec["values"]
                )
            }
            
            points.append(PointStruct(id=point_id, vector=vectors_dict, payload=payload))
            
        # Upsert the points in batches to avoid connection timeouts (WinError 10053) on large files
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                print(f"      Upserted batch {i//batch_size + 1}/{(len(points) + batch_size - 1)//batch_size} ({len(batch)} points)")
            except Exception as e:
                print(f"      Failed to upsert batch {i//batch_size + 1}: {e}")
                raise e

    def search(self, dense_query: List[float], sparse_query: Dict[str, List[Any]], limit: int = 5, filter_conditions: Filter = None) -> List[Dict[str, Any]]:
        """
        Performs a Hybrid Search using Reciprocal Rank Fusion (RRF).
        """
        # Prefetch queries both the dense and sparse vectors simultaneously
        prefetch = [
            models.Prefetch(
                query=dense_query,
                using="dense",
                limit=limit * 2,
                filter=filter_conditions
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_query["indices"],
                    values=sparse_query["values"]
                ),
                using="sparse",
                limit=limit * 2,
                filter=filter_conditions
            )
        ]
        
        # Then fuses the rankings using RRF
        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True
        )
        
        formatted_results = []
        for hit in results.points:
            formatted_results.append({
                "score": hit.score,
                "text": hit.payload["text"],
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            })
            
        return formatted_results

    def delete_by_filename(self, filename: str):
        """
        Deletes all chunks associated with a specific file from Qdrant.
        """
        print(f"Deleting all vectors for {filename} from Qdrant...")
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_name",
                            match=models.MatchValue(value=filename)
                        )
                    ]
                )
            )
        )

    def upsert_memory(self, point_id: str, payload: dict, dense_vec: list, sparse_vec: dict):
        """
        Saves a chat interaction into the chat_history collection.
        """
        vectors_dict = {
            "dense": dense_vec,
            "sparse": models.SparseVector(
                indices=sparse_vec["indices"], 
                values=sparse_vec["values"]
            )
        }
        point = PointStruct(id=point_id, vector=vectors_dict, payload=payload)
        self.client.upsert(
            collection_name="chat_history",
            points=[point]
        )

    def search_memory(self, dense_query: list, sparse_query: dict, limit: int = 5, filter_conditions: Filter = None) -> list:
        """
        Searches the chat_history collection.
        """
        prefetch = [
            models.Prefetch(
                query=dense_query,
                using="dense",
                limit=limit * 2,
                filter=filter_conditions
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_query["indices"],
                    values=sparse_query["values"]
                ),
                using="sparse",
                limit=limit * 2,
                filter=filter_conditions
            )
        ]
        
        results = self.client.query_points(
            collection_name="chat_history",
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True
        )
        
        formatted_results = []
        for hit in results.points:
            formatted_results.append({
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            })
            
        return formatted_results

    def update_source_metadata(self, old_source_path: str, new_source_path: str):
        """
        Updates the source_path in the payload for all chunks of a given file.
        """
        print(f"Updating Qdrant payload: {old_source_path} -> {new_source_path}")
        self.client.set_payload(
            collection_name=self.collection_name,
            payload={
                "source_path": new_source_path,
                # Also update file_name to reflect the new key
                "file_name": new_source_path.split("/")[-1]
            },
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source_path",
                            match=models.MatchValue(value=old_source_path)
                        )
                    ]
                )
            )
        )
