"""
Product match database models
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, CheckConstraint, Text, DECIMAL, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base
import uuid


class ProductMatch(Base):
    """Product match model"""
    __tablename__ = "product_matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    job_id = Column(UUID(as_uuid=True), ForeignKey("processing_jobs.id", ondelete="CASCADE"), nullable=False)
    product_description = Column(Text, nullable=False)
    quantity = Column(DECIMAL(10,3), nullable=False)
    unit_of_measure = Column(String(50), nullable=False)
    value = Column(DECIMAL(12,2), nullable=False)
    unit_price = Column(DECIMAL(12,2), nullable=True)
    origin_country = Column(String(3), nullable=False)
    matched_hs_code = Column(String(10), nullable=False)
    confidence_score = Column(DECIMAL(3,2), nullable=False)
    alternative_hs_codes = Column(ARRAY(String), nullable=True)
    vector_store_reasoning = Column(Text, nullable=True)
    # Packaging and weights
    packages_count = Column(Integer, nullable=True)
    packages_part = Column(String(20), nullable=True)
    packaging_kind_code = Column(String(10), nullable=True)
    packaging_kind_name = Column(String(100), nullable=True)
    gross_weight = Column(DECIMAL(10,3), nullable=True)
    net_weight = Column(DECIMAL(10,3), nullable=True)
    # Supplementary units
    supplementary_quantity = Column(DECIMAL(12,3), nullable=True)
    supplementary_uom_code = Column(String(10), nullable=True)
    supplementary_uom_name = Column(String(50), nullable=True)
    requires_manual_review = Column(Boolean, default=False, nullable=False)
    user_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='valid_confidence_score'),
        CheckConstraint('quantity > 0', name='positive_quantity'),
        CheckConstraint('value >= 0', name='positive_value'),
        CheckConstraint('length(origin_country) >= 2 AND length(origin_country) <= 3', name='valid_origin_country'),
    )
    
    # Relationships
    processing_job = relationship("ProcessingJob", back_populates="product_matches")
