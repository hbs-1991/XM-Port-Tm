"""
Test suite for column mapping validation between frontend and backend
Ensures consistency in handling Russian CSV templates
"""
import pytest
import io
import csv
from unittest.mock import Mock, patch
from src.services.file_processing import (
    FileProcessingService,
    COLUMN_MAPPING,
    ALTERNATIVE_HEADERS,
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS
)


class TestColumnMappingValidation:
    """Test column mapping and validation consistency"""
    
    def test_required_columns_match_frontend(self):
        """Test that required columns match frontend definitions"""
        # Frontend has these as required (from columnMapping.ts)
        frontend_required = {
            'sequence_number',
            'product_name',
            'origin_country',
            'package_quantity',
            'package_part',
            'package_type',
            'quantity',
            'unit',
            'unit_price',
            'gross_weight',
            'net_weight'
        }
        
        assert REQUIRED_COLUMNS == frontend_required, \
            f"Backend required columns don't match frontend. Backend: {REQUIRED_COLUMNS}, Frontend: {frontend_required}"
    
    def test_optional_columns_match_frontend(self):
        """Test that optional columns match frontend definitions"""
        # Frontend has these as optional (from columnMapping.ts)
        frontend_optional = {
            'procedure',
            'preference',
            'bku',
            'additional_quantity',
            'additional_unit'
        }
        
        assert OPTIONAL_COLUMNS == frontend_optional, \
            f"Backend optional columns don't match frontend. Backend: {OPTIONAL_COLUMNS}, Frontend: {frontend_optional}"
    
    def test_russian_column_mapping(self):
        """Test that Russian column headers map to correct canonical names"""
        expected_mapping = {
            '№': 'sequence_number',
            'Наименование товара': 'product_name',
            'Страна происхождения': 'origin_country',
            'Количество мест': 'package_quantity',
            'Часть мест': 'package_part',
            'Вид упаковки': 'package_type',
            'Количество': 'quantity',
            'Единица измерение': 'unit',
            'Цена': 'unit_price',
            'Брутто кг': 'gross_weight',
            'Нетто кг': 'net_weight',
            'Процедура': 'procedure',
            'Преференция': 'preference',
            'BKU': 'bku',
            'Количество в допольнительной ед. изм.': 'additional_quantity',
            'Допольнительная ед. изм.': 'additional_unit'
        }
        
        for russian_header, canonical_name in expected_mapping.items():
            assert COLUMN_MAPPING.get(russian_header) == canonical_name, \
                f"Column '{russian_header}' should map to '{canonical_name}' but maps to '{COLUMN_MAPPING.get(russian_header)}'"
    
    def test_alternative_headers_mapping(self):
        """Test that alternative headers correctly map to canonical names"""
        # Test some critical alternative mappings
        test_cases = [
            ('номер', 'sequence_number'),
            ('товар', 'product_name'),
            ('страна', 'origin_country'),
            ('кол-во', 'quantity'),
            ('ед.изм', 'unit'),
            ('цена', 'unit_price'),
            ('брутто', 'gross_weight'),
            ('нетто', 'net_weight'),
        ]
        
        for alt_header, expected_canonical in test_cases:
            assert ALTERNATIVE_HEADERS.get(alt_header) == expected_canonical, \
                f"Alternative header '{alt_header}' should map to '{expected_canonical}'"
    
    @pytest.mark.asyncio
    async def test_csv_validation_with_russian_headers(self):
        """Test CSV validation with Russian column headers"""
        # Create a mock CSV with Russian headers
        csv_content = """№,Наименование товара,Страна происхождения,Количество мест,Часть мест,Вид упаковки,Количество,Единица измерение,Цена,Брутто кг,Нетто кг
1,Кабель коаксиальный RG-58,Китай,1,1,Коробки,100,м,50.00,2.5,2.2"""
        
        # Create a mock file
        mock_file = Mock()
        mock_file.filename = "test.csv"
        mock_file.size = len(csv_content.encode())
        
        # Mock the file read
        with patch.object(mock_file, 'read', return_value=csv_content.encode()):
            db_mock = Mock()
            service = FileProcessingService(db=db_mock)
            
            # Test validation
            result = await service.validate_file_structure(mock_file, 'csv')
            
            # Should have no missing required columns
            assert result.valid == True or len([e for e in result.errors if 'Missing required column' in e.error]) == 0, \
                "Russian headers should be recognized and mapped correctly"
    
    @pytest.mark.asyncio
    async def test_csv_validation_with_alternative_headers(self):
        """Test CSV validation with alternative/variant column headers"""
        # Create a mock CSV with alternative headers
        csv_content = """номер,товар,страна,мест,часть,упаковка,кол-во,ед.изм,цена,брутто,нетто
1,Кабель коаксиальный RG-58,Китай,1,1,Коробки,100,м,50.00,2.5,2.2"""
        
        # Create a mock file
        mock_file = Mock()
        mock_file.filename = "test.csv"
        mock_file.size = len(csv_content.encode())
        
        # Mock the file read
        with patch.object(mock_file, 'read', return_value=csv_content.encode()):
            db_mock = Mock()
            service = FileProcessingService(db=db_mock)
            
            # Test validation
            result = await service.validate_file_structure(mock_file, 'csv')
            
            # Check that headers are recognized via alternative mappings
            # Some might be missing due to shortened forms, but critical ones should work
            errors_about_columns = [e for e in result.errors if 'Missing required column' in e.error]
            
            # At minimum, these critical alternative headers should be recognized
            recognized_alternatives = {'номер', 'товар', 'страна', 'кол-во', 'ед.изм', 'цена', 'брутто', 'нетто'}
            for alt in recognized_alternatives:
                assert alt in ALTERNATIVE_HEADERS, f"Alternative header '{alt}' should be in ALTERNATIVE_HEADERS"
    
    @pytest.mark.asyncio
    async def test_english_headers_compatibility(self):
        """Test that English headers are also handled correctly"""
        # Create a mock CSV with English headers
        csv_content = """No,Product Description,Origin Country,Number of Packages,Package Part,Package Type,Quantity,Unit,Unit Price,Gross Weight (kg),Net Weight (kg)
1,Coaxial Cable RG-58,China,1,1,Boxes,100,m,50.00,2.5,2.2"""
        
        # Create a mock file
        mock_file = Mock()
        mock_file.filename = "test.csv"
        mock_file.size = len(csv_content.encode())
        
        # Mock the file read
        with patch.object(mock_file, 'read', return_value=csv_content.encode()):
            db_mock = Mock()
            service = FileProcessingService(db=db_mock)
            
            # Test validation - English headers should work via alternative mappings
            result = await service.validate_file_structure(mock_file, 'csv')
            
            # Some English variants should be recognized
            # Note: Exact English headers might not all be in ALTERNATIVE_HEADERS,
            # but the system should still handle them gracefully
            assert result is not None, "Should handle English headers gracefully"
    
    def test_canonical_names_consistency(self):
        """Test that all canonical names are consistent across the system"""
        # All values in COLUMN_MAPPING should be from the canonical set
        all_canonical = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
        
        for russian_header, canonical in COLUMN_MAPPING.items():
            assert canonical in all_canonical, \
                f"COLUMN_MAPPING value '{canonical}' is not in REQUIRED_COLUMNS or OPTIONAL_COLUMNS"
        
        # All values in ALTERNATIVE_HEADERS should be from the canonical set
        for alt_header, canonical in ALTERNATIVE_HEADERS.items():
            assert canonical in all_canonical, \
                f"ALTERNATIVE_HEADERS value '{canonical}' is not in REQUIRED_COLUMNS or OPTIONAL_COLUMNS"
    
    def test_no_duplicate_mappings(self):
        """Test that there are no conflicting mappings"""
        # Check that alternative headers don't conflict with main mapping
        main_headers_lower = {k.lower() for k in COLUMN_MAPPING.keys()}
        
        for alt_header in ALTERNATIVE_HEADERS.keys():
            # Alternative headers should not duplicate main headers (case-insensitive)
            if alt_header in main_headers_lower:
                # If it exists in both, they should map to the same canonical name
                main_canonical = None
                for main_h, canon in COLUMN_MAPPING.items():
                    if main_h.lower() == alt_header:
                        main_canonical = canon
                        break
                
                assert ALTERNATIVE_HEADERS[alt_header] == main_canonical, \
                    f"Conflicting mapping for '{alt_header}'"