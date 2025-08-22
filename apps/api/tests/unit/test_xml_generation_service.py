"""
Unit tests for XML Generation Service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from src.services.xml_generation import (
    XMLGenerationService,
    CountrySchema,
    XMLGenerationResult,
    XMLGenerationConfig,
    XMLGenerationError,
    XMLValidationError,
    xml_generation_service
)
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch


class TestXMLGenerationService:
    """Test cases for XMLGenerationService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = XMLGenerationService()
        
        # Mock processing job
        self.mock_job = Mock(spec=ProcessingJob)
        self.mock_job.id = uuid4()
        self.mock_job.user_id = uuid4()
        self.mock_job.country_schema = "TKM"
        self.mock_job.total_products = 2
        self.mock_job.successful_matches = 2
        self.mock_job.created_at = datetime.now(timezone.utc)
        
        # Mock product matches
        self.mock_products = [
            Mock(spec=ProductMatch),
            Mock(spec=ProductMatch)
        ]
        
        # Configure first product
        self.mock_products[0].id = uuid4()
        self.mock_products[0].product_description = "Test Product 1"
        self.mock_products[0].matched_hs_code = "1234567890"
        self.mock_products[0].quantity = Decimal('10.500')
        self.mock_products[0].unit_of_measure = "KG"
        self.mock_products[0].value = Decimal('100.00')
        self.mock_products[0].origin_country = "USA"
        self.mock_products[0].confidence_score = Decimal('0.95')
        self.mock_products[0].alternative_hs_codes = ["1234567891", "1234567892"]
        self.mock_products[0].vector_store_reasoning = "High confidence match"
        self.mock_products[0].requires_manual_review = False
        self.mock_products[0].user_confirmed = True
        
        # Configure second product
        self.mock_products[1].id = uuid4()
        self.mock_products[1].product_description = "Test Product 2"
        self.mock_products[1].matched_hs_code = "9876543210"
        self.mock_products[1].quantity = Decimal('5.250')
        self.mock_products[1].unit_of_measure = "PCS"
        self.mock_products[1].value = Decimal('200.00')
        self.mock_products[1].origin_country = "GBR"
        self.mock_products[1].confidence_score = Decimal('0.88')
        self.mock_products[1].alternative_hs_codes = None
        self.mock_products[1].vector_store_reasoning = None
        self.mock_products[1].requires_manual_review = True
        self.mock_products[1].user_confirmed = False
    
    def test_initialization_success(self):
        """Test successful service initialization"""
        service = XMLGenerationService()
        
        assert service.settings is not None
        assert service.jinja_env is not None
        assert service.xml_parser is not None
        assert service.xml_serializer is not None
        assert CountrySchema.TURKMENISTAN in service._country_configs
    
    def test_get_supported_countries(self):
        """Test getting list of supported countries"""
        countries = self.service.get_supported_countries()
        
        assert isinstance(countries, list)
        assert CountrySchema.TURKMENISTAN in countries
        assert len(countries) >= 1
    
    def test_get_country_config_valid(self):
        """Test getting valid country configuration"""
        config = self.service.get_country_config(CountrySchema.TURKMENISTAN)
        
        assert config is not None
        assert isinstance(config, XMLGenerationConfig)
        assert config.country_schema == CountrySchema.TURKMENISTAN
        assert config.template_name == "asycuda_turkmenistan.xml.j2"
        assert config.encoding == "utf-8"
        assert config.validate_output is True
    
    def test_get_country_config_invalid(self):
        """Test getting invalid country configuration"""
        # Create a mock country schema that doesn't exist
        with patch('src.services.xml_generation.CountrySchema') as mock_schema:
            mock_schema.INVALID = "INV"
            config = self.service.get_country_config(mock_schema.INVALID)
            
            assert config is None
    
    def test_prepare_template_context_success(self):
        """Test successful template context preparation"""
        config = XMLGenerationConfig(
            country_schema=CountrySchema.TURKMENISTAN,
            template_name="test_template.xml.j2",
            encoding="utf-8"
        )
        
        context = self.service._prepare_template_context(
            self.mock_job, 
            self.mock_products, 
            config
        )
        
        # Verify job data
        assert 'job' in context
        assert context['job']['id'] == str(self.mock_job.id)
        assert context['job']['country_schema'] == self.mock_job.country_schema
        assert context['job']['total_products'] == self.mock_job.total_products
        
        # Verify declaration data
        assert 'declaration' in context
        assert 'id' in context['declaration']
        assert 'reference' in context['declaration']
        assert context['declaration']['country_code'] == 'TKM'
        
        # Verify product data
        assert 'products' in context
        assert context['product_count'] == 2
        assert len(context['products']) == 2
        
        # Verify summary statistics
        assert 'summary' in context
        assert context['summary']['total_quantity'] == Decimal('15.750')  # 10.500 + 5.250
        assert context['summary']['total_value'] == Decimal('300.00')     # 100.00 + 200.00
        assert context['summary']['hs_code_count'] == 2                   # 2 unique HS codes
        
        # Verify generation metadata
        assert 'generation' in context
        assert context['generation']['software'] == 'XM-Port'
        assert context['generation']['encoding'] == 'utf-8'
    
    @patch('src.services.xml_generation.XMLGenerationService._generate_from_template')
    @patch('src.services.xml_generation.XMLGenerationService._validate_xml_content')
    async def test_generate_xml_success(self, mock_validate, mock_template):
        """Test successful XML generation"""
        # Setup mocks
        mock_xml_content = '<?xml version="1.0" encoding="UTF-8"?><Declaration></Declaration>'
        mock_template.return_value = mock_xml_content
        mock_validate.return_value = None  # No validation errors
        
        # Execute
        result = await self.service.generate_xml(self.mock_job, self.mock_products)
        
        # Verify result
        assert isinstance(result, XMLGenerationResult)
        assert result.success is True
        assert result.xml_content == mock_xml_content
        assert result.file_path is not None
        assert result.file_path.endswith('.xml')
        assert result.validation_errors is None
        assert result.error_message is None
        assert result.generated_at is not None
        
        # Verify mocks were called
        mock_template.assert_called_once()
        mock_validate.assert_called_once_with(mock_xml_content, CountrySchema.TURKMENISTAN)
    
    async def test_generate_xml_no_products(self):
        """Test XML generation with no products"""
        with pytest.raises(XMLGenerationError) as exc_info:
            await self.service.generate_xml(self.mock_job, [])
        
        assert "No product matches provided" in str(exc_info.value)
    
    async def test_generate_xml_unsupported_country(self):
        """Test XML generation with unsupported country"""
        # Mock unsupported country
        self.mock_job.country_schema = "XXX"
        
        with pytest.raises(XMLGenerationError) as exc_info:
            await self.service.generate_xml(self.mock_job, self.mock_products)
        
        assert "Unsupported country schema" in str(exc_info.value)
    
    @patch('src.services.xml_generation.XMLGenerationService._generate_from_template')
    @patch('src.services.xml_generation.XMLGenerationService._validate_xml_content')
    async def test_generate_xml_validation_failure(self, mock_validate, mock_template):
        """Test XML generation with validation failure"""
        # Setup mocks
        mock_xml_content = 'invalid xml content'
        mock_template.return_value = mock_xml_content
        mock_validate.return_value = ["Missing required element: Declaration"]
        
        # Execute
        result = await self.service.generate_xml(self.mock_job, self.mock_products)
        
        # Verify result
        assert result.success is False
        assert result.xml_content is None
        assert result.validation_errors == ["Missing required element: Declaration"]
        assert "XML validation failed" in result.error_message
    
    def test_generate_from_template_success(self):
        """Test successful template generation"""
        # Create a simple test template
        with patch('jinja2.Environment.get_template') as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = '<?xml version="1.0"?>\n<test>content</test>\n'
            mock_get_template.return_value = mock_template
            
            context = {'test': 'value'}
            result = self.service._generate_from_template('test.xml.j2', context)
            
            assert '<?xml version="1.0"?>' in result
            assert '<test>content</test>' in result
            mock_template.render.assert_called_once_with(**context)
    
    def test_generate_from_template_not_found(self):
        """Test template generation with missing template"""
        with patch('jinja2.Environment.get_template') as mock_get_template:
            from jinja2 import TemplateNotFound
            mock_get_template.side_effect = TemplateNotFound('missing.xml.j2')
            
            with pytest.raises(XMLGenerationError) as exc_info:
                self.service._generate_from_template('missing.xml.j2', {})
            
            assert "Template not found" in str(exc_info.value)
    
    def test_generate_from_template_render_error(self):
        """Test template generation with rendering error"""
        with patch('jinja2.Environment.get_template') as mock_get_template:
            from jinja2 import TemplateError
            mock_template = Mock()
            mock_template.render.side_effect = TemplateError('Rendering failed')
            mock_get_template.return_value = mock_template
            
            with pytest.raises(XMLGenerationError) as exc_info:
                self.service._generate_from_template('error.xml.j2', {})
            
            assert "Template rendering error" in str(exc_info.value)
    
    async def test_validate_xml_content_valid(self):
        """Test XML content validation with valid XML"""
        valid_xml = '<?xml version="1.0"?><Declaration><DeclarationHeader></DeclarationHeader><DeclarationItems><DeclarationItem></DeclarationItem></DeclarationItems></Declaration>'
        
        errors = await self.service._validate_xml_content(valid_xml, CountrySchema.TURKMENISTAN)
        
        assert errors is None
    
    async def test_validate_xml_content_invalid_xml(self):
        """Test XML content validation with invalid XML"""
        invalid_xml = '<?xml version="1.0"?><Declaration><UnclosedTag>'
        
        errors = await self.service._validate_xml_content(invalid_xml, CountrySchema.TURKMENISTAN)
        
        assert errors is not None
        assert len(errors) > 0
        assert "XML parsing error" in errors[0]
    
    async def test_validate_xml_content_missing_elements(self):
        """Test XML content validation with missing required elements"""
        incomplete_xml = '<?xml version="1.0"?><Declaration></Declaration>'
        
        errors = await self.service._validate_xml_content(incomplete_xml, CountrySchema.TURKMENISTAN)
        
        assert errors is not None
        assert len(errors) > 0
        assert any("Missing required element" in error for error in errors)
    
    def test_validate_asycuda_structure_complete(self):
        """Test ASYCUDA structure validation with complete XML"""
        complete_xml = '''<?xml version="1.0"?>
        <Declaration>
            <DeclarationHeader></DeclarationHeader>
            <DeclarationItems>
                <DeclarationItem></DeclarationItem>
            </DeclarationItems>
        </Declaration>'''
        
        errors = self.service._validate_asycuda_structure(complete_xml)
        
        assert len(errors) == 0
    
    def test_validate_asycuda_structure_missing_elements(self):
        """Test ASYCUDA structure validation with missing elements"""
        incomplete_xml = '<?xml version="1.0"?><Declaration></Declaration>'
        
        errors = self.service._validate_asycuda_structure(incomplete_xml)
        
        assert len(errors) > 0
        assert any("Missing required element: DeclarationHeader" in error for error in errors)
        assert any("Missing required element: DeclarationItems" in error for error in errors)
        assert any("Missing required element: DeclarationItem" in error for error in errors)


