"""
embedder.py — Text to Vector Converter
======================================

WHAT THIS FILE DOES:
    Loads a local neural network (`sentence-transformers`) and uses it to convert
    text (strings) into vectors (lists of floats).

WHY IT'S DESIGNED THIS WAY:
    We wrap the `SentenceTransformer` in a class so we only have to load the model
    into RAM once. We provide a batch method `embed_chunks` because passing a list
    of 50 chunks to the model at once is much faster than passing 1 chunk 50 times
    in a loop.

HOW IT FITS IN THE PIPELINE:
    Takes `Chunk` objects (from Phase 3).
    Passes their text to the model.
    Produces vectors that get stored in Qdrant (Phase 5).
"""

from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from config import EMBEDDING_MODEL_NAME, SPARSE_MODEL_NAME

class Embedder:
    """
    Handles converting text into semantic vectors.
    """
    def __init__(self):
        # This line loads the AI model into memory. 
        # The very first time it runs, it will download the model from HuggingFace
        # and cache it on your hard drive (in ~/.cache/huggingface).
        # Subsequent runs will load it instantly from the cache.
        print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("Model loaded successfully.")

    def embed_text(self, text: str) -> List[float]:
        """
        Converts a single string into a vector.
        Useful for converting the user's search query into a vector.
        """
        # .encode() returns a NumPy array. We convert it to a standard Python list
        # because the Qdrant database client expects standard lists.
        return self.model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Converts a list of strings into a list of vectors.
        This is heavily optimized in the background by PyTorch and is much faster
        than calling embed_text in a for-loop.
        """
        # encode() can take a list of strings and process them in parallel.
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

class SparseEmbedder:
    """
    Handles converting text into sparse vectors (BM25) for Hybrid Search.
    Sparse vectors capture exact keywords and their frequencies.
    """
    def __init__(self):
        print(f"Loading sparse embedding model: {SPARSE_MODEL_NAME}...")
        self.model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
        print("Sparse model loaded successfully.")

    def embed_text(self, text: str) -> Dict[str, List[Any]]:
        """
        Converts a single string into a sparse vector dict for Qdrant.
        """
        # fastembed returns a generator, so we convert it to a list and take the first item
        sparse_embedding = list(self.model.embed([text]))[0]
        return {
            "indices": sparse_embedding.indices.tolist(),
            "values": sparse_embedding.values.tolist()
        }

    def embed_batch(self, texts: List[str]) -> List[Dict[str, List[Any]]]:
        """
        Converts a list of strings into a list of sparse vectors.
        """
        embeddings = self.model.embed(texts)
        result = []
        for e in embeddings:
            result.append({
                "indices": e.indices.tolist(),
                "values": e.values.tolist()
            })
        return result
