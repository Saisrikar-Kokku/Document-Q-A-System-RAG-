import os
import boto3
from botocore.exceptions import ClientError
from config import R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME

class S3Client:
    """
    Wrapper for boto3 to interact with Cloudflare R2 (or any S3-compatible storage).
    """
    def __init__(self):
        self.bucket_name = R2_BUCKET_NAME
        
        # We only initialize the client if credentials exist
        if R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_ENDPOINT_URL:
            self.client = boto3.client(
                's3',
                endpoint_url=R2_ENDPOINT_URL,
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                region_name="auto" # Required by boto3, but ignored by R2
            )
        else:
            self.client = None
            print("Warning: R2 Credentials not found in environment.")

    def upload_file(self, file_path: str, object_name: str = None) -> bool:
        """Uploads a file to the R2 bucket."""
        if not self.client: return False
        
        if object_name is None:
            object_name = os.path.basename(file_path)
            
        try:
            self.client.upload_file(file_path, self.bucket_name, object_name)
            return True
        except ClientError as e:
            print(f"Failed to upload to R2: {e}")
            return False

    def download_file(self, object_name: str, file_path: str) -> bool:
        """Downloads a file from the R2 bucket."""
        if not self.client: return False
        
        try:
            self.client.download_file(self.bucket_name, object_name, file_path)
            return True
        except ClientError as e:
            print(f"Failed to download from R2: {e}")
            return False

    def list_files(self, prefix: str = "") -> list:
        """Lists files in the bucket, optionally filtering by prefix."""
        if not self.client: return []
        
        files = []
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append(obj['Key'])
            return files
        except ClientError as e:
            print(f"Failed to list files in R2: {e}")
            return []

    def list_files_with_hashes(self, prefix: str = "") -> dict:
        """Returns a dictionary mapping file keys to their ETags."""
        if not self.client: return {}
        
        files_dict = {}
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files_dict[obj['Key']] = obj.get('ETag', '').strip('"')
            return files_dict
        except ClientError as e:
            print(f"Failed to list files with hashes in R2: {e}")
            return {}

    def get_file_hash(self, object_name: str) -> str:
        """Gets the ETag (hash) of an object in R2."""
        if not self.client: return ""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=object_name)
            # ETags usually have quotes around them, e.g. '"hash"'
            etag = response.get('ETag', '').strip('"')
            return etag
        except ClientError:
            return ""

    def delete_file(self, object_name: str) -> bool:
        """Deletes a file from the R2 bucket."""
        if not self.client: return False
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            print(f"Failed to delete from R2: {e}")
            return False

    def rename_file(self, old_object_name: str, new_object_name: str) -> bool:
        """Renames a file in R2 by copying and deleting."""
        if not self.client: return False
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': old_object_name}
            self.client.copy_object(CopySource=copy_source, Bucket=self.bucket_name, Key=new_object_name)
            self.client.delete_object(Bucket=self.bucket_name, Key=old_object_name)
            return True
        except ClientError as e:
            print(f"Failed to rename in R2: {e}")
            return False
