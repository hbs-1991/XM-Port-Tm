"""
HS Code database models
"""
from sqlalchemy import Column, String, Text, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from .base import Base
import uuid


class HSCode(Base):
    """HS Code model for customs classifications"""
    __tablename__ = "hs_codes"
    
    code = Column(String(10), primary_key=True)
    description = Column(Text, nullable=False)
    chapter = Column(String(2), nullable=False)
    section = Column(String(2), nullable=False)
    embedding = Column(JSONB, nullable=True)  # Store embeddings as JSON array
    country = Column(String(3), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('length(country) = 3', name='valid_country_code'),
        CheckConstraint('length(chapter) = 2', name='valid_chapter_code'),
        CheckConstraint('length(section) = 2', name='valid_section_code'),
    )