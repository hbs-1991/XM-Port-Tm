"""
File processing service for handling CSV and XLSX file uploads
"""
import csv
import io
import json
import logging
import time
from decimal import Decimal
import mimetypes
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import HTTPException, UploadFile, logger
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.user import User
from src.schemas.processing import (
    FileValidationResult, 
    FileValidationError, 
    ProductData,
    ProcessingJobCreate,
    ValidationSummary
)
from src.services.hs_matching_service import hs_matching_service
from src.schemas.hs_matching import HSCodeMatchRequest
from src.services.xml_generation import XMLGenerationService, CountrySchema
from src.models.product_match import ProductMatch

settings = get_settings()

# Import WebSocket manager for progress updates
try:
    from src.api.v1.ws import manager as ws_manager
except ImportError:
    # If WebSocket manager not available, create a dummy one
    class DummyWSManager:
        async def send_job_update(self, *args, **kwargs):
            pass
    ws_manager = DummyWSManager()

# File validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
ALLOWED_EXTENSIONS = {'.csv', '.xlsx'}
ALLOWED_MIME_TYPES = {
    'text/csv', 
    'application/csv',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}
REQUIRED_COLUMNS = {
    'product_description', 
    'quantity', 
    'unit', 
    'value', 
    'origin_country',
    'unit_price'
}


