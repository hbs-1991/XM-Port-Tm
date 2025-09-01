"""
File processing service for handling CSV and XLSX file uploads

This is a backward-compatible wrapper around the new modular file processing system.
The actual implementation has been refactored into focused services within the 
file_processing module for better maintainability and separation of concerns.
"""

from sqlalchemy.orm import Session
from fastapi import UploadFile
from typing import List, Dict, Any, Optional

# Import the new orchestrator and its dependencies
from .file_processing import FileProcessingOrchestrator
from .file_processing.constants import (
    MAX_FILE_SIZE, ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES,
    COLUMN_MAPPING, ALTERNATIVE_HEADERS, REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS, ALL_COLUMNS
)
from src.models.user import User
from src.models.processing_job import ProcessingJob
from src.schemas.processing import FileValidationResult


class FileProcessingService:
    """
    Backward-compatible wrapper for the refactored file processing system.
    
    This class maintains the same interface as the original monolithic service
    while delegating to the new modular services internally.
    """
    
    def __init__(self, db: Session):
        """Initialize the service with database session"""
        self.db = db
        self.orchestrator = FileProcessingOrchestrator(db)
        
        # Expose constants for backward compatibility
        self.MAX_FILE_SIZE = MAX_FILE_SIZE
        self.ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
        self.ALLOWED_MIME_TYPES = ALLOWED_MIME_TYPES
        self.COLUMN_MAPPING = COLUMN_MAPPING
        self.ALTERNATIVE_HEADERS = ALTERNATIVE_HEADERS
        self.REQUIRED_COLUMNS = REQUIRED_COLUMNS
        self.OPTIONAL_COLUMNS = OPTIONAL_COLUMNS
        self.ALL_COLUMNS = ALL_COLUMNS
    
    # File Validation Methods
    async def validate_file_upload(self, file: UploadFile) -> FileValidationResult:
        """Validate uploaded file before processing"""
        return await self.orchestrator.validate_file_upload(file)
    
    # Credit Management Methods
    def check_user_credits(self, user: User, estimated_credits: int = 1) -> Dict[str, Any]:
        """Check if user has sufficient credits for processing"""
        return self.orchestrator.check_user_credits(user, estimated_credits)
    
    def calculate_processing_credits(self, total_rows: int) -> int:
        """Calculate credits required for processing given number of rows"""
        return self.orchestrator.calculate_processing_credits(total_rows)
    
    def reserve_user_credits(self, user: User, credits_to_reserve: int) -> bool:
        """Reserve credits for processing"""
        return self.orchestrator.reserve_user_credits(user, credits_to_reserve)
    
    def refund_user_credits(self, user: User, credits_to_refund: int) -> bool:
        """Refund credits to user"""
        return self.orchestrator.refund_user_credits(user, credits_to_refund)
    
    # Storage Methods
    async def upload_file_to_s3(self, file: UploadFile, user_id: str) -> str:
        """Upload file to S3 storage"""
        return await self.orchestrator.upload_file_to_s3(file, user_id)
    
    # Job Management Methods
    def create_processing_job(
        self, 
        user: User, 
        file_name: str, 
        file_url: str, 
        file_size: int,
        **kwargs
    ) -> ProcessingJob:
        """Create a new processing job"""
        return self.orchestrator.create_processing_job(
            user, file_name, file_url, file_size, **kwargs
        )
    
    def get_job_data(self, job_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get processing job data for editing"""
        return self.orchestrator.get_job_data(job_id, user_id)
    
    def update_job_data(self, job_id: str, user_id: int, data: List[Dict[str, Any]]) -> bool:
        """Update processing job data with edited values"""
        return self.orchestrator.update_job_data(job_id, user_id, data)
    
    # Main Processing Methods
    async def process_file_with_hs_matching(
        self,
        file: UploadFile,
        user: User,
        country_schema: str = "default"
    ) -> Dict[str, Any]:
        """
        Complete file processing workflow with HS code matching.
        
        This is the main entry point for file processing, providing the same
        interface as the original service but using the new modular architecture.
        """
        return await self.orchestrator.process_file_with_hs_matching(
            file, user, country_schema
        )
    
    async def process_products_with_hs_matching(
        self,
        processing_job: ProcessingJob,
        products_data: List[Dict[str, Any]],
        country_schema: str = "default"
    ) -> tuple:
        """Process products with HS code matching"""
        return await self.orchestrator.process_products_with_hs_matching(
            processing_job, products_data, country_schema
        )
    
    async def complete_job_after_hs_matching(
        self, 
        job_id: str, 
        user: User, 
        hs_matches: List[dict], 
        processing_errors: List[str] = None
    ) -> dict:
        """Complete processing job after HS matching"""
        return await self.orchestrator.complete_job_after_hs_matching(
            job_id, user, hs_matches, processing_errors
        )


# Export constants for backward compatibility
__all__ = [
    'FileProcessingService',
    'MAX_FILE_SIZE',
    'ALLOWED_EXTENSIONS', 
    'ALLOWED_MIME_TYPES',
    'COLUMN_MAPPING',
    'ALTERNATIVE_HEADERS',
    'REQUIRED_COLUMNS',
    'OPTIONAL_COLUMNS',
    'ALL_COLUMNS'
]