import sys
import os
sys.path.append('.')
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from config import QDRANT_HOST, QDRANT_PORT

# User's Cloud Credentials
CLOUD_URL = "https://ce7d262c-8bb2-4584-833b-1eca3f512f71.us-east-1-1.aws.cloud.qdrant.io"
CLOUD_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6Y2Q4ZTk2M2UtOGRmYy00ZjdlLWExODUtNGZlN2JkZTE2MTMwIn0.MmSCoWY_cCUMsvAFj0lL_Eizvwb8i0mX-8ciHMQGWTE"

local_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=60.0)
cloud_client = QdrantClient(url=CLOUD_URL, api_key=CLOUD_API_KEY, timeout=60.0)

print("Starting migration...")

try:
    collections = local_client.get_collections().collections
    for c in collections:
        c_name = c.name
        print(f"\nMigrating collection: {c_name}")
        
        # Get collection details
        col_info = local_client.get_collection(c_name)
        
        # Create collection in cloud if it doesn't exist
        try:
            cloud_client.get_collection(c_name)
            print("Collection already exists in cloud.")
        except Exception:
            print("Creating collection in cloud...")
            cloud_client.create_collection(
                collection_name=c_name,
                vectors_config=col_info.config.params.vectors,
                sparse_vectors_config=col_info.config.params.sparse_vectors
            )
            
        # Scroll and copy
        offset = None
        count = 0
        while True:
            results, next_offset = local_client.scroll(
                collection_name=c_name,
                limit=50,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )
            
            if not results:
                break
                
            points = [
                PointStruct(
                    id=pt.id,
                    vector=pt.vector,
                    payload=pt.payload
                ) for pt in results
            ]
            
            import time
            for attempt in range(3):
                try:
                    cloud_client.upsert(
                        collection_name=c_name,
                        points=points,
                        wait=False
                    )
                    break
                except Exception as e:
                    print(f" Warning: Upsert failed, retrying ({attempt+1}/3): {e}")
                    time.sleep(2)
            
            count += len(points)
            print(f"\rCopied {count} points...", end="")
            
            if next_offset is None:
                break
            offset = next_offset
            
        print(f"\nFinished {c_name}!")
        
    print("\nMigration complete!")
except Exception as e:
    print(f"\nError during migration: {e}")