class TestCountrySchema:
    """Test cases for CountrySchema enum"""
    
    def test_country_schema_values(self):
        """Test country schema enum values"""
        assert CountrySchema.TURKMENISTAN.value == "TKM"
        assert CountrySchema.TURKMENISTAN == "TKM"
    
    def test_country_schema_from_string(self):
        """Test creating country schema from string"""
        schema = CountrySchema("TKM")
        assert schema == CountrySchema.TURKMENISTAN


class TestXMLGenerationResult:
    """Test cases for XMLGenerationResult dataclass"""
    
    def test_successful_result(self):
        """Test creating successful generation result"""
        timestamp = datetime.now(timezone.utc)
        result = XMLGenerationResult(
            success=True,
            xml_content="<xml></xml>",
            file_path="test.xml",
            generated_at=timestamp
        )
        
        assert result.success is True
        assert result.xml_content == "<xml></xml>"
        assert result.file_path == "test.xml"
        assert result.validation_errors is None
        assert result.error_message is None
        assert result.generated_at == timestamp
    
    def test_failed_result(self):
        """Test creating failed generation result"""
        result = XMLGenerationResult(
            success=False,
            validation_errors=["Error 1", "Error 2"],
            error_message="Generation failed"
        )
        
        assert result.success is False
        assert result.xml_content is None
        assert result.file_path is None
        assert result.validation_errors == ["Error 1", "Error 2"]
        assert result.error_message == "Generation failed"


