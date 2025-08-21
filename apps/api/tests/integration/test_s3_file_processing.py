"""
Integration tests for S3 file upload and processing workflow
"""
import io
import pytest
import boto3
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from moto import mock_s3
from sqlalchemy.orm import Session

from src.main import app
from src.services.file_processing import FileProcessingService
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.core.config import settings


@mock_s3
class TestS3FileProcessingIntegration:
    """Integration tests for S3 file processing"""
    
    @pytest.fixture(autouse=True)
    def setup_s3_mock(self):
        """Set up mock S3 environment for testing"""
        # Create mock S3 client and bucket
        self.s3_client = boto3.client(
            's3', 
            region_name='us-east-1',
            aws_access_key_id='testing',
            aws_secret_access_key='testing'
        )
        
        # Create test bucket
        bucket_name = 'test-xm-port-bucket'
        self.s3_client.create_bucket(Bucket=bucket_name)
        
        # Patch settings to use test bucket
        with patch.object(settings, 'AWS_S3_BUCKET', bucket_name):
            yield
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def test_user(self):
        """Test user with credits"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.credits_remaining = 10
        user.credits_used_this_month = 0
        user.subscription_tier = SubscriptionTier.BASIC
        user.is_active = True
        return user
    
    @pytest.fixture
    def file_service(self, mock_db):
        """File processing service with mocked S3"""
        service = FileProcessingService(mock_db)
        service.s3_client = self.s3_client
        return service
    
    @pytest.fixture
    def valid_csv_content(self):
        """Valid CSV content for testing"""
        return """Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"Test Product 1",100,pieces,500.00,USA,5.00
