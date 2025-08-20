"""
HS Code database models
"""
from sqlalchemy import Column, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from models.base import BaseModel


class HSCode(BaseModel):
    """HS Code model for customs classifications"""
    __tablename__ = "hs_codes"
    
    code = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    
    # For AI similarity matching
    embedding_vector = Column(String)  # Store as JSON string for now, pgvector later
    
    # Metadata
    tariff_rate = Column(Float, default=0.0)
    units = Column(String)
    is_restricted = Column(String)  # Boolean stored as string