class TestXMLGenerationConfig:
    """Test cases for XMLGenerationConfig dataclass"""
    
    def test_config_creation(self):
        """Test creating XML generation configuration"""
        config = XMLGenerationConfig(
            country_schema=CountrySchema.TURKMENISTAN,
            template_name="test.xml.j2",
            encoding="utf-8",
            validate_output=True,
            include_metadata=False
        )
        
        assert config.country_schema == CountrySchema.TURKMENISTAN
        assert config.template_name == "test.xml.j2"
        assert config.encoding == "utf-8"
        assert config.validate_output is True
        assert config.include_metadata is False


class TestXMLGenerationExceptions:
    """Test cases for custom exceptions"""
    
    def test_xml_generation_error(self):
        """Test XMLGenerationError exception"""
        error = XMLGenerationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_xml_validation_error(self):
        """Test XMLValidationError exception"""
        error = XMLValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, XMLGenerationError)
        assert isinstance(error, Exception)


class TestServiceInstance:
    """Test cases for service instance"""
    
    def test_service_instance_exists(self):
        """Test that service instance is created"""
        assert xml_generation_service is not None
        assert isinstance(xml_generation_service, XMLGenerationService)
    
    def test_service_instance_ready(self):
        """Test that service instance is ready to use"""
        countries = xml_generation_service.get_supported_countries()
        assert len(countries) > 0
        assert CountrySchema.TURKMENISTAN in countries


