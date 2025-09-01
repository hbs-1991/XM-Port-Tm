"""
XML File Storage Service for AWS S3 integration

This service handles storage and retrieval of generated XML files in AWS S3
with secure download links, file validation, and retention policies.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile
import os

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from botocore.config import Config

from ..core.config import get_settings
from ..models.processing_job import ProcessingJob

logger = logging.getLogger(__name__)


class XMLStorageError(Exception):
    """Base exception for XML storage operations"""
    pass


class XMLStorageService:
    """
    Service for managing XML file storage in AWS S3
    
    Features:
    - Secure file upload with validation
    - Pre-signed download URLs with expiration
    - File size and format validation
    - Automatic cleanup and retention policies
    - Fallback to local storage in development
    """
    
    def __init__(self):
        """Initialize S3 storage service"""
        self.settings = get_settings()
        self._s3_client = None
        self._bucket_name = self.settings.AWS_S3_BUCKET
        
        # Storage configuration
        self.max_file_size = 50 * 1024 * 1024  # 50MB max XML file size
        self.download_link_expiry = 3600  # 1 hour default expiry
        self.retention_days = 30  # Keep files for 30 days
        
        # Initialize S3 client if configured
        if self._is_s3_configured():
            self._initialize_s3_client()
    
    def _is_s3_configured(self) -> bool:
        """Check if S3 is properly configured"""
        return all([
            self.settings.AWS_ACCESS_KEY_ID,
            self.settings.AWS_SECRET_ACCESS_KEY,
            self.settings.AWS_S3_BUCKET,
            self.settings.AWS_REGION
        ])
    
    def _initialize_s3_client(self):
        """Initialize AWS S3 client with configuration"""
        try:
            # Configure S3 client with retry and timeout settings
            config = Config(
                region_name=self.settings.AWS_REGION,
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                },
                max_pool_connections=50
            )
            
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                config=config
            )
            
            # Verify bucket access
            self._verify_bucket_access()
            
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            if not self.settings.ALLOW_S3_FALLBACK:
                raise XMLStorageError(f"S3 initialization failed: {str(e)}")
    
    def _verify_bucket_access(self):
        """Verify that we can access the S3 bucket"""
        try:
            self._s3_client.head_bucket(Bucket=self._bucket_name)
            logger.info(f"S3 bucket '{self._bucket_name}' is accessible")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise XMLStorageError(f"S3 bucket '{self._bucket_name}' not found")
            elif error_code == '403':
                raise XMLStorageError(f"Access denied to S3 bucket '{self._bucket_name}'")
            else:
                raise XMLStorageError(f"S3 bucket verification failed: {str(e)}")
    
    def _generate_s3_key(self, processing_job: ProcessingJob, file_extension: str = "xml") -> str:
        """
        Generate S3 object key for XML file
        
        Args:
            processing_job: ProcessingJob instance
            file_extension: File extension (default: xml)
        
        Returns:
            S3 object key
        """
        # Create hierarchical key structure: year/month/user_id/job_id.xml
        created_at = processing_job.created_at
        year = created_at.strftime("%Y")
        month = created_at.strftime("%m")
        
        return f"xml-exports/{year}/{month}/{processing_job.user_id}/{processing_job.id}.{file_extension}"
    
    def _validate_xml_content(self, xml_content: str) -> Dict[str, Any]:
        """
        Validate XML content before storage
        
        Args:
            xml_content: XML content string
        
        Returns:
            Validation result dictionary
        """
        validation_result = {
            'is_valid': True,
            'file_size': 0,
            'encoding': 'utf-8',
            'errors': []
        }
        
        try:
            # Check content size
            xml_bytes = xml_content.encode('utf-8')
            file_size = len(xml_bytes)
            validation_result['file_size'] = file_size
            
            if file_size > self.max_file_size:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"File size {file_size} exceeds maximum {self.max_file_size} bytes"
                )
            
            # Basic XML structure validation
            if not xml_content.strip().startswith('<?xml'):
                validation_result['errors'].append("Missing XML declaration")
            
            if not xml_content.strip().endswith('>'):
                validation_result['errors'].append("Incomplete XML structure")
            
            # Check for required ASYCUDA elements (basic validation)
            required_elements = ['ASYCUDA', 'Consignment', 'Item']
            for element in required_elements:
                if f'<{element}' not in xml_content:
                    validation_result['errors'].append(f"Missing required element: {element}")
            
            if validation_result['errors']:
                validation_result['is_valid'] = False
                
        except UnicodeEncodeError as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Encoding error: {str(e)}")
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    async def upload_xml_file(
        self, 
        processing_job: ProcessingJob, 
        xml_content: str
    ) -> Dict[str, Any]:
        """
        Upload XML file to S3 storage
        
        Args:
            processing_job: ProcessingJob instance
            xml_content: Generated XML content
        
        Returns:
            Upload result with S3 URL and metadata
        """
        try:
            # Validate XML content first
            validation = self._validate_xml_content(xml_content)
            if not validation['is_valid']:
                raise XMLStorageError(f"XML validation failed: {validation['errors']}")
            
            if not self._is_s3_configured() or self._s3_client is None:
                # Fallback to local storage in development
                return await self._store_locally(processing_job, xml_content, validation)
            
            # Generate S3 key
            s3_key = self._generate_s3_key(processing_job)
            
            # Prepare metadata
            metadata = {
                'job-id': str(processing_job.id),
                'user-id': str(processing_job.user_id),
                'country-schema': processing_job.country_schema,
                'total-products': str(processing_job.total_products),
                'generated-at': datetime.now(timezone.utc).isoformat(),
                'file-size': str(validation['file_size']),
                'content-type': 'application/xml'
            }
            
            # Upload to S3
            upload_result = self._s3_client.put_object(
                Bucket=self._bucket_name,
                Key=s3_key,
                Body=xml_content.encode('utf-8'),
                ContentType='application/xml',
                ContentEncoding='utf-8',
                Metadata=metadata,
                ServerSideEncryption='AES256',  # Server-side encryption
                StorageClass='STANDARD_IA'  # Infrequent access for cost optimization
            )
            
            # Generate S3 URL
            s3_url = f"https://{self._bucket_name}.s3.{self.settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            logger.info(f"XML file uploaded to S3: {s3_key}")
            
            return {
                'success': True,
                'url': s3_url,
                's3_key': s3_key,
                'file_size': validation['file_size'],
                'uploaded_at': datetime.now(timezone.utc),
                'storage_type': 's3',
                'etag': upload_result.get('ETag', '').strip('"')
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 upload failed: {error_code} - {str(e)}")
            
            if self.settings.ALLOW_S3_FALLBACK:
                logger.info("Falling back to local storage")
                return await self._store_locally(processing_job, xml_content, validation)
            else:
                raise XMLStorageError(f"S3 upload failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"XML upload error: {str(e)}")
            raise XMLStorageError(f"Failed to upload XML file: {str(e)}")
    
    async def _store_locally(
        self, 
        processing_job: ProcessingJob, 
        xml_content: str, 
        validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback storage to local filesystem
        
        Args:
            processing_job: ProcessingJob instance
            xml_content: XML content to store
            validation: Validation result
        
        Returns:
            Local storage result
        """
        try:
            # Create local storage directory
            local_dir = Path("./uploads/xml-exports")
            local_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate local filename
            filename = f"{processing_job.id}.xml"
            file_path = local_dir / filename
            
            # Write XML content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            # Generate local URL (for development)
            local_url = f"/uploads/xml-exports/{filename}"
            
            logger.info(f"XML file stored locally: {file_path}")
            
            return {
                'success': True,
                'url': local_url,
                'file_path': str(file_path),
                'file_size': validation['file_size'],
                'uploaded_at': datetime.now(timezone.utc),
                'storage_type': 'local'
            }
            
        except Exception as e:
            logger.error(f"Local storage failed: {str(e)}")
            raise XMLStorageError(f"Failed to store XML file locally: {str(e)}")
    
    def generate_download_url(
        self, 
        s3_key: str, 
        expiry_seconds: Optional[int] = None
    ) -> str:
        """
        Generate secure pre-signed download URL
        
        Args:
            s3_key: S3 object key
            expiry_seconds: URL expiry time (default: 1 hour)
        
        Returns:
            Pre-signed download URL
        """
        if not self._is_s3_configured() or self._s3_client is None:
            # For local storage, return direct path
            filename = Path(s3_key).name
            return f"/uploads/xml-exports/{filename}"
        
        try:
            expiry = expiry_seconds or self.download_link_expiry
            
            url = self._s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self._bucket_name,
                    'Key': s3_key,
                    'ResponseContentType': 'application/xml',
                    'ResponseContentDisposition': f'attachment; filename="{Path(s3_key).name}"'
                },
                ExpiresIn=expiry
            )
            
            logger.info(f"Generated download URL for {s3_key}, expires in {expiry}s")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            raise XMLStorageError(f"Failed to generate download URL: {str(e)}")
    
    def delete_xml_file(self, s3_key: str) -> bool:
        """
        Delete XML file from storage
        
        Args:
            s3_key: S3 object key or local file path
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._is_s3_configured() or self._s3_client is None:
                # Delete local file
                local_path = Path("./uploads/xml-exports") / Path(s3_key).name
                if local_path.exists():
                    local_path.unlink()
                    logger.info(f"Deleted local file: {local_path}")
                    return True
                return False
            
            # Delete from S3
            self._s3_client.delete_object(
                Bucket=self._bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Deleted S3 object: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {s3_key}: {str(e)}")
            return False
    
    def cleanup_expired_files(self, retention_days: Optional[int] = None) -> int:
        """
        Clean up expired XML files based on retention policy
        
        Args:
            retention_days: Number of days to retain files (default: 30)
        
        Returns:
            Number of files deleted
        """
        retention = retention_days or self.retention_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention)
        deleted_count = 0
        
        try:
            if not self._is_s3_configured() or self._s3_client is None:
                # Cleanup local files
                local_dir = Path("./uploads/xml-exports")
                if local_dir.exists():
                    for file_path in local_dir.glob("*.xml"):
                        if file_path.stat().st_mtime < cutoff_date.timestamp():
                            file_path.unlink()
                            deleted_count += 1
                            logger.info(f"Deleted expired local file: {file_path}")
                return deleted_count
            
            # Cleanup S3 files
            paginator = self._s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self._bucket_name, Prefix='xml-exports/'):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['LastModified'] < cutoff_date:
                            self._s3_client.delete_object(
                                Bucket=self._bucket_name,
                                Key=obj['Key']
                            )
                            deleted_count += 1
                            logger.info(f"Deleted expired S3 file: {obj['Key']}")
            
            logger.info(f"Cleanup completed: {deleted_count} files deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return deleted_count
    
    def get_file_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get information about stored XML file
        
        Args:
            s3_key: S3 object key
        
        Returns:
            File information dictionary or None if not found
        """
        try:
            if not self._is_s3_configured() or self._s3_client is None:
                # Get local file info
                local_path = Path("./uploads/xml-exports") / Path(s3_key).name
                if local_path.exists():
                    stat = local_path.stat()
                    return {
                        'size': stat.st_size,
                        'last_modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                        'storage_type': 'local',
                        'path': str(local_path)
                    }
                return None
            
            # Get S3 object info
            response = self._s3_client.head_object(
                Bucket=self._bucket_name,
                Key=s3_key
            )
            
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType', 'application/xml'),
                'metadata': response.get('Metadata', {}),
                'storage_type': 's3',
                'etag': response.get('ETag', '').strip('"')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            logger.error(f"Failed to get file info for {s3_key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to get file info for {s3_key}: {str(e)}")
            return None


# Service instance
xml_storage_service = XMLStorageService()