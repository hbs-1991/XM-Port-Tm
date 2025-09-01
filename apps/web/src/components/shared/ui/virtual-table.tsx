'use client';

import React, { useMemo, useState, useEffect, useRef, CSSProperties } from 'react';
// Temporarily commented out due to TypeScript compatibility issues
// import * as ReactWindow from 'react-window';

// Define the type locally since import from types doesn't work in build
interface ListChildComponentProps<T = any> {
  index: number;
  style: CSSProperties;
  data: T;
  isScrolling?: boolean;
}
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from './table';

interface VirtualTableProps<T = any> {
  data: T[];
  columns: Array<{
    key: string;
    header: string;
    width?: number;
    render?: (value: any, row: T, rowIndex: number) => React.ReactNode;
  }>;
  height: number;
  rowHeight?: number;
  headerHeight?: number;
  onRowClick?: (row: T, index: number) => void;
  className?: string;
  loading?: boolean;
  emptyMessage?: string;
}

interface RowData<T> {
  data: T[];
  columns: VirtualTableProps<T>['columns'];
  onRowClick?: (row: T, index: number) => void;
}

const VirtualTableRow = React.memo(({ index, style, ...rowData }: any): React.ReactElement | null => {
  const { data, columns, onRowClick } = rowData;
  const row = data[index];
  
  if (!row) return null;
  
  return (
    <div style={style} className="flex border-b">
      {columns.map((column: any, colIndex: number) => {
        const value = row[column.key];
        const cellContent = column.render ? column.render(value, row, index) : String(value || '');
        
        return (
          <div
            key={column.key}
            className={`
              flex-shrink-0 px-3 py-2 text-sm border-r last:border-r-0
              ${onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800' : ''}
            `}
            style={{ width: column.width || 150 }}
            onClick={() => onRowClick?.(row, index)}
          >
            <div className="truncate" title={String(cellContent)}>
              {cellContent}
            </div>
          </div>
        );
      })}
    </div>
  );
});

export function VirtualTable<T = any>({
  data,
  columns,
  height,
  rowHeight = 40,
  headerHeight = 44,
  onRowClick,
  className = '',
  loading = false,
  emptyMessage = 'No data available'
}: VirtualTableProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  
  // Calculate total width needed for all columns
  const totalWidth = useMemo(() => {
    return columns.reduce((sum, col) => sum + (col.width || 150), 0);
  }, [columns]);
  
  // Update container width on mount and resize
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth);
      }
    };
    
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);
  
  // Adjust column widths if container is larger than total width
  const adjustedColumns = useMemo(() => {
    if (containerWidth <= totalWidth) return columns;
    
    // Distribute extra space proportionally
    const extraSpace = containerWidth - totalWidth;
    const flexColumns = columns.filter((col: VirtualTableProps<T>['columns'][0]) => !col.width || col.width < 200);
    const extraPerColumn = flexColumns.length ? extraSpace / flexColumns.length : 0;
    
    return columns.map((col: VirtualTableProps<T>['columns'][0]) => ({
      ...col,
      width: (!col.width || col.width < 200) 
        ? (col.width || 150) + extraPerColumn 
        : col.width
    }));
  }, [columns, containerWidth, totalWidth]);
  
  const rowData: RowData<T> = useMemo(() => ({
    data,
    columns: adjustedColumns,
    onRowClick
  }), [data, adjustedColumns, onRowClick]);
  
  if (loading) {
    return (
      <div 
        className={`border rounded-lg ${className}`}
        style={{ height }}
        ref={containerRef}
      >
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
          <span className="ml-3 text-sm text-muted-foreground">Loading...</span>
        </div>
      </div>
    );
  }
  
  if (!data.length) {
    return (
      <div 
        className={`border rounded-lg ${className}`}
        style={{ height }}
        ref={containerRef}
      >
        <div className="flex items-center justify-center h-full">
          <span className="text-sm text-muted-foreground">{emptyMessage}</span>
        </div>
      </div>
    );
  }
  
  return (
    <div 
      className={`border rounded-lg overflow-hidden ${className}`}
      style={{ height }}
      ref={containerRef}
    >
      {/* Header */}
      <div className="flex bg-muted/50 border-b" style={{ height: headerHeight }}>
        {adjustedColumns.map((column: VirtualTableProps<T>['columns'][0]) => (
          <div
            key={column.key}
            className="flex-shrink-0 px-3 py-2 text-sm font-medium border-r last:border-r-0"
            style={{ width: column.width || 150 }}
          >
            <div className="truncate" title={column.header}>
              {column.header}
            </div>
          </div>
        ))}
      </div>
      
      {/* Virtual scrolling body - using basic scrolling for now */}
      <div style={{ 
        height: height - headerHeight, 
        overflow: 'auto',
        width: Math.max(totalWidth, containerWidth) 
      }}>
        {data.map((row, index) => (
          <VirtualTableRow key={index} index={index} style={{ height: rowHeight }} {...rowData} />
        ))}
      </div>
    </div>
  );
}

// Hook to determine if virtual scrolling should be used
export function useVirtualScrolling(dataLength: number, threshold: number = 100) {
  return {
    shouldUseVirtual: dataLength > threshold,
    isLargeDataset: dataLength > threshold * 2,
    recommendedHeight: Math.min(600, Math.max(300, dataLength * 40))
  };
}