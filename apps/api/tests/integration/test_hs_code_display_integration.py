"""
Integration tests for HS code display functionality
"""
import pytest
import asyncio
import uuid
from decimal import Decimal
from unittest.mock import patch, AsyncMock

from src.api.v1.ws import manager
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch


@pytest.fixture
async def sample_job_with_matches(db_session):
    """Create a sample processing job with product matches"""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        subscription_tier=SubscriptionTier.FREE,
        credits_remaining=100
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create processing job
    job = ProcessingJob(
        user_id=user.id,
        input_file_name="test_products.csv",
        input_file_url="s3://bucket/test_products.csv",
        input_file_size=1024,
        country_schema="USA",
        status=ProcessingStatus.COMPLETED,
        total_products=3,
        successful_matches=3,
        average_confidence=Decimal("0.85"),
        credits_used=3
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Create product matches with different confidence levels
    matches = [
        ProductMatch(
            job_id=job.id,
            product_description="Cotton T-shirt",
            quantity=Decimal("10"),
            unit_of_measure="pieces",
            value=Decimal("100.00"),
            origin_country="VNM",
            matched_hs_code="6109.10.00",
            confidence_score=Decimal("0.95"),
            alternative_hs_codes=["6109.90.00", "6110.10.00"],
            requires_manual_review=False,
            user_confirmed=True,
            vector_store_reasoning="High confidence match for cotton textiles"
        ),
        ProductMatch(
            job_id=job.id,
            product_description="Wool sweater",
            quantity=Decimal("5"),
            unit_of_measure="pieces",
            value=Decimal("250.00"),
            origin_country="ITA",
            matched_hs_code="6110.20.00",
            confidence_score=Decimal("0.85"),
            alternative_hs_codes=["6110.10.00"],
            requires_manual_review=False,
            user_confirmed=False,
            vector_store_reasoning="Good confidence match for wool garments"
        ),
        ProductMatch(
            job_id=job.id,
            product_description="Generic fabric",
            quantity=Decimal("20"),
            unit_of_measure="meters",
            value=Decimal("50.00"),
            origin_country="CHN",
            matched_hs_code="5208.10.00",
            confidence_score=Decimal("0.70"),
            alternative_hs_codes=["5208.20.00", "5209.10.00"],
            requires_manual_review=True,
            user_confirmed=False,
            vector_store_reasoning="Low confidence match for generic fabric"
        )
    ]
    
    for match in matches:
        db_session.add(match)
    
    db_session.commit()
    
    for match in matches:
        db_session.refresh(match)
    
    return {
        "user": user,
        "job": job,
        "matches": matches
    }


class TestHSCodeDisplayIntegration:
    """Integration tests for HS code display workflow"""
    
    async def test_complete_hs_code_workflow(self, client, sample_job_with_matches, auth_headers):
        """Test the complete HS code display and editing workflow"""
        job_data = await sample_job_with_matches
        user = job_data["user"]
        job = job_data["job"]
        matches = job_data["matches"]
        
        # Test 1: Get job products with HS codes
        response = await client.get(
            f"/api/v1/processing/jobs/{job.id}/products",
            headers=auth_headers(user)
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == str(job.id)
        assert data["status"] == "COMPLETED"
        assert data["total_products"] == 3
        assert data["high_confidence_count"] == 1  # Only one >= 0.95
        assert data["requires_review_count"] == 1  # Only one requiring review
        
        products = data["products"]
        assert len(products) == 3
        
        # Verify confidence levels are calculated correctly
        confidence_levels = [p["confidence_level"] for p in products]
        assert "High" in confidence_levels  # 0.95
        assert "Medium" in confidence_levels  # 0.85
        assert "Low" in confidence_levels  # 0.70
        
        # Test 2: Update HS code for a product
        product_to_update = products[2]  # Low confidence product
        assert product_to_update["requires_manual_review"] is True
        
        new_hs_code = "5209.20.00"
        response = await client.put(
            f"/api/v1/processing/jobs/{job.id}/products/{product_to_update['id']}/hs-code",
            json={"hs_code": new_hs_code},
            headers=auth_headers(user)
        )
        assert response.status_code == 200
        
        update_result = response.json()
        assert update_result["success"] is True
        assert update_result["new_hs_code"] == new_hs_code
        
        # Test 3: Verify the update persisted
        response = await client.get(
            f"/api/v1/processing/jobs/{job.id}/products",
            headers=auth_headers(user)
        )
        assert response.status_code == 200
        
        updated_products = response.json()["products"]
        updated_product = next(p for p in updated_products if p["id"] == product_to_update["id"])
        
        assert updated_product["hs_code"] == new_hs_code
        assert updated_product["user_confirmed"] is True
        assert updated_product["requires_manual_review"] is False
    
    async def test_websocket_hs_matching_notifications(self, sample_job_with_matches):
        """Test WebSocket notifications for HS matching completion"""
        job_data = await sample_job_with_matches
        user = job_data["user"]
        job = job_data["job"]
        
        # Mock WebSocket connection
        sent_messages = []
        
        async def mock_send_personal_message(message, user_id):
            sent_messages.append({"message": message, "user_id": user_id})
        
        with patch.object(manager, 'send_personal_message', mock_send_personal_message):
            # Simulate HS matching completion
            await manager.send_hs_matching_update(
                job_id=str(job.id),
                user_id=str(user.id),
                status="completed",
                data={
                    "totalProducts": 3,
                    "processedProducts": 3,
                    "highConfidenceMatches": 1,
                    "averageConfidence": 0.85,
                    "requiresReview": 1,
                    "completedAt": "2025-01-15T10:30:00Z"
                }
            )
        
        # Verify notification was sent
        assert len(sent_messages) == 1
        message = sent_messages[0]["message"]
        
        assert message["type"] == "hs_matching_update"
        assert message["data"]["jobId"] == str(job.id)
        assert message["data"]["status"] == "completed"
        assert message["data"]["totalProducts"] == 3
        assert message["data"]["highConfidenceMatches"] == 1
        assert message["data"]["requiresReview"] == 1
    
    async def test_hs_code_validation_edge_cases(self, client, sample_job_with_matches, auth_headers):
        """Test HS code validation with edge cases"""
        job_data = await sample_job_with_matches
        user = job_data["user"]
        job = job_data["job"]
        matches = job_data["matches"]
        
        product_id = str(matches[0].id)
        
        # Test valid edge cases
        valid_codes = [
            "610910",        # 6 digits
            "6109.10",       # 6 + 2 digits
            "6109.10.00",    # 6 + 2 + 2 digits
            "6109100000"     # 10 digits
        ]
        
        for valid_code in valid_codes:
            response = await client.put(
                f"/api/v1/processing/jobs/{job.id}/products/{product_id}/hs-code",
                json={"hs_code": valid_code},
                headers=auth_headers(user)
            )
            assert response.status_code == 200
            assert response.json()["new_hs_code"] == valid_code
        
        # Test invalid codes
        invalid_codes = [
            "12345",         # Too short
            "12345678901",   # Too long
            "abcd.10.00",    # Contains letters
            "6109..10.00",   # Double dots
            "6109.1.00",     # Invalid dot structure
        ]
        
        for invalid_code in invalid_codes:
            response = await client.put(
                f"/api/v1/processing/jobs/{job.id}/products/{product_id}/hs-code",
                json={"hs_code": invalid_code},
                headers=auth_headers(user)
            )
            assert response.status_code == 422  # Validation error
    
    async def test_unauthorized_access_to_other_user_data(self, client, sample_job_with_matches, auth_headers):
        """Test that users cannot access other users' job data"""
        job_data = await sample_job_with_matches
        job = job_data["job"]
        
        # Create another user
        other_user = User(
            email="other@example.com",
            hashed_password="hashed_password",
            subscription_tier=SubscriptionTier.FREE,
            credits_remaining=100
        )
        
        # Try to access job products as different user
        response = await client.get(
            f"/api/v1/processing/jobs/{job.id}/products",
            headers=auth_headers(other_user)
        )
        assert response.status_code == 404
        
        # Try to update HS code as different user
        response = await client.put(
            f"/api/v1/processing/jobs/{job.id}/products/{str(uuid.uuid4())}/hs-code",
            json={"hs_code": "6109.10.00"},
            headers=auth_headers(other_user)
        )
        assert response.status_code == 404
    
    async def test_export_functionality_with_hs_codes(self, client, sample_job_with_matches, auth_headers):
        """Test that export functionality includes HS codes"""
        job_data = await sample_job_with_matches
        user = job_data["user"]
        job = job_data["job"]
        
        # Get products to simulate export
        response = await client.get(
            f"/api/v1/processing/jobs/{job.id}/products",
            headers=auth_headers(user)
        )
        assert response.status_code == 200
        
        data = response.json()
        products = data["products"]
        
        # Simulate CSV export format
        csv_headers = ["Product Description", "Quantity", "Unit", "Value", "Origin Country", "Unit Price", "HS Code"]
        csv_rows = []
        
        for product in products:
            row = [
                product["product_description"],
                str(product["quantity"]),
                product["unit"],
                str(product["value"]),
                product["origin_country"],
                str(product["unit_price"]),
                product["hs_code"]
            ]
            csv_rows.append(row)
        
        # Verify all products have HS codes
        for row in csv_rows:
            hs_code = row[6]  # HS Code column
            assert len(hs_code) >= 6
            assert hs_code.replace(".", "").isdigit()
        
        # Verify we have the expected number of rows
        assert len(csv_rows) == 3
        
        # Verify specific HS codes are present
        hs_codes = [row[6] for row in csv_rows]
        assert "6109.10.00" in hs_codes
        assert "6110.20.00" in hs_codes
        assert "5208.10.00" in hs_codes