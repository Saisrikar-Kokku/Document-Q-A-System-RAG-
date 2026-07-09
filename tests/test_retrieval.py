"""
test_retrieval.py — Unit Tests for Retrieval Logic
==================================================

WHAT THIS FILE DOES:
    Verifies that our `Retriever` properly filters out chunks that score
    below our `SIMILARITY_THRESHOLD`.
"""

from retrieval.retriever import Retriever
from config import SIMILARITY_THRESHOLD

class MockEmbedder:
    """A fake embedder for testing."""
    def embed_text(self, text):
        return [0.1, 0.2, 0.3] # Fake vector

class MockQdrantStore:
    """A fake database that returns predefined results."""
    def search(self, query_vector, limit, filter_conditions=None, with_payload=True):
        # We return one high-scoring chunk and one low-scoring chunk
        return [
            {"score": 0.9, "payload": {"text": "Good chunk", "file_name": "a.txt"}},
            {"score": 0.1, "payload": {"text": "Bad chunk", "file_name": "b.txt"}}
        ]

def test_retriever_filters_low_scores():
    """
    Verifies that chunks below SIMILARITY_THRESHOLD are dropped.
    """
    embedder = MockEmbedder()
    qdrant = MockQdrantStore()
    retriever = Retriever(embedder, qdrant)
    
    # Run the retrieval
    results = retriever.retrieve("Fake question")
    
    # We should only get 1 result back (the one that scored 0.9).
    # The 0.1 score should have been dropped.
    assert len(results) == 1
    assert results[0]["text"] == "Good chunk"
