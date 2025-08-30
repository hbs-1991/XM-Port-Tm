"""
File processing API endpoints
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, Request
from sqlalchemy.orm import Session
from typing import Optional, List

from src.core.auth import get_current_active_user
from src.core.database import get_db, sync_session_maker
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
async def get_processing_jobs(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated processing jobs with filtering support
    
    - **page**: Page number (default: 1)
    - **limit**: Jobs per page (default: 50, max: 100)
    - **search**: Search by file name (optional)
    - **status**: Filter by processing status (optional)
    - **date_from**: Filter jobs from date (YYYY-MM-DD format, optional)
    - **date_to**: Filter jobs to date (YYYY-MM-DD format, optional)
    """
    try:
        from sqlalchemy import and_, or_
        from src.models.processing_job import ProcessingJob, ProcessingStatus
        from datetime import datetime
        
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page number must be >= 1")
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        # Build query filters
        filters = [ProcessingJob.user_id == current_user.id]
        
        # Search by file name
        if search and search.strip():
            filters.append(
                ProcessingJob.input_file_name.ilike(f"%{search.strip()}%")
            )
        
        # Filter by status
        if status:
            try:
                status_enum = ProcessingStatus(status.upper())
                filters.append(ProcessingJob.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status. Valid values: {[s.value for s in ProcessingStatus]}"
                )
        
        # Date range filters
        if date_from:
            try:
                date_from_parsed = datetime.strptime(date_from, "%Y-%m-%d")
                filters.append(ProcessingJob.created_at >= date_from_parsed)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="date_from must be in YYYY-MM-DD format"
                )
        
        if date_to:
            try:
                date_to_parsed = datetime.strptime(date_to, "%Y-%m-%d")
                # Add 1 day to include the entire day
                from datetime import timedelta
                date_to_parsed += timedelta(days=1)
                filters.append(ProcessingJob.created_at < date_to_parsed)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="date_to must be in YYYY-MM-DD format"
                )
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Query with filters, pagination, and ordering
        query = db.query(ProcessingJob).filter(and_(*filters))
        
        # Get total count for pagination metadata
        total_count = query.count()
        
        # Get paginated results ordered by creation date (newest first)
        jobs = query.order_by(ProcessingJob.created_at.desc()).offset(offset).limit(limit).all()
        
        # Format response data
        jobs_data = []
        for job in jobs:
            # Calculate processing duration
            processing_duration = None
            if job.started_at and job.completed_at:
                processing_duration = int((job.completed_at - job.started_at).total_seconds() * 1000)
            elif job.processing_time_ms:
                processing_duration = job.processing_time_ms
            
            job_data = {
                "id": str(job.id),
                "input_file_name": job.input_file_name,
                "status": job.status.value,
                "country_schema": job.country_schema,
                "input_file_size": job.input_file_size,
                "credits_used": job.credits_used,
                "total_products": job.total_products,
                "successful_matches": job.successful_matches,
                "average_confidence": float(job.average_confidence) if job.average_confidence else None,
                "processing_time_ms": processing_duration,
                "has_xml_output": job.output_xml_url is not None,
                "xml_generation_status": job.xml_generation_status,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            jobs_data.append(job_data)
        
        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "jobs": jobs_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            },
            "filters": {
                "search": search,
                "status": status,
                "date_from": date_from,
                "date_to": date_to
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving processing jobs: {str(e)}"
        )


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


