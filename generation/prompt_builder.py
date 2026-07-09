"""
prompt_builder.py — Constructing the Instructions
=================================================

WHAT THIS FILE DOES:
    Takes the retrieved text chunks and the user's question, and formats them
    into a single, strict instruction manual for the LLM.

WHY IT'S DESIGNED THIS WAY:
    LLMs are prone to "hallucination" (making things up). If we just ask it the
    question, it will answer from its training data. We must explicitly command
    it to ONLY use the provided context, and tell it exactly what to do if the
    context doesn't contain the answer.
"""

from typing import List, Dict, Any
from config import MAX_CONTEXT_LENGTH

class PromptBuilder:
    """
    Constructs the final prompt sent to the LLM.
    """
    def __init__(self):
        # This is the "System Prompt" — the strict rules for the AI.
        # It is deliberately more permissive to avoid false "I cannot answer" responses.
        self.system_instruction = (
            "You are an intelligent document assistant. "
            "You have been given relevant excerpts from the user's personal documents. "
            "Your job is to answer the user's question using the information in the provided context.\n\n"
            "RULES:\n"
            "1. Base your answer primarily on the provided context.\n"
            "2. If the context contains the answer (even partially or indirectly), provide a helpful response.\n"
            "3. If the context genuinely does not contain any relevant information at all, "
            "say: 'I could not find specific information about this in your documents.'\n"
            "4. Do NOT make up facts that are not supported by the context.\n"
            "5. Be thorough — extract and present all relevant details from the context.\n"
            "6. If the context contains tables or structured data, present the information clearly.\n"
            "7. Be clear and concise. Do not write long introductions. Give the answer directly using bullet points where appropriate.\n"
        )

    def build_prompt(self, query: str, retrieved_chunks: List[Dict[str, Any]], history: List[Dict[str, Any]] = None) -> str:
        """
        Combines the system instructions, the retrieved context, previous chat history, and the question.
        """
        # Formulate history (last 5 interactions)
        history_text = ""
        if history:
            history_text = "PREVIOUS CONVERSATION (for context only):\n"
            # Get last 2 interactions to prevent context bloat and save tokens
            recent_history = history[-2:]
            for turn in recent_history:
                history_text += f"User: {turn['user_query']}\n"
                history_text += f"AI: {turn['ai_answer']}\n\n"
                
        # 1. Format the context pieces
        context_texts = []
        current_length = 0
        
        for i, chunk in enumerate(retrieved_chunks):
            # We prefix each chunk with its source so the LLM could cite it if we wanted it to.
            source = chunk["metadata"].get("file_name", "Unknown Source")
            chunk_idx = chunk["metadata"].get("chunk_index", i)
            formatted_chunk = f"[Document: {source} | Chunk {chunk_idx}]\n{chunk['text']}\n"
            
            # 2. Guard against Context Limits
            # If adding this chunk would exceed our max limit, we stop adding context.
            if current_length + len(formatted_chunk) > MAX_CONTEXT_LENGTH:
                print(f"Warning: Context limit reached. Only included {i} of {len(retrieved_chunks)} chunks.")
                break
                
            context_texts.append(formatted_chunk)
            current_length += len(formatted_chunk)
            
        full_context = "\n".join(context_texts)
        
        # 3. Assemble the final prompt
        final_prompt = (
            f"{self.system_instruction}\n"
            f"{history_text}"
            f"CONTEXT FROM DOCUMENTS:\n{full_context}\n\n"
            f"USER'S QUESTION: {query}\n\n"
            f"Provide a detailed and helpful answer based on the context above:"
        )
        
        return final_prompt
