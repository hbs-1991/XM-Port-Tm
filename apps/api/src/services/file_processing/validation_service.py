"""
File validation service for handling CSV and XLSX file validation
"""
import csv
import io
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter

import pandas as pd
from fastapi import UploadFile

from src.schemas.processing import (
    FileValidationResult, 
    FileValidationError, 
    ValidationSummary
)
from .constants import (
    MAX_FILE_SIZE, ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES,
    COLUMN_MAPPING, ALTERNATIVE_HEADERS, REQUIRED_COLUMNS, 
    OPTIONAL_COLUMNS, ALL_COLUMNS
)


class FileValidationService:
    """Service for handling file validation"""
    
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
            
            # Map headers using the column mapping
            normalized_headers = set()
            for header in reader.fieldnames:
                header = header.strip() if header else ''
                # First try exact match with main mapping
                if header in COLUMN_MAPPING:
                    normalized_headers.add(COLUMN_MAPPING[header])
                # Then try alternative headers
                elif header.lower() in ALTERNATIVE_HEADERS:
                    normalized_headers.add(ALTERNATIVE_HEADERS[header.lower()])
                else:
                    # Check for partial matches in alternative headers
                    header_lower = header.lower()
                    found = False
                    for alt_header, canonical in ALTERNATIVE_HEADERS.items():
                        if alt_header in header_lower or header_lower in alt_header:
                            normalized_headers.add(canonical)
                            found = True
                            break
                    if not found:
                        # Final fallback - use header as-is but normalized
                        normalized_headers.add(header.lower().replace(' ', '_').strip())
            
            missing_columns = REQUIRED_COLUMNS - normalized_headers
            
            if missing_columns:
                errors.append(FileValidationError(
                    field="headers", 
                    error=f"Missing required column headers: {', '.join(missing_columns)}. Please ensure your CSV has all required columns."
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
            
            # Map headers using the column mapping
            normalized_headers = set()
            for col in df.columns:
                col_str = str(col).strip() if col else ''
                # First try exact match with main mapping
                if col_str in COLUMN_MAPPING:
                    normalized_headers.add(COLUMN_MAPPING[col_str])
                # Then try alternative headers
                elif col_str.lower() in ALTERNATIVE_HEADERS:
                    normalized_headers.add(ALTERNATIVE_HEADERS[col_str.lower()])
                else:
                    # Check for partial matches in alternative headers
                    col_lower = col_str.lower()
                    found = False
                    for alt_header, canonical in ALTERNATIVE_HEADERS.items():
                        if alt_header in col_lower or col_lower in alt_header:
                            normalized_headers.add(canonical)
                            found = True
                            break
                    if not found:
                        # Final fallback - use header as-is but normalized
                        normalized_headers.add(col_str.lower().replace(' ', '_').strip())
            
            missing_columns = REQUIRED_COLUMNS - normalized_headers
            
            if missing_columns:
                errors.append(FileValidationError(
                    field="headers", 
                    error=f"Missing required column headers: {', '.join(missing_columns)}. Please ensure your CSV has all required columns."
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
        
        # Normalize row keys using column mapping
        normalized_row = {}
        for original_key, value in row.items():
            original_key = original_key.strip() if original_key else ''
            # First try exact match from column mapping
            if original_key in COLUMN_MAPPING:
                normalized_key = COLUMN_MAPPING[original_key]
            # Then try alternative headers
            elif original_key.lower() in ALTERNATIVE_HEADERS:
                normalized_key = ALTERNATIVE_HEADERS[original_key.lower()]
            else:
                # Check for partial matches in alternative headers
                key_lower = original_key.lower()
                found = False
                for alt_header, canonical in ALTERNATIVE_HEADERS.items():
                    if alt_header in key_lower or key_lower in alt_header:
                        normalized_key = canonical
                        found = True
                        break
                if not found:
                    # Final fallback - use key as-is but normalized
                    normalized_key = original_key.lower().replace(' ', '_').strip()
            normalized_row[normalized_key] = value
        
        # Check required fields are present and not empty
        for field in REQUIRED_COLUMNS:
            value = normalized_row.get(field)
            if pd.isna(value) or str(value).strip() == '':
                errors.append(FileValidationError(
                    field=f"{field}_row_{row_num}",  # Make field name unique per row
                    error=f"Required field '{field}' is empty in row {row_num}",
                    row=row_num,
                    column=field
                ))
        
        # Validate numeric fields
        if 'quantity' in normalized_row and not pd.isna(normalized_row['quantity']):
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
        
        if 'unit_price' in normalized_row and not pd.isna(normalized_row['unit_price']):
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
        if 'product_name' in normalized_row and not pd.isna(normalized_row['product_name']):
            desc = str(normalized_row['product_name']).strip()
            if len(desc) < 3:
                errors.append(FileValidationError(
                    field='product_name',
                    error="Product name must be at least 3 characters long",
                    row=row_num,
                    column='product_name'
                ))
            elif len(desc) > 500:
                errors.append(FileValidationError(
                    field='product_name',
                    error="Product name must be less than 500 characters",
                    row=row_num,
                    column='product_name'
                ))
        
        if 'unit' in normalized_row and not pd.isna(normalized_row['unit']):
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
        
        if 'origin_country' in normalized_row and not pd.isna(normalized_row['origin_country']):
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
        
        return errors
    
    def _generate_validation_summary(
        self, 
        errors: List[FileValidationError], 
        warnings: List[str], 
        total_rows: int, 
        valid_rows: int
    ) -> ValidationSummary:
        """Generate detailed validation summary"""
        
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
            return {
                'is_safe': True,  # Allow upload if scan fails
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }