"""
retriever.py — The Semantic Search Engine
=========================================

WHAT THIS FILE DOES:
    Glues together the Embedder (Phase 4) and QdrantStore (Phase 5). 
    It takes a user's raw text question, embeds it, queries Qdrant, and filters
    the results based on similarity thresholds and optional metadata.

WHY IT'S DESIGNED THIS WAY:
    Retrieval is a distinct step in RAG. By isolating it here, we can easily
    upgrade it later. For example, if we want to add "Re-ranking" (using a 
    second AI model to re-sort the top 10 results for better accuracy), 
    we would just add it to this file without touching the rest of the pipeline.
"""

from typing import List, Dict, Any, Optional
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from embeddings.embedder import Embedder
from vectorstore.qdrant_store import QdrantStore
from config import RETRIEVAL_TOP_K, SIMILARITY_THRESHOLD

class Retriever:
    """
    Handles fetching the most relevant document chunks for a given query.
    """
    def __init__(self, embedder: Embedder, qdrant_store: QdrantStore):
        self.embedder = embedder
        self.qdrant_store = qdrant_store

    def retrieve(
        self, 
        query: str, 
        top_k: int = RETRIEVAL_TOP_K, 
        file_type_filter: Optional[str] = None,
        file_name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # 1. Convert the user's question into math vectors (Dense)
        query_vector = self.embedder.embed_text(query)
        
        # 2. Build metadata filters if requested
        qdrant_filter = None
        must_conditions = []
        
        if file_type_filter:
            must_conditions.append(
                FieldCondition(
                    key="file_type", 
                    match=MatchValue(value=file_type_filter)
                )
            )
            
        if file_name_filter:
            must_conditions.append(
                FieldCondition(
                    key="file_name", 
                    match=MatchValue(value=file_name_filter)
                )
            )
            
        if must_conditions:
            qdrant_filter = Filter(must=must_conditions)
            
        # 3. Perform the Search in Qdrant
        raw_results = self.qdrant_store.search(
            dense_query=query_vector,
            limit=top_k,
            filter_conditions=qdrant_filter
        )
        
        # 4. Filter by Similarity Threshold
        filtered_results = [r for r in raw_results if r["score"] >= SIMILARITY_THRESHOLD]
        return filtered_results
