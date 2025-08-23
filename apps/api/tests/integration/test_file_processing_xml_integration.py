"""
Integration tests for complete file processing workflow with XML generation
"""
import pytest
import io
import csv
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.services.file_processing import FileProcessingService
from src.services.xml_generation import XMLGenerationService, xml_generation_service
from src.services.xml_storage import XMLStorageService, xml_storage_service
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.core.openai_config import HSCodeResult, HSCodeMatchResult
from src.api.v1.ws import manager as websocket_manager


@pytest.fixture
def sample_csv_content():
    """Create sample CSV content for testing"""
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    
    # Write headers
    writer.writerow(['Product Description', 'Quantity', 'Unit', 'Value', 'Origin Country', 'Unit Price'])
    
    # Write sample data
    writer.writerow(['Apple iPhone 14', '10', 'pcs', '12000.00', 'China', '1200.00'])
    writer.writerow(['Samsung Galaxy S23', '5', 'pcs', '4000.00', 'South Korea', '800.00'])
    writer.writerow(['Dell Laptop XPS 13', '3', 'pcs', '3600.00', 'Taiwan', '1200.00'])
    
    return csv_content.getvalue().encode('utf-8')


@pytest.fixture
def mock_upload_file(sample_csv_content):
    """Create mock UploadFile for testing"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_products.csv"
    file.size = len(sample_csv_content)
    file.content_type = "text/csv"
    file.read = AsyncMock(return_value=sample_csv_content)
    file.seek = AsyncMock()
    return file


@pytest.fixture
def test_user():
    """Create test user with sufficient credits"""
    user = User(
        id=1,
        email="test@example.com",
        username="testuser",
        subscription_tier=SubscriptionTier.BASIC,
        credits_remaining=100,
        credits_used_this_month=0
    )
    return user


@pytest.fixture
def mock_hs_matching_results():
    """Mock HS code matching results"""
    return [
        HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8517.12.00",
                code_description="Telephones for cellular networks",
                confidence=0.95,
                chapter="85",
                section="XVI",
                reasoning="iPhone is clearly a cellular telephone"
            ),
            alternative_matches=[],
            processing_time_ms=1200.0,
            query="Apple iPhone 14"
        ),
        HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8517.12.00",
                code_description="Telephones for cellular networks",
                confidence=0.92,
                chapter="85",
                section="XVI",
                reasoning="Samsung Galaxy is a cellular telephone"
            ),
            alternative_matches=[],
            processing_time_ms=1100.0,
            query="Samsung Galaxy S23"
        ),
        HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8471.30.01",
                code_description="Portable digital automatic data processing machines",
                confidence=0.88,
                chapter="84",
                section="XVI",
                reasoning="Dell XPS 13 is a portable laptop computer"
            ),
            alternative_matches=[],
            processing_time_ms=1300.0,
            query="Dell Laptop XPS 13"
        )
    ]


class TestFileProcessingXMLIntegration:
    """Integration tests for complete file processing workflow with XML generation"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_success(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test complete end-to-end workflow from file upload to XML generation"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 uploads for both original file and XML
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML storage service
            with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                mock_xml_store.return_value = {
                    'file_path': 's3://test-bucket/xml/job_1_export.xml',
                    'download_url': 'https://presigned-download-url.com',
                    'file_size': 2048,
                    'expires_at': '2025-01-23T12:00:00Z'
                }
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.side_effect = lambda conf: conf < 0.9
                    
                    # Mock WebSocket notifications
                    with patch.object(websocket_manager, 'send_processing_update', new_callable=AsyncMock) as mock_ws:
                        
                        # Execute complete workflow
                        result = await file_service.process_file_with_hs_matching(
                            file=mock_upload_file,
                            user=test_user,
                            country_schema="turkmenistan"
                        )
                        
                        # Verify overall success
                        assert result["success"] is True
                        assert result["products_processed"] == 3
                        assert result["credits_used"] == 1
                        
                        # Verify processing job was created and completed
                        job_id = result["job_id"]
                        job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                        assert job is not None
                        assert job.status == ProcessingStatus.COMPLETED
                        assert job.total_products == 3
                        assert job.successful_matches == 3
                        assert job.output_xml_url is not None
                        assert job.xml_generation_status == "completed"
                        assert job.xml_generated_at is not None
                        assert job.xml_file_size == 2048
                        
                        # Verify ProductMatch records were created
                        matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                        assert len(matches) == 3
                        
                        # Verify XML generation was called
                        mock_xml_store.assert_called_once()
                        
                        # Verify WebSocket progress notifications were sent
                        assert mock_ws.call_count >= 8  # At least 8 progress updates
                        
                        # Check specific progress notifications
                        progress_calls = [call[1] for call in mock_ws.call_args_list]
                        assert any("XML generation started" in str(call) for call in progress_calls)
                        assert any("XML generation completed" in str(call) for call in progress_calls)

    @pytest.mark.asyncio
    async def test_xml_generation_integration(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test XML generation service integration with file processing"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload for original file
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock HS matching service
            with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                mock_hs_service.should_require_manual_review.return_value = False
                
                # Mock XML generation service to capture parameters
                with patch.object(xml_generation_service, 'generate_xml', new_callable=AsyncMock) as mock_xml_gen:
                    mock_xml_gen.return_value = {
                        'file_path': 's3://test-bucket/xml/job_1_export.xml',
                        'download_url': 'https://presigned-download-url.com',
                        'file_size': 2048,
                        'xml_content': '<test>XML content</test>',
                        'generated_at': '2025-01-23T10:00:00Z'
                    }
                    
                    # Execute workflow
                    result = await file_service.process_file_with_hs_matching(
                        file=mock_upload_file,
                        user=test_user,
                        country_schema="turkmenistan"
                    )
                    
                    # Verify XML generation was called with correct parameters
                    mock_xml_gen.assert_called_once()
                    call_args = mock_xml_gen.call_args[1]
                    
                    assert call_args['job_id'] == result['job_id']
                    assert call_args['country_schema'] == 'turkmenistan'
                    assert 'product_matches' in call_args
                    assert len(call_args['product_matches']) == 3
                    
                    # Verify job was updated with XML details
                    job = db_session.query(ProcessingJob).filter(ProcessingJob.id == result['job_id']).first()
                    assert job.output_xml_url == 's3://test-bucket/xml/job_1_export.xml'
                    assert job.xml_generation_status == 'completed'
                    assert job.xml_file_size == 2048

    @pytest.mark.asyncio
    async def test_s3_integration_and_file_storage(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test S3 integration and file storage functionality"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 operations with realistic responses
        with patch('boto3.client') as mock_boto_client:
            # Mock S3 client
            s3_client = MagicMock()
            mock_boto_client.return_value = s3_client
            
            # Mock upload operations
            s3_client.upload_fileobj.return_value = None
            s3_client.generate_presigned_url.return_value = 'https://presigned-download-url.com'
            s3_client.head_object.return_value = {'ContentLength': 2048}
            
            # Mock file upload
            with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
                mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Execute workflow
                    result = await file_service.process_file_with_hs_matching(
                        file=mock_upload_file,
                        user=test_user,
                        country_schema="turkmenistan"
                    )
                    
                    # Verify success
                    assert result["success"] is True
                    
                    # Verify S3 operations were called
                    job = db_session.query(ProcessingJob).filter(ProcessingJob.id == result['job_id']).first()
                    
                    # Check that both original file and XML were uploaded
                    assert job.file_url == "s3://test-bucket/uploads/1/test_products.csv"
                    assert job.output_xml_url is not None
                    assert job.xml_file_size > 0
                    
                    # Verify S3 client was used for XML upload
                    assert s3_client.upload_fileobj.call_count >= 1

    @pytest.mark.asyncio
    async def test_websocket_progress_notifications(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test WebSocket progress notifications during XML generation"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML storage
            with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                mock_xml_store.return_value = {
                    'file_path': 's3://test-bucket/xml/job_1_export.xml',
                    'download_url': 'https://presigned-download-url.com',
                    'file_size': 2048,
                    'expires_at': '2025-01-23T12:00:00Z'
                }
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Mock WebSocket manager to capture notifications
                    websocket_notifications = []
                    
                    async def capture_notification(*args, **kwargs):
                        websocket_notifications.append({
                            'args': args,
                            'kwargs': kwargs,
                            'timestamp': asyncio.get_event_loop().time()
                        })
                    
                    with patch.object(websocket_manager, 'send_processing_update', side_effect=capture_notification):
                        
                        # Execute workflow
                        result = await file_service.process_file_with_hs_matching(
                            file=mock_upload_file,
                            user=test_user,
                            country_schema="turkmenistan"
                        )
                        
                        # Verify success
                        assert result["success"] is True
                        
                        # Verify WebSocket notifications were sent
                        assert len(websocket_notifications) >= 8
                        
                        # Check for specific progress stages
                        messages = [notif['kwargs'].get('message', '') for notif in websocket_notifications]
                        progress_values = [notif['kwargs'].get('progress', 0) for notif in websocket_notifications]
                        
                        # Verify progressive progress updates
                        assert any("File uploaded successfully" in msg for msg in messages)
                        assert any("HS code matching completed" in msg for msg in messages)
                        assert any("XML generation started" in msg for msg in messages)
                        assert any("XML generation completed" in msg for msg in messages)
                        
                        # Verify progress increases
                        assert 0 in progress_values  # Started
                        assert 100 in progress_values  # Completed
                        assert any(p > 0 and p < 100 for p in progress_values)  # Intermediate progress

    @pytest.mark.asyncio
    async def test_processing_job_status_updates(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test ProcessingJob status updates throughout workflow"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Track job status changes
        job_statuses = []
        original_commit = db_session.commit
        
        def track_commit():
            # Check current processing jobs and capture their status
            jobs = db_session.query(ProcessingJob).all()
            for job in jobs:
                job_statuses.append({
                    'job_id': job.id,
                    'status': job.status,
                    'xml_generation_status': job.xml_generation_status,
                    'timestamp': asyncio.get_event_loop().time()
                })
            return original_commit()
        
        db_session.commit = track_commit
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML storage
            with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                mock_xml_store.return_value = {
                    'file_path': 's3://test-bucket/xml/job_1_export.xml',
                    'download_url': 'https://presigned-download-url.com',
                    'file_size': 2048,
                    'expires_at': '2025-01-23T12:00:00Z'
                }
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Execute workflow
                    result = await file_service.process_file_with_hs_matching(
                        file=mock_upload_file,
                        user=test_user,
                        country_schema="turkmenistan"
                    )
                    
                    # Verify success
                    assert result["success"] is True
                    
                    # Verify status progression
                    job_id = result["job_id"]
                    job_updates = [status for status in job_statuses if status['job_id'] == job_id]
                    
                    # Should have multiple status updates
                    assert len(job_updates) >= 3
                    
                    # Verify final job state
                    final_job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                    assert final_job.status == ProcessingStatus.COMPLETED
                    assert final_job.xml_generation_status == "completed"
                    assert final_job.xml_generated_at is not None
                    assert final_job.xml_file_size == 2048
                    assert final_job.output_xml_url == 's3://test-bucket/xml/job_1_export.xml'

    @pytest.mark.asyncio
    async def test_xml_generation_failure_recovery(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test error recovery when XML generation fails"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML generation to fail
            with patch.object(xml_generation_service, 'generate_xml', new_callable=AsyncMock) as mock_xml_gen:
                mock_xml_gen.side_effect = Exception("XML generation service unavailable")
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Execute workflow
                    result = await file_service.process_file_with_hs_matching(
                        file=mock_upload_file,
                        user=test_user,
                        country_schema="turkmenistan"
                    )
                    
                    # Verify partial success (HS matching succeeded, XML generation failed)
                    assert result["success"] is True  # Overall success due to HS matching success
                    
                    # Verify job reflects XML generation failure
                    job_id = result["job_id"]
                    job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                    assert job.status == ProcessingStatus.COMPLETED_WITH_ERRORS
                    assert job.xml_generation_status == "failed"
                    assert job.output_xml_url is None
                    assert "XML generation failed" in (job.error_details or "")
                    
                    # Verify ProductMatch records were still created
                    matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                    assert len(matches) == 3

    @pytest.mark.asyncio
    async def test_s3_storage_failure_rollback(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test rollback when S3 storage fails during XML generation"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload for original file
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML storage to fail
            with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                mock_xml_store.side_effect = Exception("S3 storage unavailable")
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Execute workflow
                    result = await file_service.process_file_with_hs_matching(
                        file=mock_upload_file,
                        user=test_user,
                        country_schema="turkmenistan"
                    )
                    
                    # Verify handling of storage failure
                    assert result["success"] is True  # Overall success despite XML storage failure
                    
                    # Verify job reflects storage failure
                    job_id = result["job_id"]
                    job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                    assert job.status == ProcessingStatus.COMPLETED_WITH_ERRORS
                    assert job.xml_generation_status == "failed"
                    assert job.output_xml_url is None
                    
                    # Verify ProductMatch records were preserved
                    matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                    assert len(matches) == 3

    @pytest.mark.asyncio
    async def test_concurrent_processing_isolation(
        self,
        db_session: Session,
        sample_csv_content: bytes
    ):
        """Test that concurrent processing jobs are properly isolated"""
        
        # Create two users
        user1 = User(
            id=1,
            email="user1@example.com",
            username="user1",
            subscription_tier=SubscriptionTier.BASIC,
            credits_remaining=100,
            credits_used_this_month=0
        )
        user2 = User(
            id=2,
            email="user2@example.com",
            username="user2",
            subscription_tier=SubscriptionTier.BASIC,
            credits_remaining=100,
            credits_used_this_month=0
        )
        
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        
        # Create mock files for both users
        file1 = MagicMock(spec=UploadFile)
        file1.filename = "user1_products.csv"
        file1.size = len(sample_csv_content)
        file1.content_type = "text/csv"
        file1.read = AsyncMock(return_value=sample_csv_content)
        file1.seek = AsyncMock()
        
        file2 = MagicMock(spec=UploadFile)
        file2.filename = "user2_products.csv"
        file2.size = len(sample_csv_content)
        file2.content_type = "text/csv"
        file2.read = AsyncMock(return_value=sample_csv_content)
        file2.seek = AsyncMock()
        
        # Initialize services
        file_service1 = FileProcessingService(db_session)
        file_service2 = FileProcessingService(db_session)
        
        # Mock S3 uploads with different URLs
        with patch.object(file_service1, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_1:
            mock_s3_1.return_value = "s3://test-bucket/uploads/1/user1_products.csv"
            
            with patch.object(file_service2, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_2:
                mock_s3_2.return_value = "s3://test-bucket/uploads/2/user2_products.csv"
                
                # Mock XML storage with different results
                xml_results = {
                    1: {
                        'file_path': 's3://test-bucket/xml/job_1_export.xml',
                        'download_url': 'https://presigned-download-url-1.com',
                        'file_size': 2048,
                        'expires_at': '2025-01-23T12:00:00Z'
                    },
                    2: {
                        'file_path': 's3://test-bucket/xml/job_2_export.xml',
                        'download_url': 'https://presigned-download-url-2.com',
                        'file_size': 2560,
                        'expires_at': '2025-01-23T12:00:00Z'
                    }
                }
                
                async def mock_xml_storage(job_id, **kwargs):
                    job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                    user_id = job.user_id
                    return xml_results.get(user_id, xml_results[1])
                
                with patch.object(xml_storage_service, 'store_xml_file', side_effect=mock_xml_storage):
                    
                    # Mock HS matching service
                    with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                        mock_hs_service.match_batch_products = AsyncMock(return_value=[
                            HSCodeMatchResult(
                                primary_match=HSCodeResult(
                                    hs_code="8517.12.00",
                                    code_description="Telephones for cellular networks",
                                    confidence=0.95,
                                    chapter="85",
                                    section="XVI",
                                    reasoning="iPhone is clearly a cellular telephone"
                                ),
                                alternative_matches=[],
                                processing_time_ms=1200.0,
                                query="Apple iPhone 14"
                            )
                        ])
                        mock_hs_service.should_require_manual_review.return_value = False
                        
                        # Execute both workflows concurrently
                        task1 = file_service1.process_file_with_hs_matching(
                            file=file1,
                            user=user1,
                            country_schema="turkmenistan"
                        )
                        task2 = file_service2.process_file_with_hs_matching(
                            file=file2,
                            user=user2,
                            country_schema="turkmenistan"
                        )
                        
                        results = await asyncio.gather(task1, task2)
                        result1, result2 = results
                        
                        # Verify both succeeded
                        assert result1["success"] is True
                        assert result2["success"] is True
                        
                        # Verify jobs are isolated
                        job1 = db_session.query(ProcessingJob).filter(ProcessingJob.id == result1["job_id"]).first()
                        job2 = db_session.query(ProcessingJob).filter(ProcessingJob.id == result2["job_id"]).first()
                        
                        assert job1.user_id == user1.id
                        assert job2.user_id == user2.id
                        assert job1.file_url != job2.file_url
                        assert job1.output_xml_url != job2.output_xml_url
                        
                        # Verify credits were deducted separately
                        db_session.refresh(user1)
                        db_session.refresh(user2)
                        assert user1.credits_remaining == 99
                        assert user2.credits_remaining == 99

    @pytest.mark.asyncio
    async def test_large_dataset_xml_generation(
        self,
        db_session: Session,
        test_user: User
    ):
        """Test XML generation with large product datasets"""
        
        # Create large CSV content (100 products)
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        
        # Write headers
        writer.writerow(['Product Description', 'Quantity', 'Unit', 'Value', 'Origin Country', 'Unit Price'])
        
        # Write 100 rows of data
        for i in range(100):
            writer.writerow([
                f'Product {i}',
                str(i + 1),
                'pcs',
                str((i + 1) * 100.0),
                'China',
                '100.00'
            ])
        
        large_content = csv_content.getvalue().encode('utf-8')
        
        # Create mock upload file
        file = MagicMock(spec=UploadFile)
        file.filename = "large_products.csv"
        file.size = len(large_content)
        file.content_type = "text/csv"
        file.read = AsyncMock(return_value=large_content)
        file.seek = AsyncMock()
        
        # Add user to database with sufficient credits
        test_user.credits_remaining = 10  # 100 products = 10 credits
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Create large matching results
        large_results = []
        for i in range(100):
            large_results.append(
                HSCodeMatchResult(
                    primary_match=HSCodeResult(
                        hs_code="9999.99.99",
                        code_description=f"Test product {i}",
                        confidence=0.9,
                        chapter="99",
                        section="XX",
                        reasoning=f"Test reasoning for product {i}"
                    ),
                    alternative_matches=[],
                    processing_time_ms=100.0,
                    query=f"Product {i}"
                )
            )
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/large_products.csv"
            
            # Mock XML storage with large file size
            with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                mock_xml_store.return_value = {
                    'file_path': 's3://test-bucket/xml/job_1_export.xml',
                    'download_url': 'https://presigned-download-url.com',
                    'file_size': 50000,  # 50KB XML file
                    'expires_at': '2025-01-23T12:00:00Z'
                }
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=large_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Execute workflow
                    result = await file_service.process_file_with_hs_matching(
                        file=file,
                        user=test_user,
                        country_schema="turkmenistan"
                    )
                    
                    # Verify success with large dataset
                    assert result["success"] is True
                    assert result["products_processed"] == 100
                    assert result["credits_used"] == 10
                    
                    # Verify job completion
                    job_id = result["job_id"]
                    job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                    assert job.status == ProcessingStatus.COMPLETED
                    assert job.total_products == 100
                    assert job.xml_file_size == 50000
                    
                    # Verify all ProductMatch records were created
                    matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                    assert len(matches) == 100
                    
                    # Verify XML generation was called with all products
                    mock_xml_store.assert_called_once()
                    call_args = mock_xml_store.call_args[1]
                    assert len(call_args['product_matches']) == 100