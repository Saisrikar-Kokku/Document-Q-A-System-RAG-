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

from embeddings.embedder import Embedder, SparseEmbedder
from vectorstore.qdrant_store import QdrantStore
from config import RETRIEVAL_TOP_K, SIMILARITY_THRESHOLD

class Retriever:
    """
    Handles fetching the most relevant document chunks for a given query.
    """
    def __init__(self, embedder: Embedder, sparse_embedder: SparseEmbedder, qdrant_store: QdrantStore):
        # We pass these in rather than instantiating them here.
        # This is called "Dependency Injection" and makes testing much easier.
        self.embedder = embedder
        self.sparse_embedder = sparse_embedder
        self.qdrant_store = qdrant_store

    def retrieve(
        self, 
        query: str, 
        top_k: int = RETRIEVAL_TOP_K, 
        file_type_filter: Optional[str] = None,
        file_name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most relevant chunks for a user's question.
        
        Args:
            query: The user's question (e.g., "What are the rules for the firewall?")
            top_k: Max number of chunks to return.
            file_type_filter: Optional extension to restrict search (e.g., ".pdf")
            file_name_filter: Optional filename to restrict search (e.g., "Atomic Habits.pdf")
            
        Returns:
            A list of dictionaries containing text, metadata, and score.
        """
        # 1. Convert the user's question into math vectors (Dense and Sparse)
        query_vector = self.embedder.embed_text(query)
        sparse_vector = self.sparse_embedder.embed_text(query)
        
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
            
        # 3. Perform the Hybrid Search in Qdrant
        raw_results = self.qdrant_store.search(
            dense_query=query_vector,
            sparse_query=sparse_vector,
            limit=top_k,
            filter_conditions=qdrant_filter
        )
        
        # 4. Filter by Similarity Threshold
        # With Reciprocal Rank Fusion (RRF), scores are no longer cosine similarities (0 to 1).
        # They are RRF scores (e.g. 0.016). So we bypass the strict threshold for hybrid search.
        filtered_results = raw_results # Just trust the top_k ranking from RRF
        return filtered_results
