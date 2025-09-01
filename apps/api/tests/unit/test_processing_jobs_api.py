"""
Tests for processing jobs API with pagination and filtering
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.main import app

client = TestClient(app)

@pytest.fixture
def mock_user():
    """Mock user for testing"""
    user = Mock(spec=User)
    user.id = "123e4567-e89b-12d3-a456-426614174000"
    user.email = "test@example.com"
    user.subscription_tier = SubscriptionTier.BASIC
    user.credits_remaining = 100
    return user

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return Mock(spec=Session)

@pytest.fixture
def sample_jobs():
    """Sample processing jobs for testing"""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    
    jobs = []
    for i in range(75):  # More than one page
        job = Mock(spec=ProcessingJob)
        job.id = f"job-{i:03d}"
        job.user_id = "123e4567-e89b-12d3-a456-426614174000"
        job.input_file_name = f"file_{i:03d}.csv"
        job.status = ProcessingStatus.COMPLETED if i < 50 else ProcessingStatus.PROCESSING
        job.input_file_size = 1024 * (i + 1)
        job.country_schema = "USA"
        job.credits_used = 5
        job.total_products = 100
        job.successful_matches = 95
        job.average_confidence = 0.85
        job.processing_time_ms = 45000
        job.output_xml_url = f"s3://bucket/output_{i}.xml" if i < 50 else None
        job.xml_generation_status = "COMPLETED" if i < 50 else None
        job.error_message = None
        job.created_at = base_time + timedelta(hours=i)
        job.started_at = base_time + timedelta(hours=i, minutes=1)
        job.completed_at = base_time + timedelta(hours=i, minutes=2) if i < 50 else None
        jobs.append(job)
    
    return jobs

class TestProcessingJobsAPI:
    """Test processing jobs API endpoints"""
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_jobs_default_pagination(self, mock_get_db, mock_get_user, mock_user, mock_db_session, sample_jobs):
        """Test default pagination (page 1, limit 50)"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session
        
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 75
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_jobs[:50]
        
        mock_db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/processing/jobs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["jobs"]) == 50
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 50
        assert data["pagination"]["total_count"] == 75
        assert data["pagination"]["total_pages"] == 2
        assert data["pagination"]["has_next"] == True
        assert data["pagination"]["has_prev"] == False
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_jobs_second_page(self, mock_get_db, mock_get_user, mock_user, mock_db_session, sample_jobs):
        """Test second page pagination"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session
        
        # Mock database query for second page
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 75
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_jobs[50:75]  # Remaining 25 jobs
        
        mock_db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/processing/jobs?page=2&limit=50")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["jobs"]) == 25
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["limit"] == 50
        assert data["pagination"]["total_count"] == 75
        assert data["pagination"]["total_pages"] == 2
        assert data["pagination"]["has_next"] == False
        assert data["pagination"]["has_prev"] == True
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_jobs_with_search(self, mock_get_db, mock_get_user, mock_user, mock_db_session, sample_jobs):
        """Test search functionality"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session
        
        # Mock database query with search results
        filtered_jobs = [job for job in sample_jobs if "001" in job.input_file_name]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(filtered_jobs)
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = filtered_jobs
        
        mock_db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/processing/jobs?search=001")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["jobs"]) == len(filtered_jobs)
        assert data["filters"]["search"] == "001"
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_jobs_with_status_filter(self, mock_get_db, mock_get_user, mock_user, mock_db_session, sample_jobs):
        """Test status filtering"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session
        
        # Mock database query with status filter
        filtered_jobs = [job for job in sample_jobs if job.status == ProcessingStatus.COMPLETED]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(filtered_jobs)
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = filtered_jobs
        
        mock_db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/processing/jobs?status=completed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["jobs"]) == len(filtered_jobs)
        assert data["filters"]["status"] == "completed"
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_jobs_with_date_range(self, mock_get_db, mock_get_user, mock_user, mock_db_session, sample_jobs):
        """Test date range filtering"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session
        
        # Mock database query with date filter
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_jobs[:10]
        
        mock_db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/processing/jobs?date_from=2024-01-01&date_to=2024-01-02")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["filters"]["date_from"] == "2024-01-01"
        assert data["filters"]["date_to"] == "2024-01-02"
    
    def test_get_jobs_invalid_page(self):
        """Test invalid page parameter"""
        response = client.get("/api/v1/processing/jobs?page=0")
        
        assert response.status_code == 400
        assert "Page number must be >= 1" in response.json()["detail"]
    
    def test_get_jobs_invalid_limit(self):
        """Test invalid limit parameter"""
        response = client.get("/api/v1/processing/jobs?limit=0")
        
        assert response.status_code == 400
        assert "Limit must be between 1 and 100" in response.json()["detail"]
        
        response = client.get("/api/v1/processing/jobs?limit=101")
        
        assert response.status_code == 400
        assert "Limit must be between 1 and 100" in response.json()["detail"]
    
    def test_get_jobs_invalid_status(self):
        """Test invalid status parameter"""
        response = client.get("/api/v1/processing/jobs?status=invalid_status")
        
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]
    
    def test_get_jobs_invalid_date_format(self):
        """Test invalid date format"""
        response = client.get("/api/v1/processing/jobs?date_from=invalid-date")
        
        assert response.status_code == 400
        assert "date_from must be in YYYY-MM-DD format" in response.json()["detail"]
        
        response = client.get("/api/v1/processing/jobs?date_to=2024/01/01")
        
        assert response.status_code == 400
        assert "date_to must be in YYYY-MM-DD format" in response.json()["detail"]
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_jobs_response_format(self, mock_get_db, mock_get_user, mock_user, mock_db_session, sample_jobs):
        """Test response format and data structure"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session
        
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_jobs[0]]
        
        mock_db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/processing/jobs")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "jobs" in data
        assert "pagination" in data
        assert "filters" in data
        
        # Check job data structure
        job = data["jobs"][0]
        required_fields = [
            "id", "input_file_name", "status", "country_schema", "input_file_size",
            "credits_used", "total_products", "successful_matches", "average_confidence",
            "processing_time_ms", "has_xml_output", "xml_generation_status",
            "created_at", "started_at", "completed_at"
        ]
        
        for field in required_fields:
            assert field in job
        
        # Check pagination structure
        pagination = data["pagination"]
        pagination_fields = ["page", "limit", "total_count", "total_pages", "has_next", "has_prev"]
        
        for field in pagination_fields:
            assert field in pagination
        
        # Check filters structure
        filters = data["filters"]
        filter_fields = ["search", "status", "date_from", "date_to"]
        
        for field in filter_fields:
            assert field in filters
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_jobs_empty_result(self, mock_get_db, mock_get_user, mock_user, mock_db_session):
        """Test empty result handling"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session
        
        # Mock empty database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/processing/jobs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["jobs"]) == 0
        assert data["pagination"]["total_count"] == 0
        assert data["pagination"]["total_pages"] == 0
        assert data["pagination"]["has_next"] == False
        assert data["pagination"]["has_prev"] == False
    
    def test_get_jobs_unauthorized(self):
        """Test unauthorized access"""
        response = client.get("/api/v1/processing/jobs")
        
        # Should return 401 or 422 depending on auth implementation
        assert response.status_code in [401, 422]
    
    @patch('src.api.v1.processing.get_current_active_user')
    @patch('src.api.v1.processing.get_db')
    def test_get_jobs_database_error(self, mock_get_db, mock_get_user, mock_user, mock_db_session):
        """Test database error handling"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session
        
        # Mock database error
        mock_db_session.query.side_effect = Exception("Database connection error")
        
        response = client.get("/api/v1/processing/jobs")
        
        assert response.status_code == 500
        assert "Error retrieving processing jobs" in response.json()["detail"]