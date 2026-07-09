"""
groq_llm.py — Cloud LLM Interface (Groq)
========================================

WHAT THIS FILE DOES:
    Implements the LLMInterface using the official Groq Python SDK.
    
WHY IT'S DESIGNED THIS WAY:
    Groq runs open-source models (like Llama 3 and Mixtral) on custom
    hardware (LPUs) at lightning speeds. It offers a generous free tier
    and is OpenAI-API compatible.
"""

import sys
from groq import Groq
import config
from generation.llm_interface import LLMInterface

class GroqLLM(LLMInterface):
    """
    Adapter for the Groq Cloud API.
    """
    def __init__(self):
        if not config.GROQ_API_KEY:
            print("ERROR: GROQ_API_KEY is not set in config.py or .env", file=sys.stderr)
            print("Please create an API key at https://console.groq.com/keys and add it to .env", file=sys.stderr)
            sys.exit(1)
            
        self.model_name = config.GROQ_MODEL_NAME
        self.client = Groq(api_key=config.GROQ_API_KEY)

    def generate(self, prompt: str) -> str:
        """
        Sends the compiled prompt to Groq and returns the text response.
        Uses separate system and user messages for better instruction following.
        """
        try:
            # Split the prompt into system instruction and user content
            # The prompt builder separates them with the CONTEXT section
            system_msg = (
                "You are an intelligent document assistant. "
                "You answer questions based on the provided document context. "
                "Be thorough, accurate, and extract all relevant details. "
                "If the context contains the answer, always provide it — never refuse unnecessarily. "
                "Be clear and concise. Give the answer directly using bullet points where appropriate."
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": system_msg,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.1,  # Low temperature for factual accuracy, but not 0 to avoid rigidity
                max_tokens=1024,  # Cap the output to save daily tokens (most RAG answers don't need >1024)
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling Groq API: {e}", file=sys.stderr)
            return f"I encountered an error connecting to Groq: {e}"
