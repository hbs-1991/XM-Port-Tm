"""
User database models
"""
from sqlalchemy import Column, String, Integer, Boolean, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(BaseModel):
    """User model"""
    __tablename__ = "users"
    
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    credits = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    processing_jobs = relationship("ProcessingJob", back_populates="user")