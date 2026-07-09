"""
cloud_llm.py — The Cloud LLM Client (Gemini)
============================================

WHAT THIS FILE DOES:
    Implements the LLMInterface to talk to Google's Gemini (free tier).
    
WHY IT'S DESIGNED THIS WAY:
    Provides a fallback/alternative to the local LLM. If your laptop struggles
    to run Ollama, or you just want higher quality answers, you can switch to
    this by changing ONE line in config.py.
"""

from google import genai
from .llm_interface import LLMInterface
from config import GEMINI_API_KEY, GEMINI_MODEL_NAME

class CloudLLM(LLMInterface):
    """
    Client for Google's Gemini Cloud API.
    """
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")
        
        # Initialize the official SDK
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = GEMINI_MODEL_NAME
        
    def generate(self, prompt: str) -> str:
        """
        Sends the prompt to Gemini and gets the response.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error communicating with Cloud LLM: {str(e)}"
