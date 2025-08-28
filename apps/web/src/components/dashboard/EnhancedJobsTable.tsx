/**
 * EnhancedJobsTable component with advanced filtering, search, and real-time updates
 */
'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { format } from 'date-fns'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/shared/ui/table'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import { Input } from '@/components/shared/ui/input'
import { Badge } from '@/components/shared/ui/badge'
import {
  Checkbox,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/shared/ui'
import {
  Search,
  Filter,
  MoreHorizontal,
  Download,
  Trash2,
  RefreshCw,
  Eye,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useDebounce } from '@/hooks/useDebounce'
import { useJobUpdates } from '@/hooks/useJobUpdates'

export interface JobData {
  id: string;
  fileName: string;
  status: 'completed' | 'processing' | 'failed' | 'pending';
  dateCreated: string;
  dateCompleted?: string;
  productsCount: number;
  confidenceScore?: number;
  fileSize: number;
  fileType: string;
  downloadUrl?: string;
  errorMessage?: string;
}

export interface FilterOptions {
  search: string;
  status: string[];
  dateRange: {
    from: Date | null;
    to: Date | null;
  };
  fileTypes: string[];
  sortBy: 'date' | 'name' | 'status' | 'confidence';
  sortOrder: 'asc' | 'desc';
}

export interface BulkActions {
  selectedIds: string[];
  availableActions: Array<{
    id: string;
    label: string;
    icon: React.ReactNode;
    dangerous?: boolean;
  }>;
}

interface EnhancedJobsTableProps {
  jobs?: JobData[];
  loading?: boolean;
  className?: string;
  onJobAction?: (action: string, jobIds: string[]) => void;
  onJobDetails?: (jobId: string) => void;
  onRefresh?: () => void;
}

const ITEMS_PER_PAGE_OPTIONS = [10, 25, 50, 100];

const useWindowSize = () => {
  const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    function handleResize() {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    }

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return windowSize;
};

export const EnhancedJobsTable: React.FC<EnhancedJobsTableProps> = ({
  jobs = [],
  loading = false,
  className = '',
  onJobAction,
  onJobDetails,
  onRefresh
}) => {
  const [filters, setFilters] = useState<FilterOptions>({
    search: '',
    status: [],
    dateRange: { from: null, to: null },
    fileTypes: [],
    sortBy: 'date',
    sortOrder: 'desc'
  });

  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  
  const debouncedSearch = useDebounce(filters.search, 300);
  const { connectionStatus, lastUpdate, updatedJobIds } = useJobUpdates();
  const { width } = useWindowSize();
  
  const isMobile = width < 768;

  // Update jobs when WebSocket update is received
  useEffect(() => {
    if (lastUpdate && onRefresh) {
      onRefresh();
    }
  }, [lastUpdate, onRefresh]);

  // Filter and sort jobs
  const filteredAndSortedJobs = useMemo(() => {
    let filtered = jobs;

    // Search filter
    if (debouncedSearch) {
      filtered = filtered.filter(job =>
        job.fileName.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        job.status.toLowerCase().includes(debouncedSearch.toLowerCase())
      );
    }

    // Status filter
    if (filters.status.length > 0) {
      filtered = filtered.filter(job => filters.status.includes(job.status));
    }

    // File type filter
    if (filters.fileTypes.length > 0) {
      filtered = filtered.filter(job => filters.fileTypes.includes(job.fileType));
    }

    // Date range filter
    if (filters.dateRange.from || filters.dateRange.to) {
      filtered = filtered.filter(job => {
        const jobDate = new Date(job.dateCreated);
        const fromDate = filters.dateRange.from;
        const toDate = filters.dateRange.to;
        
        if (fromDate && jobDate < fromDate) return false;
        if (toDate && jobDate > toDate) return false;
        
        return true;
      });
    }

    // Sort
    filtered.sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (filters.sortBy) {
        case 'name':
          aValue = a.fileName;
          bValue = b.fileName;
          break;
        case 'status':
          aValue = a.status;
          bValue = b.status;
          break;
        case 'confidence':
          aValue = a.confidenceScore || 0;
          bValue = b.confidenceScore || 0;
          break;
        case 'date':
        default:
          aValue = new Date(a.dateCreated).getTime();
          bValue = new Date(b.dateCreated).getTime();
          break;
      }

      if (aValue < bValue) return filters.sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return filters.sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [jobs, debouncedSearch, filters]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedJobs.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedJobs = filteredAndSortedJobs.slice(startIndex, startIndex + itemsPerPage);

  // Reset pagination when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedSearch, filters.status, filters.fileTypes]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      completed: "default",
      processing: "secondary",
      failed: "destructive",
      pending: "outline",
    };

    return (
      <Badge variant={variants[status] || "outline"} className="capitalize">
        {status}
      </Badge>
    );
  };

  const formatFileSize = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const handleSelectAll = (checked: boolean | 'indeterminate') => {
    if (checked === true) {
      setSelectedJobs(new Set(paginatedJobs.map(job => job.id)));
    } else {
      setSelectedJobs(new Set());
    }
  };

  const handleSelectJob = (jobId: string, checked: boolean) => {
    const newSelected = new Set(selectedJobs);
    if (checked) {
      newSelected.add(jobId);
    } else {
      newSelected.delete(jobId);
    }
    setSelectedJobs(newSelected);
  };

  const handleBulkAction = (action: string) => {
    if (selectedJobs.size > 0 && onJobAction) {
      onJobAction(action, Array.from(selectedJobs));
      setSelectedJobs(new Set());
    }
  };

  const handleJobAction = (action: string, jobId: string) => {
    if (onJobAction) {
      onJobAction(action, [jobId]);
    }
  };

  const clearFilter = (filterType: string) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: filterType === 'status' || filterType === 'fileTypes' ? [] : ''
    }));
  };

  const activeFiltersCount = [
    filters.search,
    ...filters.status,
    ...filters.fileTypes
  ].filter(Boolean).length;

  if (loading) {
    return <EnhancedJobsTableSkeleton className={className} />;
  }

  const renderMobileCard = (job: JobData) => {
    const isUpdated = updatedJobIds.has(job.id);
    const isSelected = selectedJobs.has(job.id);

    return (
      <Card 
        key={job.id} 
        className={clsx(
          'transition-all duration-300',
          isUpdated && 'ring-2 ring-blue-500 animate-pulse',
          isSelected && 'ring-2 ring-primary'
        )}
      >
        <CardContent className="p-4">
          <div className="space-y-3">
            {/* Header with checkbox and status */}
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-2">
                <Checkbox
                  checked={isSelected}
                  onCheckedChange={(checked: boolean | 'indeterminate') => handleSelectJob(job.id, checked === true)}
                  aria-label={`Select ${job.fileName}`}
                />
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium truncate">{job.fileName}</h4>
                  <p className="text-xs text-muted-foreground">
                    {format(new Date(job.dateCreated), 'MMM dd, yyyy HH:mm')}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {getStatusBadge(job.status)}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => onJobDetails?.(job.id)}>
                      <Eye className="mr-2 h-4 w-4" />
                      View Details
                    </DropdownMenuItem>
                    {job.downloadUrl && (
                      <DropdownMenuItem onClick={() => handleJobAction('download', job.id)}>
                        <Download className="mr-2 h-4 w-4" />
                        Download
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem 
                      onClick={() => handleJobAction('delete', job.id)}
                      className="text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {/* Job details */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Products:</span>
                <span className="ml-1 font-medium">{job.productsCount}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Size:</span>
                <span className="ml-1 font-medium">{formatFileSize(job.fileSize)}</span>
              </div>
              {job.confidenceScore && (
                <div>
                  <span className="text-muted-foreground">Confidence:</span>
                  <span className="ml-1 font-medium">{job.confidenceScore.toFixed(1)}%</span>
                </div>
              )}
              <div>
                <span className="text-muted-foreground">Type:</span>
                <span className="ml-1 font-medium">{job.fileType}</span>
              </div>
            </div>

            {/* Error message for failed jobs */}
            {job.status === 'failed' && job.errorMessage && (
              <div className="bg-red-50 border border-red-200 rounded p-2">
                <p className="text-xs text-red-700">{job.errorMessage}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className={clsx('space-y-4', className)} role="region" aria-label="Jobs table">
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Processing Jobs</h3>
          <p className="text-sm text-muted-foreground">
            {filteredAndSortedJobs.length} jobs found
            {activeFiltersCount > 0 && ` (${activeFiltersCount} filters active)`}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={clsx(
            'flex items-center space-x-1 text-xs px-2 py-1 rounded-full',
            connectionStatus.connected 
              ? 'bg-green-100 text-green-700'
              : connectionStatus.reconnecting
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-red-100 text-red-700'
          )}>
            {connectionStatus.connected ? (
              <Wifi className="h-3 w-3" />
            ) : (
              <WifiOff className="h-3 w-3" />
            )}
            <span>
              {connectionStatus.connected 
                ? 'Live'
                : connectionStatus.reconnecting 
                ? 'Connecting...'
                : 'Offline'
              }
            </span>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw className={clsx('h-4 w-4 mr-2', loading && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:space-y-0 sm:space-x-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search jobs..."
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  className="pl-9"
                />
                {filters.search && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                    onClick={() => clearFilter('search')}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </div>
            </div>

            {/* Status Filter */}
            <Select
              value={filters.status.length === 0 ? "all" : filters.status.join(',')}
              onValueChange={(value: string) => setFilters(prev => ({ 
                ...prev, 
                status: value === "all" ? [] : value.split(',') 
              }))}
            >
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>

            {/* Sort */}
            <Select
              value={`${filters.sortBy}-${filters.sortOrder}`}
              onValueChange={(value: string) => {
                const [sortBy, sortOrder] = value.split('-') as [FilterOptions['sortBy'], FilterOptions['sortOrder']];
                setFilters(prev => ({ ...prev, sortBy, sortOrder }));
              }}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date-desc">Newest</SelectItem>
                <SelectItem value="date-asc">Oldest</SelectItem>
                <SelectItem value="name-asc">Name A-Z</SelectItem>
                <SelectItem value="name-desc">Name Z-A</SelectItem>
                <SelectItem value="confidence-desc">High Confidence</SelectItem>
                <SelectItem value="confidence-asc">Low Confidence</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Active Filters */}
          {activeFiltersCount > 0 && (
            <div className="flex flex-wrap gap-2 pt-2">
              {filters.search && (
                <Badge variant="secondary" className="text-xs">
                  Search: {filters.search}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-1 h-4 w-4 p-0 hover:bg-transparent"
                    onClick={() => clearFilter('search')}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              )}
              {filters.status.map(status => (
                <Badge key={status} variant="secondary" className="text-xs capitalize">
                  Status: {status}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-1 h-4 w-4 p-0 hover:bg-transparent"
                    onClick={() => setFilters(prev => ({
                      ...prev,
                      status: prev.status.filter(s => s !== status)
                    }))}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
          )}
        </CardHeader>

        {/* Bulk Actions */}
        {selectedJobs.size > 0 && (
          <CardContent className="pt-0">
            <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
              <span className="text-sm font-medium">
                {selectedJobs.size} job{selectedJobs.size > 1 ? 's' : ''} selected
              </span>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkAction('download')}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkAction('delete')}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedJobs(new Set())}
                >
                  Clear Selection
                </Button>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Table/Cards Content */}
      {filteredAndSortedJobs.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <div className="text-muted-foreground">
              <Search className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">No jobs found</p>
              <p className="text-sm">Try adjusting your search or filter criteria</p>
            </div>
          </CardContent>
        </Card>
      ) : isMobile ? (
        /* Mobile Cards View */
        <div className="space-y-4">
          {paginatedJobs.map(renderMobileCard)}
        </div>
      ) : (
        /* Desktop Table View */
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={paginatedJobs.length > 0 && selectedJobs.size === paginatedJobs.length}
                    onCheckedChange={handleSelectAll}
                    aria-label="Select all jobs"
                  />
                </TableHead>
                <TableHead>File Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Products</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Size</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedJobs.map((job) => {
                const isUpdated = updatedJobIds.has(job.id);
                const isSelected = selectedJobs.has(job.id);

                return (
                  <TableRow 
                    key={job.id} 
                    className={clsx(
                      'transition-all duration-300',
                      isUpdated && 'bg-blue-50 animate-pulse',
                      isSelected && 'bg-muted/50'
                    )}
                  >
                    <TableCell>
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={(checked: boolean | 'indeterminate') => handleSelectJob(job.id, checked === true)}
                        aria-label={`Select ${job.fileName}`}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(job.status)}
                        <div>
                          <p className="font-medium">{job.fileName}</p>
                          <p className="text-sm text-muted-foreground">{job.fileType}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {getStatusBadge(job.status)}
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="text-sm">{format(new Date(job.dateCreated), 'MMM dd, yyyy')}</p>
                        <p className="text-xs text-muted-foreground">{format(new Date(job.dateCreated), 'HH:mm')}</p>
                      </div>
                    </TableCell>
                    <TableCell>{job.productsCount}</TableCell>
                    <TableCell>
                      {job.confidenceScore ? `${job.confidenceScore.toFixed(1)}%` : '-'}
                    </TableCell>
                    <TableCell>{formatFileSize(job.fileSize)}</TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => onJobDetails?.(job.id)}>
                            <Eye className="mr-2 h-4 w-4" />
                            View Details
                          </DropdownMenuItem>
                          {job.downloadUrl && (
                            <DropdownMenuItem onClick={() => handleJobAction('download', job.id)}>
                              <Download className="mr-2 h-4 w-4" />
                              Download
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem 
                            onClick={() => handleJobAction('delete', job.id)}
                            className="text-destructive"
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Card>
          <CardContent className="py-4">
            <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-muted-foreground">Rows per page:</span>
                <Select
                  value={itemsPerPage.toString()}
                  onValueChange={(value: string) => {
                    setItemsPerPage(Number(value));
                    setCurrentPage(1);
                  }}
                >
                  <SelectTrigger className="w-20">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ITEMS_PER_PAGE_OPTIONS.map(option => (
                      <SelectItem key={option} value={option.toString()}>
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-sm text-muted-foreground">
                  Page {currentPage} of {totalPages} ({filteredAndSortedJobs.length} total)
                </span>
                <div className="flex items-center space-x-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                  >
                    <ChevronsLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(totalPages)}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronsRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export const EnhancedJobsTableSkeleton: React.FC<{ className?: string }> = ({ 
  className = '' 
}) => {
  return (
    <div className={clsx('space-y-4', className)} role="status" aria-label="Loading jobs table">
      {/* Header Skeleton */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-6 bg-gray-300 rounded w-32 animate-pulse"></div>
          <div className="h-4 bg-gray-300 rounded w-24 animate-pulse"></div>
        </div>
        <div className="flex items-center space-x-2">
          <div className="h-6 bg-gray-300 rounded w-16 animate-pulse"></div>
          <div className="h-8 bg-gray-300 rounded w-20 animate-pulse"></div>
        </div>
      </div>

      {/* Filters Skeleton */}
      <Card>
        <CardHeader>
          <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:space-y-0 sm:space-x-4">
            <div className="h-10 bg-gray-300 rounded flex-1 animate-pulse"></div>
            <div className="h-10 bg-gray-300 rounded w-32 animate-pulse"></div>
            <div className="h-10 bg-gray-300 rounded w-32 animate-pulse"></div>
          </div>
        </CardHeader>
      </Card>

      {/* Table Skeleton */}
      <Card>
        <div className="p-6 space-y-4">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="flex items-center space-x-4">
              <div className="h-4 w-4 bg-gray-300 rounded animate-pulse"></div>
              <div className="h-4 bg-gray-300 rounded w-1/4 animate-pulse"></div>
              <div className="h-4 bg-gray-300 rounded w-20 animate-pulse"></div>
              <div className="h-4 bg-gray-300 rounded w-24 animate-pulse"></div>
              <div className="h-4 bg-gray-300 rounded w-16 animate-pulse"></div>
              <div className="h-4 bg-gray-300 rounded w-16 animate-pulse"></div>
              <div className="h-4 bg-gray-300 rounded w-20 animate-pulse"></div>
              <div className="h-4 bg-gray-300 rounded w-8 animate-pulse"></div>
            </div>
          ))}
        </div>
      </Card>

      {/* Pagination Skeleton */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="h-4 bg-gray-300 rounded w-24 animate-pulse"></div>
              <div className="h-8 bg-gray-300 rounded w-16 animate-pulse"></div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="h-4 bg-gray-300 rounded w-32 animate-pulse"></div>
              <div className="flex space-x-1">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-8 w-8 bg-gray-300 rounded animate-pulse"></div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EnhancedJobsTable;