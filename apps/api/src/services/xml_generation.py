"""
XML Generation Service for ASYCUDA-compliant export declarations

This service generates XML files compliant with ASYCUDA customs systems 
using xsdata for XML processing and Jinja2 for templating.
"""
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

import jinja2
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from ..models.processing_job import ProcessingJob, ProcessingStatus
from ..models.product_match import ProductMatch
from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Import storage service (will be initialized on first use)
_xml_storage_service = None


class CountrySchema(str, Enum):
    """Supported country schemas for XML generation"""
    TURKMENISTAN = "TKM"
    # Future country support can be added here
    # UZBEKISTAN = "UZB"
    # KAZAKHSTAN = "KAZ"


@dataclass
class XMLGenerationResult:
    """Result of XML generation operation"""
    success: bool
    xml_content: Optional[str] = None
    file_path: Optional[str] = None
    s3_url: Optional[str] = None
    s3_key: Optional[str] = None
    file_size: Optional[int] = None
    storage_type: Optional[str] = None
    download_url: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    error_message: Optional[str] = None
    generated_at: Optional[datetime] = None


@dataclass
class XMLGenerationConfig:
    """Configuration for XML generation"""
    country_schema: CountrySchema
    template_name: str
    encoding: str = "utf-8"
    validate_output: bool = True
    include_metadata: bool = True


class XMLGenerationError(Exception):
    """Custom exception for XML generation errors"""
    pass


class XMLValidationError(XMLGenerationError):
    """Custom exception for XML validation errors"""
    pass


