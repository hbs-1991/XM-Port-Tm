"""
Job data operations API endpoints - Product Data and HS Code Updates
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.core.auth import get_current_active_user
from src.core.database import get_db
from src.models.user import User
from src.services.file_processing import FileProcessingService
from src.schemas.processing import ProductData, JobProductsResponse, HSCodeUpdateRequest

router = APIRouter()


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


@router.get("/jobs/{job_id}/products", response_model=JobProductsResponse)
async def get_job_products(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get processing job products with HS code data for spreadsheet preview
    
    - **job_id**: Processing job UUID
    
    Returns product data with HS codes, confidence scores, and alternative codes
    for display in the EditableSpreadsheet component
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
        
        # Format products with HS code data
        products = []
        for match in job.product_matches:
            # Calculate confidence level (High/Medium/Low)
            confidence_score = float(match.confidence_score)
            if confidence_score >= 0.95:
                confidence_level = "High"
            elif confidence_score >= 0.8:
                confidence_level = "Medium" 
            else:
                confidence_level = "Low"
            
            product = {
                "id": str(match.id),
                "product_description": match.product_description,
                "quantity": float(match.quantity),
                "unit": match.unit_of_measure,
                "value": float(match.value),
                "origin_country": match.origin_country,
                "unit_price": round(float(match.value) / float(match.quantity), 2),
                "hs_code": match.matched_hs_code,
                "confidence_score": confidence_score,
                "confidence_level": confidence_level,
                "alternative_hs_codes": match.alternative_hs_codes or [],
                "requires_manual_review": match.requires_manual_review,
                "user_confirmed": match.user_confirmed,
                "vector_store_reasoning": match.vector_store_reasoning
            }
            products.append(product)
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "products": products,
            "total_products": len(products),
            "high_confidence_count": len([p for p in products if p["confidence_level"] == "High"]),
            "requires_review_count": len([p for p in products if p["requires_manual_review"]])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving job products: {str(e)}"
        )


@router.put("/jobs/{job_id}/products/{product_id}/hs-code")
async def update_product_hs_code(
    job_id: str,
    product_id: str,
    request: HSCodeUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update HS code for a specific product (manual editing)
    
    - **job_id**: Processing job UUID
    - **product_id**: Product match UUID  
    - **hs_code**: New HS code (6-10 digits, optional dots)
    
    Validates HS code format and updates the product match record
    """
    try:
        from src.models.product_match import ProductMatch
        from src.models.processing_job import ProcessingJob
        import re
        
        # Extract HS code from request (validation already done by Pydantic)
        hs_code = request.hs_code
        
        # Query product match with job verification
        product_match = db.query(ProductMatch).join(ProcessingJob).filter(
            ProductMatch.id == product_id,
            ProcessingJob.id == job_id,
            ProcessingJob.user_id == current_user.id
        ).first()
        
        if not product_match:
            raise HTTPException(
                status_code=404,
                detail="Product not found or access denied"
            )
        
        # Update HS code and mark as user confirmed
        product_match.matched_hs_code = hs_code
        product_match.user_confirmed = True
        product_match.requires_manual_review = False
        db.commit()
        
        return {
            "success": True,
            "message": "HS code updated successfully",
            "product_id": product_id,
            "new_hs_code": hs_code
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating HS code: {str(e)}"
        )