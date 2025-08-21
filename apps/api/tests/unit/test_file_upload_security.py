"""
Security-focused unit tests for file upload functionality
"""
import io
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile

from src.services.file_processing import FileProcessingService
from src.schemas.processing import FileValidationResult, FileValidationError
from src.models.user import User


class TestFileUploadSecurity:
    """Security tests for file upload functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def file_service(self, mock_db):
        """File processing service instance"""
        return FileProcessingService(mock_db)
    
    @pytest.fixture
    def create_upload_file(self):
        """Helper function to create UploadFile instances"""
        def _create_file(content: bytes, filename: str, content_type: str = "text/csv"):
            file_obj = io.BytesIO(content)
            upload_file = UploadFile(
                filename=filename,
                file=file_obj,
                size=len(content),
                headers={"content-type": content_type}
            )
            upload_file.content_type = content_type
            return upload_file
        return _create_file
    
    # Malicious File Extension Tests
    
    async def test_reject_executable_extensions(self, file_service, create_upload_file):
        """Test rejection of potentially malicious executable file extensions"""
        malicious_extensions = [
            "malware.exe", "virus.bat", "script.ps1", "payload.scr", 
            "trojan.com", "backdoor.pif", "ransomware.cmd"
        ]
        
        for filename in malicious_extensions:
            file = create_upload_file(b"malicious content", filename, "application/octet-stream")
            
            with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
                mock_scan.return_value = {'is_safe': True}
                
                result = await file_service.validate_file_upload(file)
                
                assert not result.is_valid, f"Should reject file with extension: {filename}"
                extension_errors = [e for e in result.errors if e.field == "file_extension"]
                assert len(extension_errors) > 0
    
    async def test_reject_script_extensions(self, file_service, create_upload_file):
        """Test rejection of script file extensions"""
        script_extensions = [
            "script.js", "payload.php", "backdoor.py", "malware.pl", 
            "virus.sh", "trojan.vbs", "exploit.jar"
        ]
        
        for filename in script_extensions:
            file = create_upload_file(b"script content", filename)
            
            with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
                mock_scan.return_value = {'is_safe': True}
                
                result = await file_service.validate_file_upload(file)
                
                assert not result.is_valid, f"Should reject script file: {filename}"
    
    async def test_reject_double_extensions(self, file_service, create_upload_file):
        """Test rejection of files with double extensions (common attack vector)"""
        double_extension_files = [
            "document.pdf.exe", "data.csv.bat", "report.xlsx.scr", "file.txt.com"
        ]
        
        for filename in double_extension_files:
            file = create_upload_file(b"content", filename)
            
            with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
                mock_scan.return_value = {'is_safe': True}
                
                result = await file_service.validate_file_upload(file)
                
                assert not result.is_valid, f"Should reject double extension file: {filename}"
    
    # Content-Based Security Tests
    
    async def test_detect_script_injection_in_csv(self, file_service, create_upload_file):
        """Test detection of script injection attempts in CSV content"""
        malicious_csv_content = '''Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"<script>alert('XSS')</script>",100,pieces,500.00,USA,5.00
"=cmd|'/c calc'!A0",50,kg,250.50,Canada,5.01
"@SUM(1+1)*cmd|'/c calc'!A0",25,units,100.00,Mexico,4.00
'''
        file = create_upload_file(malicious_csv_content.encode(), "malicious.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should detect suspicious content patterns
            security_warnings = [e for e in result.errors + result.warnings if "suspicious" in e.lower()]
            assert len(security_warnings) > 0, "Should detect suspicious script patterns"
    
    async def test_detect_sql_injection_attempts(self, file_service, create_upload_file):
        """Test detection of SQL injection patterns in CSV content"""
        malicious_csv_content = '''Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"'; DROP TABLE users; --",100,pieces,500.00,USA,5.00
"1' OR '1'='1",50,kg,250.50,Canada,5.01
"UNION SELECT password FROM users",25,units,100.00,Mexico,4.00
'''
        file = create_upload_file(malicious_csv_content.encode(), "malicious.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should detect SQL injection patterns
            security_warnings = [e for e in result.errors + result.warnings if "suspicious" in e.lower()]
            assert len(security_warnings) > 0, "Should detect SQL injection patterns"
    
    async def test_detect_path_traversal_attempts(self, file_service, create_upload_file):
        """Test detection of path traversal attempts in filenames"""
        malicious_filenames = [
            "../../../etc/passwd.csv",
            "..\\..\\windows\\system32\\config\\sam.csv",
            "....//....//....//etc//passwd.csv",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd.csv"
        ]
        
        for filename in malicious_filenames:
            file = create_upload_file(b"content", filename)
            
            with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
                mock_scan.return_value = {'is_safe': True}
                
                result = await file_service.validate_file_upload(file)
                
                # Should detect path traversal attempts
                assert not result.is_valid, f"Should reject path traversal filename: {filename}"
                security_errors = [e for e in result.errors if e.field in ["filename", "security"]]
                assert len(security_errors) > 0
    
    # MIME Type Security Tests
    
    async def test_mime_type_mismatch_detection(self, file_service, create_upload_file):
        """Test detection of MIME type mismatches"""
        # CSV content with wrong MIME type
        csv_content = b"Product,Quantity\nTest,100"
        file = create_upload_file(csv_content, "test.csv", "application/x-msdownload")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should detect suspicious MIME type
            mime_errors = [e for e in result.errors if e.field == "mime_type"]
            assert len(mime_errors) > 0, "Should detect MIME type mismatch"
    
    async def test_dangerous_mime_types_rejection(self, file_service, create_upload_file):
        """Test rejection of dangerous MIME types"""
        dangerous_mime_types = [
            "application/x-msdownload",
            "application/x-executable", 
            "application/x-dosexec",
            "application/java-archive",
            "text/javascript",
            "application/javascript"
        ]
        
        for mime_type in dangerous_mime_types:
            file = create_upload_file(b"content", "test.csv", mime_type)
            
            with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
                mock_scan.return_value = {'is_safe': True}
                
                result = await file_service.validate_file_upload(file)
                
                assert not result.is_valid, f"Should reject dangerous MIME type: {mime_type}"
    
    # Virus Scanning Tests
    
    async def test_virus_scan_integration(self, file_service, create_upload_file):
        """Test virus scanning integration with different scan results"""
        file = create_upload_file(b"test content", "test.csv")
        
        scan_results = [
            {'is_safe': True},
            {'is_safe': False, 'threat': 'Trojan.Win32.Test'},
            {'is_safe': False, 'threat': 'Eicar-Test-Signature'},
            {'is_safe': False, 'threat': 'Malware.Generic.Suspicious'}
        ]
        
        for scan_result in scan_results:
            with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
                mock_scan.return_value = scan_result
                
                result = await file_service.validate_file_upload(file)
                
                if scan_result['is_safe']:
                    security_errors = [e for e in result.errors if e.field == "security"]
                    assert len(security_errors) == 0, "Safe file should not have security errors"
                else:
                    assert not result.is_valid, f"Should reject unsafe file with threat: {scan_result.get('threat')}"
                    security_errors = [e for e in result.errors if e.field == "security"]
                    assert len(security_errors) > 0
                    assert scan_result['threat'] in security_errors[0].error
    
    # File Size Bomb Tests
    
    async def test_detect_zip_bombs(self, file_service, create_upload_file):
        """Test detection of potential zip/compression bombs"""
        # Simulate a file that claims to be small but could expand significantly
        # This is a simplified test - real implementation would check compression ratios
        suspicious_file = create_upload_file(b"A" * 1000, "suspicious.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            with patch.object(file_service, '_check_compression_ratio') as mock_ratio:
                mock_ratio.return_value = {'suspicious': True, 'ratio': 10000}  # Extremely high ratio
                
                result = await file_service.validate_file_upload(suspicious_file)
                
                # Should warn about suspicious compression
                compression_warnings = [w for w in result.warnings if "compression" in w.lower()]
                assert len(compression_warnings) > 0, "Should warn about suspicious compression"
    
    # Rate Limiting Security Tests
    
    def test_user_permission_validation(self, file_service):
        """Test user permission validation for file uploads"""
        # Test with different user scenarios
        blocked_user = Mock(spec=User)
        blocked_user.id = "blocked-user"
        blocked_user.is_active = False
        blocked_user.credits_remaining = 10
        
        result = file_service.check_user_permissions(blocked_user)
        assert result['allowed'] is False
        assert "inactive" in result['reason'].lower()
        
        # Test with active user
        active_user = Mock(spec=User)
        active_user.id = "active-user"
        active_user.is_active = True
        active_user.credits_remaining = 10
        
        result = file_service.check_user_permissions(active_user)
        assert result['allowed'] is True
    
    # Content Validation Security
    
    async def test_csv_formula_injection_detection(self, file_service, create_upload_file):
        """Test detection of CSV formula injection (DDE attacks)"""
        malicious_csv_content = '''Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"=1+1+cmd|'/c calc'!A0",100,pieces,500.00,USA,5.00
"=2+3+cmd|'/c notepad'!A0",50,kg,250.50,Canada,5.01
"+cmd|'/c powershell -Command Get-Process'!A0",25,units,100.00,Mexico,4.00
"-2+3+cmd|'/c whoami'!A0",75,pieces,300.00,Brazil,4.00
"@SUM(1+1)*cmd|'/c dir'!A0",30,kg,150.00,Germany,5.00
'''
        file = create_upload_file(malicious_csv_content.encode(), "malicious.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should detect DDE/formula injection
            formula_errors = [e for e in result.errors if "formula" in e.error.lower() or "suspicious" in e.error.lower()]
            assert len(formula_errors) > 0, "Should detect CSV formula injection attempts"
    
    async def test_unicode_normalization_attacks(self, file_service, create_upload_file):
        """Test handling of Unicode normalization attacks"""
        # Using Unicode characters that could normalize to dangerous patterns
        unicode_attack_csv = '''Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"Tes\u0074 Pr\u006fduct",100,pieces,500.00,USA,5.00
"N\u006frmal Product",50,kg,250.50,Canada,5.01
'''
        file = create_upload_file(unicode_attack_csv.encode('utf-8'), "unicode.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should handle Unicode normalization safely
            assert isinstance(result, FileValidationResult)
            # Content should be normalized or flagged appropriately
    
    # Memory Exhaustion Tests
    
    async def test_large_cell_content_handling(self, file_service, create_upload_file):
        """Test handling of extremely large cell content"""
        # Create CSV with extremely large cell content
        large_content = "A" * 100000  # 100KB in a single cell
        csv_content = f'''Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"{large_content}",100,pieces,500.00,USA,5.00
"Normal Product",50,kg,250.50,Canada,5.01
'''
        file = create_upload_file(csv_content.encode(), "large_cell.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should handle large cells gracefully without memory exhaustion
            cell_size_warnings = [w for w in result.warnings if "large" in w.lower() or "size" in w.lower()]
            # Implementation might warn or truncate, both are acceptable
    
    async def test_many_columns_handling(self, file_service, create_upload_file):
        """Test handling of files with excessive number of columns"""
        # Create CSV with many columns (potential memory exhaustion)
        columns = ["Col" + str(i) for i in range(1000)]  # 1000 columns
        header = ",".join(columns)
        row = ",".join(["data" + str(i) for i in range(1000)])
        csv_content = f"{header}\n{row}\n"
        
        file = create_upload_file(csv_content.encode(), "many_columns.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should handle excessive columns gracefully
            column_warnings = [w for w in result.warnings if "column" in w.lower()]
            # Should not crash or consume excessive memory