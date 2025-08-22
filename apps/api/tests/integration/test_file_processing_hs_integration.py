"""
Integration tests for file processing with HS code matching workflow
"""
import pytest
import io
import csv
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.services.file_processing import FileProcessingService
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


class TestFileProcessingHSIntegration:
    """Integration tests for file processing with HS code matching"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_success(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test complete file processing workflow with HS matching success"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize service
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock HS matching service
            with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                mock_hs_service.should_require_manual_review.side_effect = lambda conf: conf < 0.8
                
                # Execute complete workflow
                result = await file_service.process_file_with_hs_matching(
                    file=mock_upload_file,
                    user=test_user,
                    country_schema="default"
                )
                
                # Verify success
                assert result["success"] is True
                assert result["products_processed"] == 3
                assert result["credits_used"] == 1  # 3 rows = 1 credit
                assert len(result["processing_errors"]) == 0
                
                # Verify HS matching summary
                hs_summary = result["hs_matching_summary"]
                assert hs_summary["total_matches"] == 3
                assert hs_summary["high_confidence"] == 2  # iPhone and Samsung >= 0.95
                assert hs_summary["medium_confidence"] == 1  # Dell laptop 0.88
                assert hs_summary["requires_review"] == 1  # Dell laptop < 0.8 threshold in mock
                
                # Verify processing job was created
                job_id = result["job_id"]
                job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                assert job is not None
                assert job.status == ProcessingStatus.COMPLETED
                assert job.total_products == 3
                
                # Verify ProductMatch records were created
                matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                assert len(matches) == 3
                
                # Verify first match details
                iphone_match = next(m for m in matches if "iPhone" in m.product_description)
                assert iphone_match.matched_hs_code == "8517.12.00"
                assert float(iphone_match.confidence_score) == 0.95
                assert iphone_match.vector_store_reasoning == "iPhone is clearly a cellular telephone"
                assert iphone_match.requires_manual_review is False
                
                # Verify credits were deducted
                db_session.refresh(test_user)
                assert test_user.credits_remaining == 99
                assert test_user.credits_used_this_month == 1
    
    @pytest.mark.asyncio
    async def test_hs_matching_service_failure(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile
    ):
        """Test handling of HS matching service failures"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize service
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock HS matching service to fail
            with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                mock_hs_service.match_batch_products = AsyncMock(
                    side_effect=Exception("OpenAI API temporarily unavailable")
                )
                
                # Execute workflow - should handle failure gracefully
                result = await file_service.process_file_with_hs_matching(
                    file=mock_upload_file,
                    user=test_user,
                    country_schema="default"
                )
                
                # Verify failure handling
                assert result["success"] is False
                assert "HS code matching failed" in result["error"]
                assert "OpenAI API temporarily unavailable" in result["error"]
                
                # Verify job was created but marked as failed
                job_id = result["job_id"]
                job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                assert job is not None
                assert job.status == ProcessingStatus.FAILED
                assert "HS code matching failed" in job.error_details
                
                # Verify no ProductMatch records were created
                matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                assert len(matches) == 0
                
                # Verify credits were refunded
                db_session.refresh(test_user)
                assert test_user.credits_remaining == 100  # No credits deducted
    
    @pytest.mark.asyncio
    async def test_partial_hs_matching_failure(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile
    ):
        """Test handling of partial HS matching failures (some products fail)"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize service
        file_service = FileProcessingService(db_session)
        
        # Create mixed results (some success, some error)
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
                    reasoning="Error occurred during matching: Timeout"
                ),
                alternative_matches=[],
                processing_time_ms=0.0,
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
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock HS matching service with mixed results
            with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                mock_hs_service.match_batch_products = AsyncMock(return_value=mixed_results)
                mock_hs_service.should_require_manual_review.side_effect = lambda conf: conf < 0.8
                
                # Execute workflow
                result = await file_service.process_file_with_hs_matching(
                    file=mock_upload_file,
                    user=test_user,
                    country_schema="default"
                )
                
                # Verify partial success
                assert result["success"] is True
                assert result["products_processed"] == 3  # All products processed, but one has ERROR code
                assert len(result["processing_errors"]) == 0  # No processing errors, just ERROR result
                
                # Verify job status is completed (not failed for partial errors)
                job_id = result["job_id"]
                job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                assert job.status == ProcessingStatus.COMPLETED
                
                # Verify ProductMatch records include the ERROR result
                matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                assert len(matches) == 3
                
                # Find the error match
                error_match = next(m for m in matches if m.matched_hs_code == "ERROR")
                assert error_match.confidence_score == 0.0
                assert error_match.requires_manual_review is True
                assert "Error occurred during matching" in error_match.vector_store_reasoning
    
    @pytest.mark.asyncio
    async def test_insufficient_credits(
        self,
        db_session: Session,
        mock_upload_file: UploadFile
    ):
        """Test handling of insufficient credits during workflow"""
        
        # Create user with insufficient credits
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            subscription_tier=SubscriptionTier.FREE,
            credits_remaining=0,  # No credits
            credits_used_this_month=10
        )
        db_session.add(user)
        db_session.commit()
        
        # Initialize service
        file_service = FileProcessingService(db_session)
        
        # Execute workflow - should fail with credit error
        result = await file_service.process_file_with_hs_matching(
            file=mock_upload_file,
            user=user,
            country_schema="default"
        )
        
        # Verify credit failure
        assert result["success"] is False
        assert "Insufficient credits" in result["error"]
        assert "credit_check" in result
        
        # Verify no job was created
        jobs = db_session.query(ProcessingJob).filter(ProcessingJob.user_id == user.id).all()
        assert len(jobs) == 0
        
        # Verify credits unchanged
        db_session.refresh(user)
        assert user.credits_remaining == 0
    
    @pytest.mark.asyncio
    async def test_file_validation_failure(
        self,
        db_session: Session,
        test_user: User
    ):
        """Test handling of file validation failures"""
        
        # Create invalid CSV content (missing required columns)
        invalid_csv = io.StringIO()
        writer = csv.writer(invalid_csv)
        writer.writerow(['Description', 'Amount'])  # Missing required columns
        writer.writerow(['Test Product', '100'])
        invalid_content = invalid_csv.getvalue().encode('utf-8')
        
        # Create mock upload file with invalid content
        file = MagicMock(spec=UploadFile)
        file.filename = "invalid.csv"
        file.size = len(invalid_content)
        file.content_type = "text/csv"
        file.read = AsyncMock(return_value=invalid_content)
        file.seek = AsyncMock()
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize service
        file_service = FileProcessingService(db_session)
        
        # Execute workflow - should fail validation
        result = await file_service.process_file_with_hs_matching(
            file=file,
            user=test_user,
            country_schema="default"
        )
        
        # Verify validation failure
        assert result["success"] is False
        assert "File validation failed" in result["error"]
        assert "validation_result" in result
        
        # Verify no credits were deducted
        db_session.refresh(test_user)
        assert test_user.credits_remaining == 100
    
    @pytest.mark.asyncio 
    async def test_database_transaction_rollback(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test database transaction rollback on ProductMatch creation failure"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize service
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock HS matching service
            with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                mock_hs_service.should_require_manual_review.return_value = False
                
                # Mock database commit to fail during ProductMatch creation
                original_commit = db_session.commit
                commit_count = 0
                
                def mock_commit():
                    nonlocal commit_count
                    commit_count += 1
                    if commit_count == 2:  # Fail on ProductMatch commit (second commit)
                        raise Exception("Database connection lost")
                    return original_commit()
                
                db_session.commit = mock_commit
                
                # Execute workflow - should handle database failure
                result = await file_service.process_file_with_hs_matching(
                    file=mock_upload_file,
                    user=test_user,
                    country_schema="default"
                )
                
                # Verify failure handling
                assert result["success"] is False
                assert "Failed to save ProductMatch records" in result["error"]
                
                # Verify job exists but is marked as failed
                job_id = result["job_id"]
                job = db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                assert job is not None
                assert job.status == ProcessingStatus.FAILED
                
                # Verify no ProductMatch records were created (rollback worked)
                matches = db_session.query(ProductMatch).filter(ProductMatch.job_id == job_id).all()
                assert len(matches) == 0
    
    @pytest.mark.asyncio
    async def test_performance_requirements(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test that performance requirements are met"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize service
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload (fast)
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock HS matching service
            with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                mock_hs_service.should_require_manual_review.return_value = False
                
                # Measure execution time
                import time
                start_time = time.time()
                
                result = await file_service.process_file_with_hs_matching(
                    file=mock_upload_file,
                    user=test_user,
                    country_schema="default"
                )
                
                total_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Verify performance (should be fast with mocking)
                assert result["success"] is True
                assert total_time < 5000  # Should complete in under 5 seconds with mocking
                
                # Verify processing time is tracked
                assert "processing_time_ms" in result
                assert result["processing_time_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_large_file_credit_calculation(
        self,
        db_session: Session,
        test_user: User
    ):
        """Test credit calculation for large files"""
        
        # Create large CSV content (250 rows = 3 credits)
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        
        # Write headers
        writer.writerow(['Product Description', 'Quantity', 'Unit', 'Value', 'Origin Country', 'Unit Price'])
        
        # Write 250 rows of data
        for i in range(250):
            writer.writerow([f'Product {i}', '1', 'pcs', '100.00', 'USA', '100.00'])
        
        large_content = csv_content.getvalue().encode('utf-8')
        
        # Create mock upload file
        file = MagicMock(spec=UploadFile)
        file.filename = "large_products.csv"
        file.size = len(large_content)
        file.content_type = "text/csv"
        file.read = AsyncMock(return_value=large_content)
        file.seek = AsyncMock()
        
        # Add user to database with exactly 3 credits
        test_user.credits_remaining = 3
        db_session.add(test_user)
        db_session.commit()
        
        # Initialize service
        file_service = FileProcessingService(db_session)
        
        # Mock large HS matching results
        large_results = []
        for i in range(250):
            large_results.append(
                HSCodeMatchResult(
                    primary_match=HSCodeResult(
                        hs_code="9999.99.99",
                        code_description="Test product",
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
        
        # Mock S3 upload and HS matching
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = "s3://test-bucket/uploads/1/large_products.csv"
            
            with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                mock_hs_service.match_batch_products = AsyncMock(return_value=large_results)
                mock_hs_service.should_require_manual_review.return_value = False
                
                # Execute workflow
                result = await file_service.process_file_with_hs_matching(
                    file=file,
                    user=test_user,
                    country_schema="default"
                )
                
                # Verify success with correct credit usage
                assert result["success"] is True
                assert result["products_processed"] == 250
                assert result["credits_used"] == 3  # 250 rows = 3 credits (1 + 2 additional)
                
                # Verify credits were deducted correctly
                db_session.refresh(test_user)
                assert test_user.credits_remaining == 0
                assert test_user.credits_used_this_month == 3