"Test Product 2",50,kg,250.50,Canada,5.01
"Test Product 3",75,units,375.00,Mexico,5.00
"""
    
    @pytest.fixture
    def create_upload_file(self):
        """Helper to create upload files"""
        def _create_file(content: str, filename: str, content_type: str = "text/csv"):
            from fastapi import UploadFile
            file_bytes = content.encode('utf-8')
            file_obj = io.BytesIO(file_bytes)
            upload_file = UploadFile(
                filename=filename,
                file=file_obj,
                size=len(file_bytes),
                headers={"content-type": content_type}
            )
            upload_file.content_type = content_type
            return upload_file
        return _create_file
    
    # S3 Upload Integration Tests
    
    async def test_successful_s3_upload_workflow(self, file_service, test_user, create_upload_file, valid_csv_content):
        """Test complete S3 upload workflow"""
        file = create_upload_file(valid_csv_content, "test_upload.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Upload file to S3
            s3_url = await file_service.upload_file_to_s3(file, test_user.id)
            
            # Verify S3 URL format
            assert s3_url.startswith('s3://test-xm-port-bucket/uploads/')
            assert test_user.id in s3_url
            assert 'test_upload.csv' in s3_url
            
            # Verify file exists in S3
            bucket_name = 'test-xm-port-bucket'
            key = s3_url.replace(f's3://{bucket_name}/', '')
            
            response = self.s3_client.head_object(Bucket=bucket_name, Key=key)
            assert response['ContentLength'] > 0
            
            # Verify file content in S3
            obj = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            uploaded_content = obj['Body'].read().decode('utf-8')
            assert valid_csv_content in uploaded_content
    
    async def test_s3_upload_with_encryption(self, file_service, test_user, create_upload_file, valid_csv_content):
        """Test S3 upload with server-side encryption"""
        file = create_upload_file(valid_csv_content, "encrypted_test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Mock S3 client to verify encryption parameters
            original_put_object = self.s3_client.put_object
            
            def mock_put_object(*args, **kwargs):
                # Verify encryption parameters are set
                assert 'ServerSideEncryption' in kwargs
                assert kwargs['ServerSideEncryption'] == 'AES256'
                return original_put_object(*args, **kwargs)
            
            with patch.object(self.s3_client, 'put_object', side_effect=mock_put_object) as mock_put:
                s3_url = await file_service.upload_file_to_s3(file, test_user.id)
                
                assert s3_url is not None
                mock_put.assert_called_once()
    
    async def test_s3_upload_unique_key_generation(self, file_service, test_user, create_upload_file, valid_csv_content):
        """Test that S3 keys are unique to prevent conflicts"""
        file1 = create_upload_file(valid_csv_content, "duplicate.csv")
        file2 = create_upload_file(valid_csv_content, "duplicate.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Upload same filename twice
            s3_url1 = await file_service.upload_file_to_s3(file1, test_user.id)
            s3_url2 = await file_service.upload_file_to_s3(file2, test_user.id)
            
            # URLs should be different due to unique key generation
            assert s3_url1 != s3_url2
            assert 'duplicate.csv' in s3_url1
            assert 'duplicate.csv' in s3_url2
            
            # Both files should exist in S3
            bucket_name = 'test-xm-port-bucket'
            key1 = s3_url1.replace(f's3://{bucket_name}/', '')
            key2 = s3_url2.replace(f's3://{bucket_name}/', '')
            
            self.s3_client.head_object(Bucket=bucket_name, Key=key1)
            self.s3_client.head_object(Bucket=bucket_name, Key=key2)
    
    async def test_s3_upload_error_handling(self, file_service, test_user, create_upload_file, valid_csv_content):
        """Test S3 upload error handling"""
        file = create_upload_file(valid_csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Simulate S3 error
            with patch.object(self.s3_client, 'put_object', side_effect=Exception("S3 Error")):
                with pytest.raises(Exception) as exc_info:
                    await file_service.upload_file_to_s3(file, test_user.id)
                
                assert "S3 Error" in str(exc_info.value)
    
    async def test_s3_fallback_to_local_storage(self, mock_db, test_user, create_upload_file, valid_csv_content):
        """Test fallback to local storage when S3 is unavailable"""
        file_service_no_s3 = FileProcessingService(mock_db)
        file_service_no_s3.s3_client = None  # No S3 client configured
        
        file = create_upload_file(valid_csv_content, "local_fallback.csv")
        
        with patch.object(file_service_no_s3, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            with patch('src.services.file_processing.save_file_locally') as mock_local_save:
                mock_local_save.return_value = '/local/storage/path/local_fallback.csv'
                
                result = await file_service_no_s3.upload_file_to_s3(file, test_user.id)
                
                # Should fallback to local storage
                assert result == '/local/storage/path/local_fallback.csv'
                mock_local_save.assert_called_once()
    
    # Complete Processing Workflow Integration Tests
    
    async def test_complete_file_processing_workflow(self, file_service, test_user, create_upload_file, valid_csv_content):
        """Test complete file processing workflow from upload to job creation"""
        file = create_upload_file(valid_csv_content, "workflow_test.csv")
        country_schema = "USA"
        
        # Mock database operations
        file_service.db.add = Mock()
        file_service.db.commit = Mock()
        file_service.db.refresh = Mock()
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Step 1: Validate file
            validation_result = await file_service.validate_file_upload(file)
            assert validation_result.is_valid
            
            # Step 2: Check credits
            credits_required = file_service.calculate_processing_credits(validation_result.total_rows)
            credit_check = file_service.check_user_credits(test_user, credits_required)
            assert credit_check['has_sufficient_credits'] is True
            
            # Step 3: Reserve credits
            reserve_success = file_service.reserve_user_credits(test_user, credits_required)
            assert reserve_success is True
            
            # Step 4: Upload to S3
            s3_url = await file_service.upload_file_to_s3(file, test_user.id)
            assert s3_url is not None
            
            # Step 5: Create processing job
            processing_job = file_service.create_processing_job(
                user=test_user,
                file_name=file.filename,
                file_url=s3_url,
                file_size=file.size,
                country_schema=country_schema,
                credits_used=credits_required
            )
            
            # Verify job creation
            assert isinstance(processing_job, ProcessingJob)
            assert processing_job.user_id == test_user.id
            assert processing_job.input_file_name == file.filename
            assert processing_job.input_file_url == s3_url
            assert processing_job.status == ProcessingStatus.PENDING
            assert processing_job.credits_used == credits_required
            
            # Verify database operations called
            file_service.db.add.assert_called_once()
            file_service.db.commit.assert_called_once()
            file_service.db.refresh.assert_called_once()
    
    async def test_workflow_with_insufficient_credits(self, file_service, create_upload_file, valid_csv_content):
        """Test workflow failure with insufficient credits"""
        # User with insufficient credits
        low_credit_user = Mock(spec=User)
        low_credit_user.id = "low-credit-user"
        low_credit_user.credits_remaining = 1
        low_credit_user.credits_used_this_month = 19
        low_credit_user.subscription_tier = SubscriptionTier.FREE
        low_credit_user.is_active = True
        
        file = create_upload_file(valid_csv_content * 10, "large_file.csv")  # Large file requiring more credits
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Validate file
            validation_result = await file_service.validate_file_upload(file)
            assert validation_result.is_valid
            
            # Check credits - should fail
            credits_required = file_service.calculate_processing_credits(validation_result.total_rows)
            credit_check = file_service.check_user_credits(low_credit_user, credits_required)
            assert credit_check['has_sufficient_credits'] is False
            
            # Should not proceed with upload or job creation
            # This simulates the API endpoint logic that would stop here
    
    async def test_workflow_with_credit_reservation_failure(self, file_service, test_user, create_upload_file, valid_csv_content):
        """Test workflow handling of credit reservation failure"""
        file = create_upload_file(valid_csv_content, "credit_fail.csv")
        
        # Mock database operations to simulate failure
        file_service.db.refresh = Mock()
        file_service.db.commit = Mock(side_effect=Exception("Database error"))
        file_service.db.rollback = Mock()
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Validate file
            validation_result = await file_service.validate_file_upload(file)
            assert validation_result.is_valid
            
            # Try to reserve credits - should fail
            credits_required = file_service.calculate_processing_credits(validation_result.total_rows)
            reserve_success = file_service.reserve_user_credits(test_user, credits_required)
            assert reserve_success is False
            
            # Verify rollback was called
            file_service.db.rollback.assert_called_once()
    
    async def test_workflow_with_s3_upload_failure_and_credit_refund(self, file_service, test_user, create_upload_file, valid_csv_content):
        """Test credit refund when S3 upload fails"""
        file = create_upload_file(valid_csv_content, "s3_fail.csv")
        
        # Mock database operations
        file_service.db.refresh = Mock()
        file_service.db.commit = Mock()
        file_service.db.rollback = Mock()
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Validate and reserve credits successfully
            validation_result = await file_service.validate_file_upload(file)
            credits_required = file_service.calculate_processing_credits(validation_result.total_rows)
            
            original_credits = test_user.credits_remaining
            original_used = test_user.credits_used_this_month
            
            # Reserve credits
            reserve_success = file_service.reserve_user_credits(test_user, credits_required)
            assert reserve_success is True
            
            # Simulate S3 upload failure
            with patch.object(self.s3_client, 'put_object', side_effect=Exception("S3 Failure")):
                try:
                    await file_service.upload_file_to_s3(file, test_user.id)
                    assert False, "Should have raised exception"
                except Exception:
                    # S3 upload failed, refund credits
                    refund_success = file_service.refund_user_credits(test_user, credits_required)
                    assert refund_success is True
                    
                    # Verify credits were refunded
                    assert test_user.credits_remaining == original_credits
                    assert test_user.credits_used_this_month == original_used
    
    # Performance and Scalability Tests
    
    async def test_concurrent_s3_uploads(self, file_service, create_upload_file, valid_csv_content):
        """Test handling of concurrent S3 uploads"""
        import asyncio
        
        # Create multiple users and files
        users = []
        files = []
        for i in range(5):
            user = Mock(spec=User)
            user.id = f"user-{i}"
            users.append(user)
            
            file = create_upload_file(valid_csv_content, f"concurrent_{i}.csv")
            files.append(file)
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Upload files concurrently
            upload_tasks = []
            for user, file in zip(users, files):
                task = file_service.upload_file_to_s3(file, user.id)
                upload_tasks.append(task)
            
            results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            
            # All uploads should succeed
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Upload {i} failed: {result}"
                assert result.startswith('s3://')
                assert f"user-{i}" in result
    
    async def test_large_file_s3_upload(self, file_service, test_user, create_upload_file):
        """Test S3 upload of large files"""
        # Create a large CSV file (close to 10MB limit)
        header = "Product Description,Quantity,Unit,Value,Origin Country,Unit Price\n"
        row = '"Large Product Description",100,pieces,500.00,USA,5.00\n'
        
        # Calculate rows needed for ~9MB file
        row_size = len(row)
        target_size = 9 * 1024 * 1024  # 9MB
        num_rows = target_size // row_size
        
        large_content = header + (row * num_rows)
        file = create_upload_file(large_content, "large_file.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Should handle large file upload
            s3_url = await file_service.upload_file_to_s3(file, test_user.id)
            assert s3_url is not None
            
            # Verify file was uploaded completely
            bucket_name = 'test-xm-port-bucket'
            key = s3_url.replace(f's3://{bucket_name}/', '')
            
            response = self.s3_client.head_object(Bucket=bucket_name, Key=key)
            assert response['ContentLength'] >= target_size * 0.9  # Allow some variance
    
    # Data Integrity Tests
    
    async def test_s3_upload_data_integrity(self, file_service, test_user, create_upload_file):
        """Test data integrity during S3 upload"""
        import hashlib
        
        # Create content with specific checksum
        csv_content = "Product Description,Quantity,Unit,Value,Origin Country,Unit Price\n"
        for i in range(100):
            csv_content += f'"Product {i}",{i+1},pieces,{(i+1)*5.0},Country{i%5},{5.0}\n'
        
        original_hash = hashlib.md5(csv_content.encode()).hexdigest()
        file = create_upload_file(csv_content, "integrity_test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            # Upload to S3
            s3_url = await file_service.upload_file_to_s3(file, test_user.id)
            
            # Download and verify integrity
            bucket_name = 'test-xm-port-bucket'
            key = s3_url.replace(f's3://{bucket_name}/', '')
            
            obj = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            downloaded_content = obj['Body'].read().decode('utf-8')
            downloaded_hash = hashlib.md5(downloaded_content.encode()).hexdigest()
            
            assert original_hash == downloaded_hash, "Data integrity check failed"