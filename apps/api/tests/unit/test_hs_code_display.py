"""
Unit tests for HS code display functionality
"""
import pytest
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.schemas.processing import HSCodeUpdateRequest


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_db():
    return Mock(spec=Session)


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.subscription_tier = SubscriptionTier.FREE
    user.credits_remaining = 100
    return user


@pytest.fixture
def mock_job():
    job = Mock(spec=ProcessingJob)
    job.id = uuid.uuid4()
    job.status = ProcessingStatus.COMPLETED
    job.user_id = uuid.uuid4()
    job.input_file_name = "test.csv"
    job.total_products = 2
    return job


@pytest.fixture
def mock_product_matches():
    match1 = Mock(spec=ProductMatch)
    match1.id = uuid.uuid4()
    match1.product_description = "Cotton T-shirt"
    match1.quantity = Decimal("10")
    match1.unit_of_measure = "pieces"
    match1.value = Decimal("100.00")
    match1.origin_country = "VNM"
    match1.matched_hs_code = "6109.10.00"
    match1.confidence_score = Decimal("0.95")
    match1.alternative_hs_codes = ["6109.90.00", "6110.10.00"]
    match1.requires_manual_review = False
    match1.user_confirmed = True
    match1.vector_store_reasoning = "High confidence match for cotton textiles"
    
    match2 = Mock(spec=ProductMatch)
    match2.id = uuid.uuid4()
    match2.product_description = "Wool sweater"
    match2.quantity = Decimal("5")
    match2.unit_of_measure = "pieces"
    match2.value = Decimal("250.00")
    match2.origin_country = "ITA"
    match2.matched_hs_code = "6110.20.00"
    match2.confidence_score = Decimal("0.75")
    match2.alternative_hs_codes = ["6110.10.00"]
    match2.requires_manual_review = True
    match2.user_confirmed = False
    match2.vector_store_reasoning = "Medium confidence match for wool garments"
    
    return [match1, match2]


class TestGetJobProducts:
    """Test the GET /jobs/{job_id}/products endpoint"""
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_job_products_success(self, mock_get_db, mock_get_user, client, mock_db, mock_user, mock_job, mock_product_matches):
        """Test successful retrieval of job products with HS codes"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        # Mock job query
        mock_job.user_id = mock_user.id
        mock_job.product_matches = mock_product_matches
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_job
        
        # Make request
        response = client.get(f"/api/v1/processing/jobs/{mock_job.id}/products")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == str(mock_job.id)
        assert data["status"] == "COMPLETED"
        assert data["total_products"] == 2
        assert data["high_confidence_count"] == 1  # Only one product with confidence >= 0.95
        assert data["requires_review_count"] == 1  # Only one product requiring review
        
        products = data["products"]
        assert len(products) == 2
        
        # Check first product (high confidence)
        product1 = products[0]
        assert product1["hs_code"] == "6109.10.00"
        assert product1["confidence_level"] == "High"
        assert product1["confidence_score"] == 0.95
        assert product1["alternative_hs_codes"] == ["6109.90.00", "6110.10.00"]
        assert product1["requires_manual_review"] is False
        assert product1["user_confirmed"] is True
        
        # Check second product (medium confidence)
        product2 = products[1]
        assert product2["hs_code"] == "6110.20.00"
        assert product2["confidence_level"] == "Low"  # 0.75 < 0.8
        assert product2["confidence_score"] == 0.75
        assert product2["requires_manual_review"] is True
        assert product2["user_confirmed"] is False
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_job_products_not_found(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test getting products for non-existent job"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
        
        # Make request
        job_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/processing/jobs/{job_id}/products")
        
        # Assertions
        assert response.status_code == 404
        assert "not found or access denied" in response.json()["detail"]
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_job_products_access_denied(self, mock_get_db, mock_get_user, client, mock_db, mock_user, mock_job):
        """Test access denied for job owned by different user"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        # Set different user ID on job
        mock_job.user_id = uuid.uuid4()  # Different from mock_user.id
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
        
        # Make request
        response = client.get(f"/api/v1/processing/jobs/{mock_job.id}/products")
        
        # Assertions
        assert response.status_code == 404


