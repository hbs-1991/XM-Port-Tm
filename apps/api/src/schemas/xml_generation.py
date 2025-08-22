"""
Pydantic schemas for XML generation API endpoints
"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class CountrySchemaType(str, Enum):
    """Country schema types for XML generation"""
    TURKMENISTAN = "TKM"
    # Future country support can be added here
    # UZBEKISTAN = "UZB"
    # KAZAKHSTAN = "KAZ"


class XMLGenerationStatus(str, Enum):
    """Status of XML generation process"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class XMLGenerationRequest(BaseModel):
    """Request schema for XML generation"""
    job_id: UUID = Field(..., description="Processing job ID")
    country_schema: Optional[CountrySchemaType] = Field(
        None, 
        description="Target country schema (defaults to job's country schema)"
    )
    include_metadata: bool = Field(
        True, 
        description="Include generation metadata in XML"
    )
    validate_output: bool = Field(
        True, 
        description="Validate generated XML against schema"
    )

    class Config:
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "country_schema": "TKM",
                "include_metadata": True,
                "validate_output": True
            }
        }


class ProductSummary(BaseModel):
    """Summary information for a product in XML"""
    description: str = Field(..., description="Product description")
    hs_code: str = Field(..., description="Matched HS code")
    quantity: Decimal = Field(..., description="Product quantity")
    unit_of_measure: str = Field(..., description="Unit of measurement")
    value: Decimal = Field(..., description="Product value")
    origin_country: str = Field(..., description="Country of origin")
    confidence_score: Decimal = Field(..., description="AI matching confidence score")
    requires_manual_review: bool = Field(..., description="Whether manual review is required")

    @field_validator('confidence_score')
    def validate_confidence_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v

    @field_validator('quantity', 'value')
    def validate_positive_numbers(cls, v):
        if v <= 0:
            raise ValueError('Quantity and value must be positive')
        return v

    class Config:
        schema_extra = {
            "example": {
                "description": "Cotton T-shirts",
                "hs_code": "6109100000",
                "quantity": "100.00",
                "unit_of_measure": "PCS",
                "value": "500.00",
                "origin_country": "USA",
                "confidence_score": "0.95",
                "requires_manual_review": False
            }
        }


class XMLGenerationSummary(BaseModel):
    """Summary statistics for XML generation"""
    total_products: int = Field(..., description="Total number of products")
    total_quantity: Decimal = Field(..., description="Total quantity across all products")
    total_value: Decimal = Field(..., description="Total value across all products")
    average_confidence: Decimal = Field(..., description="Average confidence score")
    unique_hs_codes: int = Field(..., description="Number of unique HS codes")
    high_confidence_products: int = Field(..., description="Number of high confidence products (>0.9)")
    manual_review_required: int = Field(..., description="Number of products requiring manual review")

    @field_validator('total_products', 'unique_hs_codes', 'high_confidence_products', 'manual_review_required')
    def validate_non_negative_integers(cls, v):
        if v < 0:
            raise ValueError('Count values must be non-negative')
        return v

    @field_validator('average_confidence')
    def validate_average_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Average confidence must be between 0 and 1')
        return v

    class Config:
        schema_extra = {
            "example": {
                "total_products": 25,
                "total_quantity": "500.00",
                "total_value": "12500.00",
                "average_confidence": "0.92",
                "unique_hs_codes": 8,
                "high_confidence_products": 20,
                "manual_review_required": 2
            }
        }


class ValidationError(BaseModel):
    """XML validation error details"""
    field: Optional[str] = Field(None, description="Field causing the error")
    message: str = Field(..., description="Error message")
    severity: str = Field(..., description="Error severity level")

    @field_validator('severity')
    def validate_severity(cls, v):
        allowed_severities = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_severities:
            raise ValueError(f'Severity must be one of: {allowed_severities}')
        return v.upper()

    class Config:
        schema_extra = {
            "example": {
                "field": "DeclarationHeader.CountryCode",
                "message": "Missing required field: CountryCode",
                "severity": "ERROR"
            }
        }


class XMLGenerationResponse(BaseModel):
    """Response schema for XML generation"""
    success: bool = Field(..., description="Whether generation was successful")
    job_id: UUID = Field(..., description="Processing job ID")
    xml_file_name: Optional[str] = Field(None, description="Generated XML file name")
    download_url: Optional[str] = Field(None, description="Secure download URL for XML file")
    country_schema: CountrySchemaType = Field(..., description="Used country schema")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    summary: Optional[XMLGenerationSummary] = Field(None, description="Generation summary statistics")
    validation_errors: Optional[List[ValidationError]] = Field(None, description="Validation errors if any")
    error_message: Optional[str] = Field(None, description="Error message if generation failed")

    @field_validator('file_size')
    def validate_file_size(cls, v):
        if v is not None and v < 0:
            raise ValueError('File size must be non-negative')
        return v

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "xml_file_name": "export_declaration_TKM_20250122.xml",
                "download_url": "https://s3.amazonaws.com/bucket/signed-url",
                "country_schema": "TKM",
                "generated_at": "2025-01-22T10:30:00Z",
                "file_size": 2048,
                "summary": {
                    "total_products": 25,
                    "total_quantity": "500.00",
                    "total_value": "12500.00",
                    "average_confidence": "0.92",
                    "unique_hs_codes": 8,
                    "high_confidence_products": 20,
                    "manual_review_required": 2
                },
                "validation_errors": None,
                "error_message": None
            }
        }


