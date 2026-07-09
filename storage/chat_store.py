"""
chat_store.py — Conversational Memory Storage
=============================================

WHAT THIS FILE DOES:
    Manages chat sessions stored as JSON files on disk. 
    It allows us to create sessions, list sessions, and append new interactions.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import DATA_DIR

CHATS_DIR = os.path.join(DATA_DIR, "chats")
os.makedirs(CHATS_DIR, exist_ok=True)

class ChatStore:
    def create_session(self) -> str:
        """Creates a new empty chat session and returns its ID."""
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "history": []
        }
        self._save(session_id, session_data)
        return session_id

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Returns a list of all chat sessions, sorted by most recent."""
        sessions = []
        if not os.path.exists(CHATS_DIR):
            return sessions
            
        for filename in os.listdir(CHATS_DIR):
            if filename.endswith(".json"):
                with open(os.path.join(CHATS_DIR, filename), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        # Derive title from the first question
                        title = "New Chat"
                        if data.get("history") and len(data["history"]) > 0:
                            title = data["history"][0]["user_query"][:35] + ("..." if len(data["history"][0]["user_query"]) > 35 else "")
                            
                        sessions.append({
                            "session_id": data.get("session_id", filename.replace(".json", "")),
                            "title": title,
                            "updated_at": data.get("updated_at", "")
                        })
                    except Exception:
                        pass
        # Sort by updated_at descending
        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Loads a specific chat session."""
        filepath = os.path.join(CHATS_DIR, f"{session_id}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def add_interaction(self, session_id: str, user_query: str, ai_answer: str, sources: List[Dict[str, Any]]):
        """Appends a single Q&A pair to the session history."""
        data = self.get_session(session_id)
        if not data:
            data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "history": []
            }
            
        data["history"].append({
            "user_query": user_query,
            "ai_answer": ai_answer,
            "sources": sources,
            "timestamp": datetime.now().isoformat()
        })
        data["updated_at"] = datetime.now().isoformat()
        self._save(session_id, data)

    def _save(self, session_id: str, data: Dict[str, Any]):
        filepath = os.path.join(CHATS_DIR, f"{session_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def delete_session(self, session_id: str) -> bool:
        """Deletes a chat session file."""
        filepath = os.path.join(CHATS_DIR, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