class FileProcessingService:
    """Service for handling file uploads and validation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.s3_client = None
        self.xml_generation_service = XMLGenerationService()
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )

    async def validate_file_upload(self, file: UploadFile) -> FileValidationResult:
        """Validate uploaded file before processing"""
        errors = []
        warnings = []
        
        # Virus scanning (placeholder for security service integration)
        virus_scan_result = await self._scan_file_for_viruses(file)
        if virus_scan_result and not virus_scan_result['is_safe']:
            errors.append(FileValidationError(
                field="security",
                error=f"File failed security scan: {virus_scan_result.get('threat', 'Unknown threat detected')}"
            ))
        
        # Check file size
        if hasattr(file, 'size') and file.size:
            if file.size > MAX_FILE_SIZE:
                errors.append(FileValidationError(
                    field="file_size",
                    error=f"File size ({file.size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)"
                ))
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            errors.append(FileValidationError(
                field="file_extension",
                error=f"File extension '{file_ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            ))
        
        # Check MIME type
        mime_type = mimetypes.guess_type(file.filename)[0]
        if mime_type not in ALLOWED_MIME_TYPES:
            errors.append(FileValidationError(
                field="mime_type",
                error=f"File type '{mime_type}' not allowed. Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
            ))
        
        # If basic validation fails, return early
        if errors:
            return FileValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=errors,
                warnings=warnings
            )
        
        # Read and validate file content
        try:
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            if file_ext == '.csv':
                validation_result = await self._validate_csv_content(content, warnings)
            elif file_ext == '.xlsx':
                validation_result = await self._validate_xlsx_content(content, warnings)
            else:
                errors.append(FileValidationError(
                    field="file_type",
                    error="Unsupported file type"
                ))
                return FileValidationResult(
                    is_valid=False,
                    total_rows=0,
                    valid_rows=0,
                    errors=errors,
                    warnings=warnings
                )
            
            return validation_result
            
        except Exception as e:
            errors.append(FileValidationError(
                field="file_content",
                error=f"Error reading file content: {str(e)}"
            ))
            return FileValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=errors,
                warnings=warnings
            )

    async def _validate_csv_content(self, content: bytes, warnings: List[str]) -> FileValidationResult:
        """Validate CSV file content"""
        errors = []
        text_content = None
        
        # Enhanced encoding detection and handling
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin1', 'iso-8859-1', 'cp1252', 'windows-1252']
        
        for encoding in encodings_to_try:
            try:
                text_content = content.decode(encoding)
                if encoding != 'utf-8':
                    warnings.append(f"File encoding detected as {encoding}. UTF-8 is recommended for better compatibility")
                break
            except UnicodeDecodeError:
                continue
        
        if text_content is None:
            # Try with chardet library if available, otherwise use error handling
            try:
                import chardet
                detected = chardet.detect(content)
                if detected['encoding'] and detected['confidence'] > 0.7:
                    try:
                        text_content = content.decode(detected['encoding'])
                        warnings.append(f"File encoding auto-detected as {detected['encoding']} (confidence: {detected['confidence']:.2f}). UTF-8 is recommended")
                    except (UnicodeDecodeError, LookupError):
                        pass
            except ImportError:
                pass
        
        if text_content is None:
            errors.append(FileValidationError(
                field="encoding",
                error="Unable to decode file. Supported encodings: UTF-8, Latin-1, Windows-1252. Please save your file with UTF-8 encoding"
            ))
            return FileValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=errors,
                warnings=warnings
            )
        
        # Parse CSV
        try:
            csv_file = io.StringIO(text_content)
            reader = csv.DictReader(csv_file)
            
            # Validate headers
            if not reader.fieldnames:
                errors.append(FileValidationError(
                    field="headers",
                    error="No headers found in CSV file"
                ))
                return FileValidationResult(
                    is_valid=False,
                    total_rows=0,
                    valid_rows=0,
                    errors=errors,
                    warnings=warnings
                )
            
            # Normalize header names (lowercase, replace spaces with underscores)
            normalized_headers = {header.lower().replace(' ', '_').strip() for header in reader.fieldnames}
            missing_columns = REQUIRED_COLUMNS - normalized_headers
            
            if missing_columns:
                errors.append(FileValidationError(
                    field="headers",
                    error=f"Missing required columns: {', '.join(missing_columns)}"
                ))
            
            # Validate data rows
            total_rows = 0
            valid_rows = 0
            
            csv_file.seek(0)  # Reset to beginning
            reader = csv.DictReader(csv_file)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                total_rows += 1
                row_errors = self._validate_data_row(row, row_num)
                errors.extend(row_errors)
                
                if not row_errors:
                    valid_rows += 1
                
                # Limit error reporting to prevent overwhelming response
                if len(errors) > 100:
                    warnings.append(f"Validation stopped at row {row_num} due to too many errors")
                    break
            
            validation_result = FileValidationResult(
                is_valid=len(errors) == 0,
                total_rows=total_rows,
                valid_rows=valid_rows,
                errors=errors,
                warnings=warnings
            )
            
            # Generate detailed validation summary
            validation_result.summary = self._generate_validation_summary(errors, warnings, total_rows, valid_rows)
            
            return validation_result
            
        except csv.Error as e:
            errors.append(FileValidationError(
                field="csv_format",
                error=f"CSV parsing error: {str(e)}"
            ))
            return FileValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=errors,
                warnings=warnings
            )

    async def _validate_xlsx_content(self, content: bytes, warnings: List[str]) -> FileValidationResult:
        """Validate XLSX file content"""
        errors = []
        
        try:
            # Read XLSX file
            df = pd.read_excel(io.BytesIO(content))
            
            # Validate headers
            if df.empty:
                errors.append(FileValidationError(
                    field="data",
                    error="Excel file contains no data"
                ))
                return FileValidationResult(
                    is_valid=False,
                    total_rows=0,
                    valid_rows=0,
                    errors=errors,
                    warnings=warnings
                )
            
            # Normalize header names
            normalized_headers = {str(col).lower().replace(' ', '_').strip() for col in df.columns}
            missing_columns = REQUIRED_COLUMNS - normalized_headers
            
            if missing_columns:
                errors.append(FileValidationError(
                    field="headers",
                    error=f"Missing required columns: {', '.join(missing_columns)}"
                ))
            
            # Validate data rows
            total_rows = len(df)
            valid_rows = 0
            
            for row_num, (_, row) in enumerate(df.iterrows(), start=2):  # Start at 2 (header is row 1)
                row_dict = {str(k).lower().replace(' ', '_').strip(): v for k, v in row.to_dict().items()}
                row_errors = self._validate_data_row(row_dict, row_num)
                errors.extend(row_errors)
                
                if not row_errors:
                    valid_rows += 1
                
                # Limit error reporting
                if len(errors) > 100:
                    warnings.append(f"Validation stopped at row {row_num} due to too many errors")
                    break
            
            validation_result = FileValidationResult(
                is_valid=len(errors) == 0,
                total_rows=total_rows,
                valid_rows=valid_rows,
                errors=errors,
                warnings=warnings
            )
            
            # Generate detailed validation summary
            validation_result.summary = self._generate_validation_summary(errors, warnings, total_rows, valid_rows)
            
            return validation_result
            
        except Exception as e:
            errors.append(FileValidationError(
                field="xlsx_format",
                error=f"Excel parsing error: {str(e)}"
            ))
            return FileValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=errors,
                warnings=warnings
            )

    def _validate_data_row(self, row: Dict[str, Any], row_num: int) -> List[FileValidationError]:
        """Validate individual data row"""
        errors = []
        
        # Normalize row keys
        normalized_row = {k.lower().replace(' ', '_').strip(): v for k, v in row.items()}
        
        # Check required fields are present and not empty
        for field in REQUIRED_COLUMNS:
            value = normalized_row.get(field)
            if pd.isna(value) or str(value).strip() == '':
                errors.append(FileValidationError(
                    field=field,
                    error=f"Required field '{field}' is empty",
                    row=row_num,
                    column=field
                ))
        
        # Validate numeric fields
        if 'quantity' in normalized_row:
            try:
                qty = float(str(normalized_row['quantity']).replace(',', ''))
                if qty <= 0:
                    errors.append(FileValidationError(
                        field='quantity',
                        error="Quantity must be greater than 0",
                        row=row_num,
                        column='quantity'
                    ))
            except (ValueError, TypeError):
                errors.append(FileValidationError(
                    field='quantity',
                    error="Quantity must be a valid number",
                    row=row_num,
                    column='quantity'
                ))
        
        if 'value' in normalized_row:
            try:
                val = float(str(normalized_row['value']).replace(',', ''))
                if val <= 0:
                    errors.append(FileValidationError(
                        field='value',
                        error="Value must be greater than 0",
                        row=row_num,
                        column='value'
                    ))
            except (ValueError, TypeError):
                errors.append(FileValidationError(
                    field='value',
                    error="Value must be a valid number",
                    row=row_num,
                    column='value'
                ))
        
        # Validate unit_price field
        if 'unit_price' in normalized_row:
            try:
                unit_price = float(str(normalized_row['unit_price']).replace(',', ''))
                if unit_price <= 0:
                    errors.append(FileValidationError(
                        field='unit_price',
                        error="Unit price must be greater than 0",
                        row=row_num,
                        column='unit_price'
                    ))
            except (ValueError, TypeError):
                errors.append(FileValidationError(
                    field='unit_price',
                    error="Unit price must be a valid number",
                    row=row_num,
                    column='unit_price'
                ))
        
        # Validate text fields length and format
        if 'product_description' in normalized_row:
            desc = str(normalized_row['product_description']).strip()
            if len(desc) < 3:
                errors.append(FileValidationError(
                    field='product_description',
                    error="Product description must be at least 3 characters long",
                    row=row_num,
                    column='product_description'
                ))
            elif len(desc) > 500:
                errors.append(FileValidationError(
                    field='product_description',
                    error="Product description must be less than 500 characters",
                    row=row_num,
                    column='product_description'
                ))
        
        if 'unit' in normalized_row:
            unit = str(normalized_row['unit']).strip()
            if len(unit) < 1:
                errors.append(FileValidationError(
                    field='unit',
                    error="Unit cannot be empty",
                    row=row_num,
                    column='unit'
                ))
            elif len(unit) > 20:
                errors.append(FileValidationError(
                    field='unit',
                    error="Unit must be less than 20 characters",
                    row=row_num,
                    column='unit'
                ))
        
        if 'origin_country' in normalized_row:
            country = str(normalized_row['origin_country']).strip()
            if len(country) < 2:
                errors.append(FileValidationError(
                    field='origin_country',
                    error="Origin country must be at least 2 characters long",
                    row=row_num,
                    column='origin_country'
                ))
            elif len(country) > 100:
                errors.append(FileValidationError(
                    field='origin_country',
                    error="Origin country must be less than 100 characters",
                    row=row_num,
                    column='origin_country'
                ))
        
        # Cross-field validation: check if quantity * unit_price = value (with some tolerance)
        if all(field in normalized_row and not pd.isna(normalized_row[field]) for field in ['quantity', 'unit_price', 'value']):
            try:
                qty = float(str(normalized_row['quantity']).replace(',', ''))
                unit_price = float(str(normalized_row['unit_price']).replace(',', ''))
                value = float(str(normalized_row['value']).replace(',', ''))
                
                expected_value = qty * unit_price
                tolerance = max(0.01, expected_value * 0.001)  # 0.1% tolerance or minimum 0.01
                
                if abs(value - expected_value) > tolerance:
                    errors.append(FileValidationError(
                        field='value_calculation',
                        error=f"Value ({value}) does not match quantity × unit price ({expected_value:.2f})",
                        row=row_num,
                        column='value'
                    ))
            except (ValueError, TypeError):
                # Skip cross-validation if any field is invalid (other validations will catch this)
                pass
        
        return errors
    
    def _generate_validation_summary(
        self, 
        errors: List[FileValidationError], 
        warnings: List[str], 
        total_rows: int, 
        valid_rows: int
    ) -> ValidationSummary:
        """Generate detailed validation summary"""
        from collections import Counter
        
        # Count errors by field and type
        errors_by_field = Counter(error.field for error in errors)
        errors_by_type = Counter(error.error for error in errors)
        
        # Get most common error messages (top 5)
        most_common_errors = [error for error, _ in errors_by_type.most_common(5)]
        
        # Calculate data quality score (0-100)
        if total_rows == 0:
            data_quality_score = 100.0
        else:
            # Base score from valid rows ratio
            valid_ratio = valid_rows / total_rows
            base_score = valid_ratio * 100
            
            # Penalty for warnings (small impact)
            warning_penalty = min(len(warnings) * 2, 10)
            
            # Penalty for error density
            error_density = len(errors) / total_rows if total_rows > 0 else 0
            error_penalty = min(error_density * 50, 30)
            
            data_quality_score = max(0, base_score - warning_penalty - error_penalty)
        
        return ValidationSummary(
            total_errors=len(errors),
            total_warnings=len(warnings),
            errors_by_field=dict(errors_by_field),
            errors_by_type=dict(errors_by_type),
            most_common_errors=most_common_errors,
            data_quality_score=round(data_quality_score, 2)
        )

    async def upload_file_to_s3(self, file: UploadFile, user_id: str) -> str:
        """Upload file to S3 and return the URL"""
        if not self.s3_client:
            raise HTTPException(
                status_code=500, 
                detail="S3 configuration not available"
            )
        
        try:
            # Generate unique file key
            file_ext = Path(file.filename).suffix
            file_key = f"uploads/{user_id}/{file.filename}_{hash(file.filename)}_{file.size}{file_ext}"
            
            # Upload file to S3
            await file.seek(0)  # Reset file pointer
            content = await file.read()
            
            self.s3_client.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=file_key,
                Body=content,
                ContentType=file.content_type,
                ServerSideEncryption='AES256'
            )
            
            # Return S3 URL
            return f"s3://{settings.AWS_S3_BUCKET}/{file_key}"
            
        except NoCredentialsError as e:
            raise HTTPException(
                status_code=500,
                detail=f"AWS credentials not configured: {str(e)}"
            )
        except Exception as e:
            # Catch any other AWS/boto3 related errors
            if 'botocore' in str(type(e)).lower() or 'aws' in str(e).lower():
                raise HTTPException(
                    status_code=500,
                    detail=f"S3 upload failed: {str(e)}"
                )
            else:
                # Re-raise non-AWS errors
                raise
        except ClientError as e:
            # Extract the error code from boto3 ClientError
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Create a detailed error message that includes the error code
            detailed_error = f"S3 upload failed: {error_code} - {error_message}"
            
            raise HTTPException(
                status_code=500,
                detail=detailed_error
            )

    def check_user_credits(self, user: User, estimated_credits: int = 1) -> Dict[str, Any]:
        """
        Check if user has sufficient credits for processing
        
        Returns:
            Dict containing:
            - has_sufficient_credits: bool
            - credits_remaining: int
            - credits_required: int
            - message: str
        """
        has_sufficient = user.credits_remaining >= estimated_credits
        
        return {
            'has_sufficient_credits': has_sufficient,
            'credits_remaining': user.credits_remaining,
            'credits_required': estimated_credits,
            'message': self._generate_credit_message(user, estimated_credits, has_sufficient)
        }
    
    def _generate_credit_message(self, user: User, required_credits: int, has_sufficient: bool) -> str:
        """Generate appropriate credit-related message for user"""
        if has_sufficient:
            return f"Processing will use {required_credits} credit(s). You have {user.credits_remaining} remaining."
        
        shortage = required_credits - user.credits_remaining
        base_message = f"Insufficient credits: You need {required_credits} credit(s) but only have {user.credits_remaining} remaining."
        
        if user.subscription_tier.value == 'FREE':
            return f"{base_message} Upgrade to a paid plan or purchase additional credits to continue processing."
        else:
            return f"{base_message} Please purchase {shortage} more credit(s) to process this file."
    
    def calculate_processing_credits(self, total_rows: int) -> int:
        """
        Calculate credits required based on file size and complexity
        
        Pricing model:
        - Base cost: 1 credit for files up to 100 rows
        - Additional: 1 credit per 100 rows or part thereof
        """
        if total_rows <= 0:
            return 1  # Minimum cost for validation
        
        # Base credit + additional credits for larger files
        base_credits = 1
        additional_credits = (total_rows - 1) // 100  # Integer division
        
        return base_credits + additional_credits
    
    def reserve_user_credits(self, user: User, credits_to_reserve: int) -> bool:
        """
        Reserve credits for processing (atomic operation with proper concurrency handling)
        
        Args:
            user: User object
            credits_to_reserve: Number of credits to reserve
            
        Returns:
            bool: True if credits were successfully reserved
        """
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy import text
        
        try:
            # Use database-level atomic update to prevent race conditions
            # This updates only if credits are sufficient and returns affected rows
            result = self.db.execute(
                text("""
                    UPDATE users 
                    SET 
                        credits_remaining = credits_remaining - :credits_to_reserve,
                        credits_used_this_month = credits_used_this_month + :credits_to_reserve,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE 
                        id = :user_id 
                        AND credits_remaining >= :credits_to_reserve
                        AND is_active = true
                """),
                {
                    "user_id": user.id,
                    "credits_to_reserve": credits_to_reserve
                }
            )
            
            # Check if any rows were affected (credit reservation successful)
            rows_affected = result.rowcount
            
            if rows_affected == 0:
                # Either insufficient credits or user not found/inactive
                self.db.rollback()
                return False
            
            # Commit the transaction
            self.db.commit()
            
            # Refresh user object to reflect the changes
            self.db.refresh(user)
            
            return True
            
        except (IntegrityError, Exception) as e:
            # Handle database constraints or other errors
            self.db.rollback()
            import logging
            logging.error(f"Credit reservation failed for user {user.id}: {str(e)}")
            return False
    
    def refund_user_credits(self, user: User, credits_to_refund: int) -> bool:
        """
        Refund credits if processing fails
        
        Args:
            user: User object  
            credits_to_refund: Number of credits to refund
            
        Returns:
            bool: True if credits were successfully refunded
        """
        try:
            # Refresh user data
            self.db.refresh(user)
            
            # Refund credits
            user.credits_remaining += credits_to_refund
            user.credits_used_this_month = max(0, user.credits_used_this_month - credits_to_refund)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            return False

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

    async def _scan_file_for_viruses(self, file: UploadFile) -> Optional[Dict[str, Any]]:
        """
        Scan uploaded file for viruses and malware.
        
        This is a placeholder implementation. In production, integrate with:
        - AWS GuardDuty Malware Protection
        - ClamAV antivirus
        - VirusTotal API
        - Third-party security scanning service
        """
        try:
            # Read file content for scanning
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Placeholder virus scan logic
            # In production, this would call external security service
            
            # Simple heuristic checks for demonstration
            file_ext = Path(file.filename).suffix.lower()
            suspicious_extensions = {'.exe', '.bat', '.cmd', '.scr', '.pif', '.com'}
            
            if file_ext in suspicious_extensions:
                return {
                    'is_safe': False,
                    'threat': f'Potentially dangerous file extension: {file_ext}'
                }
            
            # Check for suspicious content patterns (basic example)
            try:
                # Only check text-based files for suspicious patterns
                if file_ext in {'.csv', '.txt'}:
                    text_content = content.decode('utf-8', errors='ignore')
                    suspicious_patterns = [
                        '<script', 'javascript:', 'vbscript:', 'data:text/html'
                    ]
                    
                    for pattern in suspicious_patterns:
                        if pattern.lower() in text_content.lower():
                            return {
                                'is_safe': False,
                                'threat': f'Suspicious content pattern detected: {pattern}'
                            }
            except Exception:
                # If we can't decode, assume it's binary and skip pattern matching
                pass
            
            # File passed basic security checks
            return {
                'is_safe': True,
                'scan_method': 'basic_heuristics',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            # Log error but don't fail the upload
            warnings = getattr(self, '_current_warnings', [])
            warnings.append(f"Virus scan failed: {str(e)}")
            return {
                'is_safe': True,  # Allow upload if scan fails
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
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
                processing_job.status = ProcessingStatus.FAILED
                processing_job.error_message = f"HS code matching failed: {str(e)}"
                self.db.commit()
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
            
            # Commit all ProductMatch records
            try:
                self.db.commit()
                
                # Update job status to completed if no errors
                if not error_messages:
                    processing_job.status = ProcessingStatus.COMPLETED
                    processing_job.total_products = len(created_matches)
                else:
                    processing_job.status = ProcessingStatus.COMPLETED_WITH_ERRORS
                    processing_job.error_message = "; ".join(error_messages[:5])  # Limit error details
                
                self.db.commit()
                
                logger.info(f"Created {len(created_matches)} ProductMatch records with {len(error_messages)} errors")
                
            except Exception as e:
                self.db.rollback()
                error_msg = f"Failed to save ProductMatch records: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
                
                # Update job status to failed
                processing_job.status = ProcessingStatus.FAILED
                processing_job.error_message = error_msg
                self.db.commit()
            
            return created_matches, error_messages
            
        except Exception as e:
            logger.error(f"Product processing failed: {str(e)}")
            error_messages.append(f"Product processing failed: {str(e)}")
            
            # Update job status to failed
            processing_job.status = ProcessingStatus.FAILED
            processing_job.error_message = str(e)
            self.db.commit()
            
            return created_matches, error_messages

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
            await ws_manager.send_job_update(
                job_id="pending",
                user_id=str(user.id),
                status="VALIDATING",
                progress=10,
                message="Validating file format and content..."
            )
            
            validation_result = await self.validate_file_upload(file)
            if not validation_result.is_valid:
                await ws_manager.send_job_update(
                    job_id="pending",
                    user_id=str(user.id),
                    status="FAILED",
                    progress=100,
                    message="File validation failed"
                )
                return {
                    "success": False,
                    "error": "File validation failed",
                    "validation_result": validation_result
                }
            
            # Step 2: Check user credits
            await ws_manager.send_job_update(
                job_id="pending",
                user_id=str(user.id),
                status="CHECKING_CREDITS",
                progress=15,
                message="Checking user credits..."
            )
            
            estimated_credits = self.calculate_processing_credits(validation_result.total_rows)
            credit_check = self.check_user_credits(user, estimated_credits)
            
            if not credit_check['has_sufficient_credits']:
                await ws_manager.send_job_update(
                    job_id="pending",
                    user_id=str(user.id),
                    status="FAILED",
                    progress=100,
                    message="Insufficient credits for processing"
                )
                return {
                    "success": False,
                    "error": "Insufficient credits",
                    "credit_check": credit_check
                }
            
            # Step 3: Reserve credits
            credits_reserved = self.reserve_user_credits(user, estimated_credits)
            if not credits_reserved:
                return {
                    "success": False,
                    "error": "Failed to reserve credits - insufficient balance"
                }
            
            # Step 4: Upload file to S3
            await ws_manager.send_job_update(
                job_id="pending",
                user_id=str(user.id),
                status="UPLOADING",
                progress=25,
                message="Uploading file to secure storage..."
            )
            
            try:
                file_url = await self.upload_file_to_s3(file, str(user.id))
            except HTTPException as e:
                # Check if this is an S3-related error and fallback is allowed
                from src.core.config import get_settings
                settings = get_settings()
                
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
                
                if (is_s3_error and 
                    settings.ALLOW_S3_FALLBACK and 
                    not settings.is_production):
                    # Development fallback to local storage - NOT production ready
                    file_url = f"local://uploads/{user.id}/{file.filename}"
                    import logging
                    logging.warning(
                        f"Using local storage fallback for file upload in process_file_with_hs_matching. "
                        f"S3 Error: {error_detail_str}. File: {file.filename}, User: {user.id}. "
                        f"This is not suitable for production use."
                    )
                else:
                    # Refund credits if S3 upload fails and no fallback
                    self.refund_user_credits(user, estimated_credits)
                    await ws_manager.send_job_update(
                        job_id="pending",
                        user_id=str(user.id),
                        status="FAILED",
                        progress=100,
                        message=f"File upload failed: {str(e)}"
                    )
                    return {
                        "success": False,
                        "error": f"File upload failed: {str(e)}"
                    }
            except Exception as e:
                # Refund credits if S3 upload fails with other errors
                self.refund_user_credits(user, estimated_credits)
                await ws_manager.send_job_update(
                    job_id="pending",
                    user_id=str(user.id),
                    status="FAILED",
                    progress=100,
                    message=f"File upload failed: {str(e)}"
                )
                return {
                    "success": False,
                    "error": f"File upload failed: {str(e)}"
                }
            
            # Step 5: Create processing job
            await ws_manager.send_job_update(
                job_id="pending",
                user_id=str(user.id),
                status="CREATING_JOB",
                progress=30,
                message="Creating processing job..."
            )
            
            processing_job = self.create_processing_job(
                user=user,
                file_name=file.filename,
                file_url=file_url,
                file_size=file.size,
                country_schema=country_schema,
                credits_used=estimated_credits,
                total_products=validation_result.total_rows
            )
            
            # Update WebSocket with actual job ID
            await ws_manager.send_job_update(
                job_id=str(processing_job.id),
                user_id=str(user.id),
                status="PARSING",
                progress=35,
                message="Parsing file data..."
            )
            
            # Step 6: Extract product data from file
            try:
                await file.seek(0)  # Reset file pointer
                content = await file.read()
                
                # Parse products based on file type
                file_ext = Path(file.filename).suffix.lower()
                if file_ext == '.csv':
                    products_data = await self._extract_csv_products(content)
                elif file_ext == '.xlsx':
                    products_data = await self._extract_xlsx_products(content)
                else:
                    raise ValueError(f"Unsupported file type: {file_ext}")
                    
            except Exception as e:
                # Refund credits if parsing fails
                self.refund_user_credits(user, estimated_credits)
                processing_job.status = ProcessingStatus.FAILED
                processing_job.error_message = f"File parsing failed: {str(e)}"
                self.db.commit()
                
                return {
                    "success": False,
                    "error": f"File parsing failed: {str(e)}",
                    "job_id": str(processing_job.id)
                }
            
            # Step 7: Process products with HS code matching
            await ws_manager.send_job_update(
                job_id=str(processing_job.id),
                user_id=str(user.id),
                status="HS_MATCHING",
                progress=50,
                message=f"Matching HS codes for {len(products_data)} products..."
            )
            
            try:
                product_matches, processing_errors = await self.process_products_with_hs_matching(
                    processing_job=processing_job,
                    products_data=products_data,
                    country_schema=country_schema
                )
                
                # Step 8: Generate XML file after successful HS matching
                await ws_manager.send_job_update(
                    job_id=str(processing_job.id),
                    user_id=str(user.id),
                    status="GENERATING_XML",
                    progress=75,
                    message="Generating ASYCUDA-compliant XML file..."
                )
                
                xml_generation_result = None
                xml_errors = []
                
                if product_matches:  # Only generate XML if we have product matches
                    try:
                        # Update XML generation status to GENERATING
                        processing_job.xml_generation_status = "GENERATING"
                        self.db.commit()
                        
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
                            # Update processing job with XML details (file is already stored by XML service)
                            processing_job.output_xml_url = xml_generation_result.s3_url or xml_generation_result.download_url
                            processing_job.xml_generation_status = "COMPLETED"
                            processing_job.xml_generated_at = datetime.now(timezone.utc)
                            processing_job.xml_file_size = xml_generation_result.file_size
                            processing_job.status = ProcessingStatus.COMPLETED
                            
                            logger.info(
                                f"XML generated and stored successfully for job {processing_job.id}, "
                                f"storage type: {xml_generation_result.storage_type}, "
                                f"size: {xml_generation_result.file_size} bytes"
                            )
                            
                        else:
                            # XML generation failed
                            xml_errors = xml_generation_result.validation_errors or [xml_generation_result.error_message or "Unknown XML generation error"]
                            processing_job.xml_generation_status = "FAILED"
                            processing_job.status = ProcessingStatus.COMPLETED_WITH_ERRORS
                            processing_job.error_message = f"XML generation failed: {'; '.join(xml_errors[:3])}"
                            
                            logger.warning(f"XML generation failed for job {processing_job.id}: {xml_errors}")
                            
                    except Exception as e:
                        xml_error_msg = f"XML generation failed: {str(e)}"
                        xml_errors.append(xml_error_msg)
                        processing_job.xml_generation_status = "FAILED"
                        processing_job.status = ProcessingStatus.COMPLETED_WITH_ERRORS
                        processing_job.error_message = xml_error_msg
                        
                        logger.error(f"XML generation error for job {processing_job.id}: {str(e)}", exc_info=True)
                else:
                    # No product matches - mark as completed but without XML
                    processing_job.xml_generation_status = "FAILED"
                    processing_job.status = ProcessingStatus.COMPLETED
                    xml_errors.append("No product matches available for XML generation")
                
                # Commit all updates to the processing job
                self.db.commit()
                
                # Calculate final processing time
                total_processing_time = (time.time() - start_time) * 1000
                processing_job.processing_time_ms = int(total_processing_time)
                self.db.commit()
                
                # Send completion notification
                final_status = "COMPLETED" if not xml_errors else "COMPLETED_WITH_ERRORS"
                final_message = "Processing completed successfully"
                if xml_errors:
                    final_message = f"Processing completed with warnings: {xml_errors[0]}"
                
                await ws_manager.send_job_update(
                    job_id=str(processing_job.id),
                    user_id=str(user.id),
                    status=final_status,
                    progress=100,
                    message=final_message,
                    data={
                        "products_processed": len(product_matches),
                        "processing_time_ms": round(total_processing_time, 2),
                        "xml_url": processing_job.output_xml_url
                    }
                )
                
                # Prepare success response
                result = {
                    "success": True,
                    "job_id": str(processing_job.id),
                    "products_processed": len(product_matches),
                    "processing_errors": processing_errors,
                    "xml_errors": xml_errors,
                    "credits_used": estimated_credits,
                    "processing_time_ms": round(total_processing_time, 2),
                    "validation_result": validation_result,
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
                
                return result
                
            except Exception as e:
                # If HS matching fails, refund credits and update job
                self.refund_user_credits(user, estimated_credits)
                processing_job.status = ProcessingStatus.FAILED
                processing_job.error_message = f"HS code matching failed: {str(e)}"
                self.db.commit()
                
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

    async def _extract_csv_products(self, content: bytes) -> List[Dict[str, Any]]:
        """Extract product data from CSV content"""
        products = []
        
        # Decode content with encoding detection
        text_content = None
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin1', 'iso-8859-1', 'cp1252', 'windows-1252']
        
        for encoding in encodings_to_try:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if text_content is None:
            raise ValueError("Unable to decode CSV file")
        
        # Parse CSV
        csv_file = io.StringIO(text_content)
        reader = csv.DictReader(csv_file)
        
        for row in reader:
            # Normalize keys
            normalized_row = {k.lower().replace(' ', '_').strip(): v for k, v in row.items()}
            
            # Convert to standard format
            product = {
                'product_description': normalized_row.get('product_description', '').strip(),
                'quantity': float(str(normalized_row.get('quantity', 0)).replace(',', '')),
                'unit': normalized_row.get('unit', '').strip(),
                'value': float(str(normalized_row.get('value', 0)).replace(',', '')),
                'origin_country': normalized_row.get('origin_country', '').strip(),
                'unit_price': float(str(normalized_row.get('unit_price', 0)).replace(',', ''))
            }
            
            # Only add valid products (with description)
            if product['product_description']:
                products.append(product)
        
        return products

    async def _extract_xlsx_products(self, content: bytes) -> List[Dict[str, Any]]:
        """Extract product data from XLSX content"""
        products = []
        
        # Read XLSX file
        df = pd.read_excel(io.BytesIO(content))
        
        for _, row in df.iterrows():
            # Normalize keys
            normalized_row = {str(k).lower().replace(' ', '_').strip(): v for k, v in row.to_dict().items()}
            
            # Convert to standard format
            product = {
                'product_description': str(normalized_row.get('product_description', '')).strip(),
                'quantity': float(str(normalized_row.get('quantity', 0)).replace(',', '')),
                'unit': str(normalized_row.get('unit', '')).strip(),
                'value': float(str(normalized_row.get('value', 0)).replace(',', '')),
                'origin_country': str(normalized_row.get('origin_country', '')).strip(),
                'unit_price': float(str(normalized_row.get('unit_price', 0)).replace(',', ''))
            }
            
            # Only add valid products (with description)
            if product['product_description'] and product['product_description'] != 'nan':
                products.append(product)
        
        return products