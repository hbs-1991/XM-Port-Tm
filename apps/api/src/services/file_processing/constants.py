"""
Shared constants for file processing services
"""

# File validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
ALLOWED_EXTENSIONS = {'.csv', '.xlsx'}
ALLOWED_MIME_TYPES = {
    'text/csv', 
    'application/csv',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

# Column mapping from template headers to canonical names (matching frontend)
# This mapping aligns with frontend's columnMapping.ts canonical names
COLUMN_MAPPING = {
    '№': 'sequence_number',
    'номер': 'sequence_number',
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
    'Количество в дополнительной ед. изм.': 'additional_quantity',
    'Дополнительная ед. изм.': 'additional_unit',
    # Handle legacy typo headers from old CSV templates
    'Количество в допольнительной ед. изм.': 'additional_quantity',
    'Допольнительная ед. изм.': 'additional_unit'
}

# Alternative header variations that map to canonical names
# This helps with flexible column recognition
ALTERNATIVE_HEADERS = {
    # Variations for sequence_number
    'номер': 'sequence_number',
    'number': 'sequence_number',
    'no': 'sequence_number',
    '#': 'sequence_number',
    
    # Variations for product_name
    'товар': 'product_name',
    'название': 'product_name',
    'product': 'product_name',
    'description': 'product_name',
    'наименование': 'product_name',
    
    # Variations for origin_country
    'страна': 'origin_country',
    'происхождение': 'origin_country',
    'country': 'origin_country',
    'origin': 'origin_country',
    
    # Variations for package_quantity
    'мест': 'package_quantity',
    'места': 'package_quantity',
    'packages': 'package_quantity',
    
    # Variations for package_part
    'часть': 'package_part',
    'part': 'package_part',
    'части': 'package_part',
    
    # Variations for package_type
    'упаковка': 'package_type',
    'package': 'package_type',
    'packaging': 'package_type',
    'тара': 'package_type',
    
    # Variations for quantity
    'кол-во': 'quantity',
    'qty': 'quantity',
    'amount': 'quantity',
    'колво': 'quantity',
    'кол': 'quantity',
    
    # Variations for unit
    'ед.изм': 'unit',
    'единица': 'unit',
    'measure': 'unit',
    'единицы': 'unit',
    'ед': 'unit',
    'measurement': 'unit',
    
    # Variations for unit_price
    'стоимость': 'unit_price',
    'price': 'unit_price',
    'cost': 'unit_price',
    'value': 'unit_price',
    'цена за единицу': 'unit_price',
    'unit cost': 'unit_price',
    
    # Variations for gross_weight
    'брутто': 'gross_weight',
    'gross': 'gross_weight',
    'вес брутто': 'gross_weight',
    'gross weight': 'gross_weight',
    
    # Variations for net_weight
    'нетто': 'net_weight',
    'net': 'net_weight',
    'вес нетто': 'net_weight',
    'net weight': 'net_weight',
    
    # Variations for procedure
    'процедуры': 'procedure',
    'proc': 'procedure',
    
    # Variations for preference
    'преференции': 'preference',
    'pref': 'preference',
    
    # Variations for BKU
    'бку': 'bku',
    'b.k.u': 'bku',
    
    # Variations for additional_quantity
    'доп.кол-во': 'additional_quantity',
    'доп количество': 'additional_quantity',
    'дополнительное количество': 'additional_quantity',
    'допольнительное количество': 'additional_quantity',  # Common typo
    
    # Variations for additional_unit
    'доп.ед.изм': 'additional_unit',
    'доп единица': 'additional_unit',
    'дополнительная единица': 'additional_unit',
    'допольнительная единица': 'additional_unit'  # Common typo
}

# Required columns using canonical names (matching frontend columnMapping.ts)
REQUIRED_COLUMNS = {
    'sequence_number',
    'product_name',
    'origin_country',
    'package_quantity',
    'package_type',
    'quantity',
    'unit',
    'unit_price',
    'gross_weight',
    'net_weight'
}

# Optional columns using canonical names
OPTIONAL_COLUMNS = {
    'procedure',
    'preference',
    'bku',
    'additional_quantity',
    'additional_unit',
    'package_part'
}

# All columns for comprehensive validation
ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS