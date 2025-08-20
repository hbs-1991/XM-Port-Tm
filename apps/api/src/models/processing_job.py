"""
Processing job database models
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, Float, JSON, DateTime
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJob(BaseModel):
    """Processing job model"""
    __tablename__ = "processing_jobs"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    
    # Processing results
    extracted_data = Column(JSON)
    hs_code_matches = Column(JSON)
    xml_output = Column(String)
    
    # Error handling
    error_message = Column(String)
    
    # Completion tracking
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="processing_jobs")