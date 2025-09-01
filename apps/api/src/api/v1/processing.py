"""
Processing API Aggregator - Backward Compatibility Layer

This file serves as a backward compatibility layer that aggregates all processing endpoints
from the new modular structure. This ensures existing integrations continue to work while
benefiting from the improved code organization.

The original 1009-line processing.py has been split into 4 focused modules:
- file_operations.py: Upload, validation, and template endpoints
- job_management.py: Job listing, details, and completion endpoints  
- job_data.py: Product data and HS code update endpoints
- processing_workflow.py: Complete end-to-end processing workflow

All endpoints maintain the same URL paths and behavior as before.
"""
from fastapi import APIRouter

# Import all the new modular routers
from .file_operations import router as file_operations_router
from .job_management import router as job_management_router
from .job_data import router as job_data_router
from .processing_workflow import router as processing_workflow_router

# Create main aggregator router
router = APIRouter()

# Include all modular routers to maintain backward compatibility
# All endpoints will be available at the same paths as before
router.include_router(file_operations_router, tags=["file-operations"])
router.include_router(job_management_router, tags=["job-management"]) 
router.include_router(job_data_router, tags=["job-data"])
router.include_router(processing_workflow_router, tags=["processing-workflow"])

# Endpoint mapping for reference:
#
# File Operations (file_operations.py):
# - POST /upload - File upload and validation
# - POST /validate - File validation only
# - GET /template/download - Download CSV template
#
# Job Management (job_management.py):  
# - GET /jobs - List processing jobs with filtering
# - POST /jobs/{job_id}/complete - Complete job after HS matching
# - GET /jobs/{job_id}/details - Get comprehensive job details
#
# Job Data Operations (job_data.py):
# - GET /jobs/{job_id}/data - Get job data for editing
# - PUT /jobs/{job_id}/data - Update job data 
# - GET /jobs/{job_id}/products - Get products with HS codes
# - PUT /jobs/{job_id}/products/{product_id}/hs-code - Update HS code
#
# Processing Workflow (processing_workflow.py):
# - POST /process-with-hs-matching - Complete end-to-end processing