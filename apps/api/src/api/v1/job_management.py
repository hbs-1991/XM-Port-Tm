"""
Job management API endpoints - Listing, Details, and Completion
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from src.core.auth import get_current_active_user
from src.core.database import get_db, sync_session_maker
from src.models.user import User
from src.services.file_processing import FileProcessingService
from src.schemas.processing import JobCompletionRequest, JobCompletionResponse
from src.middleware.rate_limit import limiter

router = APIRouter()


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


@router.post("/jobs/{job_id}/complete", response_model=JobCompletionResponse)
@limiter.limit("30 per minute")  # Allow frequent job completion calls
async def complete_job_after_hs_matching(
    request: Request,
    job_id: str,
    completion_request: JobCompletionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Complete a processing job after HS code matching is finished.
    
    This endpoint should be called after HS matching to:
    - Create ProductMatch records from HS matching results
    - Update job status to COMPLETED or COMPLETED_WITH_ERRORS
    - Calculate job statistics and processing metrics
    
    Args:
        job_id: Processing job UUID
        completion_request: HS matching results and any errors
        current_user: Authenticated user
        
    Returns:
        Job completion status and statistics
        
    Raises:
        HTTPException: If job not found, access denied, or completion fails
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
            
            # Create file processing service
            file_service = FileProcessingService(db)
            
            # Debug: Log incoming request data
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Job completion API called for job {job_id} with {len(completion_request.hs_matches)} matches")
            
            # Convert HS matches from schema to dict format (new format with all required fields)
            hs_matches_dict = []
            for i, match in enumerate(completion_request.hs_matches):
                logger.info(f"API Processing match {i}: product_description='{match.product_description}', quantity={getattr(match, 'quantity', 'MISSING')}, unit_of_measure='{getattr(match, 'unit_of_measure', 'MISSING')}', value={getattr(match, 'value', 'MISSING')}, origin_country='{getattr(match, 'origin_country', 'MISSING')}'")
                
                match_dict = {
                    'product_description': match.product_description,
                    'matched_hs_code': match.matched_hs_code,
                    'confidence_score': match.confidence_score,
                    'code_description': match.code_description,
                    'chapter': match.chapter,
                    'section': match.section,
                    'processing_time_ms': match.processing_time_ms,
                    # Include required ProductMatch fields
                    'quantity': getattr(match, 'quantity', None),
                    'unit_of_measure': getattr(match, 'unit_of_measure', None),
                    'value': getattr(match, 'value', None),
                    'origin_country': getattr(match, 'origin_country', None),
                    'alternative_matches': []  # Frontend doesn't send alternatives currently
                }
                hs_matches_dict.append(match_dict)
                logger.info(f"API Created match dict {i}: {match_dict}")
            
            logger.info(f"API Sending {len(hs_matches_dict)} matches to job completion service")
            
            # Complete the job
            result = await file_service.complete_job_after_hs_matching(
                job_id=job_id,
                user=user_in_session,
                hs_matches=hs_matches_dict,
                processing_errors=completion_request.processing_errors
            )
            
            if result.get("success"):
                return JobCompletionResponse(
                    success=True,
                    job_id=result["job_id"],
                    status=result["status"],
                    total_products=result["total_products"],
                    successful_matches=result["successful_matches"],
                    average_confidence=result["average_confidence"],
                    processing_time_ms=result["processing_time_ms"],
                    message=result["message"]
                )
            else:
                # Job completion failed
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "job_completion_failed",
                        "message": result.get("error", "Failed to complete job"),
                        "job_id": job_id
                    }
                )
    
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Job completion error for job {job_id}: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete job: {str(e)}"
        )