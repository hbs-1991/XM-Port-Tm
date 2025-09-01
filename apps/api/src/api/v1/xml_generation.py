"""
XML Generation API endpoints - FIXED VERSION
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from src.core.auth import get_current_active_user
from src.core.database import get_db
from src.models.user import User
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.services.xml_generation import XMLGenerationService, XMLGenerationError, XMLValidationError, CountrySchema
from src.services.analytics_service import HSCodeAnalyticsService
from src.schemas.xml_generation import (
    XMLGenerationRequest,
    XMLGenerationResponse,
    XMLDownloadResponse,
    CountrySchemaType
)

router = APIRouter()


@router.post(
    "/processing/{job_id}/generate-xml",
    response_model=XMLGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "XML generation started successfully"},
        404: {"description": "Processing job not found or access denied"},
        400: {"description": "Invalid request or job state"},
        422: {"description": "XML generation failed"},
        500: {"description": "Internal server error"}
    }
)
async def generate_xml(
    job_id: UUID,
    request: XMLGenerationRequest = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate ASYCUDA-compliant XML file for a completed processing job
    
    - **job_id**: UUID of the processing job
    - **country_schema**: Target country schema (optional, defaults to job's country schema)
    - **include_metadata**: Include generation metadata in XML (default: true)
    - **validate_output**: Validate generated XML against schema (default: true)
    
    This endpoint will:
    1. Validate that the job exists and belongs to the current user
    2. Ensure the job is in COMPLETED status with successful matches
    3. Generate ASYCUDA-compliant XML using the matched product data
    4. Upload the XML file to S3 storage
    5. Update the processing job with XML generation results
    """
    async with get_db() as db:
        try:
            # Query processing job with user authorization
            result = await db.execute(
                select(ProcessingJob).filter(
                    ProcessingJob.id == job_id,
                    ProcessingJob.user_id == current_user.id
                )
            )
            processing_job = result.scalar_one_or_none()
            
            if not processing_job:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "job_not_found",
                        "message": "Processing job not found or access denied",
                        "job_id": str(job_id)
                    }
                )
            
            # Validate job status for XML generation
            if processing_job.status not in [ProcessingStatus.COMPLETED, ProcessingStatus.COMPLETED_WITH_ERRORS]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_job_status",
                        "message": f"Job must be in COMPLETED status for XML generation. Current status: {processing_job.status.value}",
                        "job_id": str(job_id),
                        "current_status": processing_job.status.value
                    }
                )
            
            # Check if job has successful matches
            if processing_job.successful_matches == 0:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "no_successful_matches",
                        "message": "Cannot generate XML: no successful product matches found",
                        "job_id": str(job_id),
                        "total_products": processing_job.total_products,
                        "successful_matches": processing_job.successful_matches
                    }
                )
            
            # Use request parameters or defaults
            if request is None:
                request = XMLGenerationRequest(job_id=job_id)
            
            # Determine country schema
            country_schema = request.country_schema.value if request.country_schema else processing_job.country_schema
            
            # Initialize XML generation service
            xml_service = XMLGenerationService()
            
            # Mark XML generation as started
            processing_job.xml_generation_status = "GENERATING"
            await db.commit()
            
            # Get product matches for the job
            result = await db.execute(
                select(ProductMatch).filter(
                    ProductMatch.job_id == job_id
                )
            )
            product_matches = result.scalars().all()
            
            if not product_matches:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "no_product_matches",
                        "message": "No product matches found for XML generation",
                        "job_id": str(job_id)
                    }
                )
            
            # Generate XML file
            result = await xml_service.generate_xml(
                processing_job=processing_job,
                product_matches=product_matches,
                country_schema=CountrySchema(country_schema)
            )
            
            if not result.success:
                # Update job with failure status
                processing_job.xml_generation_status = "FAILED"
                processing_job.error_message = result.error_message
                await db.commit()
                
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "xml_generation_failed",
                        "message": result.error_message or "XML generation failed",
                        "job_id": str(job_id),
                        "validation_errors": result.validation_errors
                    }
                )
            
            # Update processing job with XML generation results
            processing_job.xml_generation_status = "COMPLETED"
            processing_job.output_xml_url = result.download_url
            processing_job.xml_generated_at = result.generated_at
            processing_job.xml_file_size = result.file_size
            await db.commit()
            
            return XMLGenerationResponse(
                success=True,
                job_id=job_id,
                xml_file_name=f"asycuda_export_{job_id}.xml",
                download_url=result.download_url,
                country_schema=CountrySchemaType(country_schema),
                generated_at=result.generated_at,
                file_size=result.file_size,
                summary=None,  # Can be populated with actual summary if needed
                validation_errors=None,
                error_message=None
            )
            
        except HTTPException:
            raise
        except XMLGenerationError as e:
            # Update job with failure status
            if 'processing_job' in locals():
                processing_job.xml_generation_status = "FAILED"
                processing_job.error_message = str(e)
                await db.commit()
            
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "xml_generation_error",
                    "message": str(e),
                    "job_id": str(job_id)
                }
            )
        except XMLValidationError as e:
            # Update job with failure status
            if 'processing_job' in locals():
                processing_job.xml_generation_status = "FAILED"
                processing_job.error_message = f"XML validation failed: {str(e)}"
                await db.commit()
            
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "xml_validation_error",
                    "message": f"XML validation failed: {str(e)}",
                    "job_id": str(job_id)
                }
            )
        except SQLAlchemyError as e:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "database_error",
                    "message": "Database operation failed during XML generation",
                    "job_id": str(job_id)
                }
            )
        except Exception as e:
            # Update job with failure status if possible
            if 'processing_job' in locals():
                try:
                    processing_job.xml_generation_status = "FAILED"
                    processing_job.error_message = f"Unexpected error: {str(e)}"
                    await db.commit()
                except:
                    await db.rollback()
            
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error during XML generation for job {job_id}: {str(e)}", exc_info=True)
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_server_error",
                    "message": f"Unexpected error during XML generation: {str(e)}",
                    "job_id": str(job_id)
                }
            )


