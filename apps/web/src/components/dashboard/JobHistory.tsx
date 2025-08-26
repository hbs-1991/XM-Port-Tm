'use client'

import React, { useState, useEffect } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/shared/ui'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/shared/ui'
import { Input } from '@/components/shared/ui'
import { Button } from '@/components/shared/ui'
import { Badge } from '@/components/shared/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/shared/ui'
import { 
  Search, 
  Filter, 
  Download, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Calendar
} from 'lucide-react'
import { format } from 'date-fns'
import { ProcessingJob, ProcessingStatus } from '@shared/types/processing'

interface JobHistoryProps {
  className?: string
}

interface ProcessingJobsResponse {
  jobs: ProcessingJob[]
  pagination: {
    page: number
    limit: number
    total_count: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
  }
  filters: {
    search?: string
    status?: string
    date_from?: string
    date_to?: string
  }
}

const statusConfig = {
  [ProcessingStatus.PENDING]: { 
    label: 'Pending', 
    color: 'bg-yellow-100 text-yellow-800', 
    icon: Clock 
  },
  [ProcessingStatus.PROCESSING]: { 
    label: 'Processing', 
    color: 'bg-blue-100 text-blue-800', 
    icon: Clock 
  },
  [ProcessingStatus.COMPLETED]: { 
    label: 'Completed', 
    color: 'bg-green-100 text-green-800', 
    icon: CheckCircle2 
  },
  [ProcessingStatus.COMPLETED_WITH_ERRORS]: { 
    label: 'Completed with Errors', 
    color: 'bg-orange-100 text-orange-800', 
    icon: AlertCircle 
  },
  [ProcessingStatus.FAILED]: { 
    label: 'Failed', 
    color: 'bg-red-100 text-red-800', 
    icon: XCircle 
  },
  [ProcessingStatus.CANCELLED]: { 
    label: 'Cancelled', 
    color: 'bg-gray-100 text-gray-800', 
    icon: XCircle 
  }
}

