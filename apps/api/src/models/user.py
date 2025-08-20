"""
User database models
"""
from sqlalchemy import Column, String, Integer, Boolean, Enum, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import enum
import uuid


class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    PROJECT_OWNER = "PROJECT_OWNER"


class SubscriptionTier(enum.Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)
    credits_remaining = Column(Integer, default=2, nullable=False)
    credits_used_this_month = Column(Integer, default=0, nullable=False)
    company_name = Column(String(100), nullable=True)
    country = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('credits_remaining >= 0', name='positive_credits'),
        CheckConstraint('credits_used_this_month >= 0', name='positive_credits_used'),
        CheckConstraint('length(country) = 3', name='valid_country_code'),
    )
    
    # Relationships
    processing_jobs = relationship("ProcessingJob", back_populates="user", cascade="all, delete-orphan")
    billing_transactions = relationship("BillingTransaction", back_populates="user", cascade="all, delete-orphan")