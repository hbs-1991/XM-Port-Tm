'use client';

import React, { useState, useEffect } from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/shared/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/shared/ui/card';
import { Button } from '@/components/shared/ui/button';
import { Badge } from '@/components/shared/ui/badge';
import { Input } from '@/components/shared/ui/input';
import { 
  ChevronLeft, 
  ChevronRight, 
  Edit2, 
  Save, 
  X, 
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet
} from 'lucide-react';
import { 
  mapHeaders, 
  validateColumnValue, 
  validateCrossFields, 
  getDisplayName, 
  getMissingColumns,
  COLUMN_MAPPINGS 
} from './columnMapping';

interface FilePreviewProps {
  data: any[];
  fileName: string;
  editable?: boolean;
  onDataChange?: (data: any[]) => void;
  maxRows?: number;
}

interface ValidationError {
  row: number;
  column: string;
  canonical: string;
  message: string;
}

interface ColumnInfo {
  originalName: string;
  canonical: string;
  displayName: string;
  required: boolean;
}

export function FilePreview({ 
  data, 
  fileName, 
  editable = false, 
  onDataChange,
  maxRows = 100 
}: FilePreviewProps) {
  const [currentPage, setCurrentPage] = useState(0);
  const [editingCell, setEditingCell] = useState<{ row: number; column: string } | null>(null);
  const [editValue, setEditValue] = useState('');
  const [localData, setLocalData] = useState(data);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [columnInfo, setColumnInfo] = useState<ColumnInfo[]>([]);
  
  const rowsPerPage = 10;
  const totalPages = Math.ceil(localData.length / rowsPerPage);
  const startIndex = currentPage * rowsPerPage;
  const endIndex = Math.min(startIndex + rowsPerPage, localData.length);
  const visibleData = localData.slice(startIndex, endIndex);

  // Get column headers and map them
  const originalColumns = localData.length > 0 ? Object.keys(localData[0]) : [];
  
  useEffect(() => {
    if (originalColumns.length > 0) {
      // Map headers and create column info
      const headerMapping = mapHeaders(originalColumns);
      const info: ColumnInfo[] = originalColumns.map(originalName => {
        const canonical = headerMapping[originalName] || originalName;
        const mapping = COLUMN_MAPPINGS.find(m => m.canonical === canonical);
        
        return {
          originalName,
          canonical,
          displayName: getDisplayName(canonical, 'ru'),
          required: mapping?.required || false
        };
      });
      
      setColumnInfo(info);
      console.log('Column mapping established:', info);
    }
  }, [originalColumns]);

  useEffect(() => {
    if (localData.length > 0) {
      validateData();
    }
  }, [localData, columnInfo]);

  const validateData = () => {
    console.log('🔍 Starting validation...');
    const errors: ValidationError[] = [];
    
    // Check for missing required columns
    const missingColumns = getMissingColumns(originalColumns);
    if (missingColumns.length > 0) {
      console.log('❌ Missing required columns:', missingColumns);
      missingColumns.forEach(canonical => {
        errors.push({
          row: -1, // Header-level error
          column: 'header',
          canonical,
          message: `Отсутствует обязательный столбец: ${getDisplayName(canonical, 'ru')}`
        });
      });
    }
    
    localData.forEach((row, rowIndex) => {
      console.log(`Validating row ${rowIndex + 1}:`, row);
      
      // Create mapped row for validation
      const mappedRow: { [key: string]: any } = {};
      columnInfo.forEach(col => {
        mappedRow[col.canonical] = row[col.originalName];
      });
      
      // Validate each column
      columnInfo.forEach(col => {
        const value = row[col.originalName];
        const validation = validateColumnValue(value, col.canonical);
        
        if (!validation.valid && validation.error) {
          console.log(`❌ Row ${rowIndex + 1}, Column ${col.originalName}: ${validation.error}`);
          errors.push({
            row: rowIndex,
            column: col.originalName,
            canonical: col.canonical,
            message: validation.error
          });
        }
      });
      
      // Cross-field validation
      const crossFieldErrors = validateCrossFields(mappedRow);
      crossFieldErrors.forEach(crossError => {
        crossError.columns.forEach(canonical => {
          const colInfo = columnInfo.find(c => c.canonical === canonical);
          if (colInfo) {
            console.log(`❌ Cross-field error in row ${rowIndex + 1}: ${crossError.error}`);
            errors.push({
              row: rowIndex,
              column: colInfo.originalName,
              canonical,
              message: crossError.error
            });
          }
        });
      });
    });

    console.log(`📊 Validation complete: ${errors.length} errors found`);
    console.table(errors.map(e => ({
      row: e.row + 1,
      column: e.column,
      canonical: e.canonical,
      message: e.message
    })));
    
    setValidationErrors(errors);
  };

  const getCellError = (rowIndex: number, column: string) => {
    const globalRowIndex = startIndex + rowIndex;
    return validationErrors.find(error => 
      error.row === globalRowIndex && error.column === column
    );
  };

  const getCellClassName = (rowIndex: number, column: string) => {
    const error = getCellError(rowIndex, column);
    const colInfo = columnInfo.find(c => c.originalName === column);
    const baseClasses = 'p-2 text-sm';
    
    if (error) {
      return `${baseClasses} bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800`;
    }
    
    if (colInfo && !colInfo.required) {
      return `${baseClasses} bg-gray-50 dark:bg-gray-800/50`;
    }
    
    return baseClasses;
  };

  const startEdit = (rowIndex: number, column: string) => {
    if (!editable) return;
    
    setEditingCell({ row: rowIndex, column });
    setEditValue(String(visibleData[rowIndex][column] || ''));
  };

  const saveEdit = () => {
    if (!editingCell) return;
    
    const globalRowIndex = startIndex + editingCell.row;
    const newData = [...localData];
    newData[globalRowIndex] = {
      ...newData[globalRowIndex],
      [editingCell.column]: editValue
    };
    
    setLocalData(newData);
    setEditingCell(null);
    setEditValue('');
    onDataChange?.(newData);
  };

  const cancelEdit = () => {
    setEditingCell(null);
    setEditValue('');
  };

  const goToPreviousPage = () => {
    setCurrentPage(prev => Math.max(0, prev - 1));
  };

  const goToNextPage = () => {
    setCurrentPage(prev => Math.min(totalPages - 1, prev + 1));
  };

  if (!localData.length) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <FileSpreadsheet className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <p className="text-gray-500 dark:text-gray-400">
            No data to preview
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <FileSpreadsheet className="w-5 h-5" />
              Data Preview - {fileName}
            </CardTitle>
            <div className="flex items-center gap-4">
              {validationErrors.length > 0 ? (
                <Badge variant="destructive" className="flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  {validationErrors.length} error{validationErrors.length !== 1 ? 's' : ''}
                </Badge>
              ) : (
                <Badge variant="default" className="flex items-center gap-1 bg-green-500">
                  <CheckCircle2 className="w-3 h-3" />
                  Valid
                </Badge>
              )}
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {localData.length} row{localData.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <div className="rounded-lg border overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12 text-center">#</TableHead>
                    {originalColumns.map((column) => {
                      const colInfo = columnInfo.find(c => c.originalName === column);
                      return (
                        <TableHead key={column} className="min-w-32">
                          <div className="flex items-center gap-1">
                            <span className="font-medium">{column}</span>
                            {colInfo?.displayName !== column && (
                              <span className="text-xs text-gray-500">
                                ({colInfo?.displayName})
                              </span>
                            )}
                            {colInfo?.required && (
                              <span className="text-red-500">*</span>
                            )}
                          </div>
                        </TableHead>
                      );
                    })}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleData.map((row, rowIndex) => (
                    <TableRow key={startIndex + rowIndex}>
                      <TableCell className="text-center text-gray-500 dark:text-gray-400 font-mono text-xs">
                        {startIndex + rowIndex + 1}
                      </TableCell>
                      {originalColumns.map((column) => {
                        const isEditing = editingCell?.row === rowIndex && editingCell?.column === column;
                        const cellError = getCellError(rowIndex, column);
                        
                        return (
                          <TableCell 
                            key={column} 
                            className={getCellClassName(rowIndex, column)}
                          >
                            {isEditing ? (
                              <div className="flex items-center gap-2">
                                <Input
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') saveEdit();
                                    if (e.key === 'Escape') cancelEdit();
                                  }}
                                  className="h-8"
                                  autoFocus
                                />
                                <Button size="sm" variant="ghost" onClick={saveEdit}>
                                  <Save className="w-3 h-3" />
                                </Button>
                                <Button size="sm" variant="ghost" onClick={cancelEdit}>
                                  <X className="w-3 h-3" />
                                </Button>
                              </div>
                            ) : (
                              <div 
                                className={`
                                  flex items-center justify-between group
                                  ${editable ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700/50 p-1 rounded' : ''}
                                `}
                                onClick={() => startEdit(rowIndex, column)}
                              >
                                <span className="truncate">
                                  {String(row[column] || '')}
                                </span>
                                {editable && (
                                  <Edit2 className="w-3 h-3 opacity-0 group-hover:opacity-50 flex-shrink-0" />
                                )}
                              </div>
                            )}
                            
                            {cellError && (
                              <div className="mt-1">
                                <Badge variant="destructive" className="text-xs">
                                  {cellError.message}
                                </Badge>
                              </div>
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Showing {startIndex + 1} to {endIndex} of {localData.length} rows
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={goToPreviousPage}
                  disabled={currentPage === 0}
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </Button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: totalPages }, (_, i) => (
                    <Button
                      key={i}
                      variant={currentPage === i ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(i)}
                      className="w-8 h-8 p-0"
                    >
                      {i + 1}
                    </Button>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={goToNextPage}
                  disabled={currentPage === totalPages - 1}
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}