"""
Unit tests for file upload functionality
"""
import io
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.services.file_processing import FileProcessingService, MAX_FILE_SIZE
from src.schemas.processing import FileValidationResult, FileValidationError
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus


class TestFileProcessingService:
    """Test cases for FileProcessingService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_user(self):
        """Mock user with sufficient credits"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.credits_remaining = 10
        return user
    
    @pytest.fixture
    def file_service(self, mock_db):
        """File processing service instance"""
        return FileProcessingService(mock_db)
    
    @pytest.fixture
    def valid_csv_content(self):
        """Valid CSV content for testing"""
        return """№,Наименование товара,Страна происхождения,Количество мест,Часть мест,Вид упаковки,Количество,Единица измерение,Цена,Брутто кг,Нетто кг,Процедура,Преференция,BKU,Количество в допольнительной ед. изм.,Допольнительная ед. изм.
1,"Test Product 1","Россия",1,1,"Коробки",100,"шт",500.00,10.5,9.8,"40","ОР","123456",50,"кг"
2,"Test Product 2","Китай",2,1,"Мешки",50,"кг",250.50,25.0,22.5,"40","","654321",200,"кг"
"""
    
    @pytest.fixture
    def invalid_csv_content(self):
        """Invalid CSV content missing required columns"""
        return """Product,Qty,Price
"Test Product 1",100,500.00
"Test Product 2",50,250.50
"""
    
    @pytest.fixture
    def create_upload_file(self):
        """Helper function to create UploadFile instances"""
        def _create_file(content: str, filename: str, content_type: str = "text/csv"):
            file_bytes = content.encode('utf-8')
            file_obj = io.BytesIO(file_bytes)
            upload_file = UploadFile(
                filename=filename,
                file=file_obj,
                size=len(file_bytes),
                headers={"content-type": content_type}
            )
            upload_file.content_type = content_type
            return upload_file
        return _create_file

    # File Size Validation Tests
    
    async def test_validate_file_size_within_limit(self, file_service, create_upload_file, valid_csv_content):
        """Test file size validation for valid file"""
        file = create_upload_file(valid_csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert isinstance(result, FileValidationResult)
            # Should pass size validation since test content is small
    
    async def test_validate_file_size_exceeds_limit(self, file_service, create_upload_file):
        """Test file size validation for oversized file"""
        # Create a file larger than MAX_FILE_SIZE
        large_content = "x" * (MAX_FILE_SIZE + 1)
        file = create_upload_file(large_content, "large.csv")
        file.size = len(large_content)
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            assert any("exceeds maximum allowed size" in error.error for error in result.errors)

    # File Extension Validation Tests
    
    async def test_validate_csv_file_extension(self, file_service, create_upload_file, valid_csv_content):
        """Test CSV file extension validation"""
        file = create_upload_file(valid_csv_content, "test.csv", "text/csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should not have file extension errors
            extension_errors = [e for e in result.errors if e.field == "file_extension"]
            assert len(extension_errors) == 0
    
    async def test_validate_xlsx_file_extension(self, file_service, create_upload_file):
        """Test XLSX file extension validation"""
        file = create_upload_file("", "test.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should not have file extension errors for XLSX
            extension_errors = [e for e in result.errors if e.field == "file_extension"]
            assert len(extension_errors) == 0
    
    async def test_validate_invalid_file_extension(self, file_service, create_upload_file, valid_csv_content):
        """Test invalid file extension rejection"""
        file = create_upload_file(valid_csv_content, "test.txt", "text/plain")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            extension_errors = [e for e in result.errors if e.field == "file_extension"]
            assert len(extension_errors) > 0
            assert ".txt" in extension_errors[0].error

    # CSV Content Validation Tests
    
    async def test_validate_csv_with_valid_headers(self, file_service, create_upload_file, valid_csv_content):
        """Test CSV validation with all required headers"""
        file = create_upload_file(valid_csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert result.is_valid
            assert result.total_rows == 2
            assert result.valid_rows == 2
    
    async def test_validate_csv_with_missing_headers(self, file_service, create_upload_file, invalid_csv_content):
        """Test CSV validation with missing required headers"""
        file = create_upload_file(invalid_csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            header_errors = [e for e in result.errors if e.field == "headers"]
            assert len(header_errors) > 0
            assert "Missing required columns" in header_errors[0].error
    
    async def test_validate_csv_with_empty_required_fields(self, file_service, create_upload_file):
        """Test CSV validation with empty required fields"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country
"Test Product 1",,pieces,500.00,USA
"",50,kg,250.50,Canada
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            assert result.total_rows == 2
            assert result.valid_rows == 0  # Both rows have validation errors
    
    async def test_validate_csv_with_invalid_numeric_values(self, file_service, create_upload_file):
        """Test CSV validation with invalid numeric values"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country
"Test Product 1",not_a_number,pieces,500.00,USA
"Test Product 2",50,kg,not_a_number,Canada
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            assert result.total_rows == 2
            assert result.valid_rows == 0
    
    async def test_validate_csv_with_negative_values(self, file_service, create_upload_file):
        """Test CSV validation with negative quantity/value"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country
"Test Product 1",-10,pieces,500.00,USA
"Test Product 2",50,kg,-100,Canada
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            quantity_errors = [e for e in result.errors if e.field == "quantity" and "greater than 0" in e.error]
            value_errors = [e for e in result.errors if e.field == "value" and "greater than 0" in e.error]
            assert len(quantity_errors) > 0
            assert len(value_errors) > 0

    # Security Validation Tests
    
    async def test_virus_scan_safe_file(self, file_service, create_upload_file, valid_csv_content):
        """Test virus scanning with safe file"""
        file = create_upload_file(valid_csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            mock_scan.assert_called_once_with(file)
            # Should not have security errors if virus scan passes
            security_errors = [e for e in result.errors if e.field == "security"]
            assert len(security_errors) == 0
    
    async def test_virus_scan_unsafe_file(self, file_service, create_upload_file, valid_csv_content):
        """Test virus scanning with unsafe file"""
        file = create_upload_file(valid_csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': False, 'threat': 'Test virus detected'}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            security_errors = [e for e in result.errors if e.field == "security"]
            assert len(security_errors) > 0
            assert "Test virus detected" in security_errors[0].error

    # Credit Validation Tests
    
    def test_check_user_credits_sufficient(self, file_service, mock_user):
        """Test credit check with sufficient credits"""
        mock_user.credits_remaining = 10
        
        result = file_service.check_user_credits(mock_user, estimated_credits=5)
        
        assert result is True
    
    def test_check_user_credits_insufficient(self, file_service, mock_user):
        """Test credit check with insufficient credits"""
        mock_user.credits_remaining = 3
        
        result = file_service.check_user_credits(mock_user, estimated_credits=5)
        
        assert result is False

    # Processing Job Creation Tests
    
    def test_create_processing_job(self, file_service, mock_user, mock_db):
        """Test processing job creation"""
        # Mock the database operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        result = file_service.create_processing_job(
            user=mock_user,
            file_name="test.csv",
            file_url="s3://bucket/test.csv",
            file_size=1024,
            country_schema="USA"
        )
        
        assert isinstance(result, ProcessingJob)
        assert result.user_id == mock_user.id
        assert result.input_file_name == "test.csv"
        assert result.input_file_url == "s3://bucket/test.csv"
        assert result.input_file_size == 1024
        assert result.country_schema == "USA"
        assert result.status == ProcessingStatus.PENDING
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    # S3 Upload Tests
    
    @pytest.mark.asyncio
    async def test_s3_upload_success(self, file_service, create_upload_file, valid_csv_content):
        """Test successful S3 upload"""
        file = create_upload_file(valid_csv_content, "test.csv")
        
        # Mock S3 client
        mock_s3_client = Mock()
        file_service.s3_client = mock_s3_client
        mock_s3_client.put_object = Mock()
        
        with patch('src.services.file_processing.settings') as mock_settings:
            mock_settings.AWS_S3_BUCKET = "test-bucket"
            
            result = await file_service.upload_file_to_s3(file, "user123")
            
            assert result.startswith("s3://test-bucket/uploads/user123/")
            mock_s3_client.put_object.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_s3_upload_no_client(self, file_service, create_upload_file, valid_csv_content):
        """Test S3 upload when S3 client is not configured"""
        file = create_upload_file(valid_csv_content, "test.csv")
        file_service.s3_client = None
        
        with pytest.raises(Exception) as exc_info:
            await file_service.upload_file_to_s3(file, "user123")
        
        assert "S3 configuration not available" in str(exc_info.value)

    # Encoding Tests
    
    async def test_csv_utf8_encoding(self, file_service, create_upload_file):
        """Test CSV file with UTF-8 encoding"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country
"Café Français",100,pieces,500.00,France
"Naïve Product",50,kg,250.50,Canada
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert result.is_valid
            assert result.total_rows == 2
    
    async def test_csv_invalid_encoding(self, file_service, create_upload_file):
        """Test CSV file with invalid encoding"""
        # Create invalid UTF-8 content
        invalid_bytes = b"\xff\xfe" + "Product Description,Quantity,Unit,Value,Origin Country,Unit Price\nTest,1,pc,100,US,10".encode('utf-8')
        
        file_obj = io.BytesIO(invalid_bytes)
        file = UploadFile(filename="test.csv", file=file_obj, size=len(invalid_bytes))
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should handle encoding gracefully with fallback or warning
            # The specific behavior depends on implementation details
    
    # New Enhanced Validation Tests for Task 2
    
    async def test_validate_unit_price_field(self, file_service, create_upload_file):
        """Test validation of unit_price field"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"Test Product 1",100,pieces,500.00,USA,5.00
"Test Product 2",50,kg,invalid_price,Canada,invalid_price
"Test Product 3",25,pieces,250.00,Mexico,-1.00
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            assert result.total_rows == 3
            assert result.valid_rows == 1  # Only first row is valid
            
            # Check for unit_price validation errors
            unit_price_errors = [e for e in result.errors if e.field == "unit_price"]
            assert len(unit_price_errors) >= 2  # At least invalid format and negative value errors
    
    async def test_cross_field_validation(self, file_service, create_upload_file):
        """Test cross-field validation (quantity * unit_price = value)"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"Test Product 1",100,pieces,500.00,USA,5.00
"Test Product 2",50,kg,300.00,Canada,5.00
"Test Product 3",25,pieces,100.00,Mexico,4.00
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should have cross-validation errors for rows 2 and 3
            calc_errors = [e for e in result.errors if e.field == "value_calculation"]
            assert len(calc_errors) >= 1  # At least one calculation mismatch
    
    async def test_text_field_validation(self, file_service, create_upload_file):
        """Test text field validation (length and format)"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"AB",100,pieces,500.00,USA,5.00
"A very long product description that exceeds the maximum allowed length of 500 characters. This description is intentionally made very long to test the validation logic. It contains repeated text to ensure it exceeds the limit. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",50,"",250.00,"A",5.00
"Valid Product",25,pieces,100.00,"United States of America with a very long country name that exceeds one hundred characters maximum limit for origin country field validation testing purposes",4.00
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            
            # Check for text field validation errors
            desc_errors = [e for e in result.errors if e.field == "product_description"]
            unit_errors = [e for e in result.errors if e.field == "unit"]
            country_errors = [e for e in result.errors if e.field == "origin_country"]
            
            assert len(desc_errors) >= 2  # Too short and too long
            assert len(unit_errors) >= 1   # Empty unit
            assert len(country_errors) >= 2  # Too short and too long
    
    async def test_validation_summary_generation(self, file_service, create_upload_file):
        """Test detailed validation summary generation"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"",invalid_qty,pieces,500.00,,5.00
"Test Product",50,,invalid_value,USA,invalid_price
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            assert result.summary is not None
            assert result.summary.total_errors > 0
            assert isinstance(result.summary.errors_by_field, dict)
            assert isinstance(result.summary.errors_by_type, dict)
            assert isinstance(result.summary.most_common_errors, list)
            assert 0 <= result.summary.data_quality_score <= 100
    
    async def test_enhanced_encoding_detection(self, file_service):
        """Test enhanced encoding detection with multiple encodings"""
        # Test with Windows-1252 encoding (common in Excel exports)
        csv_content = "Product Description,Quantity,Unit,Value,Origin Country,Unit Price\nCafé Special,100,pieces,500.00,France,5.00"
        
        # Encode with Windows-1252
        encoded_content = csv_content.encode('windows-1252')
        file_obj = io.BytesIO(encoded_content)
        file = UploadFile(filename="test.csv", file=file_obj, size=len(encoded_content))
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            # Should detect encoding and include warning
            encoding_warnings = [w for w in result.warnings if "encoding" in w.lower()]
            assert len(encoding_warnings) > 0
    
    async def test_large_file_validation_limit(self, file_service, create_upload_file):
        """Test validation stops at error limit to prevent overwhelming response"""
        # Generate CSV with many invalid rows to test error limit
        header = "Product Description,Quantity,Unit,Value,Origin Country,Unit Price\n"
        invalid_rows = []
        for i in range(150):  # More than the 100 error limit
            invalid_rows.append(f'"Product {i}",invalid_qty,unit,invalid_value,Country,invalid_price')
        
        csv_content = header + '\n'.join(invalid_rows)
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            # Should stop validation due to too many errors
            error_limit_warning = any("too many errors" in w for w in result.warnings)
            assert error_limit_warning
            
            # Error count should be capped
            assert len(result.errors) <= 105  # Some buffer for header errors
    
    async def test_missing_unit_price_column(self, file_service, create_upload_file):
        """Test validation when unit_price column is missing"""
        csv_content = """Product Description,Quantity,Unit,Value,Origin Country
"Test Product 1",100,pieces,500.00,USA
"Test Product 2",50,kg,250.50,Canada
"""
        file = create_upload_file(csv_content, "test.csv")
        
        with patch.object(file_service, '_scan_file_for_viruses', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {'is_safe': True}
            
            result = await file_service.validate_file_upload(file)
            
            assert not result.is_valid
            # Should have error for missing unit_price column
            missing_col_errors = [e for e in result.errors if e.field == "headers" and "unit_price" in e.error]
            assert len(missing_col_errors) > 0


class TestCreditBalanceValidation:
    """Test cases for credit balance validation functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def user_with_credits(self):
        """User with sufficient credits"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.credits_remaining = 10
        user.credits_used_this_month = 5
        user.subscription_tier = SubscriptionTier.BASIC
        return user
    
    @pytest.fixture
    def user_no_credits(self):
        """User with no credits"""
        user = Mock(spec=User)
        user.id = "test-user-no-credits"
        user.credits_remaining = 0
        user.credits_used_this_month = 20
        user.subscription_tier = SubscriptionTier.FREE
        return user
    
    @pytest.fixture
    def user_low_credits(self):
        """User with low credits"""
        user = Mock(spec=User)
        user.id = "test-user-low-credits"
        user.credits_remaining = 2
        user.credits_used_this_month = 18
        user.subscription_tier = SubscriptionTier.PREMIUM
        return user
    
    @pytest.fixture
    def file_service(self, mock_db):
        """File processing service instance"""
        return FileProcessingService(mock_db)
    
    def test_check_user_credits_sufficient(self, file_service, user_with_credits):
        """Test credit check with sufficient credits"""
        result = file_service.check_user_credits(user_with_credits, estimated_credits=3)
        
        assert result['has_sufficient_credits'] is True
        assert result['credits_remaining'] == 10
        assert result['credits_required'] == 3
        assert "Processing will use 3 credit(s)" in result['message']
        assert "You have 10 remaining" in result['message']
    
    def test_check_user_credits_insufficient(self, file_service, user_no_credits):
        """Test credit check with insufficient credits"""
        result = file_service.check_user_credits(user_no_credits, estimated_credits=5)
        
        assert result['has_sufficient_credits'] is False
        assert result['credits_remaining'] == 0
        assert result['credits_required'] == 5
        assert "Insufficient credits" in result['message']
        assert "You need 5 credit(s) but only have 0 remaining" in result['message']
    
    def test_credit_message_free_tier(self, file_service, user_no_credits):
        """Test credit message for free tier users"""
        user_no_credits.subscription_tier = SubscriptionTier.FREE
        result = file_service.check_user_credits(user_no_credits, estimated_credits=1)
        
        assert result['has_sufficient_credits'] is False
        assert "Upgrade to a paid plan" in result['message']
    
    def test_credit_message_paid_tier(self, file_service, user_low_credits):
        """Test credit message for paid tier users"""
        result = file_service.check_user_credits(user_low_credits, estimated_credits=5)
        
        assert result['has_sufficient_credits'] is False
        assert "Please purchase 3 more credit(s)" in result['message']  # 5 - 2 = 3
    
    def test_calculate_processing_credits_small_file(self, file_service):
        """Test credit calculation for small files"""
        # Files up to 100 rows = 1 credit
        assert file_service.calculate_processing_credits(50) == 1
        assert file_service.calculate_processing_credits(100) == 1
    
    def test_calculate_processing_credits_medium_file(self, file_service):
        """Test credit calculation for medium files"""
        # 101-200 rows = 2 credits
        assert file_service.calculate_processing_credits(101) == 2
        assert file_service.calculate_processing_credits(150) == 2
        assert file_service.calculate_processing_credits(200) == 2
    
    def test_calculate_processing_credits_large_file(self, file_service):
        """Test credit calculation for large files"""
        # 201-300 rows = 3 credits
        assert file_service.calculate_processing_credits(201) == 3
        assert file_service.calculate_processing_credits(250) == 3
        assert file_service.calculate_processing_credits(300) == 3
    
    def test_calculate_processing_credits_very_large_file(self, file_service):
        """Test credit calculation for very large files"""
        # 501-600 rows = 6 credits
        assert file_service.calculate_processing_credits(501) == 6
        assert file_service.calculate_processing_credits(600) == 6
        # 1000 rows = 10 credits
        assert file_service.calculate_processing_credits(1000) == 10
    
    def test_calculate_processing_credits_edge_cases(self, file_service):
        """Test credit calculation edge cases"""
        assert file_service.calculate_processing_credits(0) == 1  # Minimum cost
        assert file_service.calculate_processing_credits(-5) == 1  # Negative rows
    
    def test_reserve_user_credits_success(self, file_service, user_with_credits):
        """Test successful credit reservation"""
        file_service.db.refresh = Mock()
        file_service.db.commit = Mock()
        
        result = file_service.reserve_user_credits(user_with_credits, 3)
        
        assert result is True
        assert user_with_credits.credits_remaining == 7  # 10 - 3
        assert user_with_credits.credits_used_this_month == 8  # 5 + 3
        file_service.db.refresh.assert_called_once_with(user_with_credits)
        file_service.db.commit.assert_called_once()
    
    def test_reserve_user_credits_insufficient(self, file_service, user_low_credits):
        """Test credit reservation with insufficient credits"""
        file_service.db.refresh = Mock()
        
        result = file_service.reserve_user_credits(user_low_credits, 5)
        
        assert result is False
        assert user_low_credits.credits_remaining == 2  # Unchanged
        assert user_low_credits.credits_used_this_month == 18  # Unchanged
        file_service.db.refresh.assert_called_once_with(user_low_credits)
    
    def test_reserve_user_credits_database_error(self, file_service, user_with_credits):
        """Test credit reservation with database error"""
        file_service.db.refresh = Mock()
        file_service.db.commit = Mock(side_effect=Exception("DB Error"))
        file_service.db.rollback = Mock()
        
        result = file_service.reserve_user_credits(user_with_credits, 3)
        
        assert result is False
        file_service.db.rollback.assert_called_once()
    
    def test_refund_user_credits_success(self, file_service, user_with_credits):
        """Test successful credit refund"""
        file_service.db.refresh = Mock()
        file_service.db.commit = Mock()
        user_with_credits.credits_remaining = 5  # After some credits were used
        user_with_credits.credits_used_this_month = 10
        
        result = file_service.refund_user_credits(user_with_credits, 3)
        
        assert result is True
        assert user_with_credits.credits_remaining == 8  # 5 + 3
        assert user_with_credits.credits_used_this_month == 7  # 10 - 3
        file_service.db.refresh.assert_called_once_with(user_with_credits)
        file_service.db.commit.assert_called_once()
    
    def test_refund_user_credits_zero_floor(self, file_service, user_with_credits):
        """Test credit refund doesn't go below zero for used credits"""
        file_service.db.refresh = Mock()
        file_service.db.commit = Mock()
        user_with_credits.credits_remaining = 5
        user_with_credits.credits_used_this_month = 2
        
        result = file_service.refund_user_credits(user_with_credits, 5)
        
        assert result is True
        assert user_with_credits.credits_remaining == 10  # 5 + 5
        assert user_with_credits.credits_used_this_month == 0  # max(0, 2 - 5)
    
    def test_refund_user_credits_database_error(self, file_service, user_with_credits):
        """Test credit refund with database error"""
        file_service.db.refresh = Mock()
        file_service.db.commit = Mock(side_effect=Exception("DB Error"))
        file_service.db.rollback = Mock()
        
        result = file_service.refund_user_credits(user_with_credits, 3)
        
        assert result is False
        file_service.db.rollback.assert_called_once()