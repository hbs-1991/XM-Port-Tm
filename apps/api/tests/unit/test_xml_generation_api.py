"""
Unit tests for XML Generation API endpoints
"""
import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.v1.xml_generation import generate_xml, get_xml_download, get_xml_generation_status
from src.models.user import User, UserRole, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.services.xml_generation import XMLGenerationResult, CountrySchema, XMLGenerationError, XMLValidationError
from src.schemas.xml_generation import XMLGenerationRequest, CountrySchemaType


class TestXMLGenerationAPI:
    """Test XML Generation API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing"""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.role = UserRole.USER
        user.subscription_tier = SubscriptionTier.PROFESSIONAL
        user.is_active = True
        return user
    
    @pytest.fixture
    def mock_processing_job(self, mock_user):
        """Create a mock processing job for testing"""
        job = Mock(spec=ProcessingJob)
        job.id = uuid.uuid4()
        job.user_id = mock_user.id
        job.status = ProcessingStatus.COMPLETED
        job.successful_matches = 10
        job.total_products = 10
        job.country_schema = "TKM"
        job.xml_generation_status = None
        job.output_xml_url = None
        job.xml_generated_at = None
        job.xml_file_size = None
        job.error_message = None
        job.average_confidence = Decimal("0.95")
        return job
    
    @pytest.fixture
    def mock_product_matches(self, mock_processing_job):
        """Create mock product matches for testing"""
        matches = []
        for i in range(3):
            match = Mock(spec=ProductMatch)
            match.id = uuid.uuid4()
            match.processing_job_id = mock_processing_job.id
            match.product_description = f"Test Product {i+1}"
            match.matched_hs_code = f"123456789{i}"
            match.quantity = Decimal("10.0")
            match.unit_of_measure = "PCS"
            match.value = Decimal("100.0")
            match.origin_country = "USA"
            match.confidence_score = Decimal("0.95")
            matches.append(match)
        return matches
    
    @pytest.fixture
    def mock_xml_generation_result(self):
        """Create a mock XML generation result"""
        return XMLGenerationResult(
            success=True,
            xml_content="<?xml version='1.0'?><root></root>",
            file_path="test.xml",
            s3_url="https://s3.amazonaws.com/bucket/test.xml",
            s3_key="test.xml",
            file_size=1024,
            storage_type="s3",
            download_url="https://s3.amazonaws.com/bucket/signed-url",
            generated_at=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        return Mock(spec=Session)


class TestGenerateXMLEndpoint(TestXMLGenerationAPI):
    """Test POST /processing/{job_id}/generate-xml endpoint"""
    
    @pytest.mark.asyncio
    async def test_generate_xml_success(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_product_matches, 
        mock_xml_generation_result,
        mock_db_session
    ):
        """Test successful XML generation"""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_product_matches
        
        with patch('src.api.v1.xml_generation.XMLGenerationService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.generate_xml = AsyncMock(return_value=mock_xml_generation_result)
            
            # Test the endpoint
            request = XMLGenerationRequest(
                job_id=mock_processing_job.id,
                country_schema=CountrySchemaType.TURKMENISTAN,
                include_metadata=True,
                validate_output=True
            )
            
            result = await generate_xml(
                job_id=mock_processing_job.id,
                request=request,
                current_user=mock_user,
                db=mock_db_session
            )
            
            # Assertions
            assert result.success is True
            assert result.job_id == mock_processing_job.id
            assert result.xml_file_name == f"asycuda_export_{mock_processing_job.id}.xml"
            assert result.download_url == mock_xml_generation_result.download_url
            assert result.country_schema == CountrySchemaType.TURKMENISTAN
            assert result.file_size == mock_xml_generation_result.file_size
            
            # Verify service was called correctly
            mock_service.generate_xml.assert_called_once_with(
                processing_job=mock_processing_job,
                product_matches=mock_product_matches,
                country_schema=CountrySchema.TURKMENISTAN
            )
            
            # Verify job status updates
            assert mock_processing_job.xml_generation_status == "COMPLETED"
            mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_generate_xml_job_not_found(self, mock_user, mock_db_session):
        """Test XML generation with non-existent job"""
        job_id = uuid.uuid4()
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await generate_xml(
                job_id=job_id,
                request=None,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "job_not_found"
    
    @pytest.mark.asyncio
    async def test_generate_xml_invalid_job_status(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_db_session
    ):
        """Test XML generation with job in invalid status"""
        mock_processing_job.status = ProcessingStatus.PENDING
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        
        with pytest.raises(HTTPException) as exc_info:
            await generate_xml(
                job_id=mock_processing_job.id,
                request=None,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_job_status"
    
    @pytest.mark.asyncio
    async def test_generate_xml_no_successful_matches(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_db_session
    ):
        """Test XML generation with no successful matches"""
        mock_processing_job.successful_matches = 0
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        
        with pytest.raises(HTTPException) as exc_info:
            await generate_xml(
                job_id=mock_processing_job.id,
                request=None,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "no_successful_matches"
    
    @pytest.mark.asyncio
    async def test_generate_xml_no_product_matches(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_db_session
    ):
        """Test XML generation with no product matches in database"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        with pytest.raises(HTTPException) as exc_info:
            await generate_xml(
                job_id=mock_processing_job.id,
                request=None,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "no_product_matches"
    
    @pytest.mark.asyncio
    async def test_generate_xml_generation_error(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_product_matches,
        mock_db_session
    ):
        """Test XML generation with service error"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_product_matches
        
        with patch('src.api.v1.xml_generation.XMLGenerationService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.generate_xml = AsyncMock(side_effect=XMLGenerationError("Test error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await generate_xml(
                    job_id=mock_processing_job.id,
                    request=None,
                    current_user=mock_user,
                    db=mock_db_session
                )
            
            assert exc_info.value.status_code == 422
            assert exc_info.value.detail["error"] == "xml_generation_error"
            assert mock_processing_job.xml_generation_status == "FAILED"
    
    @pytest.mark.asyncio
    async def test_generate_xml_validation_error(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_product_matches,
        mock_db_session
    ):
        """Test XML generation with validation error"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_product_matches
        
        with patch('src.api.v1.xml_generation.XMLGenerationService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.generate_xml = AsyncMock(side_effect=XMLValidationError("Validation failed"))
            
            with pytest.raises(HTTPException) as exc_info:
                await generate_xml(
                    job_id=mock_processing_job.id,
                    request=None,
                    current_user=mock_user,
                    db=mock_db_session
                )
            
            assert exc_info.value.status_code == 422
            assert exc_info.value.detail["error"] == "xml_validation_error"
            assert mock_processing_job.xml_generation_status == "FAILED"


class TestXMLDownloadEndpoint(TestXMLGenerationAPI):
    """Test GET /processing/{job_id}/xml-download endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_xml_download_success(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_db_session
    ):
        """Test successful XML download URL generation"""
        # Setup job with completed XML
        mock_processing_job.xml_generation_status = "COMPLETED"
        mock_processing_job.output_xml_url = "https://s3.amazonaws.com/bucket/test.xml"
        mock_processing_job.xml_file_size = 1024
        mock_processing_job.xml_generated_at = datetime.now(timezone.utc)
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        
        with patch('src.api.v1.xml_generation.XMLGenerationService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_storage_service = Mock()
            mock_service._get_storage_service.return_value = mock_storage_service
            mock_storage_service.generate_download_url.return_value = "https://signed-url.com"
            
            result = await get_xml_download(
                job_id=mock_processing_job.id,
                current_user=mock_user,
                db=mock_db_session
            )
            
            assert result.success is True
            assert result.job_id == mock_processing_job.id
            assert result.download_url == "https://signed-url.com"
            assert result.file_name == f"asycuda_export_{mock_processing_job.id}.xml"
            assert result.file_size == 1024
            assert result.content_type == "application/xml"
    
    @pytest.mark.asyncio
    async def test_get_xml_download_job_not_found(self, mock_user, mock_db_session):
        """Test download with non-existent job"""
        job_id = uuid.uuid4()
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_xml_download(
                job_id=job_id,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "job_not_found"
    
    @pytest.mark.asyncio
    async def test_get_xml_download_xml_not_available(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_db_session
    ):
        """Test download when XML is not available"""
        mock_processing_job.xml_generation_status = "PENDING"
        mock_processing_job.output_xml_url = None
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        
        with pytest.raises(HTTPException) as exc_info:
            await get_xml_download(
                job_id=mock_processing_job.id,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "xml_not_available"


class TestXMLStatusEndpoint(TestXMLGenerationAPI):
    """Test GET /processing/{job_id}/xml-status endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_xml_status_success(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_db_session
    ):
        """Test successful XML status retrieval"""
        mock_processing_job.xml_generation_status = "COMPLETED"
        mock_processing_job.xml_generated_at = datetime.now(timezone.utc)
        mock_processing_job.xml_file_size = 1024
        mock_processing_job.output_xml_url = "https://s3.amazonaws.com/bucket/test.xml"
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        
        result = await get_xml_generation_status(
            job_id=mock_processing_job.id,
            current_user=mock_user,
            db=mock_db_session
        )
        
        assert result["job_id"] == str(mock_processing_job.id)
        assert result["xml_generation_status"] == "COMPLETED"
        assert result["xml_available"] is True
        assert result["xml_file_size"] == 1024
        assert result["country_schema"] == "TKM"
        assert result["total_products"] == 10
        assert result["successful_matches"] == 10
        assert result["processing_status"] == ProcessingStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_get_xml_status_job_not_found(self, mock_user, mock_db_session):
        """Test status with non-existent job"""
        job_id = uuid.uuid4()
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_xml_generation_status(
                job_id=job_id,
                current_user=mock_user,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "job_not_found"


class TestXMLGenerationAPIIntegration:
    """Integration tests for XML Generation API"""
    
    @pytest.mark.asyncio
    async def test_complete_xml_generation_workflow(
        self, 
        mock_user, 
        mock_processing_job, 
        mock_product_matches,
        mock_xml_generation_result,
        mock_db_session
    ):
        """Test complete workflow: generate -> check status -> download"""
        # Setup completed processing job
        mock_processing_job.xml_generation_status = "COMPLETED"
        mock_processing_job.output_xml_url = "https://s3.amazonaws.com/bucket/test.xml"
        mock_processing_job.xml_file_size = 1024
        mock_processing_job.xml_generated_at = datetime.now(timezone.utc)
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_processing_job
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_product_matches
        
        with patch('src.api.v1.xml_generation.XMLGenerationService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.generate_xml = AsyncMock(return_value=mock_xml_generation_result)
            mock_storage_service = Mock()
            mock_service._get_storage_service.return_value = mock_storage_service
            mock_storage_service.generate_download_url.return_value = "https://signed-url.com"
            
            # 1. Generate XML
            generate_result = await generate_xml(
                job_id=mock_processing_job.id,
                request=None,
                current_user=mock_user,
                db=mock_db_session
            )
            assert generate_result.success is True
            
            # 2. Check status
            status_result = await get_xml_generation_status(
                job_id=mock_processing_job.id,
                current_user=mock_user,
                db=mock_db_session
            )
            assert status_result["xml_available"] is True
            
            # 3. Get download URL
            download_result = await get_xml_download(
                job_id=mock_processing_job.id,
                current_user=mock_user,
                db=mock_db_session
            )
            assert download_result.success is True
            assert download_result.download_url == "https://signed-url.com"