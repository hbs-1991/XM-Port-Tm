"""
Unit tests for database models
"""
import pytest
import uuid
from decimal import Decimal
from src.models import (
    User, UserRole, SubscriptionTier, ProcessingJob, ProcessingStatus,
    HSCode, ProductMatch, BillingTransaction, BillingTransactionType, BillingTransactionStatus
)


@pytest.mark.unit
def test_user_creation():
    """Test user model creation"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        role=UserRole.USER,
        subscription_tier=SubscriptionTier.FREE,
        credits_remaining=2,
        credits_used_this_month=0,
        company="Test Company",
        country="USA",
        is_active=True
    )
    
    assert user.email == "test@example.com"
    assert user.role == UserRole.USER
    assert user.subscription_tier == SubscriptionTier.FREE
    assert user.credits_remaining == 2
    assert user.credits_used_this_month == 0
    assert user.country == "USA"
    assert user.is_active is True


@pytest.mark.unit  
def test_processing_job_creation():
    """Test processing job model creation"""
    user_id = uuid.uuid4()
    job = ProcessingJob(
        user_id=user_id,
        status=ProcessingStatus.PENDING,
        input_file_name="test_file.pdf",
        input_file_url="https://s3.example.com/files/test_file.pdf",
        input_file_size=1024,
        credits_used=0,
        total_products=0,
        successful_matches=0,
        country_schema="USA"
    )
    
    assert job.input_file_name == "test_file.pdf"
    assert job.status == ProcessingStatus.PENDING
    assert job.input_file_size == 1024
    assert job.country_schema == "USA"


@pytest.mark.unit
def test_hs_code_creation():
    """Test HS code model creation"""
    hs_code = HSCode(
        code="8471300100",
        description="Portable automatic data processing machines weighing not more than 10 kg",
        chapter="84",
        section="16",
        country="USA",
        is_active=True
    )
    
    assert hs_code.code == "8471300100"
    assert hs_code.chapter == "84"
    assert hs_code.section == "16"
    assert hs_code.country == "USA"
    assert hs_code.is_active is True


@pytest.mark.unit
def test_product_match_creation():
    """Test product match model creation"""
    job_id = uuid.uuid4()
    match = ProductMatch(
        job_id=job_id,
        product_description="Test product description",
        quantity=Decimal("2.000"),
        unit_of_measure="pieces",
        value=Decimal("100.00"),
        origin_country="CHN",
        matched_hs_code="8471300100",
        confidence_score=Decimal("0.85"),
        alternative_hs_codes=["8471410100"],
        requires_manual_review=False,
        user_confirmed=False
    )
    
    assert match.product_description == "Test product description"
    assert match.confidence_score == Decimal("0.85")
    assert match.origin_country == "CHN"
    assert match.user_confirmed is False


@pytest.mark.unit
def test_billing_transaction_creation():
    """Test billing transaction model creation"""
    user_id = uuid.uuid4()
    transaction = BillingTransaction(
        user_id=user_id,
        type=BillingTransactionType.CREDIT_PURCHASE,
        amount=Decimal("25.00"),
        currency="USD",
        credits_granted=50,
        payment_provider="stripe",
        payment_id="pi_1234567890",
        status=BillingTransactionStatus.COMPLETED
    )
    
    assert transaction.type == BillingTransactionType.CREDIT_PURCHASE
    assert transaction.amount == Decimal("25.00")
    assert transaction.currency == "USD"
    assert transaction.credits_granted == 50
    assert transaction.status == BillingTransactionStatus.COMPLETED