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
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from enum import Enum

import jinja2
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.core.config import get_settings

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
        
        # Country schema base configurations
        # Note: Actual template is selected dynamically based on XML_OUTPUT_FORMAT
        self._country_configs = {
            CountrySchema.TURKMENISTAN: XMLGenerationConfig(
                country_schema=CountrySchema.TURKMENISTAN,
                template_name="declaration_turkmenistan.xml.j2",
                encoding="utf-8",
                validate_output=True,
                include_metadata=False
            )
        }
        
        logger.info("XMLGenerationService initialized successfully")
    
    def _get_storage_service(self):
        """Get XML storage service instance (lazy initialization)"""
        global _xml_storage_service
        if _xml_storage_service is None:
            from src.services.xml_storage import xml_storage_service
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
        """Get configuration for specific country schema.

        Dynamically selects the correct template based on XML_OUTPUT_FORMAT
        (ASYCUDA vs DECLARATION) while keeping other config fields.
        """
        base = self._country_configs.get(country_schema)
        if not base:
            return None

        # Pick template according to configured output format
        output_format = self.settings.xml_output_format  # normalized to upper-case
        if output_format == "ASYCUDA":
            template_name = "asycuda_turkmenistan.xml.j2"
        else:
            # Default/legacy declaration format
            template_name = "declaration_turkmenistan.xml.j2"

        # Return a shallow copy with the selected template
        return XMLGenerationConfig(
            country_schema=base.country_schema,
            template_name=template_name,
            encoding=base.encoding,
            validate_output=base.validate_output,
            include_metadata=base.include_metadata,
        )
    
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
        
        # Normalize products into plain dicts with safe defaults
        normalized_products: List[Dict[str, Any]] = []
        for pm in product_matches:
            # Use getattr to be resilient to missing attrs
            def g(name: str, default: Any = None):
                return getattr(pm, name, default)

            qty = g('quantity')
            val = g('value')
            unit_price = g('unit_price')
            if (val is None or (isinstance(val, (int, float, Decimal)) and Decimal(str(val)) == Decimal('0'))) and unit_price is not None and qty is not None:
                try:
                    val = Decimal(str(unit_price)) * Decimal(str(qty))
                except Exception:
                    pass

            normalized_products.append({
                'product_description': g('product_description', ''),
                'matched_hs_code': g('matched_hs_code', ''),
                'confidence_score': g('confidence_score', Decimal('0')),
                'quantity': qty or Decimal('0'),
                'unit_of_measure': g('unit_of_measure', ''),
                'value': val or Decimal('0'),
                'unit_price': unit_price,
                'origin_country': g('origin_country', ''),
                # Packaging and weights
                'packages_count': g('packages_count'),
                'packages_part': g('packages_part'),
                'packaging_kind_code': g('packaging_kind_code'),
                'packaging_kind_name': g('packaging_kind_name'),
                'gross_weight': g('gross_weight'),
                'net_weight': g('net_weight'),
                # Supplementary
                'supplementary_quantity': g('supplementary_quantity'),
                'supplementary_uom_code': g('supplementary_uom_code'),
                'supplementary_uom_name': g('supplementary_uom_name'),
                # Optional customs preferences if present
                'preference_reg': g('preference_reg'),
                'preference_dut': g('preference_dut'),
                'preference_exc': g('preference_exc'),
                'extended_customs_procedure': g('extended_customs_procedure'),
                'national_customs_procedure': g('national_customs_procedure'),
                'bku': g('bku')
            })

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
            'products': normalized_products,
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
            
            # Check for required elements based on selected output format
            if country_schema == CountrySchema.TURKMENISTAN:
                if self.settings.xml_output_format == "ASYCUDA":
                    validation_errors.extend(self._validate_asycuda_structure(xml_content))
                else:
                    validation_errors.extend(self._validate_declaration_structure(xml_content))
            
            # Additional validations can be added here
            # For example, XSD schema validation with xsdata
            
            return validation_errors if validation_errors else None
            
        except Exception as e:
            logger.error(f"XML validation error: {str(e)}", exc_info=True)
            return [f"Validation error: {str(e)}"]
    
    def _validate_declaration_structure(self, xml_content: str) -> List[str]:
        """
        Validate declaration.xsd compliant XML structure
        
        Args:
            xml_content: XML content to validate
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for correct namespace
        if 'xmlns="urn:gtd:item"' not in xml_content:
            errors.append("Missing or incorrect namespace: expected 'urn:gtd:item'")
        
        # Check for root element
        if '<Items' not in xml_content:
            errors.append("Missing root element: <Items>")
        
        # Required elements for each item
        required_item_elements = [
            'HSCode',
            'GoodsDescription', 
            'CountryOfOrigin',
            'QuantityPrice'
        ]
        
        for element in required_item_elements:
            if f'<{element}' not in xml_content and f'<{element}>' not in xml_content:
                errors.append(f"Missing required element: {element}")
        
        # Check nested required elements
        if '<CountryOfOrigin>' in xml_content or '<CountryOfOrigin ' in xml_content:
            if '<Code>' not in xml_content:
                errors.append("Missing required element: CountryOfOrigin/Code")
        
        if '<QuantityPrice>' in xml_content or '<QuantityPrice ' in xml_content:
            required_quantity_elements = ['Quantity', 'UOMCode']
            for element in required_quantity_elements:
                if f'<{element}>' not in xml_content and f'<{element} ' not in xml_content:
                    errors.append(f"Missing required element: QuantityPrice/{element}")
        
        # Validate structure and business rules
        self._validate_declaration_business_rules(xml_content, errors)
        
        return errors

    def _validate_asycuda_structure(self, xml_content: str) -> List[str]:
        """Validate ASYCUDA structure for generated XML.

        Minimal checks against Turkmenistan ASYCUDA example:
        - Root element <ASYCUDA>
        - At least one <Item>
        - For each item ensure presence of mapped fields
        """
        errors: List[str] = []
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_content.encode('utf-8'))

            def local(tag: str) -> str:
                return tag.split('}', 1)[1] if tag.startswith('{') else tag

            if local(root.tag) != 'ASYCUDA':
                errors.append("Missing root element: <ASYCUDA>")
                return errors

            items = [el for el in root.iter() if local(el.tag) == 'Item']
            if not items:
                errors.append("Missing required element: Item")
                return errors

            for i, item in enumerate(items, 1):
                prefix = f"Item {i}: "
                gd = next((c for c in list(item) if local(c.tag) == 'Goods_description'), None)
                if gd is None:
                    errors.append(prefix + "Missing Goods_description")
                else:
                    desc = next((c for c in list(gd) if local(c.tag) == 'Description_of_goods'), None)
                    origin = next((c for c in list(gd) if local(c.tag) == 'Country_of_origin_code'), None)
                    # ASYCUDA can auto-populate description by HS code, so allow empty content
                    if desc is None:
                        errors.append(prefix + "Missing Description_of_goods")
                    if origin is None or len((origin.text or '').strip()) != 2:
                        errors.append(prefix + "Country_of_origin_code must be 2 letters")

                pk = next((c for c in list(item) if local(c.tag) == 'Packages'), None)
                if pk is None:
                    errors.append(prefix + "Missing Packages")
                else:
                    nop = next((c for c in list(pk) if local(c.tag) == 'Number_of_packages'), None)
                    if nop is None or (nop.text or '').strip() == '':
                        errors.append(prefix + "Number_of_packages is required")

                tf = next((c for c in list(item) if local(c.tag) == 'Tarification'), None)
                if tf is None:
                    errors.append(prefix + "Missing Tarification")
                else:
                    hs = next((c for c in list(tf) if local(c.tag) == 'HScode'), None)
                    uqty = next((c for c in list(tf) if local(c.tag) == 'uom_quantity'), None)
                    ucode = next((c for c in list(tf) if local(c.tag) == 'uom_code'), None)
                    upr = next((c for c in list(tf) if local(c.tag) == 'uom_price'), None)
                    if hs is None:
                        errors.append(prefix + "Missing HScode")
                    else:
                        cc = next((c for c in list(hs) if local(c.tag) == 'Commodity_code'), None)
                        if cc is None or not (cc.text or '').strip().isdigit():
                            errors.append(prefix + "HScode/Commodity_code must be digits")
                    try:
                        if uqty is None or float((uqty.text or '0').strip() or '0') <= 0:
                            errors.append(prefix + "uom_quantity must be positive")
                    except ValueError:
                        errors.append(prefix + "uom_quantity must be a number")
                    if ucode is None or (ucode.text or '').strip() == '':
                        errors.append(prefix + "uom_code is required")
                    if upr is None or (upr.text is None):
                        errors.append(prefix + "uom_price is required")

                vi = next((c for c in list(item) if local(c.tag) == 'Valuation_item'), None)
                if vi is None:
                    errors.append(prefix + "Missing Valuation_item")
                else:
                    w = next((c for c in list(vi) if local(c.tag) == 'Weight_itm'), None)
                    if w is None:
                        errors.append(prefix + "Missing Weight_itm")
                    else:
                        net = next((c for c in list(w) if local(c.tag) == 'Net_weight_itm'), None)
                        gross = next((c for c in list(w) if local(c.tag) == 'Gross_weight_itm'), None)
                        if net is None or (net.text is None):
                            errors.append(prefix + "Net_weight_itm is required")
                        if gross is None or (gross.text is None):
                            errors.append(prefix + "Gross_weight_itm is required")

        except ET.ParseError as e:
            errors.append(f"XML parsing error in ASYCUDA validation: {str(e)}")
        except Exception as e:
            errors.append(f"ASYCUDA validation error: {str(e)}")

        return errors
    
    def _validate_declaration_business_rules(self, xml_content: str, errors: List[str]) -> None:
        """
        Validate declaration business rules
        
        Args:
            xml_content: XML content to validate
            errors: List to append validation errors to
        """
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_content.encode('utf-8'))
            
            # Define namespace for XPath queries
            namespace = {'ns': 'urn:gtd:item'}
            
            # Find all items
            items = root.findall('.//ns:Item', namespace)
            if not items:
                errors.append("No items found in declaration")
                return
            
            # Validate each item
            for i, item in enumerate(items, 1):
                item_prefix = f"Item {i}: "
                
                # Validate HS code format (6 or 8 digits)
                hs_code_elem = item.find('.//ns:HSCode', namespace)
                if hs_code_elem is not None and hs_code_elem.text:
                    hs_code = hs_code_elem.text.strip()
                    if not hs_code.isdigit():
                        errors.append(f"{item_prefix}HSCode must contain only digits: {hs_code}")
                    elif len(hs_code) not in [6, 8, 9]:
                        errors.append(f"{item_prefix}HSCode must be 6, 8, or 9 digits: {hs_code}")
                
                # Validate country code (2-letter format)
                country_code_elem = item.find('.//ns:Code', namespace)
                if country_code_elem is not None and country_code_elem.text:
                    country_code = country_code_elem.text.strip()
                    if len(country_code) != 2 or not country_code.isupper() or not country_code.isalpha():
                        errors.append(f"{item_prefix}Country code must be 2 uppercase letters: {country_code}")
                
                # Validate quantity is positive
                quantity_elem = item.find('.//ns:Quantity', namespace)
                if quantity_elem is not None and quantity_elem.text:
                    try:
                        quantity = float(quantity_elem.text)
                        if quantity <= 0:
                            errors.append(f"{item_prefix}Quantity must be positive: {quantity}")
                    except ValueError:
                        errors.append(f"{item_prefix}Quantity must be a valid number: {quantity_elem.text}")
                
                # Validate unit price if present
                unit_price_elem = item.find('.//ns:UnitPrice', namespace)
                if unit_price_elem is not None and unit_price_elem.text:
                    try:
                        unit_price = float(unit_price_elem.text)
                        if unit_price < 0:
                            errors.append(f"{item_prefix}UnitPrice cannot be negative: {unit_price}")
                    except ValueError:
                        errors.append(f"{item_prefix}UnitPrice must be a valid number: {unit_price_elem.text}")
                
                # Validate weights if present
                for weight_field in ['NetKg', 'GrossKg']:
                    weight_elem = item.find(f'.//ns:{weight_field}', namespace)
                    if weight_elem is not None and weight_elem.text:
                        try:
                            weight = float(weight_elem.text)
                            if weight < 0:
                                errors.append(f"{item_prefix}{weight_field} cannot be negative: {weight}")
                        except ValueError:
                            errors.append(f"{item_prefix}{weight_field} must be a valid number: {weight_elem.text}")
                            
        except ET.ParseError:
            # XML parsing errors are handled in parent method
            pass
        except Exception as e:
            errors.append(f"Declaration business rule validation error: {str(e)}")

    
    def get_supported_countries(self) -> List[CountrySchema]:
        """Get list of supported country schemas"""
        return list(self._country_configs.keys())
    
    def get_country_config(self, country_schema: CountrySchema) -> Optional[XMLGenerationConfig]:
        """Get configuration for a specific country schema"""
        return self._country_configs.get(country_schema)
    
    def _validate_hs_code(self, hs_code: Optional[str]) -> Optional[List[str]]:
        """Validate HS code format
        
        Args:
            hs_code: HS code to validate
            
        Returns:
            List of validation errors or None if valid
        """
        errors = []
        
        if hs_code is None:
            errors.append("HS code is required")
            return errors
        
        if not hs_code:
            errors.append("HS code cannot be empty")
            return errors
        
        # HS codes should be 6-10 digits
        if len(hs_code) < 6:
            errors.append(f"HS code too short: {hs_code} (minimum 6 digits)")
        elif len(hs_code) > 10:
            errors.append(f"HS code too long: {hs_code} (maximum 10 digits)")
        
        # Should contain only digits
        if not hs_code.isdigit():
            errors.append(f"HS code must contain only digits: {hs_code}")
        
        return errors if errors else None
    
    def _validate_country_code(self, country_code: Optional[str]) -> Optional[List[str]]:
        """Validate country code format (ISO 3166-1 alpha-3)
        
        Args:
            country_code: Country code to validate
            
        Returns:
            List of validation errors or None if valid
        """
        errors = []
        
        if country_code is None:
            errors.append("Country code is required")
            return errors
        
        if not country_code:
            errors.append("Country code cannot be empty")
            return errors
        
        # Country codes should be exactly 3 uppercase letters
        if len(country_code) != 3:
            errors.append(f"Country code must be exactly 3 characters: {country_code}")
        
        if not country_code.isupper() or not country_code.isalpha():
            errors.append(f"Country code must be 3 uppercase letters: {country_code}")
        
        return errors if errors else None
    
    def _validate_numeric_value(self, value: Any, field_name: str) -> Optional[List[str]]:
        """Validate numeric value
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
            
        Returns:
            List of validation errors or None if valid
        """
        errors = []
        
        if value is None:
            errors.append(f"{field_name} is required")
            return errors
        
        # Check if it's a valid numeric type
        if not isinstance(value, (int, float, Decimal)):
            if isinstance(value, str):
                try:
                    Decimal(value)
                except (ValueError, InvalidOperation):
                    errors.append(f"{field_name} must be a valid number: {value}")
                    return errors
            else:
                errors.append(f"{field_name} must be numeric: {type(value)}")
                return errors
        
        # Convert to Decimal for consistent handling
        try:
            decimal_value = Decimal(str(value))
            
            # Check if negative
            if decimal_value < 0:
                errors.append(f"{field_name} cannot be negative: {decimal_value}")
            
        except (ValueError, InvalidOperation):
            errors.append(f"{field_name} is not a valid number: {value}")
        
        return errors if errors else None


# Service instance
xml_generation_service = XMLGenerationService()
