/**
 * Unified column mapping system for CSV validation
 * Supports both Russian and English headers with flexible matching
 */

export interface ColumnMapping {
  canonical: string; // Standard internal name
  russian: string;   // Russian header name
  english: string;   // English header name
  aliases: string[]; // Alternative names/variations
  required: boolean; // Whether this field is mandatory
  type: 'text' | 'number' | 'currency' | 'country' | 'unit';
  validation?: {
    min?: number;
    max?: number;
    pattern?: RegExp;
  };
}

export const COLUMN_MAPPINGS: ColumnMapping[] = [
  {
    canonical: 'sequence_number',
    russian: 'номер',
    english: 'No',
    aliases: ['№', 'number', 'no', '#', 'п/п', 'пп'],
    required: true,
    type: 'number',
    validation: { min: 1 }
  },
  {
    canonical: 'product_name',
    russian: 'Наименование товара',
    english: 'Product Description',
    aliases: ['товар', 'название', 'product', 'description', 'наименование', 'product name'],
    required: true,
    type: 'text',
    validation: { min: 3, max: 500 }
  },
  {
    canonical: 'origin_country',
    russian: 'Страна происхождения',
    english: 'Origin Country',
    aliases: ['страна', 'происхождение', 'country', 'origin', 'country of origin'],
    required: true,
    type: 'country'
  },
  {
    canonical: 'package_quantity',
    russian: 'Количество мест',
    english: 'Number of Packages',
    aliases: ['мест', 'места', 'packages', 'количество мест', 'package count'],
    required: true,
    type: 'number',
    validation: { min: 1 }
  },
  {
    canonical: 'package_part',
    russian: 'Часть мест',
    english: 'Package Part',
    aliases: ['часть', 'part', 'части', 'package part'],
    required: false,
    type: 'number',
    validation: { min: 1 }
  },
  {
    canonical: 'package_type',
    russian: 'Вид упаковки',
    english: 'Package Type',
    aliases: ['упаковка', 'package', 'packaging', 'тара', 'packaging type'],
    required: true,
    type: 'text'
  },
  {
    canonical: 'quantity',
    russian: 'Количество',
    english: 'Quantity',
    aliases: ['кол-во', 'qty', 'quantity', 'amount', 'кол', 'колво'],
    required: true,
    type: 'number',
    validation: { min: 0.001 }
  },
  {
    canonical: 'unit',
    russian: 'Единица измерение',
    english: 'Unit',
    aliases: ['ед.изм', 'единица', 'unit', 'measure', 'единицы', 'ед', 'measurement'],
    required: true,
    type: 'unit'
  },
  {
    canonical: 'unit_price',
    russian: 'Цена',
    english: 'Unit Price',
    aliases: ['стоимость', 'price', 'cost', 'value', 'цена за единицу', 'unit cost'],
    required: true,
    type: 'currency',
    validation: { min: 0.01 }
  },
  {
    canonical: 'gross_weight',
    russian: 'Брутто кг',
    english: 'Gross Weight (kg)',
    aliases: ['брутто', 'gross', 'вес брутто', 'gross weight'],
    required: true,
    type: 'number',
    validation: { min: 0.001 }
  },
  {
    canonical: 'net_weight',
    russian: 'Нетто кг',
    english: 'Net Weight (kg)',
    aliases: ['нетто', 'net', 'вес нетто', 'net weight'],
    required: true,
    type: 'number',
    validation: { min: 0.001 }
  },
  {
    canonical: 'procedure',
    russian: 'Процедура',
    english: 'Procedure',
    aliases: ['procedure', 'процедуры', 'proc'],
    required: false,
    type: 'text'
  },
  {
    canonical: 'preference',
    russian: 'Преференция',
    english: 'Preference',
    aliases: ['preference', 'преференции', 'pref'],
    required: false,
    type: 'text'
  },
  {
    canonical: 'bku',
    russian: 'BKU',
    english: 'BKU',
    aliases: ['бку', 'b.k.u'],
    required: false,
    type: 'text'
  },
  {
    canonical: 'additional_quantity',
    russian: 'Количество в дополнительной ед. изм.',
    english: 'Additional Quantity',
    aliases: ['доп.кол-во', 'additional quantity', 'доп количество', 'дополнительное количество', 'допольнительное количество', 'количество в допольнительной ед. изм.'],
    required: false,
    type: 'number',
    validation: { min: 0 }
  },
  {
    canonical: 'additional_unit',
    russian: 'Дополнительная ед. изм.',
    english: 'Additional Unit',
    aliases: ['доп.ед.изм', 'additional unit', 'доп единица', 'дополнительная единица', 'допольнительная единица', 'допольнительная ед. изм.'],
    required: false,
    type: 'unit'
  }
];

/**
 * Find column mapping by header name (case-insensitive, flexible matching)
 */
export function findColumnMapping(headerName: string): ColumnMapping | null {
  const normalized = headerName.trim().toLowerCase();
  
  // First pass: Look for exact matches only
  let exactMatch = COLUMN_MAPPINGS.find(mapping => {
    // Check exact russian/english matches
    if (mapping.russian.toLowerCase() === normalized ||
        mapping.english.toLowerCase() === normalized) {
      return true;
    }
    
    // Check exact alias matches only (no partial matching)
    return mapping.aliases.some(alias => 
      alias.toLowerCase() === normalized
    );
  });
  
  if (exactMatch) {
    return exactMatch;
  }
  
  // Second pass: Look for partial matches only if no exact match found
  return COLUMN_MAPPINGS.find(mapping => {
    return mapping.aliases.some(alias => 
      normalized.includes(alias.toLowerCase()) ||
      alias.toLowerCase().includes(normalized)
    );
  }) || null;
}

