"""
File operations API endpoints - Upload, Validation, and Templates
"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Optional, List

from src.core.auth import get_current_active_user
from src.core.database import get_db, sync_session_maker
from src.core.config import get_settings
from src.models.user import User
from src.services.file_processing import FileProcessingService
from src.schemas.processing import FileUploadResponse, FileUploadError
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
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and validate CSV or XLSX file for processing
    
    - **file**: CSV (UTF-8) or XLSX file with required columns
    - **country_schema**: 3-letter country code (default: USA)
    
    Required columns: Product Description, Quantity, Unit, Value, Origin Country
    """
    try:
        # Create a synchronous database session for file processing
        with sync_session_maker() as db:
            # Re-fetch the user in the current session to avoid session issues
            from src.models.user import User as UserModel
            user_in_session = db.query(UserModel).filter(UserModel.id == current_user.id).first()
            if not user_in_session:
                raise HTTPException(
                    status_code=401,
                    detail="User not found in current session"
                )
            
            # Initialize file processing service
            file_service = FileProcessingService(db)
            
            # Check user credits before processing
            credit_check = file_service.check_user_credits(user_in_session, estimated_credits=1)
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
                credit_check = file_service.check_user_credits(user_in_session, required_credits)
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
            if not file_service.reserve_user_credits(user_in_session, required_credits):
                # Refresh user data to get current balance
                db.refresh(user_in_session)
                
                # Provide specific error message based on current balance
                if user_in_session.credits_remaining < required_credits:
                    raise HTTPException(
                        status_code=402,  # Payment Required
                        detail={
                            "error": "insufficient_credits",
                            "message": f"Insufficient credits. You have {user_in_session.credits_remaining} credits but need {required_credits} for this file.",
                            "credits_remaining": user_in_session.credits_remaining,
                            "credits_required": required_credits,
                            "subscription_tier": user_in_session.subscription_tier.value
                        }
                    )
                else:
                    # Credits were available but reservation failed due to concurrency
                    raise HTTPException(
                        status_code=409,  # Conflict
                        detail={
                            "error": "credit_reservation_conflict",
                            "message": "Credit reservation failed due to concurrent requests. Please try again in a moment.",
                            "credits_required": required_credits,
                            "retry_suggested": True
                        }
                    )
            
            # Upload file to S3 (if configured)
            try:
                file_url = await file_service.upload_file_to_s3(file, str(user_in_session.id))
            except HTTPException as e:
                # Check if this is an S3-related error and fallback is allowed
                error_detail_str = str(e.detail)
                s3_error_indicators = [
                    "S3 configuration not available",
                    "AWS credentials not configured", 
                    "S3 upload failed",
                    "InvalidAccessKeyId",
                    "AccessDenied",
                    "NoSuchBucket",
                    "NoCredentialsError",
                    "CredentialsError",
                    "BotoCoreError",
                    "EndpointConnectionError"
                ]
                
                # More robust S3 error detection
                is_s3_error = (
                    any(indicator in error_detail_str for indicator in s3_error_indicators) or
                    "S3 upload failed:" in error_detail_str or
                    e.status_code == 500 and "S3" in error_detail_str
                )
                
                # Debug logging for S3 errors
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"S3 upload error detected - Status: {e.status_code}, "
                    f"Detail: {error_detail_str}, "
                    f"Is S3 Error: {is_s3_error}, "
                    f"Fallback Enabled: {settings.ALLOW_S3_FALLBACK}, "
                    f"Is Production: {settings.is_production}"
                )
                
                if (is_s3_error and 
                    settings.ALLOW_S3_FALLBACK and 
                    not settings.is_production):
                    # Development fallback to local storage - NOT production ready
                    file_url = f"local://uploads/{user_in_session.id}/{file.filename}"
                    # Log warning about using fallback
                    logger.warning(
                        f"Using local storage fallback for file upload. "
                        f"S3 Error: {error_detail_str}. File: {file.filename}, User: {user_in_session.id}. "
                        f"This is not suitable for production use."
                    )
                else:
                    # In production or when fallback is disabled, raise the original error
                    raise
            
            # Create processing job with credit information
            try:
                processing_job = file_service.create_processing_job(
                    user=user_in_session,
                    file_name=file.filename,
                    file_url=file_url,
                    file_size=file.size or 0,
                    country_schema=country_schema.upper(),
                    credits_used=required_credits,
                    total_products=validation_result.total_rows
                )
            except Exception as e:
                # If job creation fails, refund credits
                file_service.refund_user_credits(user_in_session, required_credits)
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
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"File upload error: {str(e)}", exc_info=True)
        
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
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate CSV or XLSX file without uploading or processing
    
    - **file**: CSV (UTF-8) or XLSX file with required columns
    
    Returns validation results with detailed error information.
    Required columns: Product Description, Quantity, Unit, Value, Origin Country, Unit Price
    """
    try:
        # Create a synchronous database session for file processing
        with sync_session_maker() as db:
            # Re-fetch the user in the current session to avoid session issues
            from src.models.user import User as UserModel
            user_in_session = db.query(UserModel).filter(UserModel.id == current_user.id).first()
            if not user_in_session:
                raise HTTPException(
                    status_code=401,
                    detail="User not found in current session"
                )
            
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


@router.get("/template/download")
async def download_csv_template():
    """
    Download CSV template with Russian column headers in UTF-8 format
    
    Returns a CSV file with UTF-8 BOM for proper Russian character support
    in Excel and other applications.
    """
    template_path = Path(__file__).parent.parent.parent / "templates" / "csv_template.csv"
    
    if not template_path.exists():
        raise HTTPException(
            status_code=404,
            detail="CSV template file not found"
        )
    
    # Read the template and add UTF-8 BOM for proper Russian character support
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add UTF-8 BOM (Byte Order Mark) for Excel compatibility with Russian characters
        utf8_bom = '\ufeff'
        content_with_bom = utf8_bom + content
        
        # Create response with proper UTF-8 encoding
        return Response(
            content=content_with_bom.encode('utf-8'),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=upload_template.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading template file: {str(e)}"
        )