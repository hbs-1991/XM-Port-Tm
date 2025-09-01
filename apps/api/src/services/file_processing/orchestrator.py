"""
File processing orchestrator that coordinates all file processing services
"""
import time
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.models.user import User
from src.schemas.hs_matching import HSCodeMatchRequest
from src.services.hs_matching_service import hs_matching_service
from src.services.xml_generation import XMLGenerationService, CountrySchema

from .validation_service import FileValidationService
from .credit_service import CreditService
from .storage_service import StorageService
from .data_extraction_service import DataExtractionService
from .job_management_service import JobManagementService

logger = logging.getLogger(__name__)

# Import WebSocket manager for progress updates
try:
    from src.api.v1.ws import manager as ws_manager
except ImportError:
    # If WebSocket manager not available, create a dummy one
    class DummyWSManager:
        async def send_job_update(self, *args, **kwargs):
            pass
    ws_manager = DummyWSManager()


class FileProcessingOrchestrator:
    """Main orchestrator that coordinates all file processing services"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Initialize all services
        self.validation_service = FileValidationService()
        self.credit_service = CreditService(db)
        self.storage_service = StorageService()
        self.data_extraction_service = DataExtractionService()
        self.job_management_service = JobManagementService(db)
        self.xml_generation_service = XMLGenerationService()
    
    async def validate_file_upload(self, file: UploadFile):
        """Delegate to validation service"""
        return await self.validation_service.validate_file_upload(file)
    
    def check_user_credits(self, user: User, estimated_credits: int = 1):
        """Delegate to credit service"""
        return self.credit_service.check_user_credits(user, estimated_credits)
    
    def calculate_processing_credits(self, total_rows: int):
        """Delegate to credit service"""
        return self.credit_service.calculate_processing_credits(total_rows)
    
    def reserve_user_credits(self, user: User, credits_to_reserve: int):
        """Delegate to credit service"""
        return self.credit_service.reserve_user_credits(user, credits_to_reserve)
    
    def refund_user_credits(self, user: User, credits_to_refund: int):
        """Delegate to credit service"""
        return self.credit_service.refund_user_credits(user, credits_to_refund)
    
    async def upload_file_to_s3(self, file: UploadFile, user_id: str):
        """Delegate to storage service"""
        return await self.storage_service.upload_file_to_s3(file, user_id)
    
    def create_processing_job(self, user: User, file_name: str, file_url: str, file_size: int, **kwargs):
        """Delegate to job management service"""
        return self.job_management_service.create_processing_job(
            user, file_name, file_url, file_size, **kwargs
        )
    
    def get_job_data(self, job_id: str, user_id: int):
        """Delegate to job management service"""
        return self.job_management_service.get_job_data(job_id, user_id)
    
    def update_job_data(self, job_id: str, user_id: int, data: List[Dict[str, Any]]):
        """Delegate to job management service"""
        return self.job_management_service.update_job_data(job_id, user_id, data)
    
    async def process_file_with_hs_matching(
        self,
        file: UploadFile,
        user: User,
        country_schema: str = "default"
    ) -> Dict[str, Any]:
        """
        Complete file processing workflow with HS code matching
        
        Args:
            file: Uploaded file to process
            user: User who uploaded the file
            country_schema: Country schema for HS code matching
            
        Returns:
            Dictionary with processing results and statistics
        """
        start_time = time.time()
        
        try:
            # WebSocket: Notify file processing started
            await ws_manager.send_job_update(
                job_id="pending",
                user_id=str(user.id),
                status="STARTED",
                progress=5,
                message="Starting file processing..."
            )
            
            # Step 1: Validate file upload
            await self._send_progress_update(user.id, "pending", "VALIDATING", 10, "Validating file format and content...")
            
            validation_result = await self.validation_service.validate_file_upload(file)
            if not validation_result.is_valid:
                await self._send_progress_update(user.id, "pending", "FAILED", 100, "File validation failed")
                return {
                    "success": False,
                    "error": "File validation failed",
                    "validation_result": validation_result
                }
            
            # Step 2: Check user credits
            await self._send_progress_update(user.id, "pending", "CHECKING_CREDITS", 15, "Checking user credits...")
            
            estimated_credits = self.credit_service.calculate_processing_credits(validation_result.total_rows)
            credit_check = self.credit_service.check_user_credits(user, estimated_credits)
            
            if not credit_check['has_sufficient_credits']:
                await self._send_progress_update(user.id, "pending", "FAILED", 100, "Insufficient credits for processing")
                return {
                    "success": False,
                    "error": "Insufficient credits",
                    "credit_check": credit_check
                }
            
            # Step 3: Reserve credits
            credits_reserved = self.credit_service.reserve_user_credits(user, estimated_credits)
            if not credits_reserved:
                return {
                    "success": False,
                    "error": "Failed to reserve credits - insufficient balance"
                }
            
            # Step 4: Upload file to S3 (with fallback handling)
            await self._send_progress_update(user.id, "pending", "UPLOADING", 25, "Uploading file to secure storage...")
            
            file_url = await self._handle_file_upload(file, user, estimated_credits)
            if not file_url:
                return {
                    "success": False,
                    "error": "File upload failed"
                }
            
            # Step 5: Create processing job
            await self._send_progress_update(user.id, "pending", "CREATING_JOB", 30, "Creating processing job...")
            
            processing_job = self.job_management_service.create_processing_job(
                user=user,
                file_name=file.filename,
                file_url=file_url,
                file_size=file.size,
                country_schema=country_schema,
                credits_used=estimated_credits,
                total_products=validation_result.total_rows
            )
            
            # Step 6: Extract product data from file
            await self._send_progress_update(processing_job.id, user.id, "PARSING", 35, "Parsing file data...")
            
            try:
                await file.seek(0)  # Reset file pointer
                content = await file.read()
                
                products_data = await self.data_extraction_service.extract_products_from_file(
                    content, file.filename
                )
                    
            except Exception as e:
                # Refund credits if parsing fails
                self.credit_service.refund_user_credits(user, estimated_credits)
                self.job_management_service.update_job_status(
                    processing_job, ProcessingStatus.FAILED, f"File parsing failed: {str(e)}"
                )
                
                return {
                    "success": False,
                    "error": f"File parsing failed: {str(e)}",
                    "job_id": str(processing_job.id)
                }
            
            # Step 7: Process products with HS code matching
            await self._send_progress_update(
                processing_job.id, user.id, "HS_MATCHING", 50, 
                f"Matching HS codes for {len(products_data)} products..."
            )
            
            try:
                product_matches, processing_errors = await self.process_products_with_hs_matching(
                    processing_job=processing_job,
                    products_data=products_data,
                    country_schema=country_schema
                )
                
                # Step 8: Generate XML file after successful HS matching
                result = await self._generate_xml_output(
                    processing_job, product_matches, country_schema, processing_errors
                )
                
                # Calculate final processing time
                total_processing_time = (time.time() - start_time) * 1000
                processing_job.processing_time_ms = int(total_processing_time)
                self.db.commit()
                
                # Send completion notification
                await self._send_completion_notification(
                    processing_job, product_matches, processing_errors, total_processing_time
                )
                
                return result
                
            except Exception as e:
                # If HS matching fails, refund credits and update job
                self.credit_service.refund_user_credits(user, estimated_credits)
                self.job_management_service.update_job_status(
                    processing_job, ProcessingStatus.FAILED, f"HS code matching failed: {str(e)}"
                )
                
                return {
                    "success": False,
                    "error": f"HS code matching failed: {str(e)}",
                    "job_id": str(processing_job.id)
                }
        
        except Exception as e:
            logger.error(f"Complete file processing failed: {str(e)}")
            return {
                "success": False,
                "error": f"File processing failed: {str(e)}"
            }

    async def process_products_with_hs_matching(
        self,
        processing_job: ProcessingJob,
        products_data: List[Dict[str, Any]],
        country_schema: str = "default"
    ) -> Tuple[List[ProductMatch], List[str]]:
        """
        Process products data and match HS codes using the HS matching service
        
        Args:
            processing_job: The processing job to associate matches with
            products_data: List of validated product data dictionaries
            country_schema: Country schema for HS code matching
            
        Returns:
            Tuple of (created ProductMatch records, error messages)
        """
        created_matches = []
        error_messages = []
        
        try:
            # Convert product data to HS matching requests
            match_requests = []
            for product in products_data:
                match_request = HSCodeMatchRequest(
                    product_description=product.get('product_description', ''),
                    country=country_schema,
                    include_alternatives=True,
                    confidence_threshold=0.5  # Lower threshold for initial matching
                )
                match_requests.append(match_request)
            
            logger.info(f"Processing {len(match_requests)} products for HS code matching")
            
            # Batch process HS code matching
            try:
                matching_results = await hs_matching_service.match_batch_products(
                    requests=match_requests,
                    max_concurrent=5  # Conservative concurrency for file processing
                )
            except Exception as e:
                error_messages.append(f"HS code matching service failed: {str(e)}")
                # Update job status to failed
                self.job_management_service.update_job_status(
                    processing_job, ProcessingStatus.FAILED, f"HS code matching failed: {str(e)}"
                )
                return created_matches, error_messages
            
            # Create ProductMatch records for each successful result
            for i, (product_data, match_result) in enumerate(zip(products_data, matching_results)):
                try:
                    # Extract numeric values with proper conversion
                    quantity = Decimal(str(product_data.get('quantity', 0)).replace(',', ''))
                    value = Decimal(str(product_data.get('value', 0)).replace(',', ''))
                    
                    # Determine if manual review is required
                    requires_review = hs_matching_service.should_require_manual_review(
                        match_result.primary_match.confidence
                    )
                    
                    # Extract alternative HS codes
                    alternatives = []
                    if match_result.alternative_matches:
                        alternatives = [alt.hs_code for alt in match_result.alternative_matches]
                    
                    # Create ProductMatch record
                    product_match = ProductMatch(
                        job_id=processing_job.id,
                        product_description=product_data.get('product_description', ''),
                        quantity=quantity,
                        unit_of_measure=product_data.get('unit', ''),
                        value=value,
                        origin_country=product_data.get('origin_country', '')[:3].upper(),  # Ensure 3-char country code
                        matched_hs_code=match_result.primary_match.hs_code,
                        confidence_score=Decimal(str(match_result.primary_match.confidence)),
                        alternative_hs_codes=alternatives if alternatives else None,
                        vector_store_reasoning=match_result.primary_match.reasoning,
                        requires_manual_review=requires_review,
                        user_confirmed=False
                    )
                    
                    self.db.add(product_match)
                    created_matches.append(product_match)
                    
                except Exception as e:
                    error_msg = f"Failed to create ProductMatch for row {i+1}: {str(e)}"
                    logger.error(error_msg)
                    error_messages.append(error_msg)
                    continue
            
            # Commit all ProductMatch records and update job status
            try:
                self.db.commit()
                
                # Update job status and statistics after successful processing
                if not error_messages:
                    status = ProcessingStatus.COMPLETED
                    processing_job.total_products = len(created_matches)
                    processing_job.successful_matches = len(created_matches)
                else:
                    status = ProcessingStatus.COMPLETED_WITH_ERRORS
                    processing_job.total_products = len(created_matches)
                    processing_job.successful_matches = len([m for m in created_matches if m.matched_hs_code != "ERROR"])
                    processing_job.error_message = "; ".join(error_messages[:5])  # Limit error details
                
                # Calculate average confidence
                if created_matches:
                    total_confidence = sum(float(match.confidence_score) for match in created_matches)
                    processing_job.average_confidence = Decimal(str(total_confidence / len(created_matches)))
                
                # Set completion timestamp
                processing_job.completed_at = datetime.now(timezone.utc)
                processing_job.status = status
                
                self.db.commit()
                
                logger.info(f"Created {len(created_matches)} ProductMatch records with {len(error_messages)} errors")
                
            except Exception as e:
                self.db.rollback()
                error_msg = f"Failed to save ProductMatch records: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
                
                # Update job status to failed
                self.job_management_service.update_job_status(
                    processing_job, ProcessingStatus.FAILED, error_msg
                )
            
            return created_matches, error_messages
            
        except Exception as e:
            logger.error(f"Product processing failed: {str(e)}")
            error_messages.append(f"Product processing failed: {str(e)}")
            
            # Update job status to failed
            self.job_management_service.update_job_status(
                processing_job, ProcessingStatus.FAILED, str(e)
            )
            
            return created_matches, error_messages

    async def complete_job_after_hs_matching(self, job_id: str, user: User, hs_matches: List[dict], processing_errors: List[str] = None):
        """Delegate to job management service"""
        return await self.job_management_service.complete_job_after_hs_matching(
            job_id, user, hs_matches, processing_errors
        )
    
    # Private helper methods
    async def _send_progress_update(self, job_id, user_id, status, progress, message):
        """Send progress update via WebSocket"""
        await ws_manager.send_job_update(
            job_id=str(job_id),
            user_id=str(user_id),
            status=status,
            progress=progress,
            message=message
        )
    
    async def _handle_file_upload(self, file: UploadFile, user: User, estimated_credits: int) -> str:
        """Handle file upload with S3 fallback"""
        try:
            return await self.storage_service.upload_file_to_s3(file, str(user.id))
        except HTTPException as e:
            # Try fallback
            fallback_url = await self.storage_service.handle_s3_fallback(e, file, str(user.id))
            if fallback_url:
                return fallback_url
            
            # Refund credits if upload fails and no fallback
            self.credit_service.refund_user_credits(user, estimated_credits)
            await self._send_progress_update(
                user.id, "pending", "FAILED", 100, f"File upload failed: {str(e)}"
            )
            return None
        except Exception as e:
            # Refund credits for other upload errors
            self.credit_service.refund_user_credits(user, estimated_credits)
            await self._send_progress_update(
                user.id, "pending", "FAILED", 100, f"File upload failed: {str(e)}"
            )
            return None
    
    async def _generate_xml_output(
        self, 
        processing_job: ProcessingJob, 
        product_matches: List[ProductMatch], 
        country_schema: str,
        processing_errors: List[str]
    ) -> Dict[str, Any]:
        """Generate XML output and update job"""
        await self._send_progress_update(
            processing_job.id, processing_job.user_id, "GENERATING_XML", 75,
            "Generating ASYCUDA-compliant XML file..."
        )
        
        xml_errors = []
        xml_generation_result = None
        
        if product_matches:  # Only generate XML if we have product matches
            try:
                # Update XML generation status
                self.job_management_service.update_job_xml_status(processing_job, "GENERATING")
                
                # Convert country schema to CountrySchema enum
                xml_country_schema = CountrySchema.TURKMENISTAN  # Default to Turkmenistan for now
                if country_schema.upper() == "TKM":
                    xml_country_schema = CountrySchema.TURKMENISTAN
                
                # Generate XML using the XML Generation Service
                xml_generation_result = await self.xml_generation_service.generate_xml(
                    processing_job=processing_job,
                    product_matches=product_matches,
                    country_schema=xml_country_schema
                )
                
                if xml_generation_result.success:
                    # Update processing job with XML details
                    self.job_management_service.update_job_xml_status(
                        processing_job, 
                        "COMPLETED",
                        xml_url=xml_generation_result.s3_url or xml_generation_result.download_url,
                        xml_file_size=xml_generation_result.file_size
                    )
                    processing_job.status = ProcessingStatus.COMPLETED
                    
                    logger.info(
                        f"XML generated and stored successfully for job {processing_job.id}, "
                        f"storage type: {xml_generation_result.storage_type}, "
                        f"size: {xml_generation_result.file_size} bytes"
                    )
                else:
                    # XML generation failed
                    xml_errors = xml_generation_result.validation_errors or [
                        xml_generation_result.error_message or "Unknown XML generation error"
                    ]
                    self.job_management_service.update_job_xml_status(
                        processing_job, "FAILED", 
                        error_message=f"XML generation failed: {'; '.join(xml_errors[:3])}"
                    )
                    processing_job.status = ProcessingStatus.COMPLETED_WITH_ERRORS
                    
                    logger.warning(f"XML generation failed for job {processing_job.id}: {xml_errors}")
                    
            except Exception as e:
                xml_error_msg = f"XML generation failed: {str(e)}"
                xml_errors.append(xml_error_msg)
                self.job_management_service.update_job_xml_status(
                    processing_job, "FAILED", error_message=xml_error_msg
                )
                processing_job.status = ProcessingStatus.COMPLETED_WITH_ERRORS
                
                logger.error(f"XML generation error for job {processing_job.id}: {str(e)}", exc_info=True)
        else:
            # No product matches - mark as completed but without XML
            self.job_management_service.update_job_xml_status(processing_job, "FAILED")
            processing_job.status = ProcessingStatus.COMPLETED
            xml_errors.append("No product matches available for XML generation")
        
        # Commit all updates
        self.db.commit()
        
        # Prepare success response
        return {
            "success": True,
            "job_id": str(processing_job.id),
            "products_processed": len(product_matches),
            "processing_errors": processing_errors,
            "xml_errors": xml_errors,
            "credits_used": processing_job.credits_used,
            "hs_matching_summary": {
                "total_matches": len(product_matches),
                "high_confidence": len([m for m in product_matches if m.confidence_score >= 0.95]),
                "medium_confidence": len([m for m in product_matches if 0.8 <= m.confidence_score < 0.95]),
                "low_confidence": len([m for m in product_matches if m.confidence_score < 0.8]),
                "requires_review": len([m for m in product_matches if m.requires_manual_review])
            },
            "xml_generation": {
                "success": xml_generation_result.success if xml_generation_result else False,
                "xml_url": processing_job.output_xml_url,
                "errors": xml_errors
            }
        }
    
    async def _send_completion_notification(
        self, 
        processing_job: ProcessingJob, 
        product_matches: List[ProductMatch], 
        processing_errors: List[str],
        total_processing_time: float
    ):
        """Send final completion notification"""
        xml_errors = processing_job.error_message.split("; ") if processing_job.error_message else []
        final_status = "COMPLETED" if not xml_errors else "COMPLETED_WITH_ERRORS"
        final_message = "Processing completed successfully"
        if xml_errors:
            final_message = f"Processing completed with warnings: {xml_errors[0]}"
        
        await ws_manager.send_job_update(
            job_id=str(processing_job.id),
            user_id=str(processing_job.user_id),
            status=final_status,
            progress=100,
            message=final_message,
            data={
                "products_processed": len(product_matches),
                "processing_time_ms": round(total_processing_time, 2),
                "xml_url": processing_job.output_xml_url
            }
        )