/**
 * Map CSV headers to canonical column names
 */
export function mapHeaders(headers: string[]): { [key: string]: string } {
  const mapping: { [key: string]: string } = {};
  
  headers.forEach(header => {
    const columnMapping = findColumnMapping(header);
    if (columnMapping) {
      mapping[header] = columnMapping.canonical;
    }
  });
  
  return mapping;
}

/**
 * Get display name for a canonical column
 */
export function getDisplayName(canonical: string, locale: 'ru' | 'en' = 'ru'): string {
  const mapping = COLUMN_MAPPINGS.find(m => m.canonical === canonical);
  if (!mapping) return canonical;
  
  return locale === 'ru' ? mapping.russian : mapping.english;
}

/**
 * Get all required columns (canonical names)
 */
export function getRequiredColumns(): string[] {
  return COLUMN_MAPPINGS
    .filter(mapping => mapping.required)
    .map(mapping => mapping.canonical);
}

/**
 * Get missing required columns from headers
 */
export function getMissingColumns(headers: string[]): string[] {
  const headerMappings = mapHeaders(headers);
  const mappedCanonicals = Object.values(headerMappings);
  const requiredCanonicals = getRequiredColumns();
  
  return requiredCanonicals.filter(canonical => 
    !mappedCanonicals.includes(canonical)
  );
}

/**
 * Validate column value based on its type and rules
 */
export function validateColumnValue(
  value: any, 
  canonical: string
): { valid: boolean; error?: string } {
  const mapping = COLUMN_MAPPINGS.find(m => m.canonical === canonical);
  if (!mapping) {
    return { valid: true }; // Unknown columns are valid by default
  }

  // Handle empty values
  const stringValue = String(value || '').trim();
  if (!stringValue && mapping.required) {
    return { valid: false, error: 'Обязательное поле не заполнено' };
  }
  if (!stringValue && !mapping.required) {
    return { valid: true }; // Optional empty fields are valid
  }

  // Type-specific validation
  switch (mapping.type) {
    case 'number':
    case 'currency': {
      const num = parseFloat(stringValue.replace(/[,\s]/g, ''));
      if (isNaN(num)) {
        return { valid: false, error: 'Должно быть числом' };
      }
      if (mapping.validation?.min !== undefined && num < mapping.validation.min) {
        return { valid: false, error: `Должно быть больше ${mapping.validation.min}` };
      }
      if (mapping.validation?.max !== undefined && num > mapping.validation.max) {
        return { valid: false, error: `Должно быть меньше ${mapping.validation.max}` };
      }
      break;
    }

    case 'text':
      if (mapping.validation?.min !== undefined && stringValue.length < mapping.validation.min) {
        return { valid: false, error: `Минимум ${mapping.validation.min} символов` };
      }
      if (mapping.validation?.max !== undefined && stringValue.length > mapping.validation.max) {
        return { valid: false, error: `Максимум ${mapping.validation.max} символов` };
      }
      if (mapping.validation?.pattern && !mapping.validation.pattern.test(stringValue)) {
        return { valid: false, error: 'Неверный формат' };
      }
      break;

    case 'country':
      // Basic country validation - could be enhanced with ISO codes
      if (stringValue.length < 2) {
        return { valid: false, error: 'Укажите корректную страну' };
      }
      break;

    case 'unit':
      // Basic unit validation
      if (stringValue.length < 1) {
        return { valid: false, error: 'Укажите единицу измерения' };
      }
      break;
  }

  return { valid: true };
}

/**
 * Cross-field validation rules
 */
export function validateCrossFields(row: { [key: string]: any }): Array<{
  columns: string[];
  error: string;
}> {
  const errors: Array<{ columns: string[]; error: string }> = [];
  
  // Validate that net weight <= gross weight
  const netWeight = parseFloat(row['net_weight'] || '0');
  const grossWeight = parseFloat(row['gross_weight'] || '0');
  
  if (netWeight && grossWeight && netWeight > grossWeight) {
    errors.push({
      columns: ['net_weight', 'gross_weight'],
      error: 'Вес нетто не может быть больше веса брутто'
    });
  }
  
  // Validate package part <= package quantity
  const packagePart = parseFloat(row['package_part'] || '0');
  const packageQuantity = parseFloat(row['package_quantity'] || '0');
  
  if (packagePart && packageQuantity && packagePart > packageQuantity) {
    errors.push({
      columns: ['package_part', 'package_quantity'],
      error: 'Часть мест не может быть больше общего количества мест'
    });
  }
  
  // Validate reasonable unit price calculation
  const quantity = parseFloat(row['quantity'] || '0');
  const unitPrice = parseFloat(row['unit_price'] || '0');
  
  if (quantity && unitPrice) {
    const totalValue = quantity * unitPrice;
    
    // Warn if total value seems unreasonable
    if (totalValue < 0.01) {
      errors.push({
        columns: ['quantity', 'unit_price'],
        error: 'Общая стоимость кажется слишком низкой'
      });
    }
  }
  
  return errors;
}