"""
File processing API endpoints
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, Request
from sqlalchemy.orm import Session
from typing import Optional, List

from src.core.auth import get_current_active_user
from src.core.database import get_db
from src.core.config import get_settings
from src.models.user import User
from src.services.file_processing import FileProcessingService
from src.schemas.processing import FileUploadResponse, FileUploadError, ProductData
from src.middleware.rate_limit import limiter, UPLOAD_RATE_LIMITS

settings = get_settings()

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit(UPLOAD_RATE_LIMITS["per_minute"])
@limiter.limit(UPLOAD_RATE_LIMITS["per_hour"])
@limiter.limit(UPLOAD_RATE_LIMITS["per_day"])
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="CSV or XLSX file to upload"),
    country_schema: str = Form(default="USA", description="Country schema (3-letter code)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and validate CSV or XLSX file for processing
    
    - **file**: CSV (UTF-8) or XLSX file with required columns
    - **country_schema**: 3-letter country code (default: USA)
    
    Required columns: Product Description, Quantity, Unit, Value, Origin Country
    """
    try:
        # Initialize file processing service
        file_service = FileProcessingService(db)
        
        # Check user credits before processing
        credit_check = file_service.check_user_credits(current_user, estimated_credits=1)
        if not credit_check['has_sufficient_credits']:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "insufficient_credits",
                    "message": credit_check['message'],
                    "credits_remaining": credit_check['credits_remaining'],
                    "credits_required": credit_check['credits_required'],
                    "subscription_tier": current_user.subscription_tier.value
                }
            )
        
        # Validate uploaded file
        validation_result = await file_service.validate_file_upload(file)
        
        if not validation_result.is_valid:
            return FileUploadResponse(
                job_id="",
                file_name=file.filename,
                file_size=file.size or 0,
                status="FAILED",
                message="File validation failed",
                validation_results=validation_result.dict()
            )
        
        # Calculate actual credits required based on file size
        required_credits = file_service.calculate_processing_credits(validation_result.total_rows)
        
        # Re-check credits with actual requirement
        if required_credits > 1:  # If more credits needed than initially estimated
            credit_check = file_service.check_user_credits(current_user, required_credits)
            if not credit_check['has_sufficient_credits']:
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail={
                        "error": "insufficient_credits",
                        "message": credit_check['message'],
                        "credits_remaining": credit_check['credits_remaining'],
                        "credits_required": credit_check['credits_required'],
                        "subscription_tier": current_user.subscription_tier.value,
                        "file_rows": validation_result.total_rows
                    }
                )
        
        # Reserve credits atomically before processing
        if not file_service.reserve_user_credits(current_user, required_credits):
            raise HTTPException(
                status_code=409,  # Conflict
                detail={
                    "error": "credit_reservation_failed",
                    "message": "Unable to reserve credits. Please try again or check your balance.",
                    "credits_required": required_credits
                }
            )
        
        # Upload file to S3 (if configured)
        try:
            file_url = await file_service.upload_file_to_s3(file, str(current_user.id))
        except HTTPException as e:
            # Check if fallback is allowed and we're not in production
            if ("S3 configuration not available" in str(e.detail) and 
                settings.ALLOW_S3_FALLBACK and 
                not settings.is_production):
                # Development fallback to local storage - NOT production ready
                file_url = f"local://uploads/{current_user.id}/{file.filename}"
                # Log warning about using fallback
                import logging
                logging.warning(
                    f"Using local storage fallback for file upload. "
                    f"File: {file.filename}, User: {current_user.id}. "
                    f"This is not suitable for production use."
                )
            else:
                # In production or when fallback is disabled, raise the original error
                raise
        
        # Create processing job with credit information
        try:
            processing_job = file_service.create_processing_job(
                user=current_user,
                file_name=file.filename,
                file_url=file_url,
                file_size=file.size or 0,
                country_schema=country_schema.upper(),
                credits_used=required_credits,
                total_products=validation_result.total_rows
            )
        except Exception as e:
            # If job creation fails, refund credits
            file_service.refund_user_credits(current_user, required_credits)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create processing job: {str(e)}"
            )
        
        return FileUploadResponse(
            job_id=str(processing_job.id),
            file_name=processing_job.input_file_name,
            file_size=processing_job.input_file_size,
            status=processing_job.status.value,
            message="File uploaded and validated successfully. Processing will begin shortly.",
            validation_results=validation_result.dict() if validation_result.warnings else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during file upload: {str(e)}"
        )


@router.post("/validate", response_model=dict)
@limiter.limit("30 per minute")  # More lenient for validation-only requests
@limiter.limit("100 per hour")
async def validate_file_only(
    request: Request,
    file: UploadFile = File(..., description="CSV or XLSX file to validate"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Validate CSV or XLSX file without uploading or processing
    
    - **file**: CSV (UTF-8) or XLSX file with required columns
    
    Returns validation results with detailed error information.
    Required columns: Product Description, Quantity, Unit, Value, Origin Country, Unit Price
    """
    try:
        # Initialize file processing service
        file_service = FileProcessingService(db)
        
        # Validate uploaded file without storage
        validation_result = await file_service.validate_file_upload(file)
        
        return {
            "valid": validation_result.is_valid,
            "errors": [error.dict() for error in validation_result.errors],
            "warnings": validation_result.warnings,
            "total_rows": validation_result.total_rows,
            "valid_rows": validation_result.valid_rows,
            "summary": validation_result.summary.dict() if validation_result.summary else None,
            "previewData": validation_result.preview_data if hasattr(validation_result, 'preview_data') else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during file validation: {str(e)}"
        )


@router.get("/jobs")
async def get_processing_jobs(current_user: User = Depends(get_current_active_user)):
    """Get processing jobs endpoint - requires authentication"""
    return {"message": "Processing jobs endpoint - to be implemented", "user_id": str(current_user.id)}


@router.get("/jobs/{job_id}/data")
async def get_job_data(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get processing job data for editing"""
    try:
        file_service = FileProcessingService(db)
        job_data = file_service.get_job_data(job_id, current_user.id)
        
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail="Processing job not found or access denied"
            )
        
        return {
            "job_id": job_id,
            "data": job_data["data"],
            "metadata": job_data["metadata"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving job data: {str(e)}"
        )


@router.put("/jobs/{job_id}/data")
async def update_job_data(
    job_id: str,
    data: List[dict],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update processing job data with edited values"""
    try:
        file_service = FileProcessingService(db)
        
        # Validate data format
        validated_data = []
        for i, row in enumerate(data):
            try:
                # Validate each row against ProductData schema
                product_data = ProductData(
                    product_description=str(row.get('Product Description', '')),
                    quantity=float(row.get('Quantity', 0)),
                    unit=str(row.get('Unit', '')),
                    value=float(row.get('Value', 0)),
                    origin_country=str(row.get('Origin Country', '')),
                    unit_price=float(row.get('Unit Price', 0)),
                    row_number=i + 1
                )
                validated_data.append(product_data.dict())
            except Exception as validation_error:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid data in row {i + 1}: {str(validation_error)}"
                )
        
        # Update job data
        success = file_service.update_job_data(job_id, current_user.id, validated_data)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Processing job not found or access denied"
            )
        
        return {
            "message": "Job data updated successfully",
            "job_id": job_id,
            "rows_updated": len(validated_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating job data: {str(e)}"
        )