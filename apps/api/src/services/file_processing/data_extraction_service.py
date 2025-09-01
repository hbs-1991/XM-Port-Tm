"""
Data extraction service for parsing CSV and XLSX files
"""
import csv
import io
from typing import List, Dict, Any
from pathlib import Path

import pandas as pd

from .constants import COLUMN_MAPPING, ALTERNATIVE_HEADERS


class DataExtractionService:
    """Service for extracting product data from files"""
    
    async def extract_products_from_file(self, content: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Extract product data from file content
        
        Args:
            content: File content as bytes
            filename: Name of the file to determine file type
            
        Returns:
            List of product dictionaries with normalized keys
        """
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == '.csv':
            return await self._extract_csv_products(content)
        elif file_ext == '.xlsx':
            return await self._extract_xlsx_products(content)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

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
            # Normalize keys using our mapping
            normalized_row = self._normalize_row_keys(row)
            
            # Convert to standard format using canonical names
            product = self._create_product_dict(normalized_row)
            
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
            # Normalize keys using our mapping
            normalized_row = self._normalize_row_keys(row.to_dict())
            
            # Convert to standard format using canonical names
            product = self._create_product_dict(normalized_row)
            
            # Only add valid products (with description)
            if product['product_description'] and product['product_description'] != 'nan':
                products.append(product)
        
        return products
    
    def _normalize_row_keys(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize row keys using column mapping
        
        Args:
            row: Dictionary with original column names as keys
            
        Returns:
            Dictionary with normalized column names as keys
        """
        normalized_row = {}
        
        for original_key, value in row.items():
            original_key = str(original_key).strip() if original_key else ''
            
            # Use the same normalization as validation
            if original_key in COLUMN_MAPPING:
                normalized_key = COLUMN_MAPPING[original_key]
            elif original_key.lower() in ALTERNATIVE_HEADERS:
                normalized_key = ALTERNATIVE_HEADERS[original_key.lower()]
            else:
                # Check for partial matches
                key_lower = original_key.lower()
                found = False
                for alt_header, canonical in ALTERNATIVE_HEADERS.items():
                    if alt_header in key_lower or key_lower in alt_header:
                        normalized_key = canonical
                        found = True
                        break
                if not found:
                    normalized_key = original_key.lower().replace(' ', '_').strip()
            
            normalized_row[normalized_key] = value
        
        return normalized_row
    
    def _create_product_dict(self, normalized_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a standardized product dictionary from normalized row
        
        Args:
            normalized_row: Dictionary with normalized column names
            
        Returns:
            Standardized product dictionary
        """
        try:
            # Extract and clean values
            product_name = str(normalized_row.get('product_name', '')).strip()
            quantity = float(str(normalized_row.get('quantity', 0)).replace(',', ''))
            unit = str(normalized_row.get('unit', '')).strip()
            unit_price = float(str(normalized_row.get('unit_price', 0)).replace(',', ''))
            origin_country = str(normalized_row.get('origin_country', '')).strip()
            
            # Calculate total value
            total_value = unit_price * quantity
            
            return {
                'product_description': product_name,
                'quantity': quantity,
                'unit': unit,
                'value': total_value,
                'origin_country': origin_country,
                'unit_price': unit_price
            }
        except (ValueError, TypeError) as e:
            # Return empty product if there are conversion errors
            return {
                'product_description': '',
                'quantity': 0,
                'unit': '',
                'value': 0,
                'origin_country': '',
                'unit_price': 0
            }
    
    def validate_extracted_products(self, products: List[Dict[str, Any]]) -> List[str]:
        """
        Validate extracted products and return list of issues
        
        Args:
            products: List of extracted product dictionaries
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if not products:
            issues.append("No products were extracted from the file")
            return issues
        
        empty_descriptions = 0
        invalid_quantities = 0
        invalid_prices = 0
        
        for i, product in enumerate(products):
            if not product.get('product_description'):
                empty_descriptions += 1
            
            if product.get('quantity', 0) <= 0:
                invalid_quantities += 1
            
            if product.get('unit_price', 0) <= 0:
                invalid_prices += 1
        
        if empty_descriptions > 0:
            issues.append(f"{empty_descriptions} products have empty descriptions")
        
        if invalid_quantities > 0:
            issues.append(f"{invalid_quantities} products have invalid quantities")
        
        if invalid_prices > 0:
            issues.append(f"{invalid_prices} products have invalid unit prices")
        
        return issues