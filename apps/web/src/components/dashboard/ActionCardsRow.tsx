/**
 * ActionCardsRow component with interactive action cards
 */
'use client'

import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import { Progress } from '@/components/shared/ui/progress'
import {
  Upload,
  BarChart3,
  PieChart as PieChartIcon,
  TrendingUp,
  FileText,
  CheckCircle,
  AlertCircle,
  XCircle,
  RefreshCw
} from 'lucide-react'
import { clsx } from 'clsx'

export interface ActionCardsData {
  upload: {
    allowedTypes: string[];
    maxSize: number;
    isUploading: boolean;
  };
  monthlyOverview: {
    currentMonth: {
      creditsUsed: number;
      jobsCompleted: number;
      avgProcessingTime: number;
    };
    previousMonth: {
      creditsUsed: number;
      jobsCompleted: number;
      avgProcessingTime: number;
    };
    chartData: Array<{
      month: string;
      jobs: number;
      credits: number;
    }>;
  };
  performance: {
    successRate: number;
    totalJobs: number;
    successfulJobs: number;
    failedJobs: number;
    pendingJobs: number;
  };
}

interface ActionCardsRowProps {
  data?: ActionCardsData;
  loading?: boolean;
  className?: string;
  onFileUpload?: (files: File[]) => void;
  onRetry?: () => void;
}

interface QuickUploadCardProps {
  allowedTypes: string[];
  maxSize: number;
  isUploading: boolean;
  onFileUpload?: (files: File[]) => void;
}

interface MonthlyOverviewCardProps {
  currentMonth: ActionCardsData['monthlyOverview']['currentMonth'];
  previousMonth: ActionCardsData['monthlyOverview']['previousMonth'];
  chartData: ActionCardsData['monthlyOverview']['chartData'];
}

interface ProcessingPerformanceCardProps {
  performance: ActionCardsData['performance'];
}

