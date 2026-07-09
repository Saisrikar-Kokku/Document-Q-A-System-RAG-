import os
import sys
from pathlib import Path

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage.s3_client import S3Client
from config import DATA_DIR

def sync_local_to_r2():
    s3_client = S3Client()
    if not s3_client.client:
        print("Error: R2 Client not initialized.")
        return

    print("Scanning local data directory...")
    base_dir = Path(DATA_DIR)
    
    files_to_upload = []
    
    for root, _, filenames in os.walk(DATA_DIR):
        for f in filenames:
            # We don't want to upload internal files like .ingestion_index.json if they exist in data/
            if f.startswith('.'):
                continue
                
            full_path = Path(root) / f
            rel_path = full_path.relative_to(base_dir)
            
            # Use forward slashes for R2 keys
            key = str(rel_path).replace("\\", "/")
            files_to_upload.append((str(full_path), key))
            
    print(f"Found {len(files_to_upload)} files to sync to Cloudflare R2.")
    
    success_count = 0
    for file_path, key in files_to_upload:
        print(f"Uploading {key}...", end=" ")
        if s3_client.upload_file(file_path, key):
            print("OK")
            success_count += 1
        else:
            print("FAILED")
            
    print(f"\nSync complete! Successfully uploaded {success_count} out of {len(files_to_upload)} files to R2.")

if __name__ == "__main__":
    sync_local_to_r2()
