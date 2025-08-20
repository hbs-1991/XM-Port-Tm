"""
Unit tests for database models
"""
import pytest
from models import User, UserRole, ProcessingJob, ProcessingStatus


@pytest.mark.unit
def test_user_creation():
    """Test user model creation"""
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password="hashed_password",
        role=UserRole.USER,
        credits=100,
        is_active=True
    )
    
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.role == UserRole.USER
    assert user.credits == 100
    assert user.is_active is True


@pytest.mark.unit  
def test_processing_job_creation():
    """Test processing job model creation"""
    job = ProcessingJob(
        user_id=1,
        filename="test_file.pdf",
        original_filename="test_file.pdf",
        file_size=1024,
        file_path="/uploads/test_file.pdf",
        status=ProcessingStatus.PENDING,
        progress=0.0
    )
    
    assert job.filename == "test_file.pdf"
    assert job.status == ProcessingStatus.PENDING
    assert job.progress == 0.0