import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vectorstore.qdrant_store import QdrantStore
from qdrant_client.http import models

def main():
    store = QdrantStore()
    file_to_delete = "DBMS Notes - CodeHype.pdf"
    
    print(f"Deleting all points where file_name == '{file_to_delete}'...")
    try:
        store.client.delete(
            collection_name=store.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_name",
                            match=models.MatchValue(value=file_to_delete),
                        ),
                    ],
                )
            ),
        )
        print(f"Successfully sent delete command for {file_to_delete}")
    except Exception as e:
        print(f"Error deleting: {e}")

if __name__ == "__main__":
    main()