@router.get("/jobs/{job_id}/details")
async def get_job_details(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive job details including product matches and HS codes
    
    - **job_id**: Processing job UUID
    
    Returns job information, product matches with confidence scores,
    HS code assignments, and validation status for dashboard preview
    """
    try:
        from sqlalchemy.orm import joinedload
        from src.models.processing_job import ProcessingJob
        from src.models.product_match import ProductMatch
        
        # Query job with product matches
        job = db.query(ProcessingJob).options(
            joinedload(ProcessingJob.product_matches)
        ).filter(
            ProcessingJob.id == job_id,
            ProcessingJob.user_id == current_user.id
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Processing job not found or access denied"
            )
        
        # Format job details
        job_details = {
            "id": str(job.id),
            "input_file_name": job.input_file_name,
            "status": job.status.value,
            "country_schema": job.country_schema,
            "input_file_size": job.input_file_size,
            "credits_used": job.credits_used,
            "processing_time_ms": job.processing_time_ms,
            "total_products": job.total_products,
            "successful_matches": job.successful_matches,
            "average_confidence": float(job.average_confidence) if job.average_confidence else None,
            "has_xml_output": job.output_xml_url is not None,
            "xml_generation_status": job.xml_generation_status,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
        
        # Format product matches
        product_matches = []
        for match in job.product_matches:
            product_match = {
                "id": str(match.id),
                "product_description": match.product_description,
                "quantity": float(match.quantity),
                "unit_of_measure": match.unit_of_measure,
                "value": float(match.value),
                "origin_country": match.origin_country,
                "matched_hs_code": match.matched_hs_code,
                "confidence_score": float(match.confidence_score),
                "alternative_hs_codes": match.alternative_hs_codes or [],
                "vector_store_reasoning": match.vector_store_reasoning,
                "requires_manual_review": match.requires_manual_review,
                "user_confirmed": match.user_confirmed,
                "created_at": match.created_at.isoformat()
            }
            product_matches.append(product_match)
        
        # Calculate additional statistics
        if product_matches:
            high_confidence_matches = len([m for m in product_matches if m["confidence_score"] >= 0.8])
            manual_review_required = len([m for m in product_matches if m["requires_manual_review"]])
            user_confirmed_matches = len([m for m in product_matches if m["user_confirmed"]])
        else:
            high_confidence_matches = 0
            manual_review_required = 0
            user_confirmed_matches = 0
        
        statistics = {
            "total_matches": len(product_matches),
            "high_confidence_matches": high_confidence_matches,
            "manual_review_required": manual_review_required,
            "user_confirmed": user_confirmed_matches,
            "success_rate": (job.successful_matches / job.total_products * 100) if job.total_products > 0 else 0
        }
        
        return {
            "job": job_details,
            "product_matches": product_matches,
            "statistics": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving job details: {str(e)}"
        )


@router.post("/process-with-hs-matching", response_model=dict)
@limiter.limit(UPLOAD_RATE_LIMITS["per_minute"])
@limiter.limit(UPLOAD_RATE_LIMITS["per_hour"]) 
@limiter.limit(UPLOAD_RATE_LIMITS["per_day"])
async def process_file_with_hs_matching(
    request: Request,
    file: UploadFile = File(..., description="CSV or XLSX file to process"),
    country_schema: str = Form(default="default", description="Country schema for HS code matching"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete file processing workflow with HS code matching
    
    - **file**: CSV (UTF-8) or XLSX file with required columns
    - **country_schema**: Country schema for HS code matching (default: default)
    
    Required columns: Product Description, Quantity, Unit, Value, Origin Country, Unit Price
    
    This endpoint performs the complete workflow:
    1. File validation
    2. Credit verification and reservation
    3. File upload to S3
    4. Product extraction
    5. HS code matching using OpenAI Vector Store
    6. ProductMatch record creation
    """
    try:
        # Initialize file processing service
        file_service = FileProcessingService(db)
        
        # Execute complete processing workflow with HS matching
        result = await file_service.process_file_with_hs_matching(
            file=file,
            user=current_user,
            country_schema=country_schema
        )
        
        # Return result based on success/failure
        if result.get("success"):
            return {
                "success": True,
                "job_id": result["job_id"],
                "products_processed": result["products_processed"],
                "processing_errors": result["processing_errors"],
                "credits_used": result["credits_used"],
                "processing_time_ms": result["processing_time_ms"],
                "hs_matching_summary": result["hs_matching_summary"],
                "validation_summary": {
                    "total_rows": result["validation_result"].total_rows,
                    "valid_rows": result["validation_result"].valid_rows,
                    "warnings": result["validation_result"].warnings
                }
            }
        else:
            # Processing failed
            status_code = 422 if "validation" in result.get("error", "") else 500
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": result.get("error"),
                    "job_id": result.get("job_id"),
                    "validation_result": result.get("validation_result"),
                    "credit_check": result.get("credit_check")
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"File processing with HS matching error: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during file processing: {str(e)}"
        )