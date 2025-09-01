"""
Processing workflow API endpoints - Complete end-to-end processing
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.core.auth import get_current_active_user
from src.core.database import get_db, sync_session_maker
from src.models.user import User
from src.services.file_processing import FileProcessingService
from src.services.hs_matching_service import hs_matching_service
from src.schemas.processing import ProcessWithHSMatchingRequest, ProcessWithHSMatchingResponse
from src.middleware.rate_limit import limiter

router = APIRouter()


@router.post("/process-with-hs-matching", response_model=ProcessWithHSMatchingResponse)
@limiter.limit("10 per minute")  # Stricter limit for full processing
@limiter.limit("50 per hour")
async def process_file_with_hs_matching(
    request: Request,
    processing_request: ProcessWithHSMatchingRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Process uploaded file with immediate HS code matching
    
    This endpoint combines file processing and HS code matching into a single workflow.
    It reads the processed data from the job and performs HS code matching using OpenAI.
    
    Args:
        processing_request: Contains job_id and optional parameters
        current_user: Authenticated user
        
    Returns:
        Processing results with HS codes and confidence scores
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
            
            # Process the file and get products with HS matching
            result = await file_service.process_file_with_hs_matching(
                job_id=processing_request.job_id,
                user=user_in_session,
                country_schema=processing_request.country_schema,
                enable_caching=processing_request.enable_caching,
                confidence_threshold=processing_request.confidence_threshold
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "processing_failed",
                        "message": result.get("error", "Failed to process file"),
                        "job_id": processing_request.job_id
                    }
                )
            
            # Format response
            response = ProcessWithHSMatchingResponse(
                success=True,
                job_id=result["job_id"],
                status=result["status"],
                products_with_hs_codes=result["products"],
                processing_stats={
                    "total_products": result["total_products"],
                    "successful_matches": result["successful_matches"],
                    "failed_matches": result["failed_matches"],
                    "average_confidence": result["average_confidence"],
                    "processing_time_ms": result["processing_time_ms"],
                    "cache_hits": result.get("cache_hits", 0),
                    "cache_misses": result.get("cache_misses", 0)
                },
                message="File processed successfully with HS code matching"
            )
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Processing workflow error: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during processing workflow: {str(e)}"
        )