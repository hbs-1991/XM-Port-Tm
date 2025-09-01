"""
Job management service for handling processing jobs lifecycle
"""
import time
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.models.user import User
from src.schemas.processing import ProcessingJobCreate

logger = logging.getLogger(__name__)


class JobManagementService:
    """Service for managing processing jobs lifecycle"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_processing_job(
        self, 
        user: User, 
        file_name: str, 
        file_url: str, 
        file_size: int,
        country_schema: str = "USA",
        credits_used: int = 1,
        total_products: int = 0
    ) -> ProcessingJob:
        """Create a new processing job in the database"""
        
        job_data = ProcessingJobCreate(
            input_file_name=file_name,
            input_file_url=file_url,
            input_file_size=file_size,
            country_schema=country_schema,
            credits_used=credits_used,
            total_products=total_products
        )
        
        processing_job = ProcessingJob(
            user_id=user.id,
            input_file_name=job_data.input_file_name,
            input_file_url=job_data.input_file_url,
            input_file_size=job_data.input_file_size,
            country_schema=job_data.country_schema,
            credits_used=job_data.credits_used,
            total_products=job_data.total_products,
            status=ProcessingStatus.PENDING
        )
        
        self.db.add(processing_job)
        self.db.commit()
        self.db.refresh(processing_job)
        
        return processing_job
    
    def get_job_data(self, job_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get processing job data for editing"""
        try:
            # Find the processing job
            job = self.db.query(ProcessingJob).filter(
                ProcessingJob.id == job_id,
                ProcessingJob.user_id == user_id
            ).first()
            
            if not job:
                return None
            
            # For now, we'll return sample data structure
            # In a real implementation, this would fetch actual processed data from S3 or database
            # This could be stored in a separate table like ProcessingJobData
            sample_data = [
                {
                    'Product Description': 'Apple iPhone 14 Pro',
                    'Quantity': 10,
                    'Unit': 'pcs',
                    'Value': 12000.00,
                    'Origin Country': 'China',
                    'Unit Price': 1200.00
                },
                {
                    'Product Description': 'Samsung Galaxy S23',
                    'Quantity': 5,
                    'Unit': 'pcs', 
                    'Value': 4000.00,
                    'Origin Country': 'South Korea',
                    'Unit Price': 800.00
                }
            ]
            
            return {
                'data': sample_data,
                'metadata': {
                    'job_id': job_id,
                    'file_name': job.input_file_name,
                    'total_rows': len(sample_data),
                    'status': job.status.value,
                    'created_at': job.created_at.isoformat()
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving job data: {str(e)}"
            )
    
    def update_job_data(self, job_id: str, user_id: int, data: List[Dict[str, Any]]) -> bool:
        """Update processing job data with edited values"""
        try:
            # Find the processing job
            job = self.db.query(ProcessingJob).filter(
                ProcessingJob.id == job_id,
                ProcessingJob.user_id == user_id
            ).first()
            
            if not job:
                return False
            
            # In a real implementation, this would:
            # 1. Store the updated data in a ProcessingJobData table
            # 2. Update the file in S3 with the new data
            # 3. Mark the job as "modified" or "pending re-processing"
            
            # For now, we'll just validate the data format and return success
            for row in data:
                required_fields = ['product_description', 'quantity', 'unit', 'value', 'origin_country', 'unit_price']
                for field in required_fields:
                    if field not in row:
                        raise ValueError(f"Missing required field: {field}")
            
            # Update job metadata to indicate data was modified
            job.total_products = len(data)
            # You could add a 'modified_at' field to track when data was last edited
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error updating job data: {str(e)}"
            )
    
    def update_job_status(
        self, 
        job: ProcessingJob, 
        status: ProcessingStatus, 
        error_message: Optional[str] = None
    ) -> None:
        """Update job status and error message"""
        job.status = status
        if error_message:
            job.error_message = error_message
        
        # Set timestamps based on status
        if status == ProcessingStatus.PROCESSING and not job.started_at:
            job.started_at = datetime.now(timezone.utc)
        elif status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.COMPLETED_WITH_ERRORS]:
            if not job.completed_at:
                job.completed_at = datetime.now(timezone.utc)
        
        self.db.commit()
    
    def update_job_xml_status(
        self,
        job: ProcessingJob,
        xml_status: str,
        xml_url: Optional[str] = None,
        xml_file_size: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update job XML generation status"""
        job.xml_generation_status = xml_status
        
        if xml_url:
            job.output_xml_url = xml_url
        
        if xml_file_size:
            job.xml_file_size = xml_file_size
            
        if xml_status == "COMPLETED":
            job.xml_generated_at = datetime.now(timezone.utc)
        
        if error_message:
            job.error_message = error_message
            
        self.db.commit()
    
    async def complete_job_after_hs_matching(
        self,
        job_id: str,
        user: User,
        hs_matches: List[dict],
        processing_errors: List[str] = None
    ) -> dict:
        """
        Complete a processing job after HS code matching is done.
        Creates ProductMatch records and updates job status to COMPLETED.
        
        Args:
            job_id: Processing job UUID
            user: User object
            hs_matches: List of HS matching results
            processing_errors: Optional list of processing errors
            
        Returns:
            Dict with completion result
        """
        start_time = time.time()
        processing_errors = processing_errors or []
        
        try:
            # Get the processing job
            processing_job = self.db.query(ProcessingJob).filter(
                ProcessingJob.id == job_id,
                ProcessingJob.user_id == user.id
            ).first()
            
            if not processing_job:
                raise ValueError(f"Processing job {job_id} not found or access denied")
            
            # Check if job is already in a final state
            if processing_job.status not in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]:
                # If job is already completed, return the existing result instead of failing
                if processing_job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.COMPLETED_WITH_ERRORS]:
                    logger.info(f"Job {job_id} is already completed with status {processing_job.status.value}, returning existing result")
                    return {
                        "success": True,
                        "job_id": job_id,
                        "status": processing_job.status.value,
                        "total_products": processing_job.total_products,
                        "successful_matches": processing_job.successful_matches,
                        "average_confidence": float(processing_job.average_confidence) if processing_job.average_confidence else None,
                        "processing_time_ms": processing_job.processing_time_ms,
                        "message": f"Job was already completed with status {processing_job.status.value}",
                        "errors": []
                    }
                else:
                    # For FAILED status or other invalid states, still raise error
                    raise ValueError(f"Job must be in PENDING or PROCESSING status. Current status: {processing_job.status.value}")
            
            logger.info(f"Completing job {job_id} after HS matching with {len(hs_matches)} matches")
            
            # Update job status to processing
            processing_job.status = ProcessingStatus.PROCESSING
            processing_job.started_at = datetime.now(timezone.utc)
            self.db.commit()
            
            # Create ProductMatch records from HS matching results
            created_matches = []
            error_count = 0
            
            for match_data in hs_matches:
                try:
                    logger.info(f"Processing match data: {match_data}")
                    
                    # Handle both old and new format for backward compatibility
                    if 'query' in match_data and 'primary_match' in match_data:
                        # Old format - extract from nested structure
                        product_description = match_data.get('query', '')
                        primary_match = match_data.get('primary_match', {})
                        
                        if not primary_match:
                            error_count += 1
                            continue
                            
                        matched_hs_code = primary_match.get('hs_code', 'ERROR')
                        confidence_score = primary_match.get('confidence', 0.0)
                        code_description = primary_match.get('code_description', '')
                        chapter = primary_match.get('chapter', '')
                        section = primary_match.get('section', '')
                        
                        # Required fields - use defaults if not present
                        quantity = Decimal('1.0')
                        unit_of_measure = 'PCE'
                        value = Decimal('0.0')
                        origin_country = 'XX'
                        
                    else:
                        # New format - direct field access
                        product_description = match_data.get('product_description', '')
                        matched_hs_code = match_data.get('matched_hs_code', 'ERROR')
                        confidence_score = match_data.get('confidence_score', 0.0)
                        code_description = match_data.get('code_description', '')
                        chapter = match_data.get('chapter', '')
                        section = match_data.get('section', '')
                        
                        # Required fields from frontend
                        quantity = Decimal(str(match_data.get('quantity', 1.0)))
                        unit_of_measure = match_data.get('unit_of_measure', 'PCE')
                        value = Decimal(str(match_data.get('value', 0.0)))
                        origin_country = match_data.get('origin_country', 'XX')
                    
                    # Validate required fields
                    logger.info(f"Validation - product_description: '{product_description}', matched_hs_code: '{matched_hs_code}', quantity: {quantity}, unit_of_measure: '{unit_of_measure}', value: {value}, origin_country: '{origin_country}'")
                    
                    if not product_description or matched_hs_code == 'ERROR':
                        logger.error(f"Validation failed: product_description='{product_description}', matched_hs_code='{matched_hs_code}'")
                        error_count += 1
                        continue
                    
                    # Map alternative matches into the model's alternative_hs_codes (ARRAY of strings)
                    alternative_hs_codes = []
                    try:
                        raw_alternatives = match_data.get('alternative_matches', [])
                        if isinstance(raw_alternatives, list):
                            for alt in raw_alternatives:
                                # Support both dicts with hs_code and raw string lists
                                if isinstance(alt, dict) and 'hs_code' in alt:
                                    alternative_hs_codes.append(str(alt.get('hs_code')))
                                elif isinstance(alt, str):
                                    alternative_hs_codes.append(alt)
                    except Exception:
                        # Be resilient; alternatives are optional
                        alternative_hs_codes = []

                    # Optional vector store reasoning (present in some matching responses)
                    vector_store_reasoning = None
                    try:
                        if 'primary_match' in match_data and isinstance(match_data.get('primary_match'), dict):
                            vector_store_reasoning = match_data['primary_match'].get('reasoning')
                    except Exception:
                        vector_store_reasoning = None

                    # Create ProductMatch record (only with valid model fields)
                    product_match = ProductMatch(
                        job_id=processing_job.id,
                        product_description=product_description,
                        quantity=quantity,
                        unit_of_measure=unit_of_measure,
                        value=value,
                        origin_country=origin_country,
                        matched_hs_code=matched_hs_code,
                        confidence_score=Decimal(str(confidence_score)),
                        # The following additional attributes exist on the model
                        alternative_hs_codes=alternative_hs_codes if alternative_hs_codes else None,
                        vector_store_reasoning=vector_store_reasoning,
                        # Descriptive fields stored if the model supports them
                        requires_manual_review=confidence_score < 0.8,
                        user_confirmed=False,
                    )
                    
                    self.db.add(product_match)
                    created_matches.append(product_match)
                    
                except Exception as e:
                    logger.error(f"Error creating ProductMatch for job {job_id}: {str(e)}")
                    logger.error(f"Failed match data: {match_data}")
                    processing_errors.append(f"Error processing product: {str(e)}")
                    error_count += 1
            
            # Commit all ProductMatch records
            self.db.commit()
            
            # Update job status and statistics
            total_processing_time = (time.time() - start_time) * 1000
            
            if not processing_errors and error_count == 0:
                processing_job.status = ProcessingStatus.COMPLETED
                status_message = "Job completed successfully"
            else:
                processing_job.status = ProcessingStatus.COMPLETED_WITH_ERRORS
                status_message = f"Job completed with {len(processing_errors) + error_count} errors"
                logger.error(f"Job completion errors - processing_errors: {processing_errors}, error_count: {error_count}")
                logger.info(f"Created {len(created_matches)} matches out of {len(hs_matches)} total matches")
            
            processing_job.total_products = len(created_matches)
            processing_job.successful_matches = len([m for m in created_matches if m.matched_hs_code != "ERROR"])
            processing_job.processing_time_ms = int(total_processing_time)
            
            # Calculate average confidence
            if created_matches:
                total_confidence = sum(float(match.confidence_score) for match in created_matches if match.matched_hs_code != "ERROR")
                successful_count = len([m for m in created_matches if m.matched_hs_code != "ERROR"])
                if successful_count > 0:
                    processing_job.average_confidence = Decimal(str(total_confidence / successful_count))
            
            # Set completion timestamp
            processing_job.completed_at = datetime.now(timezone.utc)
            
            # Store errors if any
            if processing_errors:
                processing_job.error_message = "; ".join(processing_errors[:5])  # Limit error details
            
            self.db.commit()
            
            logger.info(f"Job {job_id} completed with {len(created_matches)} products, {processing_job.successful_matches} successful matches")
            
            return {
                "success": True,
                "job_id": job_id,
                "status": processing_job.status.value,
                "total_products": processing_job.total_products,
                "successful_matches": processing_job.successful_matches,
                "average_confidence": float(processing_job.average_confidence) if processing_job.average_confidence else None,
                "processing_time_ms": processing_job.processing_time_ms,
                "message": status_message,
                "errors": processing_errors
            }
            
        except Exception as e:
            logger.error(f"Error completing job {job_id} after HS matching: {str(e)}")
            
            # Update job status to failed if possible
            try:
                if 'processing_job' in locals():
                    processing_job.status = ProcessingStatus.FAILED
                    processing_job.error_message = f"Job completion failed: {str(e)}"
                    processing_job.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
            except:
                pass
            
            return {
                "success": False,
                "error": str(e),
                "job_id": job_id
            }
