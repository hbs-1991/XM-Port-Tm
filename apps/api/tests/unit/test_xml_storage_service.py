"""
Unit tests for XML Storage Service

Tests the XMLStorageService functionality including:
- S3 upload and download functionality
- Local storage fallback
- File validation and size checks
- Download URL generation
- Cleanup and retention policies
"""
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
from pathlib import Path
import uuid

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from moto import mock_s3

from src.services.xml_storage import XMLStorageService, XMLStorageError
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.user import User


class TestXMLStorageService:
    """Test cases for XMLStorageService"""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        with patch('src.services.xml_storage.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.AWS_ACCESS_KEY_ID = "test_access_key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test_secret_key"
            mock_settings.AWS_S3_BUCKET = "test-bucket"
            mock_settings.AWS_REGION = "us-west-2"
            mock_settings.ALLOW_S3_FALLBACK = True
            mock_get_settings.return_value = mock_settings
            yield mock_settings
    
    @pytest.fixture
    def processing_job(self):
        """Create a test processing job"""
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            full_name="Test User",
            credits_remaining=100
        )
        
        job = ProcessingJob(
            id=uuid.uuid4(),
            user_id=user.id,
            status=ProcessingStatus.PROCESSING,
            input_file_name="test_file.csv",
            input_file_url="s3://bucket/test_file.csv",
            input_file_size=1024,
            credits_used=0,
            total_products=10,
            successful_matches=8,
            country_schema="TKM",
            created_at=datetime.now(timezone.utc)
        )
        job.user = user
        return job
    
    @pytest.fixture
    def sample_xml_content(self):
        """Sample ASYCUDA XML content for testing"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<ASYCUDA xmlns="http://www.asycuda.org/2017/ASYCUDA">
    <Header>
        <Created_Date_Time>2024-01-01T10:00:00Z</Created_Date_Time>
        <Reference>TEST-12345</Reference>
    </Header>
    <Consignment>
        <Total_Number_of_Items>2</Total_Number_of_Items>
        <Total_Invoice_Amount>1000.00</Total_Invoice_Amount>
        <Currency_Code>USD</Currency_Code>
    </Consignment>
    <Item>
        <Item_Number>1</Item_Number>
        <Commodity_Code>123456</Commodity_Code>
        <Good_Description>Test Product 1</Good_Description>
        <Item_Invoice_Amount>500.00</Item_Invoice_Amount>
        <Country_of_Origin_Code>USA</Country_of_Origin_Code>
    </Item>
    <Item>
        <Item_Number>2</Item_Number>
        <Commodity_Code>789012</Commodity_Code>
        <Good_Description>Test Product 2</Good_Description>
        <Item_Invoice_Amount>500.00</Item_Invoice_Amount>
        <Country_of_Origin_Code>USA</Country_of_Origin_Code>
    </Item>
</ASYCUDA>'''
    
    def test_storage_service_initialization(self, mock_settings):
        """Test XMLStorageService initialization"""
        service = XMLStorageService()
        
        assert service.settings == mock_settings
        assert service.max_file_size == 50 * 1024 * 1024  # 50MB
        assert service.download_link_expiry == 3600  # 1 hour
        assert service.retention_days == 30
    
    def test_is_s3_configured_true(self, mock_settings):
        """Test S3 configuration check when properly configured"""
        service = XMLStorageService()
        assert service._is_s3_configured() is True
    
    def test_is_s3_configured_false(self, mock_settings):
        """Test S3 configuration check when missing credentials"""
        mock_settings.AWS_ACCESS_KEY_ID = ""
        service = XMLStorageService()
        assert service._is_s3_configured() is False
    
    def test_generate_s3_key(self, mock_settings, processing_job):
        """Test S3 key generation"""
        service = XMLStorageService()
        s3_key = service._generate_s3_key(processing_job)
        
        year = processing_job.created_at.strftime("%Y")
        month = processing_job.created_at.strftime("%m")
        expected_key = f"xml-exports/{year}/{month}/{processing_job.user_id}/{processing_job.id}.xml"
        
        assert s3_key == expected_key
    
    def test_validate_xml_content_valid(self, mock_settings, sample_xml_content):
        """Test XML content validation with valid content"""
        service = XMLStorageService()
        validation = service._validate_xml_content(sample_xml_content)
        
        assert validation['is_valid'] is True
        assert validation['file_size'] > 0
        assert validation['encoding'] == 'utf-8'
        assert len(validation['errors']) == 0
    
    def test_validate_xml_content_missing_declaration(self, mock_settings):
        """Test XML content validation with missing XML declaration"""
        service = XMLStorageService()
        invalid_xml = "<root>No declaration</root>"
        validation = service._validate_xml_content(invalid_xml)
        
        assert validation['is_valid'] is False
        assert "Missing XML declaration" in validation['errors']
    
    def test_validate_xml_content_missing_asycuda_elements(self, mock_settings):
        """Test XML content validation with missing required elements"""
        service = XMLStorageService()
        invalid_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<root>
    <header>Test</header>
</root>'''
        validation = service._validate_xml_content(invalid_xml)
        
        assert validation['is_valid'] is False
        error_messages = ' '.join(validation['errors'])
        assert "Missing required element: ASYCUDA" in error_messages
        assert "Missing required element: Consignment" in error_messages
        assert "Missing required element: Item" in error_messages
    
    def test_validate_xml_content_oversized(self, mock_settings):
        """Test XML content validation with oversized content"""
        service = XMLStorageService()
        service.max_file_size = 100  # Set very small limit for testing
        
        large_xml = "<?xml version='1.0'?>" + "x" * 200  # Content larger than limit
        validation = service._validate_xml_content(large_xml)
        
        assert validation['is_valid'] is False
        assert "exceeds maximum" in validation['errors'][0]
    
    @mock_s3
    @pytest.mark.asyncio
    async def test_upload_xml_file_s3_success(self, mock_settings, processing_job, sample_xml_content):
        """Test successful XML file upload to S3"""
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-west-2')
        s3_client.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        
        with patch.object(XMLStorageService, '_initialize_s3_client'):
            service = XMLStorageService()
            service._s3_client = s3_client
            
            result = await service.upload_xml_file(processing_job, sample_xml_content)
            
            assert result['success'] is True
            assert result['storage_type'] == 's3'
            assert result['file_size'] > 0
            assert 'url' in result
            assert 's3_key' in result
            assert 'etag' in result
            assert result['uploaded_at'] is not None
    
    @pytest.mark.asyncio
    async def test_upload_xml_file_local_fallback(self, mock_settings, processing_job, sample_xml_content):
        """Test XML file upload with local storage fallback"""
        mock_settings.AWS_ACCESS_KEY_ID = ""  # Disable S3
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.services.xml_storage.Path') as mock_path:
                mock_path.return_value = Path(temp_dir) / "uploads" / "xml-exports"
                mock_path.return_value.mkdir(parents=True, exist_ok=True)
                
                service = XMLStorageService()
                result = await service.upload_xml_file(processing_job, sample_xml_content)
                
                assert result['success'] is True
                assert result['storage_type'] == 'local'
                assert result['file_size'] > 0
                assert result['url'].startswith('/uploads/xml-exports/')
                assert 'file_path' in result
    
    @pytest.mark.asyncio
    async def test_upload_xml_file_validation_failure(self, mock_settings, processing_job):
        """Test XML file upload with validation failure"""
        service = XMLStorageService()
        invalid_xml = "Not valid XML content"
        
        with pytest.raises(XMLStorageError) as exc_info:
            await service.upload_xml_file(processing_job, invalid_xml)
        
        assert "XML validation failed" in str(exc_info.value)
    
    @mock_s3
    def test_generate_download_url_s3(self, mock_settings):
        """Test download URL generation for S3"""
        # Create mock S3 bucket and object
        s3_client = boto3.client('s3', region_name='us-west-2')
        s3_client.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        
        with patch.object(XMLStorageService, '_initialize_s3_client'):
            service = XMLStorageService()
            service._s3_client = s3_client
            
            s3_key = "xml-exports/2024/01/user123/job456.xml"
            url = service.generate_download_url(s3_key, expiry_seconds=3600)
            
            assert url is not None
            assert isinstance(url, str)
            assert len(url) > 0
    
    def test_generate_download_url_local(self, mock_settings):
        """Test download URL generation for local storage"""
        mock_settings.AWS_ACCESS_KEY_ID = ""  # Disable S3
        
        service = XMLStorageService()
        s3_key = "xml-exports/2024/01/user123/job456.xml"
        url = service.generate_download_url(s3_key)
        
        assert url == "/uploads/xml-exports/job456.xml"
    
    @mock_s3
    def test_delete_xml_file_s3(self, mock_settings):
        """Test XML file deletion from S3"""
        # Create mock S3 bucket and object
        s3_client = boto3.client('s3', region_name='us-west-2')
        s3_client.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        s3_key = "xml-exports/2024/01/user123/job456.xml"
        s3_client.put_object(Bucket='test-bucket', Key=s3_key, Body=b'test content')
        
        with patch.object(XMLStorageService, '_initialize_s3_client'):
            service = XMLStorageService()
            service._s3_client = s3_client
            
            result = service.delete_xml_file(s3_key)
            assert result is True
            
            # Verify file is deleted
            with pytest.raises(ClientError):
                s3_client.head_object(Bucket='test-bucket', Key=s3_key)
    
    def test_delete_xml_file_local(self, mock_settings):
        """Test XML file deletion from local storage"""
        mock_settings.AWS_ACCESS_KEY_ID = ""  # Disable S3
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            xml_dir = Path(temp_dir) / "uploads" / "xml-exports"
            xml_dir.mkdir(parents=True, exist_ok=True)
            test_file = xml_dir / "job456.xml"
            test_file.write_text("test content")
            
            with patch('src.services.xml_storage.Path') as mock_path:
                mock_path.return_value = xml_dir
                
                service = XMLStorageService()
                result = service.delete_xml_file("xml-exports/2024/01/user123/job456.xml")
                
                assert result is True
                assert not test_file.exists()
    
    @mock_s3
    def test_cleanup_expired_files_s3(self, mock_settings):
        """Test cleanup of expired files in S3"""
        # Create mock S3 bucket with old and new objects
        s3_client = boto3.client('s3', region_name='us-west-2')
        s3_client.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        
        # Create objects with different ages
        old_key = "xml-exports/2023/01/user123/old-job.xml"
        new_key = "xml-exports/2024/12/user123/new-job.xml"
        
        s3_client.put_object(Bucket='test-bucket', Key=old_key, Body=b'old content')
        s3_client.put_object(Bucket='test-bucket', Key=new_key, Body=b'new content')
        
        with patch.object(XMLStorageService, '_initialize_s3_client'):
            service = XMLStorageService()
            service._s3_client = s3_client
            
            # Mock the last modified dates
            with patch.object(s3_client, 'get_paginator') as mock_paginator:
                mock_page = {
                    'Contents': [
                        {
                            'Key': old_key,
                            'LastModified': datetime.now(timezone.utc) - timedelta(days=60)
                        },
                        {
                            'Key': new_key,
                            'LastModified': datetime.now(timezone.utc) - timedelta(days=1)
                        }
                    ]
                }
                mock_paginator.return_value.paginate.return_value = [mock_page]
                
                deleted_count = service.cleanup_expired_files(retention_days=30)
                
                assert deleted_count == 1
    
    def test_cleanup_expired_files_local(self, mock_settings):
        """Test cleanup of expired files in local storage"""
        mock_settings.AWS_ACCESS_KEY_ID = ""  # Disable S3
        
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_dir = Path(temp_dir) / "uploads" / "xml-exports"
            xml_dir.mkdir(parents=True, exist_ok=True)
            
            # Create old and new files
            old_file = xml_dir / "old-job.xml"
            new_file = xml_dir / "new-job.xml"
            
            old_file.write_text("old content")
            new_file.write_text("new content")
            
            # Set old file modification time to 60 days ago
            old_timestamp = (datetime.now() - timedelta(days=60)).timestamp()
            old_file.touch(times=(old_timestamp, old_timestamp))
            
            with patch('src.services.xml_storage.Path') as mock_path:
                mock_path.return_value = xml_dir
                
                service = XMLStorageService()
                deleted_count = service.cleanup_expired_files(retention_days=30)
                
                assert deleted_count == 1
                assert not old_file.exists()
                assert new_file.exists()
    
    @mock_s3
    def test_get_file_info_s3(self, mock_settings):
        """Test getting file information from S3"""
        # Create mock S3 bucket and object
        s3_client = boto3.client('s3', region_name='us-west-2')
        s3_client.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        s3_key = "xml-exports/2024/01/user123/job456.xml"
        s3_client.put_object(
            Bucket='test-bucket', 
            Key=s3_key, 
            Body=b'test content',
            Metadata={'job-id': 'test-job-123'}
        )
        
        with patch.object(XMLStorageService, '_initialize_s3_client'):
            service = XMLStorageService()
            service._s3_client = s3_client
            
            file_info = service.get_file_info(s3_key)
            
            assert file_info is not None
            assert file_info['storage_type'] == 's3'
            assert file_info['size'] > 0
            assert 'last_modified' in file_info
            assert file_info['content_type'] == 'application/xml'
            assert 'metadata' in file_info
    
    def test_get_file_info_local(self, mock_settings):
        """Test getting file information from local storage"""
        mock_settings.AWS_ACCESS_KEY_ID = ""  # Disable S3
        
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_dir = Path(temp_dir) / "uploads" / "xml-exports"
            xml_dir.mkdir(parents=True, exist_ok=True)
            test_file = xml_dir / "job456.xml"
            test_file.write_text("test content")
            
            with patch('src.services.xml_storage.Path') as mock_path:
                mock_path.return_value = xml_dir
                
                service = XMLStorageService()
                file_info = service.get_file_info("xml-exports/2024/01/user123/job456.xml")
                
                assert file_info is not None
                assert file_info['storage_type'] == 'local'
                assert file_info['size'] > 0
                assert 'last_modified' in file_info
                assert 'path' in file_info
    
    def test_get_file_info_not_found(self, mock_settings):
        """Test getting file information for non-existent file"""
        mock_settings.AWS_ACCESS_KEY_ID = ""  # Disable S3
        
        service = XMLStorageService()
        file_info = service.get_file_info("non-existent-file.xml")
        
        assert file_info is None
    
    @pytest.mark.asyncio
    async def test_storage_error_handling(self, mock_settings, processing_job):
        """Test error handling in storage operations"""
        service = XMLStorageService()
        
        # Test with S3 client error
        with patch.object(service, '_s3_client') as mock_s3:
            mock_s3.put_object.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'PutObject'
            )
            service._bucket_name = 'test-bucket'
            
            # Should fallback to local storage if allowed
            with patch.object(service, '_store_locally') as mock_local:
                mock_local.return_value = {'success': True, 'storage_type': 'local'}
                
                valid_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<ASYCUDA><Consignment></Consignment><Item></Item></ASYCUDA>'''
                
                result = await service.upload_xml_file(processing_job, valid_xml)
                assert mock_local.called
    
    @pytest.mark.asyncio
    async def test_s3_upload_with_metadata(self, mock_settings, processing_job, sample_xml_content):
        """Test S3 upload includes proper metadata"""
        with patch.object(XMLStorageService, '_initialize_s3_client'):
            service = XMLStorageService()
            
            # Mock S3 client
            mock_s3 = Mock()
            mock_s3.put_object.return_value = {'ETag': '"test-etag"'}
            service._s3_client = mock_s3
            service._bucket_name = 'test-bucket'
            
            result = await service.upload_xml_file(processing_job, sample_xml_content)
            
            # Verify put_object was called with correct metadata
            assert mock_s3.put_object.called
            call_args = mock_s3.put_object.call_args
            
            assert call_args[1]['Bucket'] == 'test-bucket'
            assert call_args[1]['ContentType'] == 'application/xml'
            assert call_args[1]['ContentEncoding'] == 'utf-8'
            assert call_args[1]['ServerSideEncryption'] == 'AES256'
            assert call_args[1]['StorageClass'] == 'STANDARD_IA'
            
            metadata = call_args[1]['Metadata']
            assert metadata['job-id'] == str(processing_job.id)
            assert metadata['user-id'] == str(processing_job.user_id)
            assert metadata['country-schema'] == processing_job.country_schema
            assert metadata['content-type'] == 'application/xml'