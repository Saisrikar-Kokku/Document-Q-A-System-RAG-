"""
rag_pipeline.py — The Master Orchestrator
=========================================

WHAT THIS FILE DOES:
    Ties the retrieval and generation phases into a single `answer_question` function.
    
WHY IT'S DESIGNED THIS WAY:
    The API (or UI) shouldn't have to know how to retrieve chunks, build prompts,
    and call the LLM. It should just be able to say `pipeline.answer_question("...")`.
    This hides the complexity of the RAG system from the outside world.
"""

from typing import Dict, Any, Optional

from retrieval.retriever import Retriever
from retrieval.reranker import Reranker
from tools.web_search import WebSearcher
from generation.llm_interface import LLMInterface
from generation.prompt_builder import PromptBuilder

class RAGPipeline:
    """
    The orchestrator that executes the full RAG lifecycle.
    """
    def __init__(self, retriever: Retriever, reranker: Reranker, web_searcher: WebSearcher, llm: LLMInterface, chat_store=None, embedder=None, qdrant_store=None):
        # We inject our dependencies
        self.retriever = retriever
        self.reranker = reranker
        self.web_searcher = web_searcher
        self.llm = llm
        self.prompt_builder = PromptBuilder()
        self.chat_store = chat_store
        self.embedder = embedder
        self.qdrant_store = qdrant_store

    def answer_question(self, query: str, file_type_filter: Optional[str] = None, file_name_filter: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the full Retrieval-Augmented Generation process.
        
        Args:
            query: The user's question.
            file_type_filter: Optional filter (e.g., ".pdf")
            file_name_filter: Optional filter (e.g., "my_document.pdf")
            session_id: Optional chat session ID for conversational memory

            
        Returns:
            A dictionary containing the answer and the sources used.
        """
        # Step 1: Retrieval (Fetch top 20 candidates)
        print(f"Retrieving context for: '{query}'...")
        raw_chunks = self.retriever.retrieve(query, top_k=20, file_type_filter=file_type_filter, file_name_filter=file_name_filter)
        
        # Step 2: Re-ranking (Narrow down to top 5 chunks to save tokens)
        print(f"Re-ranking {len(raw_chunks)} candidates...")
        retrieved_chunks = self.reranker.rerank(query, raw_chunks, top_k=5)
        
        # Guard: Check relevance
        # Only fallback to web search if we found absolutely nothing in the local database.
        if not retrieved_chunks:
            print("Local documents irrelevant. Falling back to web search...")
            web_chunks = self.web_searcher.search(query, max_results=3)
            if web_chunks:
                retrieved_chunks = web_chunks
            else:
                return {
                    "answer": "I don't have any information in your documents, and a web search failed to find an answer.",
                    "sources": []
                }
            
        # Step 2.5: Retrieve Memory Vectors
        if self.qdrant_store and self.embedder:
            print(f"Retrieving relevant memories from past chats...")
            dense_query = self.embedder.embed_text(query)
            memories = self.qdrant_store.search_memory(dense_query, limit=3)
            
            for i, mem in enumerate(memories):
                # Format memory into a chunk-like structure so prompt builder accepts it
                mem_chunk = {
                    "text": mem["text"],
                    "metadata": {
                        "file_name": "Past Conversation Memory",
                        "chunk_index": i
                    }
                }
                retrieved_chunks.insert(0, mem_chunk) # Prepend memories so they are seen first
            
        # Step 3: Prompt Construction
        print(f"Building prompt from {len(retrieved_chunks)} relevant chunks/memories...")
        history = []
        if self.chat_store and session_id:
            session = self.chat_store.get_session(session_id)
            if session:
                history = session.get("history", [])
        
        prompt = self.prompt_builder.build_prompt(query, retrieved_chunks, history)
        
        # Step 3: LLM Generation
        print(f"Generating answer using {self.llm.__class__.__name__}...")
        answer = self.llm.generate(prompt)
        
        # Save Interaction
        sources = [chunk["metadata"] for chunk in retrieved_chunks]
        if self.chat_store and session_id:
            self.chat_store.add_interaction(session_id, query, answer, sources)
            
        # Convert Q&A to Memory Vector
        if self.qdrant_store and self.embedder and session_id:
            print("Saving interaction to memory vectors...")
            import uuid
            memory_text = f"User asked: {query}\nAI answered: {answer}"
            dense_vec = self.embedder.embed_text(memory_text)
            payload = {
                "text": memory_text,
                "session_id": session_id,
                "query": query,
                "answer": answer
            }
            # Give it a random UUID
            point_id = str(uuid.uuid4())
            self.qdrant_store.upsert_memory(point_id, payload, dense_vec)
        
        # Return the answer ALONG WITH the sources used, so the user can verify it.
        # This is a critical feature for a trustworthy RAG system.
        return {
            "answer": answer,
            "sources": sources
        }

    def answer_question_stream(self, query: str, file_type_filter: Optional[str] = None, file_name_filter: Optional[str] = None, session_id: Optional[str] = None):
        """
        Executes the full Retrieval-Augmented Generation process, but yields
        status updates in real-time before yielding the final answer.
        This allows the frontend to visually show the AI's "thought process".
        """
        import json
        
        # Tell the UI we are starting retrieval
        yield json.dumps({"step": "retrieving", "message": f"Analyzing question to extract semantic meaning..."}) + "\n"
        yield json.dumps({"step": "retrieving", "message": f"Searching Qdrant for vectors closely matching: '{query}'"}) + "\n"
        
        raw_chunks = self.retriever.retrieve(query, top_k=20, file_type_filter=file_type_filter, file_name_filter=file_name_filter)
        
        yield json.dumps({"step": "retrieving", "message": f"Re-ranking {len(raw_chunks)} candidates using Cross-Encoder..."}) + "\n"
        retrieved_chunks = self.reranker.rerank(query, raw_chunks, top_k=5)
        
        if not retrieved_chunks:
            yield json.dumps({"step": "retrieving", "message": f"Local documents lack the answer. Automatically searching the internet..."}) + "\n"
            web_chunks = self.web_searcher.search(query, max_results=3)
            
            if web_chunks:
                retrieved_chunks = web_chunks
            else:
                yield json.dumps({
                    "step": "done",
                    "answer": "I don't have any information in your documents, and a web search failed to find an answer.",
                    "sources": []
                }) + "\n"
                return
            
        # Extract metadata for dynamic thought
        is_web_search = any("Web Search" in c["metadata"].get("file_name", "") for c in retrieved_chunks)
        
        if is_web_search:
            yield json.dumps({"step": "prompting", "message": f"Successfully retrieved {len(retrieved_chunks)} results from DuckDuckGo internet search."}) + "\n"
            unique_files = ["Internet Search"]
        else:
            top_score = retrieved_chunks[0].get("rerank_score", retrieved_chunks[0].get("score", 0))
            top_file = retrieved_chunks[0]["metadata"].get("file_name", "unknown")
            unique_files = list(set([c["metadata"].get("file_name", "unknown") for c in retrieved_chunks]))
            
            yield json.dumps({"step": "prompting", "message": f"Found {len(retrieved_chunks)} relevant passages. Most relevant match comes from '{top_file}' with a confidence score of {top_score:.2f}."}) + "\n"
        
        # Retrieve Memory Vectors
        if self.qdrant_store and self.embedder:
            yield json.dumps({"step": "retrieving", "message": f"Searching past conversations for relevant memories..."}) + "\n"
            dense_query = self.embedder.embed_text(query)
            memories = self.qdrant_store.search_memory(dense_query, limit=3)
            
            if memories:
                yield json.dumps({"step": "retrieving", "message": f"Found {len(memories)} relevant memories from past chats."}) + "\n"
                for i, mem in enumerate(memories):
                    mem_chunk = {
                        "text": mem["text"],
                        "metadata": {
                            "file_name": "Past Conversation Memory",
                            "chunk_index": i
                        }
                    }
                    retrieved_chunks.insert(0, mem_chunk)
                    
        # Fetch history
        history = []
        if self.chat_store and session_id:
            session = self.chat_store.get_session(session_id)
            if session:
                history = session.get("history", [])
                
        prompt = self.prompt_builder.build_prompt(query, retrieved_chunks, history)
        
        # Tell the UI we are generating
        if is_web_search:
            yield json.dumps({"step": "generating", "message": f"Synthesizing internet results and sending strict instructions to {self.llm.__class__.__name__}..."}) + "\n"
        else:
            yield json.dumps({"step": "generating", "message": f"Assembling context from {len(unique_files)} unique local files and sending strict instructions to {self.llm.__class__.__name__}..."}) + "\n"
        
        answer = self.llm.generate(prompt)
        
        sources = [chunk["metadata"] for chunk in retrieved_chunks]
        if self.chat_store and session_id:
            self.chat_store.add_interaction(session_id, query, answer, sources)
            
        if self.qdrant_store and self.embedder and session_id:
            import uuid
            memory_text = f"User asked: {query}\nAI answered: {answer}"
            dense_vec = self.embedder.embed_text(memory_text)
            payload = {
                "text": memory_text,
                "session_id": session_id,
                "query": query,
                "answer": answer
            }
            point_id = str(uuid.uuid4())
            self.qdrant_store.upsert_memory(point_id, payload, dense_vec)
        
        # Yield the final answer
        yield json.dumps({
            "step": "done",
            "answer": answer,
            "sources": sources
        }) + "\n"
