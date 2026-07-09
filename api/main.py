"""
main.py — The FastAPI Server
============================

WHAT THIS FILE DOES:
    Creates a web server with endpoints: `/ingest`, `/query`, `/query_stream`, and `/upload`.
    It initializes all our backend components (Embedder, Qdrant, LLM, Pipeline, Indexer)
    and attaches them to the web routes.
    It also serves the Web UI from the `ui/web` directory.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import shutil
import os
from pathlib import Path

from embeddings.embedder import Embedder, SparseEmbedder
from vectorstore.qdrant_store import QdrantStore
from retrieval.retriever import Retriever
from retrieval.reranker import Reranker
from tools.web_search import WebSearcher
from generation.ollama_llm import OllamaLLM
from generation.cloud_llm import CloudLLM
from generation.groq_llm import GroqLLM
from pipeline.rag_pipeline import RAGPipeline
from indexer.change_tracker import Indexer
from storage.chat_store import ChatStore
from storage.s3_client import S3Client
from config import LLM_PROVIDER, DATA_DIR

# 1. Initialize the FastAPI app
app = FastAPI(
    title="Personal RAG API",
    description="A production-grade RAG pipeline running locally.",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Global variables to hold our heavy backend components.
components = {}
is_ingesting = False
ingestion_progress = ""

@app.on_event("startup")
async def startup_event():
    print("Starting up RAG backend...")
    
    embedder = Embedder()
    sparse_embedder = SparseEmbedder()
    qdrant_store = QdrantStore()
    components["qdrant_store"] = qdrant_store
    
    s3_client = S3Client()
    components["s3_client"] = s3_client
    retriever = Retriever(embedder, sparse_embedder, qdrant_store)
    
    if LLM_PROVIDER == "cloud":
        llm = CloudLLM()
    elif LLM_PROVIDER == "groq":
        llm = GroqLLM()
    else:
        llm = OllamaLLM()
        
    reranker = Reranker()
    web_searcher = WebSearcher()
    chat_store = ChatStore()
    pipeline = RAGPipeline(retriever, reranker, web_searcher, llm, chat_store, embedder, sparse_embedder, qdrant_store)
    indexer = Indexer(embedder, sparse_embedder, qdrant_store)
    
    components["pipeline"] = pipeline
    components["indexer"] = indexer
    components["chat_store"] = chat_store
    print("Startup complete. API is ready.")

# 3. Define the input schemas for our API endpoints
class QueryRequest(BaseModel):
    query: str
    file_type_filter: Optional[str] = None
    file_name_filter: Optional[str] = None
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

class IngestResponse(BaseModel):
    status: str
    processed: int
    skipped: int
    failed: int

# 4. Define the API Routes

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    pipeline = components.get("pipeline")
    if not pipeline:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
        
    try:
        result = pipeline.answer_question(
            query=request.query, 
            file_type_filter=request.file_type_filter,
            file_name_filter=request.file_name_filter,
            session_id=request.session_id
        )
        return QueryResponse(answer=result["answer"], sources=result["sources"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query_stream")
async def query_rag_stream(request: QueryRequest):
    """
    Streaming endpoint that returns Server-Sent Events (SSE) detailing the 
    internal thought process before returning the final answer.
    """
    pipeline = components.get("pipeline")
    if not pipeline:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
        
    return StreamingResponse(
        pipeline.answer_question_stream(
            query=request.query, 
            file_type_filter=request.file_type_filter,
            file_name_filter=request.file_name_filter,
            session_id=request.session_id
        ),
        media_type="text/event-stream"
    )

@app.post("/ingest", response_model=IngestResponse)
async def trigger_ingestion(background_tasks: BackgroundTasks):
    indexer: Indexer = components.get("indexer")
    if not indexer:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
        
    def run_ingestion():
        global is_ingesting, ingestion_progress
        is_ingesting = True
        ingestion_progress = "Starting ingestion..."
        
        def progress_cb(msg):
            global ingestion_progress
            ingestion_progress = msg
            
        try:
            indexer.ingest_all(progress_callback=progress_cb)
        finally:
            is_ingesting = False
            ingestion_progress = ""
        
    background_tasks.add_task(run_ingestion)
    
    return IngestResponse(
        status="Ingestion started in the background. Check terminal for progress.",
        processed=0,
        skipped=0,
        failed=0
    )

@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    category: Optional[str] = Form(None)
):
    """
    Uploads a file to the data/ directory (optionally within a category subfolder) 
    and triggers ingestion.
    """
    indexer: Indexer = components.get("indexer")
    if not indexer:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")

    s3_client: S3Client = components.get("s3_client")
    if not s3_client:
        raise HTTPException(status_code=503, detail="S3 Client not initialized.")

    # Temporarily save the file
    save_dir = Path(DATA_DIR) / "temp"
    os.makedirs(save_dir, exist_ok=True)
    temp_path = save_dir / file.filename
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    object_name = file.filename
    if category and category.strip():
        safe_category = "".join([c for c in category if c.isalpha() or c.isdigit() or c==' ']).strip()
        object_name = f"{safe_category}/{file.filename}"
        
    # Upload to R2
    s3_client.upload_file(str(temp_path), object_name)
    
    # Delete temp file
    os.remove(temp_path)
        
    # Trigger ingestion automatically in the background
    def run_ingestion():
        global is_ingesting, ingestion_progress
        is_ingesting = True
        ingestion_progress = "Starting ingestion..."
        
        def progress_cb(msg):
            global ingestion_progress
            ingestion_progress = msg
            
        try:
            indexer.ingest_all(progress_callback=progress_cb)
        finally:
            is_ingesting = False
            ingestion_progress = ""
            
    background_tasks.add_task(run_ingestion)
    
    return {"status": f"Successfully uploaded {file.filename} and started ingestion."}

@app.get("/ingest/status")
async def get_ingest_status():
    global is_ingesting, ingestion_progress
    return {"is_ingesting": is_ingesting, "progress": ingestion_progress}

@app.post("/chat/session")
async def create_chat_session():
    chat_store: ChatStore = components.get("chat_store")
    if not chat_store:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
    session_id = chat_store.create_session()
    return {"session_id": session_id}

@app.get("/chat/sessions")
async def list_chat_sessions():
    chat_store: ChatStore = components.get("chat_store")
    if not chat_store:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
    return {"sessions": chat_store.list_sessions()}

@app.get("/chat/session/{session_id}")
async def get_chat_session(session_id: str):
    chat_store: ChatStore = components.get("chat_store")
    if not chat_store:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
    session = chat_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session

@app.delete("/chat/session/{session_id}")
async def delete_chat_session(session_id: str):
    chat_store: ChatStore = components.get("chat_store")
    if not chat_store:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
    success = chat_store.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "success"}

@app.get("/files")
async def list_files():
    """
    Returns a list of all files currently in the R2 bucket.
    """
    s3_client: S3Client = components.get("s3_client")
    if not s3_client:
        return {"files": [], "folders": []}
        
    keys = s3_client.list_files()
    files = []
    folders = set()
    
    for key in keys:
        parts = key.split('/')
        if len(parts) > 1:
            category = parts[0]
            folders.add(category)
            filename = parts[-1]
        else:
            category = "Uncategorized"
            filename = key
            
        files.append({"name": filename, "size": "Cloud", "category": category, "key": key})
            
    return {"files": files, "folders": list(folders)}

class FolderRequest(BaseModel):
    name: str

@app.post("/folders")
async def create_folder(req: FolderRequest):
    # Cloudflare R2 / S3 doesn't have true folders. 
    # It creates folders implicitly when a file has a prefix (e.g. 'folder/file.pdf').
    # We can simulate creating a folder by creating an empty object with a trailing slash,
    # but since our list_files already checks for prefixes, we can just return success 
    # and the frontend will allow the user to select this category when uploading.
    # We don't actually need to write anything to R2 right now.
    safe_name = "".join([c for c in req.name if c.isalpha() or c.isdigit() or c==' ']).strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid folder name")
    
    return {"status": "success", "folder": safe_name}

class MoveRequest(BaseModel):
    filename: str
    target_folder: str

@app.put("/files/move")
async def move_file(req: MoveRequest):
    indexer: Indexer = components.get("indexer")
    s3_client: S3Client = components.get("s3_client")
    if not indexer or not s3_client:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
        
    keys = s3_client.list_files()
    old_key = None
    for key in keys:
        if key.endswith(req.filename):
            old_key = key
            break
            
    if not old_key:
        raise HTTPException(status_code=404, detail="File not found")
        
    if req.target_folder == "Uncategorized":
        new_key = req.filename
    else:
        safe_category = "".join([c for c in req.target_folder if c.isalpha() or c.isdigit() or c==' ']).strip()
        new_key = f"{safe_category}/{req.filename}"
        
    if new_key in keys and new_key != old_key:
        raise HTTPException(status_code=400, detail="File already exists in target folder")
        
    if new_key != old_key:
        # Rename in R2
        success = s3_client.rename_file(old_key, new_key)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to move file in Cloudflare R2")
        
        # Update ingestion index so it doesn't get re-ingested
        index_data = indexer._load_index()
        if old_key in index_data:
            index_data[new_key] = index_data[old_key]
            del index_data[old_key]
            indexer._save_index(index_data)
            
        # Update Qdrant metadata so the source points to the new key
        # Qdrant allows updating payloads
        try:
            indexer.qdrant_store.update_source_metadata(old_key, new_key)
        except Exception as e:
            print(f"Warning: Failed to update Qdrant payload: {e}")
            
    return {"status": "success"}

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """
    Deletes a file from R2, removes its vectors from Qdrant, 
    and removes it from the ingestion index.
    """
    indexer: Indexer = components.get("indexer")
    s3_client: S3Client = components.get("s3_client")
    if not indexer or not s3_client:
        raise HTTPException(status_code=503, detail="Backend not initialized yet.")
        
    # Find the object key in R2 since the frontend just passes filename
    keys = s3_client.list_files()
    target_key = None
    for key in keys:
        if key.endswith(filename):
            target_key = key
            break
            
    if target_key:
        s3_client.delete_file(target_key)
        
    # 1. Delete from Qdrant
    indexer.qdrant_store.delete_by_filename(filename)
        
    # 3. Delete from ingestion index
    index_data = indexer._load_index()
    if target_key and target_key in index_data:
        del index_data[target_key]
        indexer._save_index(index_data)
        
    return {"status": f"Successfully deleted {filename}"}

# 5. Serve the Static Web UI and Files
# We mount this last so the API routes take precedence

data_dir = Path(__file__).parent.parent / "data"
os.makedirs(data_dir, exist_ok=True)
from fastapi.responses import FileResponse

@app.get("/files/{file_path:path}")
async def serve_file(file_path: str):
    """
    Serves a file from the DATA_DIR.
    If the file is not found at the exact path, it searches recursively
    through all subdirectories to find a file with a matching name.
    """
    # 1. Try direct path first
    direct_path = data_dir / file_path
    if direct_path.exists() and direct_path.is_file():
        return FileResponse(str(direct_path))
        
    # 2. Search recursively if not found
    target_name = Path(file_path).name
    for root, dirs, files in os.walk(data_dir):
        if target_name in files:
            found_path = Path(root) / target_name
            return FileResponse(str(found_path))
            
    # 3. Not found anywhere
    raise HTTPException(status_code=404, detail="Not Found")

ui_dir = Path(__file__).parent.parent / "ui" / "web"
os.makedirs(ui_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="web")

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
