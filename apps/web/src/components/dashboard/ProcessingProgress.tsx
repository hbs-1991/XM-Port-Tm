'use client'

import React from 'react'
import { Clock, Loader2 } from 'lucide-react'
import { Progress } from '@/components/shared/ui'
import { Badge } from '@/components/shared/ui'
import { Card, CardContent } from '@/components/shared/ui'

interface ProcessingProgressProps {
  jobId: string
  fileName: string
  status: string
  progress: number
  message?: string
  className?: string
}

const ProcessingProgress: React.FC<ProcessingProgressProps> = ({
  jobId,
  fileName,
  status,
  progress,
  message,
  className
}) => {
  const getStatusColor = () => {
    switch (status.toLowerCase()) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'processing':
        return 'bg-blue-100 text-blue-800'
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const isActive = ['pending', 'processing'].includes(status.toLowerCase())

  return (
    <Card className={`border-l-4 ${isActive ? 'border-l-blue-500' : 'border-l-gray-300'} ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {isActive && <Loader2 className="h-4 w-4 animate-spin text-blue-500" />}
            <h4 className="font-medium text-sm truncate max-w-[200px]" title={fileName}>
              {fileName}
            </h4>
          </div>
          
          <Badge variant="secondary" className={getStatusColor()}>
            {status}
          </Badge>
        </div>

        {isActive && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{message || 'Processing...'}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            
            <Progress 
              value={progress} 
              className="h-2" 
              aria-label={`Processing progress: ${Math.round(progress)}%`}
            />
          </div>
        )}

        {!isActive && message && (
          <p className="text-xs text-muted-foreground mt-1">{message}</p>
        )}

        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>Job ID: {jobId.slice(0, 8)}</span>
        </div>
      </CardContent>
    </Card>
  )
}

export default ProcessingProgress