class XMLDownloadResponse(BaseModel):
    """Response schema for XML download"""
    success: bool = Field(..., description="Whether download link generation was successful")
    job_id: UUID = Field(..., description="Processing job ID")
    download_url: Optional[str] = Field(None, description="Secure download URL")
    file_name: Optional[str] = Field(None, description="XML file name")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    expires_at: Optional[datetime] = Field(None, description="Download link expiration time")
    content_type: str = Field(default="application/xml", description="File content type")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @field_validator('file_size')
    def validate_file_size(cls, v):
        if v is not None and v < 0:
            raise ValueError('File size must be non-negative')
        return v

    @field_validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['application/xml', 'text/xml']
        if v not in allowed_types:
            raise ValueError(f'Content type must be one of: {allowed_types}')
        return v

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "download_url": "https://s3.amazonaws.com/bucket/signed-url",
                "file_name": "export_declaration_TKM_20250122.xml",
                "file_size": 2048,
                "expires_at": "2025-01-22T16:30:00Z",
                "content_type": "application/xml",
                "error_message": None
            }
        }


class XMLGenerationProgress(BaseModel):
    """WebSocket progress update schema for XML generation"""
    job_id: UUID = Field(..., description="Processing job ID")
    status: XMLGenerationStatus = Field(..., description="Current generation status")
    progress_percentage: int = Field(..., description="Progress percentage (0-100)")
    current_step: str = Field(..., description="Current processing step")
    products_processed: int = Field(default=0, description="Number of products processed")
    total_products: int = Field(..., description="Total number of products to process")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @field_validator('progress_percentage')
    def validate_progress_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Progress percentage must be between 0 and 100')
        return v

    @field_validator('products_processed')
    def validate_products_processed(cls, v):
        if v < 0:
            raise ValueError('Products processed must be non-negative')
        return v

    @field_validator('total_products')
    def validate_total_products(cls, v):
        if v <= 0:
            raise ValueError('Total products must be positive')
        return v

    class Config:
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "PROCESSING",
                "progress_percentage": 65,
                "current_step": "Generating XML content",
                "products_processed": 16,
                "total_products": 25,
                "estimated_completion_time": "2025-01-22T10:35:00Z",
                "error_message": None
            }
        }


class SupportedCountriesResponse(BaseModel):
    """Response schema for supported countries endpoint"""
    success: bool = Field(..., description="Whether request was successful")
    countries: List[dict] = Field(..., description="List of supported country schemas")
    total_countries: int = Field(..., description="Total number of supported countries")

    @field_validator('total_countries')
    def validate_total_countries(cls, v):
        if v < 0:
            raise ValueError('Total countries must be non-negative')
        return v

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "countries": [
                    {
                        "code": "TKM",
                        "name": "Turkmenistan",
                        "template": "asycuda_turkmenistan.xml.j2",
                        "supported_features": [
                            "multi_product_declarations",
                            "hs_code_validation",
                            "customs_value_calculation"
                        ]
                    }
                ],
                "total_countries": 1
            }
        }


class XMLValidationRequest(BaseModel):
    """Request schema for XML validation"""
    job_id: UUID = Field(..., description="Processing job ID")
    country_schema: CountrySchemaType = Field(..., description="Country schema for validation")
    xml_content: Optional[str] = Field(None, description="XML content to validate (optional)")
    validation_level: str = Field(default="STANDARD", description="Validation level")

    @field_validator('validation_level')
    def validate_validation_level(cls, v):
        allowed_levels = ['BASIC', 'STANDARD', 'STRICT', 'CUSTOM']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Validation level must be one of: {allowed_levels}')
        return v.upper()

    class Config:
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "country_schema": "TKM",
                "xml_content": "<?xml version=\"1.0\"?>...",
                "validation_level": "STANDARD"
            }
        }


class XMLValidationResponse(BaseModel):
    """Response schema for XML validation"""
    success: bool = Field(..., description="Whether validation was successful")
    job_id: UUID = Field(..., description="Processing job ID")
    is_valid: bool = Field(..., description="Whether XML is valid")
    country_schema: CountrySchemaType = Field(..., description="Used country schema")
    validation_level: str = Field(..., description="Applied validation level")
    validation_errors: Optional[List[ValidationError]] = Field(None, description="Validation errors")
    warnings: Optional[List[ValidationError]] = Field(None, description="Validation warnings")
    validated_at: datetime = Field(..., description="Validation timestamp")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "is_valid": True,
                "country_schema": "TKM",
                "validation_level": "STANDARD",
                "validation_errors": None,
                "warnings": [
                    {
                        "field": "ProductDescription",
                        "message": "Product description exceeds recommended length",
                        "severity": "WARNING"
                    }
                ],
                "validated_at": "2025-01-22T10:30:00Z",
                "error_message": None
            }
        }