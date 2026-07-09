"""
reranker.py — The Cross-Encoder Filter
======================================

WHAT THIS FILE DOES:
    Loads a Cross-Encoder model and uses it to re-rank the results from Qdrant.

WHY IT'S DESIGNED THIS WAY:
    Vector search (Cosine or Hybrid) is fast but slightly imprecise because it 
    embeds the query and document separately. A Cross-Encoder feeds BOTH the query 
    and document into the neural network at the exact same time, allowing the model 
    to see how words in the query interact with words in the document.
    It's much slower, which is why we only use it on the top 20 results from Qdrant,
    narrowing them down to the absolute best 5 for the LLM.
"""

from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

# We use a lightweight but highly accurate model trained on MS MARCO (Microsoft's QA dataset)
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

class Reranker:
    """
    Filters and re-orders search results for maximum accuracy.
    """
    def __init__(self):
        print(f"Loading re-ranking model: {RERANKER_MODEL_NAME}...")
        self.model = CrossEncoder(RERANKER_MODEL_NAME)
        print("Re-ranking model loaded successfully.")

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Takes the raw results from Qdrant and re-scores them against the query.
        
        Args:
            query: The user's exact question.
            chunks: The list of chunks returned by Qdrant.
            top_k: How many chunks to keep after re-ranking.
        """
        if not chunks:
            return []
            
        # The Cross-Encoder expects a list of pairs: [[query, text1], [query, text2], ...]
        pairs = [[query, chunk["text"]] for chunk in chunks]
        
        # This computes a relevance score for each pair
        scores = self.model.predict(pairs)
        
        # Attach the new scores to our chunks
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)
            
        # Sort chunks by their new Cross-Encoder score (highest to lowest)
        chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Keep only the top_k best ones
        return chunks[:top_k]
