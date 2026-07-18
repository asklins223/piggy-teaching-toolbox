"""Tencent Cloud COS client.

This module provides COS upload/download functionality.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, BinaryIO

from qcloud_cos import CosConfig, CosS3Client

from backend.db.models import get_cos_config, COSConfig


_cos_client: Optional[CosS3Client] = None


def get_cos_client() -> Optional[CosS3Client]:
    """Get COS client instance."""
    global _cos_client
    
    config = get_cos_config()
    if not config.secret_id or not config.secret_key or not config.bucket:
        return None
    
    if _cos_client is None:
        cos_config = CosConfig(
            Region=config.region,
            SecretId=config.secret_id,
            SecretKey=config.secret_key,
        )
        _cos_client = CosS3Client(cos_config)
    
    return _cos_client


# Re-export for convenience
def get_cos_config_info() -> COSConfig:
    """Get COS config (re-export for external use)."""
    return get_cos_config()


def upload_file(
    file_data: bytes,
    filename: str,
    folder: str = "voices",
    content_type: str = "audio/mpeg"
) -> Optional[dict]:
    """Upload file to COS.
    
    Args:
        file_data: File binary data.
        filename: Original filename.
        folder: COS folder path.
        content_type: File content type.
        
    Returns:
        Dict with cos_key and cos_url, or None if failed.
    """
    client = get_cos_client()
    config = get_cos_config()
    
    if not client:
        print(f"COS upload error: COS client not initialized. Check COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET config.")
        return None
    
    if not config.bucket:
        print(f"COS upload error: COS_BUCKET not configured")
        return None
    
    # Generate unique key
    ext = Path(filename).suffix or ".mp3"
    date_path = datetime.now().strftime("%Y/%m/%d")
    unique_id = uuid.uuid4().hex[:12]
    cos_key = f"{folder}/{date_path}/{unique_id}{ext}"
    
    try:
        print(f"COS uploading: bucket={config.bucket}, key={cos_key}, size={len(file_data)} bytes")
        response = client.put_object(
            Bucket=config.bucket,
            Body=file_data,
            Key=cos_key,
            ContentType=content_type,
        )
        
        if response.get("ETag"):
            cos_url = f"{config.base_url}/{cos_key}"
            print(f"COS upload success: {cos_url}")
            return {
                "cos_key": cos_key,
                "cos_url": cos_url,
            }
        else:
            print(f"COS upload error: No ETag in response. Response: {response}")
    except Exception as e:
        print(f"COS upload error: {type(e).__name__}: {e}")
    
    return None


def delete_file(cos_key: str) -> bool:
    """Delete file from COS.
    
    Args:
        cos_key: COS object key.
        
    Returns:
        True if deleted successfully.
    """
    client = get_cos_client()
    config = get_cos_config()
    
    if not client or not cos_key:
        return False
    
    try:
        client.delete_object(
            Bucket=config.bucket,
            Key=cos_key,
        )
        return True
    except Exception as e:
        print(f"COS delete error: {e}")
        return False


def get_presigned_url(cos_key: str, expires: int = 3600) -> Optional[str]:
    """Get presigned URL for file.
    
    Args:
        cos_key: COS object key.
        expires: URL expiration time in seconds.
        
    Returns:
        Presigned URL or None.
    """
    client = get_cos_client()
    config = get_cos_config()
    
    if not client or not cos_key:
        return None
    
    try:
        url = client.get_presigned_url(
            Method="GET",
            Bucket=config.bucket,
            Key=cos_key,
            Expired=expires,
        )
        return url
    except Exception as e:
        print(f"COS presigned URL error: {e}")
        return None


def copy_object(source_key: str, dest_key: str) -> Optional[str]:
    """Copy object within COS bucket.
    
    Args:
        source_key: Source object key (can be full URL or key).
        dest_key: Destination object key.
        
    Returns:
        New COS URL or None if failed.
    """
    client = get_cos_client()
    config = get_cos_config()
    
    if not client:
        return None
    
    # Extract key from URL if needed
    if source_key.startswith("http"):
        # Extract key from URL like https://bucket.cos.region.myqcloud.com/path/to/file
        try:
            from urllib.parse import urlparse
            parsed = urlparse(source_key)
            source_key = parsed.path.lstrip("/")
        except Exception:
            return None
    
    try:
        copy_source = {
            "Bucket": config.bucket,
            "Key": source_key,
            "Region": config.region,
        }
        response = client.copy_object(
            Bucket=config.bucket,
            Key=dest_key,
            CopySource=copy_source,
        )
        if response.get("ETag"):
            return f"{config.base_url}/{dest_key}"
    except Exception as e:
        print(f"COS copy error: {e}")
    
    return None


def upload_text(
    content: str,
    dest_key: str,
    content_type: str = "text/plain; charset=utf-8"
) -> Optional[str]:
    """Upload text content directly to COS.
    
    Args:
        content: Text content.
        dest_key: Destination key.
        content_type: Content type.
        
    Returns:
        COS URL or None.
    """
    client = get_cos_client()
    config = get_cos_config()
    
    if not client:
        return None
    
    try:
        response = client.put_object(
            Bucket=config.bucket,
            Body=content.encode("utf-8"),
            Key=dest_key,
            ContentType=content_type,
        )
        if response.get("ETag"):
            return f"{config.base_url}/{dest_key}"
    except Exception as e:
        print(f"COS upload text error: {e}")
    
    return None
