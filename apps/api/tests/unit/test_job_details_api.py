"""
Unit tests for job details API endpoint
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from unittest.mock import Mock

from src.api.v1.processing import get_job_details
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.models.user import User, SubscriptionTier
from src.core.database import get_db
from src.core.auth import get_current_active_user


class TestJobDetailsAPI:
    """Test cases for job details API endpoint"""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing"""
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            is_active=True,
            credits_remaining=100,
            subscription_tier=SubscriptionTier.PREMIUM
        )
    
    @pytest.fixture
    def mock_job(self, mock_user):
        """Create a mock processing job"""
        return ProcessingJob(
            id=uuid.uuid4(),
            user_id=mock_user.id,
            status=ProcessingStatus.COMPLETED,
            input_file_name="test-products.xlsx",
            input_file_url="s3://bucket/test-products.xlsx",
            input_file_size=12345,
            output_xml_url="s3://bucket/output.xml",
            xml_generation_status="COMPLETED",
            credits_used=5,
            processing_time_ms=15000,
            total_products=10,
            successful_matches=8,
            average_confidence=Decimal('0.85'),
            country_schema="USA",
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    def mock_product_matches(self, mock_job):
        """Create mock product matches"""
        return [
            ProductMatch(
                id=uuid.uuid4(),
                job_id=mock_job.id,
                product_description="Wireless Bluetooth Headphones",
                quantity=Decimal('100.000'),
                unit_of_measure="pcs",
                value=Decimal('2500.00'),
                origin_country="CHN",
                matched_hs_code="8518.30.20",
                confidence_score=Decimal('0.92'),
                alternative_hs_codes=["8518.30.10", "8518.40.00"],
                vector_store_reasoning="Matched based on electronics category",
                requires_manual_review=False,
                user_confirmed=True,
                created_at=datetime.now(timezone.utc)
            ),
            ProductMatch(
                id=uuid.uuid4(),
                job_id=mock_job.id,
                product_description="Organic Cotton T-Shirt",
                quantity=Decimal('50.000'),
                unit_of_measure="pcs",
                value=Decimal('750.00'),
                origin_country="IND",
                matched_hs_code="6109.10.00",
                confidence_score=Decimal('0.65'),
                alternative_hs_codes=["6109.90.10"],
                vector_store_reasoning="Low confidence match - requires review",
                requires_manual_review=True,
                user_confirmed=False,
                created_at=datetime.now(timezone.utc)
            )
        ]
    
    @pytest.fixture
    def mock_db_session(self, mock_job, mock_product_matches):
        """Create a mock database session"""
        db = Mock(spec=Session)
        mock_job.product_matches = mock_product_matches
        
        # Mock query chain
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.first.return_value = mock_job
        db.query.return_value = mock_query
        
        return db
    
    @pytest.mark.asyncio
    async def test_get_job_details_success(self, mock_user, mock_job, mock_db_session):
        """Test successful job details retrieval"""
        job_id = str(mock_job.id)
        
        result = await get_job_details(
            job_id=job_id,
            current_user=mock_user,
            db=mock_db_session
        )
        
        # Verify job details
        assert result["job"]["id"] == job_id
        assert result["job"]["input_file_name"] == "test-products.xlsx"
        assert result["job"]["status"] == "COMPLETED"
        assert result["job"]["country_schema"] == "USA"
        assert result["job"]["credits_used"] == 5
        assert result["job"]["total_products"] == 10
        assert result["job"]["successful_matches"] == 8
        assert result["job"]["has_xml_output"] is True
        
        # Verify product matches
        assert len(result["product_matches"]) == 2
        
        match1 = result["product_matches"][0]
        assert match1["product_description"] == "Wireless Bluetooth Headphones"
        assert match1["matched_hs_code"] == "8518.30.20"
        assert match1["confidence_score"] == 0.92
        assert match1["requires_manual_review"] is False
        assert match1["user_confirmed"] is True
        
        match2 = result["product_matches"][1]
        assert match2["product_description"] == "Organic Cotton T-Shirt"
        assert match2["matched_hs_code"] == "6109.10.00"
        assert match2["confidence_score"] == 0.65
        assert match2["requires_manual_review"] is True
        assert match2["user_confirmed"] is False
        
        # Verify statistics
        stats = result["statistics"]
        assert stats["total_matches"] == 2
        assert stats["high_confidence_matches"] == 1  # Only 1 match >= 0.8
        assert stats["manual_review_required"] == 1
        assert stats["user_confirmed"] == 1
        assert stats["success_rate"] == 80.0  # 8/10 * 100
    
    @pytest.mark.asyncio
    async def test_get_job_details_not_found(self, mock_user, mock_db_session):
        """Test job not found scenario"""
        from fastapi import HTTPException
        
        # Mock empty query result
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        job_id = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await get_job_details(
                job_id=job_id,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_job_details_access_denied(self, mock_user, mock_job, mock_db_session):
        """Test access denied when user doesn't own the job"""
        # Create different user
        other_user = User(
            id=uuid.uuid4(),
            email="other@example.com",
            username="otheruser",
            is_active=True
        )
        
        job_id = str(mock_job.id)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_job_details(
                job_id=job_id,
                current_user=other_user,  # Different user
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 404
        assert "access denied" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_statistics_calculation_empty_matches(self, mock_user, mock_job, mock_db_session):
        """Test statistics calculation with no product matches"""
        # Mock job with no matches
        mock_job.product_matches = []
        mock_job.total_products = 0
        mock_job.successful_matches = 0
        
        job_id = str(mock_job.id)
        
        result = await get_job_details(
            job_id=job_id,
            current_user=mock_user,
            db=mock_db_session
        )
        
        stats = result["statistics"]
        assert stats["total_matches"] == 0
        assert stats["high_confidence_matches"] == 0
        assert stats["manual_review_required"] == 0
        assert stats["user_confirmed"] == 0
        assert stats["success_rate"] == 0
    
    @pytest.mark.asyncio
    async def test_confidence_score_thresholds(self, mock_user, mock_job, mock_db_session):
        """Test confidence score classification thresholds"""
        # Create matches with different confidence levels
        high_confidence = ProductMatch(
            id=uuid.uuid4(),
            job_id=mock_job.id,
            product_description="High Confidence Product",
            quantity=Decimal('10.000'),
            unit_of_measure="pcs",
            value=Decimal('100.00'),
            origin_country="USA",
            matched_hs_code="1234.56.78",
            confidence_score=Decimal('0.85'),  # High confidence >= 0.8
            alternative_hs_codes=[],
            requires_manual_review=False,
            user_confirmed=False,
            created_at=datetime.now(timezone.utc)
        )
        
        low_confidence = ProductMatch(
            id=uuid.uuid4(),
            job_id=mock_job.id,
            product_description="Low Confidence Product",
            quantity=Decimal('5.000'),
            unit_of_measure="pcs",
            value=Decimal('50.00'),
            origin_country="USA",
            matched_hs_code="9876.54.32",
            confidence_score=Decimal('0.75'),  # Below 0.8 threshold
            alternative_hs_codes=[],
            requires_manual_review=True,
            user_confirmed=False,
            created_at=datetime.now(timezone.utc)
        )
        
        mock_job.product_matches = [high_confidence, low_confidence]
        
        job_id = str(mock_job.id)
        
        result = await get_job_details(
            job_id=job_id,
            current_user=mock_user,
            db=mock_db_session
        )
        
        stats = result["statistics"]
        assert stats["total_matches"] == 2
        assert stats["high_confidence_matches"] == 1  # Only 1 >= 0.8
        assert stats["manual_review_required"] == 1
        assert stats["user_confirmed"] == 0
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_user, mock_db_session):
        """Test database error handling"""
        from fastapi import HTTPException
        
        # Mock database error
        mock_db_session.query.side_effect = Exception("Database connection failed")
        
        job_id = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await get_job_details(
                job_id=job_id,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 500
        assert "Error retrieving job details" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_alternative_hs_codes_handling(self, mock_user, mock_job, mock_db_session):
        """Test handling of alternative HS codes"""
        match_with_alternatives = ProductMatch(
            id=uuid.uuid4(),
            job_id=mock_job.id,
            product_description="Product with alternatives",
            quantity=Decimal('10.000'),
            unit_of_measure="pcs",
            value=Decimal('100.00'),
            origin_country="USA",
            matched_hs_code="1234.56.78",
            confidence_score=Decimal('0.75'),
            alternative_hs_codes=["1234.56.79", "1234.56.80", "1234.56.81"],
            vector_store_reasoning="Multiple possible classifications",
            requires_manual_review=True,
            user_confirmed=False,
            created_at=datetime.now(timezone.utc)
        )
        
        mock_job.product_matches = [match_with_alternatives]
        
        job_id = str(mock_job.id)
        
        result = await get_job_details(
            job_id=job_id,
            current_user=mock_user,
            db=mock_db_session
        )
        
        match = result["product_matches"][0]
        assert len(match["alternative_hs_codes"]) == 3
        assert "1234.56.79" in match["alternative_hs_codes"]
        assert "1234.56.80" in match["alternative_hs_codes"]
        assert "1234.56.81" in match["alternative_hs_codes"]
    
    @pytest.mark.asyncio
    async def test_job_status_variants(self, mock_user, mock_job, mock_db_session):
        """Test different job statuses"""
        test_cases = [
            (ProcessingStatus.PENDING, "PENDING"),
            (ProcessingStatus.PROCESSING, "PROCESSING"),
            (ProcessingStatus.COMPLETED, "COMPLETED"),
            (ProcessingStatus.COMPLETED_WITH_ERRORS, "COMPLETED_WITH_ERRORS"),
            (ProcessingStatus.FAILED, "FAILED"),
            (ProcessingStatus.CANCELLED, "CANCELLED")
        ]
        
        for status_enum, status_str in test_cases:
            mock_job.status = status_enum
            mock_job.product_matches = []
            
            job_id = str(mock_job.id)
            
            result = await get_job_details(
                job_id=job_id,
                current_user=mock_user,
                db=mock_db_session
            )
            
            assert result["job"]["status"] == status_str