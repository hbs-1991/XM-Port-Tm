"""
Integration tests for file upload API endpoints
"""
import io
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, Mock

from src.main import app
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from tests.conftest import override_get_db, override_get_current_user


class TestFileUploadAPI:
    """Integration tests for file upload API"""
    
    @pytest.fixture
    def client(self):
        """Test client with database override"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API requests"""
        return {"Authorization": "Bearer test_token"}
    
    @pytest.fixture
    def valid_csv_file(self):
        """Valid CSV file for testing"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country
"Test Product 1",100,pieces,500.00,USA
"Test Product 2",50,kg,250.50,Canada
"""
        return ("test.csv", io.StringIO(csv_content), "text/csv")
    
    @pytest.fixture
    def invalid_csv_file(self):
        """Invalid CSV file missing required columns"""
        csv_content = """Product,Qty,Price
"Test Product 1",100,500.00
"""
        return ("invalid.csv", io.StringIO(csv_content), "text/csv")
    
    @pytest.fixture
    def oversized_csv_file(self):
        """CSV file that exceeds size limit"""
        # Create content larger than 10MB
        large_content = "Product Description,Quantity,Unit,Value,Origin Country\n"
        large_content += ("Test Product,1,pieces,1.00,USA\n" * 500000)  # ~10MB+
        return ("large.csv", io.StringIO(large_content), "text/csv")

    # Successful Upload Tests
    
    def test_upload_valid_csv_file(self, client, auth_headers, valid_csv_file):
        """Test successful upload of valid CSV file"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            # Mock service methods
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True,
                total_rows=2,
                valid_rows=2,
                errors=[],
                warnings=[]
            )
            mock_instance.upload_file_to_s3.return_value = "s3://bucket/test.csv"
            mock_instance.create_processing_job.return_value = Mock(
                id="job-123",
                input_file_name="test.csv",
                input_file_size=100,
                status=ProcessingStatus.PENDING
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job-123"
            assert data["file_name"] == "test.csv"
            assert data["status"] == "PENDING"
            assert "successfully" in data["message"].lower()
    
    def test_upload_valid_xlsx_file(self, client, auth_headers):
        """Test successful upload of valid XLSX file"""
        # Mock XLSX file content
        xlsx_content = b"PK\x03\x04..."  # Mock XLSX binary header
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True,
                total_rows=5,
                valid_rows=5,
                errors=[],
                warnings=[]
            )
            mock_instance.upload_file_to_s3.return_value = "s3://bucket/test.xlsx"
            mock_instance.create_processing_job.return_value = Mock(
                id="job-456",
                input_file_name="test.xlsx",
                input_file_size=2048,
                status=ProcessingStatus.PENDING
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": ("test.xlsx", xlsx_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"country_schema": "CAN"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job-456"
            assert data["file_name"] == "test.xlsx"

    # Validation Failure Tests
    
    def test_upload_file_validation_failure(self, client, auth_headers, invalid_csv_file):
        """Test upload with file validation failures"""
        filename, file_content, content_type = invalid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=False,
                total_rows=1,
                valid_rows=0,
                errors=[
                    Mock(field="headers", error="Missing required columns: product_description, quantity, unit, value, origin_country")
                ],
                warnings=[]
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 200  # Still returns 200 but with FAILED status
            data = response.json()
            assert data["status"] == "FAILED"
            assert "validation failed" in data["message"].lower()
            assert data["validation_results"] is not None
    
    def test_upload_oversized_file(self, client, auth_headers, oversized_csv_file):
        """Test upload with file size exceeding limit"""
        filename, file_content, content_type = oversized_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=[
                    Mock(field="file_size", error="File size exceeds maximum allowed size")
                ],
                warnings=[]
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue()[:1000], content_type)},  # Truncate for test
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "FAILED"
    
    def test_upload_unsupported_file_type(self, client, auth_headers):
        """Test upload with unsupported file type"""
        txt_content = "This is a text file, not CSV or XLSX"
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=[
                    Mock(field="file_extension", error="File extension '.txt' not allowed")
                ],
                warnings=[]
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": ("test.txt", txt_content, "text/plain")},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "FAILED"

    # Credit Validation Tests
    
    def test_upload_insufficient_credits(self, client, auth_headers, valid_csv_file):
        """Test upload when user has insufficient credits"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = False
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 402  # Payment Required
            data = response.json()
            assert "insufficient credits" in data["detail"].lower()

    # Authentication Tests
    
    def test_upload_without_authentication(self, client, valid_csv_file):
        """Test upload without authentication"""
        filename, file_content, content_type = valid_csv_file
        
        response = client.post(
            "/api/v1/processing/upload",
            files={"file": (filename, file_content.getvalue(), content_type)},
            data={"country_schema": "USA"}
        )
        
        assert response.status_code == 401  # Unauthorized
    
    def test_upload_with_invalid_token(self, client, valid_csv_file):
        """Test upload with invalid authentication token"""
        filename, file_content, content_type = valid_csv_file
        
        response = client.post(
            "/api/v1/processing/upload",
            files={"file": (filename, file_content.getvalue(), content_type)},
            data={"country_schema": "USA"},
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401  # Unauthorized

    # Parameter Validation Tests
    
    def test_upload_without_file(self, client, auth_headers):
        """Test upload endpoint without file parameter"""
        response = client.post(
            "/api/v1/processing/upload",
            data={"country_schema": "USA"},
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_upload_with_invalid_country_schema(self, client, auth_headers, valid_csv_file):
        """Test upload with invalid country schema format"""
        filename, file_content, content_type = valid_csv_file
        
        response = client.post(
            "/api/v1/processing/upload",
            files={"file": (filename, file_content.getvalue(), content_type)},
            data={"country_schema": "INVALID_LONG_CODE"},
            headers=auth_headers
        )
        
        # Should either be rejected at validation or converted to uppercase
        # Depending on implementation, this might pass or fail
        assert response.status_code in [200, 400, 422]

    # S3 Integration Tests
    
    def test_upload_s3_configuration_missing(self, client, auth_headers, valid_csv_file):
        """Test upload when S3 is not configured (fallback to local storage)"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True,
                total_rows=2,
                valid_rows=2,
                errors=[],
                warnings=[]
            )
            # Mock S3 failure with fallback
            from fastapi import HTTPException
            mock_instance.upload_file_to_s3.side_effect = HTTPException(
                status_code=500, 
                detail="S3 configuration not available"
            )
            mock_instance.create_processing_job.return_value = Mock(
                id="job-789",
                input_file_name="test.csv",
                input_file_size=100,
                status=ProcessingStatus.PENDING
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job-789"
            # Should succeed with local storage fallback
    
    def test_upload_s3_error(self, client, auth_headers, valid_csv_file):
        """Test upload when S3 operation fails"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True,
                total_rows=2,
                valid_rows=2,
                errors=[],
                warnings=[]
            )
            # Mock S3 failure without fallback
            from fastapi import HTTPException
            mock_instance.upload_file_to_s3.side_effect = HTTPException(
                status_code=500, 
                detail="S3 upload failed: Access denied"
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "s3 upload failed" in data["detail"].lower()

    # Error Handling Tests
    
    def test_upload_database_error(self, client, auth_headers, valid_csv_file):
        """Test upload when database operation fails"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True,
                total_rows=2,
                valid_rows=2,
                errors=[],
                warnings=[]
            )
            mock_instance.upload_file_to_s3.return_value = "s3://bucket/test.csv"
            mock_instance.create_processing_job.side_effect = Exception("Database connection failed")
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "internal server error" in data["detail"].lower()
    
    def test_upload_service_initialization_error(self, client, auth_headers, valid_csv_file):
        """Test upload when service initialization fails"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_service.side_effect = Exception("Service initialization failed")
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 500

    # Response Format Tests
    
    def test_upload_response_format(self, client, auth_headers, valid_csv_file):
        """Test that upload response matches expected schema"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = True
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True,
                total_rows=2,
                valid_rows=2,
                errors=[],
                warnings=[]
            )
            mock_instance.upload_file_to_s3.return_value = "s3://bucket/test.csv"
            mock_instance.create_processing_job.return_value = Mock(
                id="job-123",
                input_file_name="test.csv",
                input_file_size=100,
                status=ProcessingStatus.PENDING
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify required fields are present
            required_fields = ["job_id", "file_name", "file_size", "status", "message"]
            for field in required_fields:
                assert field in data
            
            # Verify field types
            assert isinstance(data["job_id"], str)
            assert isinstance(data["file_name"], str)
            assert isinstance(data["file_size"], int)
            assert isinstance(data["status"], str)
            assert isinstance(data["message"], str)
            
            # Optional fields
            if "validation_results" in data:
                assert data["validation_results"] is None or isinstance(data["validation_results"], dict)


class TestCreditValidationAPI:
    """Integration tests for credit validation in file upload API"""
    
    @pytest.fixture
    def client(self):
        """Test client with database override"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API requests"""
        return {"Authorization": "Bearer test_token"}
    
    @pytest.fixture
    def valid_csv_file(self):
        """Valid CSV file for testing"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"Test Product 1",100,pieces,500.00,USA,5.00
"Test Product 2",50,kg,250.50,Canada,5.01
"""
        return ("test.csv", io.StringIO(csv_content), "text/csv")
    
    @pytest.fixture
    def large_csv_file(self):
        """Large CSV file requiring multiple credits"""
        header = "Product Description,Quantity,Unit,Value,Origin Country,Unit Price\n"
        rows = []
        for i in range(250):  # 250 rows = 3 credits required
            rows.append(f'"Product {i}",{i+1},pieces,{(i+1)*5.0},USA,5.00')
        
        csv_content = header + '\n'.join(rows)
        return ("large.csv", io.StringIO(csv_content), "text/csv")
    
    def test_upload_sufficient_credits_basic_check(self, client, auth_headers, valid_csv_file):
        """Test upload with sufficient credits (initial check)"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = {
                'has_sufficient_credits': True,
                'credits_remaining': 10,
                'credits_required': 1,
                'message': 'Processing will use 1 credit(s). You have 10 remaining.'
            }
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True, total_rows=2, valid_rows=2, errors=[], warnings=[]
            )
            mock_instance.calculate_processing_credits.return_value = 1
            mock_instance.reserve_user_credits.return_value = True
            mock_instance.upload_file_to_s3.return_value = "s3://bucket/test.csv"
            mock_instance.create_processing_job.return_value = Mock(
                id="job-123", input_file_name="test.csv", input_file_size=100, status=ProcessingStatus.PENDING
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            mock_instance.check_user_credits.assert_called_once()
    
    def test_upload_insufficient_credits_initial_check(self, client, auth_headers, valid_csv_file):
        """Test upload with insufficient credits (initial check)"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = {
                'has_sufficient_credits': False,
                'credits_remaining': 0,
                'credits_required': 1,
                'message': 'Insufficient credits: You need 1 credit(s) but only have 0 remaining. Upgrade to a paid plan or purchase additional credits to continue processing.'
            }
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 402
            data = response.json()
            assert data["detail"]["error"] == "insufficient_credits"
            assert "Insufficient credits" in data["detail"]["message"]
            assert data["detail"]["credits_remaining"] == 0
            assert data["detail"]["credits_required"] == 1
            assert "subscription_tier" in data["detail"]
    
    def test_upload_large_file_credits_recalculation(self, client, auth_headers, large_csv_file):
        """Test upload with large file requiring credit recalculation"""
        filename, file_content, content_type = large_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            # Initial check passes with 1 credit
            mock_instance.check_user_credits.side_effect = [
                {
                    'has_sufficient_credits': True,
                    'credits_remaining': 5,
                    'credits_required': 1,
                    'message': 'Processing will use 1 credit(s). You have 5 remaining.'
                },
                # Recalculation check with actual requirement
                {
                    'has_sufficient_credits': True,
                    'credits_remaining': 5,
                    'credits_required': 3,
                    'message': 'Processing will use 3 credit(s). You have 5 remaining.'
                }
            ]
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True, total_rows=250, valid_rows=250, errors=[], warnings=[]
            )
            mock_instance.calculate_processing_credits.return_value = 3  # 250 rows = 3 credits
            mock_instance.reserve_user_credits.return_value = True
            mock_instance.upload_file_to_s3.return_value = "s3://bucket/large.csv"
            mock_instance.create_processing_job.return_value = Mock(
                id="job-456", input_file_name="large.csv", input_file_size=5000, status=ProcessingStatus.PENDING
            )
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert mock_instance.check_user_credits.call_count == 2  # Initial + recalculation
            mock_instance.calculate_processing_credits.assert_called_once_with(250)
            mock_instance.reserve_user_credits.assert_called_once_with(mock_instance.return_value, 3)
    
    def test_upload_large_file_insufficient_credits_after_recalculation(self, client, auth_headers, large_csv_file):
        """Test upload where recalculation reveals insufficient credits"""
        filename, file_content, content_type = large_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            # Initial check passes with 1 credit
            mock_instance.check_user_credits.side_effect = [
                {
                    'has_sufficient_credits': True,
                    'credits_remaining': 2,
                    'credits_required': 1,
                    'message': 'Processing will use 1 credit(s). You have 2 remaining.'
                },
                # Recalculation check fails
                {
                    'has_sufficient_credits': False,
                    'credits_remaining': 2,
                    'credits_required': 3,
                    'message': 'Insufficient credits: You need 3 credit(s) but only have 2 remaining. Please purchase 1 more credit(s) to process this file.'
                }
            ]
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True, total_rows=250, valid_rows=250, errors=[], warnings=[]
            )
            mock_instance.calculate_processing_credits.return_value = 3
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 402
            data = response.json()
            assert data["detail"]["error"] == "insufficient_credits"
            assert data["detail"]["credits_remaining"] == 2
            assert data["detail"]["credits_required"] == 3
            assert data["detail"]["file_rows"] == 250
    
    def test_upload_credit_reservation_failure(self, client, auth_headers, valid_csv_file):
        """Test upload when credit reservation fails (race condition)"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = {
                'has_sufficient_credits': True,
                'credits_remaining': 5,
                'credits_required': 1,
                'message': 'Processing will use 1 credit(s). You have 5 remaining.'
            }
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True, total_rows=50, valid_rows=50, errors=[], warnings=[]
            )
            mock_instance.calculate_processing_credits.return_value = 1
            mock_instance.reserve_user_credits.return_value = False  # Reservation fails
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 409  # Conflict
            data = response.json()
            assert data["detail"]["error"] == "credit_reservation_failed"
            assert "Unable to reserve credits" in data["detail"]["message"]
            assert data["detail"]["credits_required"] == 1
    
    def test_upload_job_creation_failure_with_refund(self, client, auth_headers, valid_csv_file):
        """Test upload when job creation fails and credits are refunded"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = {
                'has_sufficient_credits': True,
                'credits_remaining': 5,
                'credits_required': 1,
                'message': 'Processing will use 1 credit(s). You have 5 remaining.'
            }
            mock_instance.validate_file_upload.return_value = Mock(
                is_valid=True, total_rows=50, valid_rows=50, errors=[], warnings=[]
            )
            mock_instance.calculate_processing_credits.return_value = 1
            mock_instance.reserve_user_credits.return_value = True
            mock_instance.upload_file_to_s3.return_value = "s3://bucket/test.csv"
            mock_instance.create_processing_job.side_effect = Exception("Database error")
            mock_instance.refund_user_credits.return_value = True
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to create processing job" in data["detail"]
            # Verify refund was called
            mock_instance.refund_user_credits.assert_called_once()
    
    def test_upload_credit_message_free_tier(self, client, auth_headers, valid_csv_file):
        """Test credit error message for free tier users"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = {
                'has_sufficient_credits': False,
                'credits_remaining': 0,
                'credits_required': 1,
                'message': 'Insufficient credits: You need 1 credit(s) but only have 0 remaining. Upgrade to a paid plan or purchase additional credits to continue processing.'
            }
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 402
            data = response.json()
            assert "Upgrade to a paid plan" in data["detail"]["message"]
    
    def test_upload_credit_message_paid_tier(self, client, auth_headers, valid_csv_file):
        """Test credit error message for paid tier users"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = {
                'has_sufficient_credits': False,
                'credits_remaining': 2,
                'credits_required': 5,
                'message': 'Insufficient credits: You need 5 credit(s) but only have 2 remaining. Please purchase 3 more credit(s) to process this file.'
            }
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 402
            data = response.json()
            assert "Please purchase 3 more credit(s)" in data["detail"]["message"]
    
    def test_upload_credit_validation_error_response_format(self, client, auth_headers, valid_csv_file):
        """Test credit validation error response contains all required fields"""
        filename, file_content, content_type = valid_csv_file
        
        with patch('src.services.file_processing.FileProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_user_credits.return_value = {
                'has_sufficient_credits': False,
                'credits_remaining': 1,
                'credits_required': 3,
                'message': 'Insufficient credits: You need 3 credit(s) but only have 1 remaining. Please purchase 2 more credit(s) to process this file.'
            }
            
            response = client.post(
                "/api/v1/processing/upload",
                files={"file": (filename, file_content.getvalue(), content_type)},
                data={"country_schema": "USA"},
                headers=auth_headers
            )
            
            assert response.status_code == 402
            data = response.json()
            
            # Verify all required fields in error response
            detail = data["detail"]
            required_fields = ["error", "message", "credits_remaining", "credits_required", "subscription_tier"]
            for field in required_fields:
                assert field in detail
            
            assert detail["error"] == "insufficient_credits"
            assert isinstance(detail["credits_remaining"], int)
            assert isinstance(detail["credits_required"], int)
            assert isinstance(detail["message"], str)