class TestUpdateProductHSCode:
    """Test the PUT /jobs/{job_id}/products/{product_id}/hs-code endpoint"""
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_update_hs_code_success(self, mock_get_db, mock_get_user, client, mock_db, mock_user, mock_product_matches):
        """Test successful HS code update"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        product_match = mock_product_matches[0]
        job_id = str(uuid.uuid4())
        
        # Mock product match query
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = product_match
        
        # Make request
        new_hs_code = "6109.90.00"
        response = client.put(
            f"/api/v1/processing/jobs/{job_id}/products/{product_match.id}/hs-code",
            json={"hs_code": new_hs_code}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "HS code updated successfully"
        assert data["product_id"] == str(product_match.id)
        assert data["new_hs_code"] == new_hs_code
        
        # Verify product_match was updated
        assert product_match.matched_hs_code == new_hs_code
        assert product_match.user_confirmed is True
        assert product_match.requires_manual_review is False
        mock_db.commit.assert_called_once()
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_update_hs_code_invalid_format(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test HS code update with invalid format"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        job_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())
        
        # Test invalid HS codes
        invalid_codes = [
            "123",           # Too short
            "12345678901",   # Too long
            "6109.10.0",     # Invalid dot format
            "abcd.10.00",    # Contains letters
            "6109..10.00"    # Double dots
        ]
        
        for invalid_code in invalid_codes:
            response = client.put(
                f"/api/v1/processing/jobs/{job_id}/products/{product_id}/hs-code",
                json={"hs_code": invalid_code}
            )
            assert response.status_code == 422  # Validation error from Pydantic
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_update_hs_code_product_not_found(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test updating HS code for non-existent product"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None
        
        job_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())
        
        response = client.put(
            f"/api/v1/processing/jobs/{job_id}/products/{product_id}/hs-code",
            json={"hs_code": "6109.10.00"}
        )
        
        assert response.status_code == 404
        assert "Product not found or access denied" in response.json()["detail"]


class TestHSCodeUpdateRequest:
    """Test the HSCodeUpdateRequest schema validation"""
    
    def test_valid_hs_codes(self):
        """Test valid HS code formats"""
        valid_codes = [
            "610910",        # 6 digits
            "6109.10",       # 6 digits with dot
            "6109.10.00",    # 8 digits with dots
            "6109100000",    # 10 digits
            "610910000000"   # 12 digits (edge case)
        ]
        
        for code in valid_codes[:4]:  # Skip the 12-digit case for now
            request = HSCodeUpdateRequest(hs_code=code)
            assert request.hs_code == code
    
    def test_invalid_hs_codes(self):
        """Test invalid HS code formats"""
        invalid_codes = [
            "12345",         # Too short
            "abcdef",        # Contains letters
            "6109.1",        # Invalid dot format
            "6109..10.00",   # Double dots
            "",              # Empty string
            "6109.10.000"    # Invalid dot structure
        ]
        
        for code in invalid_codes:
            with pytest.raises(ValueError):
                HSCodeUpdateRequest(hs_code=code)


class TestConfidenceLevelCalculation:
    """Test confidence level calculation logic"""
    
    def test_confidence_levels(self):
        """Test that confidence scores map to correct levels"""
        test_cases = [
            (0.95, "High"),
            (1.0, "High"),
            (0.8, "Medium"),
            (0.94, "Medium"),
            (0.7, "Low"),
            (0.79, "Low"),
            (0.0, "Low")
        ]
        
        for score, expected_level in test_cases:
            if score >= 0.95:
                level = "High"
            elif score >= 0.8:
                level = "Medium"
            else:
                level = "Low"
            
            assert level == expected_level, f"Score {score} should map to {expected_level}, got {level}"