"""
web_search.py — The Internet Fallback
=====================================

WHAT THIS FILE DOES:
    Provides a simple function to search DuckDuckGo and return the top text snippets.

WHY IT'S DESIGNED THIS WAY:
    If the user asks a question that isn't in our local Qdrant database, 
    the RAG pipeline can dynamically fetch context from the open web 
    to prevent hallucinations.
"""

from ddgs import DDGS
from typing import List, Dict, Any

class WebSearcher:
    """
    Handles fetching live information from the internet.
    """
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Searches the web and formats the results to look like Qdrant chunks
        so the prompt builder can process them interchangeably.
        """
        print(f"Executing web search for: '{query}'...")
        
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            
            # Format results to mimic our standard chunk metadata
            formatted_chunks = []
            for r in results:
                formatted_chunks.append({
                    "text": r["body"],
                    "metadata": {
                        "source_path": r["href"],
                        "file_name": "Web Search: " + r["title"],
                        "file_type": "URL",
                        "last_modified": "Just now"
                    },
                    "score": 1.0,  # Web results don't have a cosine similarity score
                    "rerank_score": 1.0 # Or a cross-encoder score
                })
            
            return formatted_chunks
        except Exception as e:
            print(f"Web search failed: {e}")
            return []