const JobHistory: React.FC<JobHistoryProps> = ({ className }) => {
  const [jobs, setJobs] = useState<ProcessingJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [totalCount, setTotalCount] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)
  
  // Filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  
  // Applied filters (for API calls)
  const [appliedFilters, setAppliedFilters] = useState({
    search: '',
    status: '',
    date_from: '',
    date_to: ''
  })

  const fetchJobs = async (page: number = 1, filters = appliedFilters) => {
    try {
      setLoading(true)
      setError(null)
      
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '50'
      })
      
      if (filters.search) params.append('search', filters.search)
      if (filters.status) params.append('status', filters.status)
      if (filters.date_from) params.append('date_from', filters.date_from)
      if (filters.date_to) params.append('date_to', filters.date_to)
      
      const response = await fetch(`/api/proxy/processing/jobs?${params}`, {
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to fetch processing jobs')
      }
      
      const data: ProcessingJobsResponse = await response.json()
      
      setJobs(data.jobs)
      setCurrentPage(data.pagination.page)
      setTotalPages(data.pagination.total_pages)
      setTotalCount(data.pagination.total_count)
      setHasNext(data.pagination.has_next)
      setHasPrev(data.pagination.has_prev)
      
    } catch (err) {
      console.error('Error fetching jobs:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch processing jobs')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    const filters = {
      search: searchQuery.trim(),
      status: statusFilter,
      date_from: dateFrom,
      date_to: dateTo
    }
    setAppliedFilters(filters)
    fetchJobs(1, filters)
  }

  const handleClearFilters = () => {
    setSearchQuery('')
    setStatusFilter('')
    setDateFrom('')
    setDateTo('')
    const emptyFilters = { search: '', status: '', date_from: '', date_to: '' }
    setAppliedFilters(emptyFilters)
    fetchJobs(1, emptyFilters)
  }

  const handlePageChange = (page: number) => {
    fetchJobs(page, appliedFilters)
  }

  const handleDownload = async (jobId: string, fileName: string) => {
    try {
      const response = await fetch(`/api/proxy/xml-generation/${jobId}/download`, {
        credentials: 'include'
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to download file')
      }
      
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${fileName}_processed.xml`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Download error:', err)
      alert(err instanceof Error ? err.message : 'Failed to download file')
    }
  }

  const formatProcessingTime = (timeMs: number | null) => {
    if (!timeMs) return 'N/A'
    
    if (timeMs < 1000) {
      return `${timeMs}ms`
    } else if (timeMs < 60000) {
      return `${(timeMs / 1000).toFixed(1)}s`
    } else {
      const minutes = Math.floor(timeMs / 60000)
      const seconds = ((timeMs % 60000) / 1000).toFixed(0)
      return `${minutes}m ${seconds}s`
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  useEffect(() => {
    fetchJobs()
  }, [])

  const StatusBadge: React.FC<{ status: ProcessingStatus }> = ({ status }) => {
    const config = statusConfig[status] || statusConfig[ProcessingStatus.PENDING]
    const Icon = config.icon
    
    return (
      <Badge variant="secondary" className={config.color}>
        <Icon className="mr-1 h-3 w-3" />
        {config.label}
      </Badge>
    )
  }

  if (loading && jobs.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Processing History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center p-8">
            <div className="text-center">
              <div className="animate-spin h-8 w-8 border-b-2 border-primary mx-auto mb-4" role="progressbar" aria-label="Loading"></div>
              <p className="text-muted-foreground">Loading processing history...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Processing History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center p-8">
            <div className="text-center">
              <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
              <p className="text-red-600 font-medium">Error loading jobs</p>
              <p className="text-sm text-muted-foreground mt-2">{error}</p>
              <Button 
                onClick={() => fetchJobs()} 
                variant="outline" 
                size="sm" 
                className="mt-4"
              >
                Try Again
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Processing History</CardTitle>
        <div className="flex flex-col gap-4 mt-4">
          {/* Search and Filters */}
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by file name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                />
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-2">
              <Select value={statusFilter || 'all'} onValueChange={(value) => setStatusFilter(value === 'all' ? '' : value)}>
                <SelectTrigger className="w-full sm:w-[140px]">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {Object.values(ProcessingStatus).map((status) => (
                    <SelectItem key={status} value={status}>
                      {statusConfig[status]?.label || status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <div className="flex gap-2">
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="date"
                    placeholder="From date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="pl-10 w-full sm:w-[140px]"
                  />
                </div>
                
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="date"
                    placeholder="To date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="pl-10 w-full sm:w-[140px]"
                  />
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-2">
            <Button onClick={handleSearch} className="flex-1 sm:flex-none">
              <Filter className="mr-2 h-4 w-4" />
              Apply Filters
            </Button>
            <Button onClick={handleClearFilters} variant="outline" className="flex-1 sm:flex-none">
              Clear Filters
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {jobs.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground">No processing jobs found</p>
            {(appliedFilters.search || appliedFilters.status || appliedFilters.date_from || appliedFilters.date_to) && (
              <p className="text-sm text-muted-foreground mt-2">
                Try adjusting your filters or clearing them to see more results
              </p>
            )}
          </div>
        ) : (
          <>
            {/* Jobs Table */}
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>File Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Processing Time</TableHead>
                    <TableHead>Products</TableHead>
                    <TableHead>Credits</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{job.input_file_name}</div>
                          <div className="text-sm text-muted-foreground">
                            {formatFileSize(job.input_file_size)} • {job.country_schema}
                          </div>
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <StatusBadge status={job.status as ProcessingStatus} />
                      </TableCell>
                      
                      <TableCell>
                        <div className="text-sm">
                          {format(new Date(job.created_at), 'MMM dd, yyyy')}
                          <div className="text-muted-foreground">
                            {format(new Date(job.created_at), 'HH:mm')}
                          </div>
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <div className="text-sm">
                          {formatProcessingTime(
                            job.processing_time_ms === undefined ? null : job.processing_time_ms
                          )}
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <div className="text-sm">
                          {job.successful_matches}/{job.total_products}
                          {job.average_confidence && (
                            <div className="text-muted-foreground">
                              {(job.average_confidence * 100).toFixed(0)}% avg
                            </div>
                          )}
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <div className="text-sm font-medium">
                          {job.credits_used}
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <div className="flex gap-2">
                          {job.has_xml_output && job.xml_generation_status === 'COMPLETED' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDownload(job.id, job.input_file_name)}
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-muted-foreground">
                  Showing {jobs.length} of {totalCount} jobs
                </div>
                
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={!hasPrev || loading}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  
                  <div className="flex items-center gap-1">
                    <span className="text-sm">
                      Page {currentPage} of {totalPages}
                    </span>
                  </div>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={!hasNext || loading}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default JobHistory