const QuickUploadCard: React.FC<QuickUploadCardProps> = ({
  allowedTypes,
  maxSize,
  isUploading,
  onFileUpload
}) => {
  const [uploadState, setUploadState] = useState<'default' | 'success' | 'error'>('default');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setUploadState('success');
      onFileUpload?.(acceptedFiles);
      // Reset to default after 3 seconds
      setTimeout(() => setUploadState('default'), 3000);
    }
  }, [onFileUpload]);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
    },
    maxSize: maxSize,
    multiple: true,
    disabled: isUploading
  });

  const hasErrors = fileRejections.length > 0;

  const getCardState = () => {
    if (hasErrors) return 'error';
    if (uploadState === 'success') return 'success';
    if (isDragActive) return 'dragActive';
    return 'default';
  };

  const cardState = getCardState();

  const stateStyles = {
    default: 'bg-gradient-to-br from-blue-50 to-purple-50 border-dashed border-2 border-gray-300 hover:border-blue-400',
    dragActive: 'bg-gradient-to-br from-blue-100 to-purple-100 border-solid border-2 border-blue-500 animate-pulse',
    success: 'bg-gradient-to-br from-green-50 to-emerald-50 border-solid border-2 border-green-500',
    error: 'bg-gradient-to-br from-red-50 to-pink-50 border-solid border-2 border-red-500'
  };

  const formatFileSize = (bytes: number) => {
    return `${Math.round(bytes / (1024 * 1024))}MB`;
  };

  return (
    <Card className={clsx(
      'transition-all duration-300 hover:scale-105 hover:shadow-lg cursor-pointer',
      stateStyles[cardState]
    )}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          {cardState === 'success' ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : cardState === 'error' ? (
            <XCircle className="h-5 w-5 text-red-600" />
          ) : isUploading ? (
            <RefreshCw className="h-5 w-5 text-blue-600 animate-spin" />
          ) : (
            <Upload className="h-5 w-5 text-blue-600" />
          )}
          Quick Upload
        </CardTitle>
        <CardDescription>
          {cardState === 'success' ? 'Files uploaded successfully!' :
           cardState === 'error' ? 'Upload failed - please try again' :
           isDragActive ? 'Drop files here to upload' :
           isUploading ? 'Uploading files...' :
           'Drag & drop files or click to browse'}
        </CardDescription>
      </CardHeader>
      <CardContent {...getRootProps()} className="space-y-4">
        <input {...getInputProps()} aria-label="File upload input" />
        
        {isUploading && (
          <div className="space-y-2">
            <Progress value={65} className="h-2" />
            <p className="text-xs text-muted-foreground text-center">
              Processing files... 65% complete
            </p>
          </div>
        )}

        {!isUploading && (
          <>
            <div className="text-center py-6">
              <div className={clsx(
                'mx-auto w-12 h-12 rounded-full flex items-center justify-center mb-3',
                cardState === 'success' ? 'bg-green-100' :
                cardState === 'error' ? 'bg-red-100' :
                isDragActive ? 'bg-blue-100' : 'bg-gray-100'
              )}>
                {cardState === 'success' ? (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                ) : cardState === 'error' ? (
                  <XCircle className="h-6 w-6 text-red-600" />
                ) : (
                  <Upload className={clsx(
                    'h-6 w-6',
                    isDragActive ? 'text-blue-600' : 'text-gray-500'
                  )} />
                )}
              </div>
              
              <Button 
                variant="outline" 
                size="sm" 
                disabled={isUploading}
                className="h-8"
              >
                <FileText className="mr-2 h-4 w-4" />
                Browse Files
              </Button>
            </div>

            <div className="text-xs text-muted-foreground space-y-1">
              <p>Supported: {allowedTypes.join(', ')}</p>
              <p>Max size: {formatFileSize(maxSize)} per file</p>
              {hasErrors && (
                <p className="text-red-600">
                  {fileRejections[0]?.errors[0]?.message}
                </p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};

const MonthlyOverviewCard: React.FC<MonthlyOverviewCardProps> = ({
  currentMonth,
  previousMonth,
  chartData
}) => {
  const creditsChange = currentMonth.creditsUsed - previousMonth.creditsUsed;
  const jobsChange = currentMonth.jobsCompleted - previousMonth.jobsCompleted;
  const timeChange = currentMonth.avgProcessingTime - previousMonth.avgProcessingTime;

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    return `${Math.round(seconds / 60)}m`;
  };

  const getTrendIcon = (change: number) => {
    return change > 0 ? (
      <TrendingUp className="h-4 w-4 text-green-600" />
    ) : change < 0 ? (
      <TrendingUp className="h-4 w-4 text-red-600 rotate-180" />
    ) : (
      <div className="h-4 w-4 bg-gray-400 rounded-full" />
    );
  };

  return (
    <Card className="bg-gradient-to-br from-green-50 to-teal-50 border-0 shadow-md hover:shadow-lg transition-all duration-300 hover:scale-105">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <BarChart3 className="h-5 w-5 text-green-600" />
          Monthly Overview
        </CardTitle>
        <CardDescription>Current vs previous month comparison</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Mini Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <span className="text-lg font-bold text-green-700">
                {currentMonth.creditsUsed}
              </span>
              {getTrendIcon(creditsChange)}
            </div>
            <p className="text-xs text-muted-foreground">Credits Used</p>
            <p className="text-xs text-green-600">
              {creditsChange > 0 ? '+' : ''}{creditsChange} from last month
            </p>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <span className="text-lg font-bold text-green-700">
                {currentMonth.jobsCompleted}
              </span>
              {getTrendIcon(jobsChange)}
            </div>
            <p className="text-xs text-muted-foreground">Jobs Done</p>
            <p className="text-xs text-green-600">
              {jobsChange > 0 ? '+' : ''}{jobsChange} from last month
            </p>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <span className="text-lg font-bold text-green-700">
                {formatTime(currentMonth.avgProcessingTime)}
              </span>
              {getTrendIcon(-timeChange)} {/* Negative because lower time is better */}
            </div>
            <p className="text-xs text-muted-foreground">Avg Time</p>
            <p className="text-xs text-green-600">
              {timeChange < 0 ? '' : '+'}{Math.round(timeChange / 60)}m vs last month
            </p>
          </div>
        </div>

        {/* Chart */}
        <div className="h-32">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e7ff" />
              <XAxis 
                dataKey="month" 
                tick={{ fontSize: 10 }}
                stroke="#6b7280"
              />
              <YAxis hide />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '12px'
                }}
                formatter={(value, name) => [
                  value,
                  name === 'jobs' ? 'Jobs' : 'Credits'
                ]}
              />
              <Bar 
                dataKey="jobs" 
                fill="url(#greenGradient)" 
                radius={[2, 2, 0, 0]}
              />
              <defs>
                <linearGradient id="greenGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#059669" />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

const ProcessingPerformanceCard: React.FC<ProcessingPerformanceCardProps> = ({
  performance
}) => {
  const pieData = [
    { name: 'Successful', value: performance.successfulJobs, color: '#10b981' },
    { name: 'Failed', value: performance.failedJobs, color: '#ef4444' },
    { name: 'Pending', value: performance.pendingJobs, color: '#f59e0b' },
  ];

  const RADIAN = Math.PI / 180;
  const renderCustomizedLabel = ({
    cx, cy, midAngle, innerRadius, outerRadius, percent
  }: any) => {
    if (percent < 0.05) return null; // Don't show labels for very small segments
    
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        fontSize="12"
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card className="bg-gradient-to-br from-orange-50 to-red-50 border-0 shadow-md hover:shadow-lg transition-all duration-300 hover:scale-105">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <PieChartIcon className="h-5 w-5 text-orange-600" />
          Processing Performance
        </CardTitle>
        <CardDescription>Job completion and success rates</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Center Performance Score */}
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-700">
            {performance.successRate.toFixed(1)}%
          </div>
          <p className="text-sm text-muted-foreground">Overall Success Rate</p>
        </div>

        {/* Donut Chart */}
        <div className="h-32 relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderCustomizedLabel}
                outerRadius={45}
                innerRadius={25}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '12px'
                }}
                formatter={(value: number) => [value, 'Jobs']}
              />
            </PieChart>
          </ResponsiveContainer>
          
          {/* Center Label */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-xs font-semibold text-orange-700">
                {performance.totalJobs}
              </div>
              <div className="text-xs text-muted-foreground">
                Total
              </div>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex justify-center space-x-4">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-xs text-muted-foreground">Success</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span className="text-xs text-muted-foreground">Failed</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
            <span className="text-xs text-muted-foreground">Pending</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export const ActionCardsRow: React.FC<ActionCardsRowProps> = ({
  data,
  loading = false,
  className = '',
  onFileUpload,
  onRetry
}) => {
  if (loading || !data) {
    return <ActionCardsRowSkeleton className={className} />;
  }

  return (
    <div 
      className={clsx(
        'grid gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3',
        className
      )}
      role="region"
      aria-label="Interactive action cards"
    >
      <QuickUploadCard
        allowedTypes={data.upload.allowedTypes}
        maxSize={data.upload.maxSize}
        isUploading={data.upload.isUploading}
        onFileUpload={onFileUpload}
      />
      
      <MonthlyOverviewCard
        currentMonth={data.monthlyOverview.currentMonth}
        previousMonth={data.monthlyOverview.previousMonth}
        chartData={data.monthlyOverview.chartData}
      />
      
      <ProcessingPerformanceCard
        performance={data.performance}
      />
    </div>
  );
};

export const ActionCardsRowSkeleton: React.FC<{ className?: string }> = ({ 
  className = '' 
}) => {
  return (
    <div 
      className={clsx(
        'grid gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3',
        className
      )}
      role="status"
      aria-label="Loading action cards"
    >
      {Array.from({ length: 3 }).map((_, index) => (
        <Card key={index} className="animate-pulse">
          <CardHeader>
            <div className="flex items-center space-x-2">
              <div className="h-5 w-5 bg-gray-300 rounded"></div>
              <div className="h-5 bg-gray-300 rounded w-1/2"></div>
            </div>
            <div className="h-4 bg-gray-300 rounded w-3/4"></div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="h-24 bg-gray-300 rounded"></div>
            <div className="space-y-2">
              <div className="h-3 bg-gray-300 rounded w-full"></div>
              <div className="h-3 bg-gray-300 rounded w-2/3"></div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default ActionCardsRow;