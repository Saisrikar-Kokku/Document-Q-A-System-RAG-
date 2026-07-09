"""
ollama_llm.py — The Local LLM Client
====================================

WHAT THIS FILE DOES:
    Implements the LLMInterface to talk to your local Ollama instance.
    
WHY IT'S DESIGNED THIS WAY:
    We use `httpx` to send a simple POST request to Ollama's local API. This means
    we don't need any heavy external libraries just to talk to a local server.
"""

import httpx
from .llm_interface import LLMInterface
from config import OLLAMA_BASE_URL, OLLAMA_MODEL_NAME

class OllamaLLM(LLMInterface):
    """
    Client for a local Ollama model.
    """
    def __init__(self):
        # We don't connect immediately, we just set the config.
        self.url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        self.model_name = OLLAMA_MODEL_NAME
        
    def generate(self, prompt: str) -> str:
        """
        Sends the prompt to Ollama and gets the response.
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False # For simplicity, we wait for the full answer rather than streaming chunks
        }
        
        # We use a long timeout because local LLMs can take several minutes to
        # read large contexts (like our 30,000 char prompt) and generate a response on a local CPU/GPU.
        # NOTE: If we were using async/await in FastAPI, we'd use AsyncClient here.
        # For simplicity in this core pipeline, we use the synchronous client.
        try:
            with httpx.Client(timeout=300.0) as client:
                response = client.post(self.url, json=payload)
                response.raise_for_status()
                return response.json()["response"]
        except httpx.HTTPError as e:
            return f"Error communicating with local Ollama: {str(e)}"