@router.get(
    "/processing/{job_id}/xml-download",
    response_model=XMLDownloadResponse,
    responses={
        200: {"description": "XML download information retrieved successfully"},
        404: {"description": "Processing job not found, access denied, or XML not generated"},
        400: {"description": "XML not available for download"},
        500: {"description": "Internal server error"}
    }
)
async def get_xml_download(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get download information for generated XML file
    
    - **job_id**: UUID of the processing job
    
    Returns secure download URL with expiration time for the generated XML file.
    The download URL is pre-signed and expires after a configurable time period (default: 1 hour).
    """
    async with get_db() as db:
        try:
            # Query processing job with user authorization
            result = await db.execute(
                select(ProcessingJob).filter(
                    ProcessingJob.id == job_id,
                    ProcessingJob.user_id == current_user.id
                )
            )
            processing_job = result.scalar_one_or_none()
            
            if not processing_job:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "job_not_found",
                        "message": "Processing job not found or access denied",
                        "job_id": str(job_id)
                    }
                )
            
            # Check if XML has been generated
            if processing_job.xml_generation_status != "COMPLETED" or not processing_job.output_xml_url:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "xml_not_available",
                        "message": "XML file has not been generated for this job",
                        "job_id": str(job_id),
                        "xml_generation_status": processing_job.xml_generation_status
                    }
                )
            
            # Initialize services
            xml_service = XMLGenerationService()
            storage_service = xml_service._get_storage_service()
            analytics_service = HSCodeAnalyticsService()
            
            # Generate fresh download URL (in case the stored one is expired)
            try:
                # Extract S3 key from the stored URL if it's an S3 URL
                if processing_job.output_xml_url.startswith('https://') and 's3' in processing_job.output_xml_url:
                    # For S3 URLs, extract the key part
                    s3_key = processing_job.output_xml_url.split('/')[-1]
                    download_url = storage_service.generate_download_url(s3_key)
                else:
                    # For direct URLs, use as-is (local development)
                    download_url = processing_job.output_xml_url
                    
                # Record successful download activity
                await analytics_service.record_download_activity(
                    job_id=str(job_id),
                    user_id=str(current_user.id),
                    file_name=f"asycuda_export_{job_id}.xml",
                    download_success=True
                )
                
            except Exception as e:
                # Record failed download activity
                await analytics_service.record_download_activity(
                    job_id=str(job_id),
                    user_id=str(current_user.id),
                    file_name=f"asycuda_export_{job_id}.xml",
                    download_success=False,
                    error_message=str(e)
                )
                
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "download_url_generation_failed",
                        "message": f"Failed to generate download URL: {str(e)}",
                        "job_id": str(job_id)
                    }
                )
            
            return XMLDownloadResponse(
                success=True,
                job_id=job_id,
                download_url=download_url,
                file_name=f"asycuda_export_{job_id}.xml",
                file_size=processing_job.xml_file_size,
                expires_at=None,  # Will be set by the storage service based on pre-signed URL
                content_type="application/xml",
                error_message=None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving XML download for job {job_id}: {str(e)}", exc_info=True)
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_server_error",
                    "message": f"Error retrieving XML download information: {str(e)}",
                    "job_id": str(job_id)
                }
            )


@router.get(
    "/processing/{job_id}/xml-status",
    response_model=dict,
    responses={
        200: {"description": "XML generation status retrieved successfully"},
        404: {"description": "Processing job not found or access denied"},
        500: {"description": "Internal server error"}
    }
)
async def get_xml_generation_status(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get XML generation status for a processing job
    
    - **job_id**: UUID of the processing job
    
    Returns the current status of XML generation and related metadata.
    """
    async with get_db() as db:
        try:
            # Query processing job with user authorization
            result = await db.execute(
                select(ProcessingJob).filter(
                    ProcessingJob.id == job_id,
                    ProcessingJob.user_id == current_user.id
                )
            )
            processing_job = result.scalar_one_or_none()
            
            if not processing_job:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "job_not_found",
                        "message": "Processing job not found or access denied",
                        "job_id": str(job_id)
                    }
                )
            
            return {
                "job_id": str(job_id),
                "xml_generation_status": processing_job.xml_generation_status,
                "xml_available": processing_job.xml_generation_status == "COMPLETED" and processing_job.output_xml_url is not None,
                "xml_generated_at": processing_job.xml_generated_at.isoformat() if processing_job.xml_generated_at else None,
                "xml_file_size": processing_job.xml_file_size,
                "country_schema": processing_job.country_schema,
                "total_products": processing_job.total_products,
                "successful_matches": processing_job.successful_matches,
                "average_confidence": float(processing_job.average_confidence) if processing_job.average_confidence else None,
                "processing_status": processing_job.status.value,
                "error_message": processing_job.error_message
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving XML status for job {job_id}: {str(e)}", exc_info=True)
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_server_error",
                    "message": f"Error retrieving XML generation status: {str(e)}",
                    "job_id": str(job_id)
                }
            )