import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from qdrant_client import models
from vectorstore.qdrant_store import QdrantStore

def add_indices():
    store = QdrantStore()
    
    fields_to_index = ["file_name", "source_path", "file_type"]
    
    for field in fields_to_index:
        try:
            print(f"Creating payload index for {field} in {store.collection_name}...")
            store.client.create_payload_index(
                collection_name=store.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            print(f"Success for {field}.")
        except Exception as e:
            print(f"Skipped/Error for {field}: {e}")

if __name__ == "__main__":
    add_indices()
