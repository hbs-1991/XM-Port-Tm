"""
File processing related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class ProcessingStatusEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class FileUploadResponse(BaseModel):
    """Response schema for file upload endpoint"""
    job_id: str = Field(..., description="Processing job ID")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    status: ProcessingStatusEnum = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    validation_results: Optional[dict] = Field(None, description="File validation results")
    
    class Config:
        from_attributes = True


class FileValidationError(BaseModel):
    """Schema for file validation errors"""
    field: str = Field(..., description="Field name that failed validation")
    error: str = Field(..., description="Error description")
    row: Optional[int] = Field(None, description="Row number (if applicable)")
    column: Optional[str] = Field(None, description="Column name (if applicable)")


class ValidationSummary(BaseModel):
    """Detailed validation summary by category"""
    total_errors: int = Field(..., description="Total number of errors")
    total_warnings: int = Field(..., description="Total number of warnings")
    errors_by_field: dict = Field(default_factory=dict, description="Error count by field")
    errors_by_type: dict = Field(default_factory=dict, description="Error count by error type")
    most_common_errors: List[str] = Field(default_factory=list, description="Most frequent error messages")
    data_quality_score: float = Field(..., description="Data quality score (0-100)")


class FileValidationResult(BaseModel):
    """Schema for file validation results"""
    is_valid: bool = Field(..., description="Whether file passed validation")
    total_rows: int = Field(..., description="Total number of data rows")
    valid_rows: int = Field(..., description="Number of valid data rows")
    errors: List[FileValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    summary: Optional[ValidationSummary] = Field(None, description="Detailed validation summary")


class ProcessingJobResponse(BaseModel):
    """Response schema for processing job data"""
    id: str
    user_id: str
    status: ProcessingStatusEnum
    input_file_name: str
    input_file_url: str
    input_file_size: int
    output_xml_url: Optional[str] = None
    credits_used: int
    processing_time_ms: Optional[int] = None
    total_products: int
    successful_matches: int
    average_confidence: Optional[Decimal] = None
    country_schema: str
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProcessingJobCreate(BaseModel):
    """Schema for creating a processing job"""
    input_file_name: str = Field(..., max_length=255)
    input_file_url: str
    input_file_size: int = Field(..., gt=0)
    country_schema: str = Field(..., min_length=3, max_length=3)
    total_products: int = Field(default=0, ge=0)
    credits_used: int = Field(default=1, ge=1, description="Credits used for processing")
    
    @validator('country_schema')
    def validate_country_schema(cls, v):
        if not v.isupper():
            raise ValueError('Country schema must be uppercase')
        return v


class ProductData(BaseModel):
    """Schema for product data extracted from uploaded files"""
    product_description: str = Field(..., description="Product description")
    quantity: float = Field(..., gt=0, description="Product quantity")
    unit: str = Field(..., description="Unit of measure")
    value: float = Field(..., gt=0, description="Product value")
    origin_country: str = Field(..., description="Origin country")
    unit_price: float = Field(..., gt=0, description="Unit price")
    row_number: int = Field(..., description="Row number in source file")
    
    @validator('quantity', 'value', 'unit_price')
    def validate_positive_numbers(cls, v):
        if v <= 0:
            raise ValueError('Must be positive')
        return v


class ProductDataWithHS(BaseModel):
    """Schema for product data with HS code information"""
    id: str = Field(..., description="Product match UUID")
    product_description: str = Field(..., description="Product description")
    quantity: float = Field(..., gt=0, description="Product quantity")
    unit: str = Field(..., description="Unit of measure")
    value: float = Field(..., gt=0, description="Product value")
    origin_country: str = Field(..., description="Origin country")
    unit_price: float = Field(..., gt=0, description="Unit price")
    hs_code: str = Field(..., description="Matched HS code")
    confidence_score: float = Field(..., ge=0, le=1, description="Matching confidence score (0-1)")
    confidence_level: str = Field(..., description="Confidence level (High/Medium/Low)")
    alternative_hs_codes: List[str] = Field(default_factory=list, description="Alternative HS codes")
    requires_manual_review: bool = Field(..., description="Whether product requires manual review")
    user_confirmed: bool = Field(..., description="Whether user has confirmed the HS code")
    vector_store_reasoning: Optional[str] = Field(None, description="AI reasoning for HS code match")


class JobProductsResponse(BaseModel):
    """Response schema for job products with HS code data"""
    job_id: str = Field(..., description="Processing job UUID")
    status: str = Field(..., description="Job processing status")
    products: List[ProductDataWithHS] = Field(..., description="Products with HS code data")
    total_products: int = Field(..., description="Total number of products")
    high_confidence_count: int = Field(..., description="Number of high confidence matches")
    requires_review_count: int = Field(..., description="Number of products requiring review")


class HSCodeUpdateRequest(BaseModel):
    """Schema for HS code update request"""
    hs_code: str = Field(..., description="New HS code (6-10 digits with optional dots)")
    
    @validator('hs_code')
    def validate_hs_code_format(cls, v):
        import re
        v = v.strip()
        # Allow formats: 610910(6), 6109.10(4.2), 6109.10.00(4.2.2), 61091000(8), 6109100000(10)
        patterns = [
            r'^\d{6}$',              # 610910
            r'^\d{4}\.\d{2}$',       # 6109.10  
            r'^\d{4}\.\d{2}\.\d{2}$',# 6109.10.00
            r'^\d{8}$',              # 61091000
            r'^\d{10}$'              # 6109100000
        ]
        if not any(re.match(pattern, v) for pattern in patterns):
            raise ValueError('Invalid HS code format. Must be 6-10 digits with optional dots (e.g., 6109.10.00)')
        return v


class FileUploadError(BaseModel):
    """Schema for file upload errors"""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")