class XMLGenerationService:
    """
    Service for generating ASYCUDA-compliant XML files from product match data
    
    Features:
    - Country-specific XML schema support
    - xsdata integration for XML parsing and validation
    - Jinja2 templating for flexible XML generation
    - Comprehensive error handling and validation
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.templates_dir = Path(__file__).parent.parent / "templates" / "xml"
        self.schemas_dir = Path(__file__).parent.parent / "schemas" / "xml"
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=False,  # XML content should not be autoescaped
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Initialize XML parser and serializer
        self.xml_parser = XmlParser()
        self.xml_serializer = XmlSerializer(
            config=SerializerConfig(
                pretty_print=True,
                xml_declaration=True,
                encoding="UTF-8"
            )
        )
        
        # Country schema configurations
        self._country_configs = {
            CountrySchema.TURKMENISTAN: XMLGenerationConfig(
                country_schema=CountrySchema.TURKMENISTAN,
                template_name="asycuda_turkmenistan.xml.j2",
                encoding="utf-8",
                validate_output=True,
                include_metadata=True
            )
        }
        
        logger.info("XMLGenerationService initialized successfully")
    
    def _get_storage_service(self):
        """Get XML storage service instance (lazy initialization)"""
        global _xml_storage_service
        if _xml_storage_service is None:
            from .xml_storage import xml_storage_service
            _xml_storage_service = xml_storage_service
        return _xml_storage_service
    
    async def generate_xml(
        self, 
        processing_job: ProcessingJob, 
        product_matches: List[ProductMatch],
        country_schema: Optional[CountrySchema] = None
    ) -> XMLGenerationResult:
        """
        Generate XML file for a processing job
        
        Args:
            processing_job: The processing job containing metadata
            product_matches: List of product matches to include in XML
            country_schema: Target country schema (defaults to job's country_schema)
        
        Returns:
            XMLGenerationResult: Result of the generation operation
        """
        try:
            # Determine country schema
            if country_schema is None:
                country_schema = CountrySchema(processing_job.country_schema)
            
            # Validate inputs
            if not product_matches:
                raise XMLGenerationError("No product matches provided for XML generation")
            
            # Get configuration for country
            config = self._get_country_config(country_schema)
            if not config:
                raise XMLGenerationError(f"Unsupported country schema: {country_schema}")
            
            # Prepare template context
            context = self._prepare_template_context(processing_job, product_matches, config)
            
            # Generate XML content from template
            xml_content = self._generate_from_template(config.template_name, context)
            
            # Validate XML if required
            if config.validate_output:
                validation_errors = await self._validate_xml_content(xml_content, country_schema)
                if validation_errors:
                    return XMLGenerationResult(
                        success=False,
                        validation_errors=validation_errors,
                        error_message="XML validation failed"
                    )
            
            # Store XML file using storage service
            storage_service = self._get_storage_service()
            storage_result = await storage_service.upload_xml_file(processing_job, xml_content)
            
            if not storage_result['success']:
                raise XMLGenerationError(f"Failed to store XML file: {storage_result.get('error', 'Unknown error')}")
            
            # Generate download URL
            download_url = None
            if storage_result.get('s3_key'):
                try:
                    download_url = storage_service.generate_download_url(storage_result['s3_key'])
                except Exception as e:
                    logger.warning(f"Failed to generate download URL: {str(e)}")
            
            logger.info(
                f"Successfully generated and stored XML for job {processing_job.id} "
                f"with {len(product_matches)} products, size: {storage_result.get('file_size', 0)} bytes"
            )
            
            return XMLGenerationResult(
                success=True,
                xml_content=xml_content,
                file_path=storage_result.get('file_path'),
                s3_url=storage_result.get('url'),
                s3_key=storage_result.get('s3_key'),
                file_size=storage_result.get('file_size'),
                storage_type=storage_result.get('storage_type'),
                download_url=download_url,
                generated_at=datetime.now(timezone.utc)
            )
            
        except XMLGenerationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in XML generation: {str(e)}", exc_info=True)
            raise XMLGenerationError(f"XML generation failed: {str(e)}")
    
    def _get_country_config(self, country_schema: CountrySchema) -> Optional[XMLGenerationConfig]:
        """Get configuration for specific country schema"""
        return self._country_configs.get(country_schema)
    
    def _prepare_template_context(
        self, 
        processing_job: ProcessingJob, 
        product_matches: List[ProductMatch],
        config: XMLGenerationConfig
    ) -> Dict[str, Any]:
        """
        Prepare template context with job and product data
        
        Args:
            processing_job: Processing job metadata
            product_matches: Product matches for XML
            config: Generation configuration
        
        Returns:
            Dictionary containing template context
        """
        # Calculate totals and statistics
        total_quantity = sum(Decimal(str(pm.quantity)) for pm in product_matches)
        total_value = sum(Decimal(str(pm.value)) for pm in product_matches)
        avg_confidence = sum(Decimal(str(pm.confidence_score)) for pm in product_matches) / len(product_matches)
        
        # Group products by HS code for summary
        hs_code_summary = {}
        for pm in product_matches:
            hs_code = pm.matched_hs_code
            if hs_code not in hs_code_summary:
                hs_code_summary[hs_code] = {
                    'count': 0,
                    'total_quantity': Decimal('0'),
                    'total_value': Decimal('0'),
                    'products': []
                }
            
            hs_code_summary[hs_code]['count'] += 1
            hs_code_summary[hs_code]['total_quantity'] += Decimal(str(pm.quantity))
            hs_code_summary[hs_code]['total_value'] += Decimal(str(pm.value))
            hs_code_summary[hs_code]['products'].append(pm)
        
        # Create template context
        context = {
            # Job metadata
            'job': {
                'id': str(processing_job.id),
                'created_at': processing_job.created_at,
                'country_schema': processing_job.country_schema,
                'total_products': processing_job.total_products,
                'successful_matches': processing_job.successful_matches,
                'user_id': str(processing_job.user_id)
            },
            
            # Declaration metadata
            'declaration': {
                'id': str(uuid.uuid4()),  # Unique declaration ID
                'reference': f"XMP-{processing_job.id.hex[:8].upper()}",
                'created_at': datetime.now(timezone.utc),
                'country_code': config.country_schema.value,
                'currency': 'USD',  # Default currency
                'exchange_rate': Decimal('1.0')  # Default exchange rate
            },
            
            # Product data
            'products': product_matches,
            'product_count': len(product_matches),
            
            # Summary statistics
            'summary': {
                'total_quantity': total_quantity,
                'total_value': total_value,
                'average_confidence': avg_confidence,
                'hs_code_count': len(hs_code_summary),
                'hs_code_summary': hs_code_summary
            },
            
            # Template metadata
            'generation': {
                'timestamp': datetime.now(timezone.utc),
                'software': 'XM-Port',
                'version': '1.0.0',
                'encoding': config.encoding
            }
        }
        
        return context
    
    def _generate_from_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Generate XML content from Jinja2 template
        
        Args:
            template_name: Name of the template file
            context: Template context data
        
        Returns:
            Generated XML content as string
        """
        try:
            template = self.jinja_env.get_template(template_name)
            xml_content = template.render(**context)
            
            # Clean up any extra whitespace
            lines = xml_content.split('\n')
            cleaned_lines = [line.rstrip() for line in lines if line.strip()]
            xml_content = '\n'.join(cleaned_lines)
            
            return xml_content
            
        except jinja2.TemplateNotFound as e:
            raise XMLGenerationError(f"Template not found: {template_name}")
        except jinja2.TemplateError as e:
            raise XMLGenerationError(f"Template rendering error: {str(e)}")
    
    async def _validate_xml_content(
        self, 
        xml_content: str, 
        country_schema: CountrySchema
    ) -> Optional[List[str]]:
        """
        Validate XML content against schema
        
        Args:
            xml_content: Generated XML content
            country_schema: Target country schema
        
        Returns:
            List of validation errors or None if valid
        """
        validation_errors = []
        
        try:
            # Basic XML parsing validation
            from xml.etree import ElementTree as ET
            try:
                ET.fromstring(xml_content.encode('utf-8'))
            except ET.ParseError as e:
                validation_errors.append(f"XML parsing error: {str(e)}")
                return validation_errors
            
            # Check for required elements based on country schema
            if country_schema == CountrySchema.TURKMENISTAN:
                validation_errors.extend(
                    self._validate_asycuda_structure(xml_content)
                )
            
            # Additional validations can be added here
            # For example, XSD schema validation with xsdata
            
            return validation_errors if validation_errors else None
            
        except Exception as e:
            logger.error(f"XML validation error: {str(e)}", exc_info=True)
            return [f"Validation error: {str(e)}"]
    
    def _validate_asycuda_structure(self, xml_content: str) -> List[str]:
        """
        Validate ASYCUDA-specific XML structure for Turkmenistan
        
        Args:
            xml_content: XML content to validate
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Required ASYCUDA 4.1 root elements
        required_root_elements = [
            'ASYCUDA_Declaration',
            'Document_Header',
            'Declaration_Items',
            'Summary'
        ]
        
        for element in required_root_elements:
            if f'<{element}' not in xml_content and f'<{element}>' not in xml_content:
                errors.append(f"Missing required ASYCUDA root element: {element}")
        
        # Required header elements
        required_header_elements = [
            'Document_number',
            'Registration_Date',
            'Declaration_Type_Code',
            'Customs_Office_Code',
            'Currency_Code',
            'Total_Number_of_Items'
        ]
        
        for element in required_header_elements:
            if f'<{element}' not in xml_content and f'<{element}>' not in xml_content:
                errors.append(f"Missing required header element: {element}")
        
        # Required item elements (check for at least one item)
        required_item_elements = [
            'Item_Number',
            'Commodity_Code',
            'Commodity_Description',
            'Country_of_Origin_Code'
        ]
        
        for element in required_item_elements:
            if f'<{element}' not in xml_content and f'<{element}>' not in xml_content:
                errors.append(f"Missing required item element: {element}")
        
        # Validate ASYCUDA namespace
        if 'xmlns="http://asycuda.org/asycuda"' not in xml_content:
            errors.append("Missing ASYCUDA namespace declaration")
        
        # Validate version
        if 'version="4.1"' not in xml_content:
            errors.append("Missing or incorrect ASYCUDA version (should be 4.1)")
        
        # Validate Turkmenistan-specific elements
        turkmenistan_elements = [
            'Country_of_Destination>TKM',
            'Customs_Office_Code>TKM001',
            'Declaration_Type_Code>IM4'
        ]
        
        for element in turkmenistan_elements:
            if f'<{element}<' not in xml_content.replace('>', '<'):
                errors.append(f"Missing Turkmenistan-specific element: {element}")
        
        # Validate tax structure
        required_tax_elements = [
            'Duty_Tax',
            'Tax_line',
            'Tax_type_Code',
            'Tax_rate',
            'Tax_amount'
        ]
        
        for element in required_tax_elements:
            if f'<{element}' not in xml_content and f'<{element}>' not in xml_content:
                errors.append(f"Missing required tax element: {element}")
        
        # Validate signature elements
        required_signature_elements = [
            'Declaration_Signature',
            'Signature_Method',
            'Signature_Value'
        ]
        
        for element in required_signature_elements:
            if f'<{element}' not in xml_content and f'<{element}>' not in xml_content:
                errors.append(f"Missing required signature element: {element}")
        
        # Additional business rule validations
        self._validate_asycuda_business_rules(xml_content, errors)
        
        return errors
    
    def _validate_asycuda_business_rules(self, xml_content: str, errors: List[str]) -> None:
        """
        Validate ASYCUDA business rules
        
        Args:
            xml_content: XML content to validate
            errors: List to append validation errors to
        """
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_content.encode('utf-8'))
            
            # Validate that total items count matches actual items
            total_items_elem = root.find('.//Total_Number_of_Items')
            items = root.findall('.//Item')
            
            if total_items_elem is not None and items:
                declared_count = int(total_items_elem.text)
                actual_count = len(items)
                if declared_count != actual_count:
                    errors.append(f"Item count mismatch: declared {declared_count}, actual {actual_count}")
            
            # Validate HS codes format (should be 6-10 digits)
            commodity_codes = root.findall('.//Commodity_Code')
            for code_elem in commodity_codes:
                if code_elem.text:
                    code = code_elem.text.strip()
                    if not code.isdigit() or len(code) < 6 or len(code) > 10:
                        errors.append(f"Invalid HS code format: {code}")
            
            # Validate currency codes (should be 3-letter ISO codes)
            currency_codes = root.findall('.//Currency_Code')
            for currency_elem in currency_codes:
                if currency_elem.text:
                    currency = currency_elem.text.strip()
                    if len(currency) != 3 or not currency.isupper():
                        errors.append(f"Invalid currency code format: {currency}")
            
            # Validate country codes (should be 3-letter ISO codes)
            country_codes = root.findall('.//Country_of_Origin_Code')
            for country_elem in country_codes:
                if country_elem.text:
                    country = country_elem.text.strip()
                    if len(country) != 3 or not country.isupper():
                        errors.append(f"Invalid country code format: {country}")
            
            # Validate numeric fields are positive
            numeric_fields = [
                './/Total_Invoice_Amount',
                './/Item_Invoice_Amount',
                './/Statistical_value',
                './/Net_weight',
                './/Gross_weight'
            ]
            
            for field_xpath in numeric_fields:
                elements = root.findall(field_xpath)
                for elem in elements:
                    if elem.text:
                        try:
                            value = float(elem.text)
                            if value < 0:
                                errors.append(f"Negative value not allowed in {field_xpath}: {value}")
                        except ValueError:
                            errors.append(f"Invalid numeric value in {field_xpath}: {elem.text}")
                            
        except ET.ParseError:
            # XML parsing errors are handled in parent method
            pass
        except Exception as e:
            errors.append(f"Business rule validation error: {str(e)}")
    
    def get_supported_countries(self) -> List[CountrySchema]:
        """Get list of supported country schemas"""
        return list(self._country_configs.keys())
    
    def get_country_config(self, country_schema: CountrySchema) -> Optional[XMLGenerationConfig]:
        """Get configuration for a specific country schema"""
        return self._country_configs.get(country_schema)


# Service instance
xml_generation_service = XMLGenerationService()