import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from qdrant_client import QdrantClient
from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME, DATA_DIR
import pymupdf4llm
from rapidocr import RapidOCR

def get_qdrant_char_count(client, filename):
    try:
        points = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter={
                "must": [
                    {
                        "key": "file_name",
                        "match": {"value": filename}
                    }
                ]
            },
            limit=10000,
            with_payload=True,
            with_vectors=False
        )[0]
        
        total_chars = 0
        chunks = 0
        for p in points:
            if "text" in p.payload:
                total_chars += len(p.payload["text"])
                chunks += 1
        return total_chars, chunks
    except Exception as e:
        return 0, 0

def get_raw_char_count(filename):
    file_path = Path(DATA_DIR) / filename
    try:
        md_pages = pymupdf4llm.to_markdown(str(file_path.absolute()), page_chunks=True)
        total_text = ""
        for page in md_pages:
            total_text += page.get("text", "")
        return len(total_text)
    except Exception as e:
        return -1

def main():
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    files_to_check = [
        "(OBC) CERTIFICATE.pdf",
        "10TH MEMO.pdf",
        "10TH MIGRATION.pdf",
        "ABC ID.pdf",
        "ADDHAR CARD.pdf",
        "Atomic Habits.pdf",
        "C Programming Notes - CodeHype.pdf"
    ]
    
    print(f"{'Filename':<35} | {'Raw Chars':<10} | {'DB Chars':<10} | {'Chunks':<8} | {'Status'}")
    print("-" * 80)
    
    for f in files_to_check:
        raw_chars = get_raw_char_count(f)
        db_chars, chunks = get_qdrant_char_count(client, f)
        
        # We expect DB chars to be slightly HIGHER than raw chars because
        # our semantic chunker uses chunk overlap (10-20% duplication between chunks).
        status = "✅ OK"
        if db_chars < raw_chars * 0.9: # Give a 10% tolerance for stripped whitespace or bad chars
            status = "❌ MISSING DATA"
            
        print(f"{f[:33]:<35} | {raw_chars:<10} | {db_chars:<10} | {chunks:<8} | {status}")

if __name__ == "__main__":
    main()
