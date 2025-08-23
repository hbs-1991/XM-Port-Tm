"""
Integration tests for XML generation error recovery and rollback scenarios
"""
import pytest
import io
import csv
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


class TestXMLErrorRecovery:
    """Integration tests for XML generation error recovery and rollback scenarios"""

    @pytest.mark.asyncio
    async def test_xml_generation_service_failure_recovery(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test recovery when XML generation service fails"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML generation service to fail
            with patch.object(xml_generation_service, 'generate_xml', new_callable=AsyncMock) as mock_xml_gen:
                mock_xml_gen.side_effect = Exception("XML generation service temporarily unavailable")
                
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
                    assert result["success"] is True  # Overall success due to HS matching completion
                    
                    # Verify job reflects XML generation failure
                    job_id = result["job_id"]
                    job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                    assert job.status == ProcessingStatus.COMPLETED_WITH_ERRORS
                    assert job.xml_generation_status == "failed"
                    assert job.output_xml_url is None
                    assert "XML generation failed" in (job.error_details or "")
                    
                    # Verify ProductMatch records were still created (no rollback of HS matching)
                    matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                    assert len(matches) == 3
                    
                    # Verify user credits were still deducted (HS matching succeeded)
                    db_session.refresh(test_user)
                    assert test_user.credits_remaining == 99

    @pytest.mark.asyncio
    async def test_xml_storage_failure_rollback(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test rollback when XML storage fails"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload for original file
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML generation to succeed
            with patch.object(xml_generation_service, 'generate_xml', new_callable=AsyncMock) as mock_xml_gen:
                mock_xml_gen.return_value = {
                    'xml_content': '<xml>Test XML content</xml>',
                    'file_size': 1024,
                    'generated_at': '2025-01-23T10:00:00Z'
                }
                
                # Mock XML storage to fail
                with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                    mock_xml_store.side_effect = Exception("S3 storage service unavailable")
                    
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
                        
                        # Verify partial success
                        assert result["success"] is True  # HS matching and XML generation succeeded
                        
                        # Verify job reflects storage failure
                        job_id = result["job_id"]
                        job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                        assert job.status == ProcessingStatus.COMPLETED_WITH_ERRORS
                        assert job.xml_generation_status == "failed"  # Failed due to storage failure
                        assert job.output_xml_url is None
                        assert "XML storage failed" in (job.error_details or "")
                        
                        # Verify ProductMatch records were preserved
                        matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                        assert len(matches) == 3

    @pytest.mark.asyncio
    async def test_database_transaction_rollback_during_xml_generation(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test database transaction rollback during XML generation"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock HS matching service
            with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                mock_hs_service.should_require_manual_review.return_value = False
                
                # Mock database commit to fail during XML generation status update
                original_commit = db_session.commit
                commit_count = 0
                
                def mock_commit():
                    nonlocal commit_count
                    commit_count += 1
                    if commit_count == 3:  # Fail on XML status update commit
                        raise Exception("Database connection lost")
                    return original_commit()
                
                db_session.commit = mock_commit
                
                # Execute workflow - should handle database failure
                result = await file_service.process_file_with_hs_matching(
                    file=mock_upload_file,
                    user=test_user,
                    country_schema="turkmenistan"
                )
                
                # Verify failure handling
                assert result["success"] is False
                assert "Database error during XML generation" in result["error"] or \
                       "Database connection lost" in result["error"]
                
                # Verify job exists but is marked as failed
                job_id = result["job_id"]
                job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                assert job is not None
                assert job.status == ProcessingStatus.FAILED

    @pytest.mark.asyncio
    async def test_concurrent_processing_failure_isolation(
        self,
        db_session: Session,
        sample_csv_content: bytes
    ):
        """Test that failures in one processing job don't affect concurrent jobs"""
        
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
        
        # Create mock files
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
        
        # Mock S3 uploads
        with patch.object(file_service1, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_1:
            mock_s3_1.return_value = "s3://test-bucket/uploads/1/user1_products.csv"
            
            with patch.object(file_service2, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_2:
                mock_s3_2.return_value = "s3://test-bucket/uploads/2/user2_products.csv"
                
                # Mock XML generation - fail for user1, succeed for user2
                def xml_generation_mock(job_id, **kwargs):
                    job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                    if job.user_id == user1.id:
                        raise Exception("XML generation failed for user 1")
                    return {
                        'file_path': 's3://test-bucket/xml/job_2_export.xml',
                        'download_url': 'https://presigned-download-url-2.com',
                        'file_size': 2048,
                        'expires_at': '2025-01-23T12:00:00Z'
                    }
                
                with patch.object(xml_storage_service, 'store_xml_file', side_effect=xml_generation_mock):
                    
                    # Mock HS matching service
                    mock_results = [
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
                    ]
                    
                    with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                        mock_hs_service.match_batch_products = AsyncMock(return_value=mock_results)
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
                        
                        results = await asyncio.gather(task1, task2, return_exceptions=True)
                        result1, result2 = results
                        
                        # Verify user1 failed, user2 succeeded
                        assert result1["success"] is True  # HS matching succeeded
                        assert result2["success"] is True
                        
                        # Check job statuses
                        job1 = db_session.query(ProcessingJob).filter(ProcessingJob.id == result1["job_id"]).first()
                        job2 = db_session.query(ProcessingJob).filter(ProcessingJob.id == result2["job_id"]).first()
                        
                        # User1's job should have XML generation failure
                        assert job1.status == ProcessingStatus.COMPLETED_WITH_ERRORS
                        assert job1.xml_generation_status == "failed"
                        
                        # User2's job should be fully successful
                        assert job2.status == ProcessingStatus.COMPLETED
                        assert job2.xml_generation_status == "completed"
                        assert job2.output_xml_url is not None

    @pytest.mark.asyncio
    async def test_partial_xml_generation_with_invalid_products(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile
    ):
        """Test XML generation with some invalid product data"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Create mixed HS matching results (some valid, some invalid)
        mixed_results = [
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
                    hs_code="ERROR",
                    code_description="Failed to match HS code",
                    confidence=0.0,
                    chapter="ERROR",
                    section="ERROR",
                    reasoning="Error occurred during matching"
                ),
                alternative_matches=[],
                processing_time_ms=0.0,
                query="Invalid Product"
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
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML generation to handle invalid products
            with patch.object(xml_generation_service, 'generate_xml', new_callable=AsyncMock) as mock_xml_gen:
                
                def xml_gen_with_validation(job_id, product_matches, **kwargs):
                    # Filter out invalid products
                    valid_matches = [m for m in product_matches if m.matched_hs_code != "ERROR"]
                    if len(valid_matches) == 0:
                        raise Exception("No valid products for XML generation")
                    
                    return {
                        'xml_content': f'<xml>Generated XML for {len(valid_matches)} valid products</xml>',
                        'file_size': 1024,
                        'generated_at': '2025-01-23T10:00:00Z'
                    }
                
                mock_xml_gen.side_effect = xml_gen_with_validation
                
                # Mock XML storage
                with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                    mock_xml_store.return_value = {
                        'file_path': 's3://test-bucket/xml/job_1_export.xml',
                        'download_url': 'https://presigned-download-url.com',
                        'file_size': 1024,
                        'expires_at': '2025-01-23T12:00:00Z'
                    }
                    
                    # Mock HS matching service
                    with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                        mock_hs_service.match_batch_products = AsyncMock(return_value=mixed_results)
                        mock_hs_service.should_require_manual_review.side_effect = lambda conf: conf < 0.8
                        
                        # Execute workflow
                        result = await file_service.process_file_with_hs_matching(
                            file=mock_upload_file,
                            user=test_user,
                            country_schema="turkmenistan"
                        )
                        
                        # Verify success despite invalid products
                        assert result["success"] is True
                        
                        # Verify job completed successfully
                        job_id = result["job_id"]
                        job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                        assert job.status == ProcessingStatus.COMPLETED
                        assert job.xml_generation_status == "completed"
                        assert job.output_xml_url is not None
                        
                        # Verify all ProductMatch records were created (including invalid ones)
                        matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                        assert len(matches) == 3
                        
                        # Verify XML generation was called with only valid products
                        mock_xml_gen.assert_called_once()
                        call_args = mock_xml_gen.call_args[1]
                        valid_products = [m for m in call_args['product_matches'] if m.matched_hs_code != "ERROR"]
                        assert len(valid_products) == 2  # Only iPhone and Dell laptop

    @pytest.mark.asyncio
    async def test_retry_mechanism_for_transient_failures(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test retry mechanism for transient XML generation failures"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML generation to fail initially then succeed
            call_count = 0
            
            async def xml_gen_with_retry(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:  # Fail first 2 attempts
                    raise Exception("Temporary service unavailable")
                return {
                    'xml_content': '<xml>Generated XML content</xml>',
                    'file_size': 1024,
                    'generated_at': '2025-01-23T10:00:00Z'
                }
            
            with patch.object(xml_generation_service, 'generate_xml', side_effect=xml_gen_with_retry):
                
                # Mock XML storage
                with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                    mock_xml_store.return_value = {
                        'file_path': 's3://test-bucket/xml/job_1_export.xml',
                        'download_url': 'https://presigned-download-url.com',
                        'file_size': 1024,
                        'expires_at': '2025-01-23T12:00:00Z'
                    }
                    
                    # Mock HS matching service
                    with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                        mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                        mock_hs_service.should_require_manual_review.return_value = False
                        
                        # Enable retry mechanism in file processing
                        with patch('src.services.file_processing.MAX_XML_GENERATION_RETRIES', 3):
                            
                            # Execute workflow
                            result = await file_service.process_file_with_hs_matching(
                                file=mock_upload_file,
                                user=test_user,
                                country_schema="turkmenistan"
                            )
                            
                            # Verify success after retries
                            assert result["success"] is True
                            
                            # Verify job completed successfully
                            job_id = result["job_id"]
                            job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                            assert job.status == ProcessingStatus.COMPLETED
                            assert job.xml_generation_status == "completed"
                            assert job.output_xml_url is not None
                            
                            # Verify retry attempts were made
                            assert call_count == 3

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_critical_failure(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test graceful degradation when critical components fail"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML generation service to be completely unavailable
            with patch.object(xml_generation_service, 'generate_xml', new_callable=AsyncMock) as mock_xml_gen:
                mock_xml_gen.side_effect = Exception("XML service completely unavailable")
                
                # Mock XML storage service to also be unavailable
                with patch.object(xml_storage_service, 'store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                    mock_xml_store.side_effect = Exception("Storage service unavailable")
                    
                    # Mock HS matching service to succeed
                    with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                        mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                        mock_hs_service.should_require_manual_review.return_value = False
                        
                        # Execute workflow with graceful degradation
                        result = await file_service.process_file_with_hs_matching(
                            file=mock_upload_file,
                            user=test_user,
                            country_schema="turkmenistan"
                        )
                        
                        # Verify graceful degradation: HS matching succeeds, XML fails
                        assert result["success"] is True  # Core functionality (HS matching) succeeded
                        
                        # Verify job status reflects degraded state
                        job_id = result["job_id"]
                        job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                        assert job.status == ProcessingStatus.COMPLETED_WITH_ERRORS
                        assert job.xml_generation_status == "failed"
                        assert job.output_xml_url is None
                        assert "XML generation failed" in (job.error_details or "")
                        
                        # Verify core functionality completed successfully
                        assert job.total_products == 3
                        assert job.successful_matches == 3
                        
                        # Verify ProductMatch records were created
                        matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                        assert len(matches) == 3
                        
                        # Verify user received value despite XML failure
                        db_session.refresh(test_user)
                        assert test_user.credits_remaining == 99  # Credits deducted for HS matching