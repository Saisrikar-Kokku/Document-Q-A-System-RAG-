import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from qdrant_client import QdrantClient
from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

try:
    points = client.scroll(
        collection_name=QDRANT_COLLECTION_NAME,
        limit=10000, # Large enough to fetch a sample of all chunks
        with_payload=True,
        with_vectors=False
    )[0]

    unique_files = set()
    for point in points:
        if "file_name" in point.payload:
            unique_files.add(point.payload["file_name"])
            
    print("FINISHED_FILES:")
    for f in sorted(list(unique_files)):
        print(f"- {f}")
except Exception as e:
    print(f"Error: {e}")
