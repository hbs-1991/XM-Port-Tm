"""
Processing job database models
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, CheckConstraint, Text, DECIMAL, BIGINT
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import enum
import uuid


class ProcessingStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProcessingJob(Base):
    """Processing job model"""
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    input_file_name = Column(String(255), nullable=False)
    input_file_url = Column(Text, nullable=False)
    input_file_size = Column(BIGINT, nullable=False)
    output_xml_url = Column(Text, nullable=True)
    xml_generation_status = Column(String(20), nullable=True)  # PENDING, GENERATING, COMPLETED, FAILED
    xml_generated_at = Column(DateTime(timezone=True), nullable=True)
    xml_file_size = Column(Integer, nullable=True)
    credits_used = Column(Integer, default=0, nullable=False)
    processing_time_ms = Column(Integer, nullable=True)
    total_products = Column(Integer, default=0, nullable=False)
    successful_matches = Column(Integer, default=0, nullable=False)
    average_confidence = Column(DECIMAL(3,2), nullable=True)
    country_schema = Column(String(3), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('input_file_size > 0', name='positive_file_size'),
        CheckConstraint('credits_used >= 0', name='positive_credits_used'),
        CheckConstraint('total_products >= 0', name='positive_total_products'),
        CheckConstraint('successful_matches >= 0', name='positive_successful_matches'),
        CheckConstraint('average_confidence >= 0 AND average_confidence <= 1', name='valid_confidence_range'),
        CheckConstraint('length(country_schema) = 3', name='valid_country_schema'),
        CheckConstraint('processing_time_ms >= 0', name='positive_processing_time'),
        CheckConstraint('xml_file_size >= 0', name='positive_xml_file_size'),
        CheckConstraint(
            "xml_generation_status IN ('PENDING', 'GENERATING', 'COMPLETED', 'FAILED') OR xml_generation_status IS NULL", 
            name='valid_xml_generation_status'
        ),
    )
    
    # Relationships
    user = relationship("User", back_populates="processing_jobs")
    product_matches = relationship("ProductMatch", back_populates="processing_job", cascade="all, delete-orphan")