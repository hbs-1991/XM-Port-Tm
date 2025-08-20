"""
Billing transaction database models
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, CheckConstraint, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import enum
import uuid


class BillingTransactionType(enum.Enum):
    CREDIT_PURCHASE = "CREDIT_PURCHASE"
    SUBSCRIPTION = "SUBSCRIPTION"
    REFUND = "REFUND"


class BillingTransactionStatus(enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class BillingTransaction(Base):
    """Billing transaction model"""
    __tablename__ = "billing_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(BillingTransactionType), nullable=False)
    amount = Column(DECIMAL(10,2), nullable=False)
    currency = Column(String(3), default='USD', nullable=False)
    credits_granted = Column(Integer, default=0, nullable=False)
    payment_provider = Column(String(50), nullable=False)
    payment_id = Column(String(255), nullable=False)
    status = Column(Enum(BillingTransactionStatus), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('amount >= 0', name='positive_amount'),
        CheckConstraint('credits_granted >= 0', name='positive_credits_granted'),
        CheckConstraint('length(currency) = 3', name='valid_currency_code'),
    )
    
    # Relationships
    user = relationship("User", back_populates="billing_transactions")