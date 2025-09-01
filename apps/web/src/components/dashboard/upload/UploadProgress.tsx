'use client';

import React from 'react';
import { Progress } from '@/components/shared/ui/progress';
import { Button } from '@/components/shared/ui/button';
import { X, Loader2 } from 'lucide-react';

interface UploadProgressProps {
  progress: number;
  fileName: string;
  onCancel?: () => void;
  showCancel?: boolean;
}

export function UploadProgress({ 
  progress, 
  fileName, 
  onCancel,
  showCancel = true 
}: UploadProgressProps) {
  const getProgressLabel = () => {
    if (progress < 20) return 'Validating file...';
    if (progress < 50) return 'Uploading...';
    if (progress < 80) return 'Processing data...';
    if (progress < 95) return 'Finalizing...';
    return 'Complete!';
  };

  const getProgressColor = () => {
    if (progress < 30) return 'bg-blue-500';
    if (progress < 70) return 'bg-green-500';
    if (progress < 90) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {getProgressLabel()}
          </span>
        </div>
        
        {showCancel && onCancel && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-4 h-4" />
            Cancel
          </Button>
        )}
      </div>

      <div className="space-y-2">
        <Progress 
          value={progress} 
          className="w-full"
        />
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>{fileName}</span>
          <span>{Math.round(progress)}%</span>
        </div>
      </div>
    </div>
  );
}