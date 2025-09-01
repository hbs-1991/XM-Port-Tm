"""
File processing services module

This module provides a refactored file processing system split into focused services:
- ValidationService: File validation and content checking
- CreditService: User credit management
- StorageService: S3 and local file storage
- DataExtractionService: CSV/XLSX data parsing
- JobManagementService: Processing job lifecycle
- FileProcessingOrchestrator: Main coordinator

The FileProcessingService class provides backward compatibility with the original monolithic service.
"""

from .constants import (
    MAX_FILE_SIZE, ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES,
    COLUMN_MAPPING, ALTERNATIVE_HEADERS, REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS, ALL_COLUMNS
)

from .validation_service import FileValidationService
from .credit_service import CreditService
from .storage_service import StorageService
from .data_extraction_service import DataExtractionService
from .job_management_service import JobManagementService
from .orchestrator import FileProcessingOrchestrator

# Import the backward-compatible service wrapper
from ..file_processing_service import FileProcessingService

__all__ = [
    'MAX_FILE_SIZE', 'ALLOWED_EXTENSIONS', 'ALLOWED_MIME_TYPES',
    'COLUMN_MAPPING', 'ALTERNATIVE_HEADERS', 'REQUIRED_COLUMNS',
    'OPTIONAL_COLUMNS', 'ALL_COLUMNS',
    'FileValidationService',
    'CreditService', 
    'StorageService',
    'DataExtractionService',
    'JobManagementService',
    'FileProcessingOrchestrator',
    'FileProcessingService'
]