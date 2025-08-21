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
  message: string;
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
  
  const rowsPerPage = 10;
  const totalPages = Math.ceil(localData.length / rowsPerPage);
  const startIndex = currentPage * rowsPerPage;
  const endIndex = Math.min(startIndex + rowsPerPage, localData.length);
  const visibleData = localData.slice(startIndex, endIndex);

  // Get column headers from the first row
  const columns = localData.length > 0 ? Object.keys(localData[0]) : [];
  const requiredColumns = [
    'Product Description',
    'Quantity',
    'Unit',
    'Value', 
    'Origin Country',
    'Unit Price'
  ];

  useEffect(() => {
    validateData();
  }, [localData]);

  const validateData = () => {
    const errors: ValidationError[] = [];
    
    localData.forEach((row, index) => {
      // Check required columns
      requiredColumns.forEach(column => {
        const value = row[column];
        if (!value || (typeof value === 'string' && value.trim() === '')) {
          errors.push({
            row: index,
            column,
            message: 'Required field is empty'
          });
        }
      });

      // Validate numeric fields
      ['Quantity', 'Value', 'Unit Price'].forEach(column => {
        const value = row[column];
        if (value && isNaN(Number(value))) {
          errors.push({
            row: index,
            column,
            message: 'Must be a valid number'
          });
        }
      });

      // Validate positive numeric fields
      ['Quantity', 'Value', 'Unit Price'].forEach(column => {
        const value = Number(row[column]);
        if (value && value <= 0) {
          errors.push({
            row: index,
            column,
            message: 'Must be greater than 0'
          });
        }
      });

      // Cross-field validation: Quantity × Unit Price ≈ Value
      const quantity = Number(row['Quantity']);
      const unitPrice = Number(row['Unit Price']);
      const value = Number(row['Value']);
      
      if (quantity && unitPrice && value) {
        const calculatedValue = quantity * unitPrice;
        const tolerance = Math.max(calculatedValue * 0.001, 0.01); // 0.1% tolerance
        
        if (Math.abs(calculatedValue - value) > tolerance) {
          errors.push({
            row: index,
            column: 'Value',
            message: `Value should be approximately ${calculatedValue.toFixed(2)} (Quantity × Unit Price)`
          });
        }
      }
    });

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
    const baseClasses = 'p-2 text-sm';
    
    if (error) {
      return `${baseClasses} bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800`;
    }
    
    if (!requiredColumns.includes(column)) {
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
                    {columns.map((column) => (
                      <TableHead key={column} className="min-w-32">
                        <div className="flex items-center gap-1">
                          {column}
                          {requiredColumns.includes(column) && (
                            <span className="text-red-500">*</span>
                          )}
                        </div>
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleData.map((row, rowIndex) => (
                    <TableRow key={startIndex + rowIndex}>
                      <TableCell className="text-center text-gray-500 dark:text-gray-400 font-mono text-xs">
                        {startIndex + rowIndex + 1}
                      </TableCell>
                      {columns.map((column) => {
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