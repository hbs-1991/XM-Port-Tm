"""
Storage service for handling file uploads to S3 and local storage
"""
from pathlib import Path
import logging
from typing import Optional

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import HTTPException, UploadFile

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageService:
    """Service for managing file storage operations"""
    
    def __init__(self):
        self.s3_client = None
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
    
    async def upload_file_to_s3(self, file: UploadFile, user_id: str) -> str:
        """Upload file to S3 and return the URL"""
        if not self.s3_client:
            raise HTTPException(
                status_code=500, 
                detail="S3 configuration not available"
            )
        
        try:
            # Generate unique file key
            file_ext = Path(file.filename).suffix
            file_key = f"uploads/{user_id}/{file.filename}_{hash(file.filename)}_{file.size}{file_ext}"
            
            # Upload file to S3
            await file.seek(0)  # Reset file pointer
            content = await file.read()
            
            self.s3_client.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=file_key,
                Body=content,
                ContentType=file.content_type,
                ServerSideEncryption='AES256'
            )
            
            # Return S3 URL
            return f"s3://{settings.AWS_S3_BUCKET}/{file_key}"
            
        except NoCredentialsError as e:
            raise HTTPException(
                status_code=500,
                detail=f"AWS credentials not configured: {str(e)}"
            )
        except ClientError as e:
            # Extract the error code from boto3 ClientError
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Create a detailed error message that includes the error code
            detailed_error = f"S3 upload failed: {error_code} - {error_message}"
            
            raise HTTPException(
                status_code=500,
                detail=detailed_error
            )
        except Exception as e:
            # Catch any other AWS/boto3 related errors
            if 'botocore' in str(type(e)).lower() or 'aws' in str(e).lower():
                raise HTTPException(
                    status_code=500,
                    detail=f"S3 upload failed: {str(e)}"
                )
            else:
                # Re-raise non-AWS errors
                raise
    
    async def handle_s3_fallback(
        self, 
        error: HTTPException, 
        file: UploadFile, 
        user_id: str
    ) -> Optional[str]:
        """
        Handle S3 upload failures with local storage fallback
        
        Args:
            error: The HTTPException from S3 upload attempt
            file: The file to upload
            user_id: User ID for organizing files
            
        Returns:
            Local file URL if fallback is allowed, None otherwise
        """
        error_detail_str = str(error.detail)
        s3_error_indicators = [
            "S3 configuration not available",
            "AWS credentials not configured", 
            "S3 upload failed",
            "InvalidAccessKeyId",
            "AccessDenied",
            "NoSuchBucket",
            "NoCredentialsError",
            "CredentialsError",
            "BotoCoreError",
            "EndpointConnectionError"
        ]
        
        # More robust S3 error detection
        is_s3_error = (
            any(indicator in error_detail_str for indicator in s3_error_indicators) or
            "S3 upload failed:" in error_detail_str or
            error.status_code == 500 and "S3" in error_detail_str
        )
        
        if (is_s3_error and 
            settings.ALLOW_S3_FALLBACK and 
            not settings.is_production):
            # Development fallback to local storage - NOT production ready
            file_url = f"local://uploads/{user_id}/{file.filename}"
            logger.warning(
                f"Using local storage fallback for file upload. "
                f"S3 Error: {error_detail_str}. File: {file.filename}, User: {user_id}. "
                f"This is not suitable for production use."
            )
            return file_url
        
        return None
    
    def get_file_url(self, file_key: str) -> str:
        """
        Generate a URL for accessing a stored file
        
        Args:
            file_key: The S3 key or local path of the file
            
        Returns:
            URL for accessing the file
        """
        if file_key.startswith("s3://"):
            # Generate presigned URL for S3 files
            if self.s3_client:
                try:
                    bucket_and_key = file_key.replace("s3://", "")
                    bucket, key = bucket_and_key.split("/", 1)
                    
                    url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=3600  # URL expires in 1 hour
                    )
                    return url
                except Exception as e:
                    logger.error(f"Error generating presigned URL: {str(e)}")
                    return file_key
            return file_key
        elif file_key.startswith("local://"):
            # For local files, return a relative URL
            return file_key.replace("local://", "/static/")
        else:
            return file_key
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            file_url: The URL of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            if file_url.startswith("s3://"):
                if not self.s3_client:
                    return False
                
                # Extract bucket and key from URL
                bucket_and_key = file_url.replace("s3://", "")
                bucket, key = bucket_and_key.split("/", 1)
                
                self.s3_client.delete_object(Bucket=bucket, Key=key)
                return True
            elif file_url.startswith("local://"):
                # For local files, delete from filesystem
                file_path = Path(file_url.replace("local://", ""))
                if file_path.exists():
                    file_path.unlink()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_url}: {str(e)}")
            return False