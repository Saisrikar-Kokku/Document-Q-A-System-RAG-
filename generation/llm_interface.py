"""
llm_interface.py — The LLM Abstraction
======================================

WHAT THIS FILE DOES:
    Defines the standard "contract" for any AI model we plug into the system.
    
WHY IT'S DESIGNED THIS WAY:
    By forcing both our Local LLM (Ollama) and Cloud LLM (Gemini) to inherit from
    this base class, we guarantee they both have a `generate()` method that takes
    a string and returns a string. The pipeline never needs to know WHICH model
    it is talking to.
"""

from abc import ABC, abstractmethod

class LLMInterface(ABC):
    """
    Abstract Base Class for LLM providers.
    """
    
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Takes a fully formatted prompt and returns the AI's response.
        
        Args:
            prompt: The string containing the instructions, context, and question.
            
        Returns:
            The AI's generated answer.
        """
        pass