# Test fixtures for integration testing
@pytest.fixture
def sample_processing_job():
    """Create a sample processing job for testing"""
    job = Mock(spec=ProcessingJob)
    job.id = uuid4()
    job.user_id = uuid4()
    job.country_schema = "TKM"
    job.total_products = 1
    job.successful_matches = 1
    job.created_at = datetime.now(timezone.utc)
    return job


@pytest.fixture
def sample_product_matches():
    """Create sample product matches for testing"""
    product = Mock(spec=ProductMatch)
    product.id = uuid4()
    product.product_description = "Sample Product"
    product.matched_hs_code = "1234567890"
    product.quantity = Decimal('10.00')
    product.unit_of_measure = "KG"
    product.value = Decimal('100.00')
    product.origin_country = "USA"
    product.confidence_score = Decimal('0.95')
    product.alternative_hs_codes = None
    product.vector_store_reasoning = None
    product.requires_manual_review = False
    product.user_confirmed = True
    return [product]


@pytest.mark.asyncio
async def test_integration_generate_xml_complete_workflow(sample_processing_job, sample_product_matches):
    """Integration test for complete XML generation workflow"""
    service = XMLGenerationService()
    
    # This test requires the actual template file to exist
    # In a real test environment, you would mock the template loading
    with patch.object(service, '_generate_from_template') as mock_template:
        mock_template.return_value = '<?xml version="1.0"?><Declaration><DeclarationHeader></DeclarationHeader><DeclarationItems><DeclarationItem></DeclarationItem></DeclarationItems></Declaration>'
        
        result = await service.generate_xml(sample_processing_job, sample_product_matches)
        
        assert result.success is True
        assert result.xml_content is not None
        assert result.file_path is not None
        assert result.generated_at is not None