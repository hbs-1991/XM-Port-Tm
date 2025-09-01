/**
 * Test suite for column mapping consistency
 */
import {
  COLUMN_MAPPINGS,
  findColumnMapping,
  mapHeaders,
  getRequiredColumns,
  getMissingColumns,
  validateColumnValue
} from '@/components/dashboard/upload/columnMapping';

describe('Column Mapping Tests', () => {
  describe('Required and Optional Columns', () => {
    it('should have exactly 11 required columns', () => {
      const requiredColumns = COLUMN_MAPPINGS.filter(m => m.required);
      expect(requiredColumns).toHaveLength(11);
    });

    it('should have exactly 5 optional columns', () => {
      const optionalColumns = COLUMN_MAPPINGS.filter(m => !m.required);
      expect(optionalColumns).toHaveLength(5);
    });

    it('should have correct required columns', () => {
      const requiredCanonicals = getRequiredColumns();
      const expected = [
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
      ];
      
      expect(requiredCanonicals.sort()).toEqual(expected.sort());
    });
  });

  describe('Russian Header Mapping', () => {
    it('should correctly map Russian headers', () => {
      const russianHeaders = [
        '№',
        'Наименование товара',
        'Страна происхождения',
        'Количество мест',
        'Часть мест',
        'Вид упаковки',
        'Количество',
        'Единица измерение',
        'Цена',
        'Брутто кг',
        'Нетто кг'
      ];

      const mapped = mapHeaders(russianHeaders);
      
      expect(mapped['№']).toBe('sequence_number');
      expect(mapped['Наименование товара']).toBe('product_name');
      expect(mapped['Страна происхождения']).toBe('origin_country');
      expect(mapped['Количество мест']).toBe('package_quantity');
      expect(mapped['Часть мест']).toBe('package_part');
      expect(mapped['Вид упаковки']).toBe('package_type');
      expect(mapped['Количество']).toBe('quantity');
      expect(mapped['Единица измерение']).toBe('unit');
      expect(mapped['Цена']).toBe('unit_price');
      expect(mapped['Брутто кг']).toBe('gross_weight');
      expect(mapped['Нетто кг']).toBe('net_weight');
    });

    it('should identify missing required columns from Russian template', () => {
      const incompleteHeaders = [
        '№',
        'Наименование товара',
        'Страна происхождения',
        // Missing other required columns
      ];

      const missing = getMissingColumns(incompleteHeaders);
      
      expect(missing).toContain('package_quantity');
      expect(missing).toContain('package_part');
      expect(missing).toContain('package_type');
      expect(missing).toContain('quantity');
      expect(missing).toContain('unit');
      expect(missing).toContain('unit_price');
      expect(missing).toContain('gross_weight');
      expect(missing).toContain('net_weight');
    });
  });

  describe('Alternative Header Recognition', () => {
    it('should recognize common variations', () => {
      const variations = [
        { header: 'номер', expected: 'sequence_number' },
        { header: 'товар', expected: 'product_name' },
        { header: 'страна', expected: 'origin_country' },
        { header: 'кол-во', expected: 'quantity' },
        { header: 'ед.изм', expected: 'unit' },
        { header: 'цена', expected: 'unit_price' },
        { header: 'брутто', expected: 'gross_weight' },
        { header: 'нетто', expected: 'net_weight' }
      ];

      variations.forEach(({ header, expected }) => {
        const mapping = findColumnMapping(header);
        expect(mapping?.canonical).toBe(expected);
      });
    });

    it('should handle English variations', () => {
      const englishVariations = [
        { header: 'Product Description', expected: 'product_name' },
        { header: 'Origin Country', expected: 'origin_country' },
        { header: 'Quantity', expected: 'quantity' },
        { header: 'Unit', expected: 'unit' },
        { header: 'Unit Price', expected: 'unit_price' }
      ];

      englishVariations.forEach(({ header, expected }) => {
        const mapping = findColumnMapping(header);
        expect(mapping?.canonical).toBe(expected);
      });
    });

    it('should handle partial matches', () => {
      const partialHeaders = [
        { header: 'Наименование', expected: 'product_name' }, // Partial of "Наименование товара"
        { header: 'Происхождение', expected: 'origin_country' }, // Partial of "Страна происхождения"
        { header: 'Упаковка', expected: 'package_type' } // Partial of "Вид упаковки"
      ];

      partialHeaders.forEach(({ header, expected }) => {
        const mapping = findColumnMapping(header);
        expect(mapping?.canonical).toBe(expected);
      });
    });
  });

  describe('Column Value Validation', () => {
    it('should validate numeric fields correctly', () => {
      const numericFields = ['sequence_number', 'quantity', 'unit_price', 'gross_weight', 'net_weight'];
      
      numericFields.forEach(field => {
        // Valid numbers
        expect(validateColumnValue('123', field).valid).toBe(true);
        expect(validateColumnValue('12.5', field).valid).toBe(true);
        expect(validateColumnValue('1,234.56', field).valid).toBe(true);
        
        // Invalid numbers
        expect(validateColumnValue('abc', field).valid).toBe(false);
        expect(validateColumnValue('', field).valid).toBe(false);
      });
    });

    it('should validate text fields correctly', () => {
      // Product name should have min length
      expect(validateColumnValue('AB', 'product_name').valid).toBe(false); // Too short
      expect(validateColumnValue('Valid Product Name', 'product_name').valid).toBe(true);
      expect(validateColumnValue('A'.repeat(501), 'product_name').valid).toBe(false); // Too long
      
      // Country validation
      expect(validateColumnValue('US', 'origin_country').valid).toBe(true);
      expect(validateColumnValue('United States', 'origin_country').valid).toBe(true);
      expect(validateColumnValue('U', 'origin_country').valid).toBe(false); // Too short
    });

    it('should handle empty optional fields', () => {
      const optionalFields = ['procedure', 'preference', 'bku', 'additional_quantity', 'additional_unit'];
      
      optionalFields.forEach(field => {
        expect(validateColumnValue('', field).valid).toBe(true); // Empty is OK for optional
        expect(validateColumnValue(null, field).valid).toBe(true);
        expect(validateColumnValue(undefined, field).valid).toBe(true);
      });
    });

    it('should require values for required fields', () => {
      const requiredFields = getRequiredColumns();
      
      requiredFields.forEach(field => {
        expect(validateColumnValue('', field).valid).toBe(false); // Empty not OK for required
        expect(validateColumnValue(null, field).valid).toBe(false);
        expect(validateColumnValue(undefined, field).valid).toBe(false);
      });
    });
  });

  describe('Cross-field Validation', () => {
    it('should validate that all required fields have proper types', () => {
      const typeMap = {
        'sequence_number': 'number',
        'product_name': 'text',
        'origin_country': 'country',
        'package_quantity': 'number',
        'package_part': 'number',
        'package_type': 'text',
        'quantity': 'number',
        'unit': 'unit',
        'unit_price': 'currency',
        'gross_weight': 'number',
        'net_weight': 'number'
      };

      COLUMN_MAPPINGS.forEach(mapping => {
        if (mapping.required) {
          expect(typeMap).toHaveProperty(mapping.canonical);
          expect(mapping.type).toBeDefined();
        }
      });
    });

    it('should have consistent Russian and English names', () => {
      COLUMN_MAPPINGS.forEach(mapping => {
        expect(mapping.russian).toBeTruthy();
        expect(mapping.english).toBeTruthy();
        expect(mapping.canonical).toBeTruthy();
        expect(mapping.aliases).toBeInstanceOf(Array);
      });
    });
  });
});