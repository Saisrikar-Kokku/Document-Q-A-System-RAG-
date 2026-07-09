"""
embedder.py — Text to Vector Converter (Cloud API Version)
==========================================================

WHAT THIS FILE DOES:
    Uses the Hugging Face Inference API to convert text into semantic vectors
    without requiring heavy local ML libraries like PyTorch.

WHY IT'S DESIGNED THIS WAY:
    By offloading the heavy math to Hugging Face, our server's RAM usage drops
    from ~600MB down to ~50MB, allowing it to run perfectly on the Render Free Tier.
"""

from typing import List, Dict, Any
import httpx
import os
import json
from config import EMBEDDING_MODEL_NAME

class Embedder:
    """
    Handles converting text into semantic vectors via Hugging Face Cloud.
    """
    def __init__(self):
        # Hugging Face provides a free inference API for small models.
        self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{EMBEDDING_MODEL_NAME}"
        self.hf_token = os.environ.get("HF_TOKEN", "")
        
        if not self.hf_token:
            print("WARNING: HF_TOKEN environment variable not set. API calls may be severely rate limited.")

    def _call_api(self, payload: Any) -> Any:
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
            
        try:
            # We use httpx for a simple synchronous call. For massive batching, 
            # this could be made async, but for a simple RAG, this works perfectly.
            with httpx.Client() as client:
                response = client.post(self.api_url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error calling Hugging Face Embedding API: {e}")
            # Return a zero-vector fallback to prevent crashes if the API fails
            # We know bge-small uses 384 dimensions.
            return [0.0] * 384 if isinstance(payload, str) else [[0.0] * 384 for _ in payload]

    def embed_text(self, text: str) -> List[float]:
        """
        Converts a single string into a vector.
        """
        # The API returns a list of floats for a single string.
        # Sometimes HF wraps it in an outer list depending on the model pipeline.
        result = self._call_api(text)
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            return result[0]
        return result

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Converts a list of strings into a list of vectors.
        """
        # The API natively accepts lists of strings!
        result = self._call_api(texts)
        return result
