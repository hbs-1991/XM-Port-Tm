'use client';

import React, { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/shared/ui/card';
import { Button } from '@/components/shared/ui/button';
import { Progress } from '@/components/shared/ui/progress';
import { Badge } from '@/components/shared/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/shared/ui/alert';
import { 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle, 
  Clock, 
  FileText,
  BarChart3,
  RefreshCw
} from 'lucide-react';
import { validateFile } from '@/services/processing';

interface ValidationError {
  field: string;
  error: string;
  row?: number;
  column?: string;
}

interface ValidationSummary {
  total_errors: number;
  total_warnings: number;
  errors_by_field: Record<string, number>;
  errors_by_type: Record<string, number>;
  most_common_errors: string[];
  data_quality_score: number;
}

interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: string[];
  total_rows: number;
  valid_rows: number;
  summary?: ValidationSummary;
  previewData?: any[];
}

interface UploadValidationProps {
  file: File;
  onValidationComplete?: (result: ValidationResult) => void;
  onRetry?: () => void;
  className?: string;
}

export function UploadValidation({ 
  file, 
  onValidationComplete, 
  onRetry,
  className = "" 
}: UploadValidationProps) {
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const validationMutation = useMutation({
    mutationFn: validateFile,
    onSuccess: (result) => {
      setValidationResult(result);
      onValidationComplete?.(result);
    },
    onError: (error: any) => {
      console.error('Validation error:', error);
      const errorResult: ValidationResult = {
        valid: false,
        errors: [{
          field: 'file',
          error: error.message || 'Validation failed'
        }],
        warnings: [],
        total_rows: 0,
        valid_rows: 0
      };
      setValidationResult(errorResult);
      onValidationComplete?.(errorResult);
    }
  });

  // Auto-validate on file change
  React.useEffect(() => {
    if (file) {
      setValidationResult(null);
      validationMutation.mutate(file);
    }
  }, [file]);

  const handleRetry = useCallback(() => {
    setValidationResult(null);
    validationMutation.mutate(file);
    onRetry?.();
  }, [file, validationMutation, onRetry]);

  const getStatusIcon = () => {
    if (validationMutation.isPending) {
      return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
    }
    if (validationResult?.valid) {
      return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    }
    if (validationResult?.errors.length) {
      return <AlertCircle className="w-5 h-5 text-red-500" />;
    }
    return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
  };

  const getStatusMessage = () => {
    if (validationMutation.isPending) {
      return 'Validating file...';
    }
    if (validationResult?.valid) {
      return `File validation successful! ${validationResult.valid_rows} of ${validationResult.total_rows} rows are valid.`;
    }
    if (validationResult?.errors.length) {
      return `Validation failed with ${validationResult.errors.length} error(s).`;
    }
    return 'File validation completed with warnings.';
  };

  const getQualityScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getQualityScoreBadge = (score: number) => {
    if (score >= 90) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Fair';
    return 'Poor';
  };

  return (
    <div className={`${className}`}>
      {/* Loading State */}
      {validationMutation.isPending && (
        <div className="flex items-center gap-2 py-2 px-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <Clock className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
          <span className="text-sm text-blue-700 dark:text-blue-300">Validating file...</span>
          <Progress value={65} className="w-16 h-1.5 ml-auto" />
        </div>
      )}

      {/* Compact Success State - Single Line */}
      {validationResult?.valid && validationResult.errors.length === 0 && !validationMutation.isPending && (
        <div className="flex items-center gap-2 py-2 px-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
          <span className="text-sm text-green-700 dark:text-green-300 flex-1">
            File validation successful! {validationResult.valid_rows} of {validationResult.total_rows} rows are valid.
          </span>
          {validationResult.summary && (
            <div className="flex items-center gap-1">
              <BarChart3 className="w-3 h-3 text-green-500" />
              <span className="text-xs font-medium text-green-600 dark:text-green-400">
                {Math.round(validationResult.summary.data_quality_score)}%
              </span>
              <Badge variant="outline" className="text-xs border-green-300 text-green-600 dark:border-green-700 dark:text-green-400">
                {getQualityScoreBadge(validationResult.summary.data_quality_score)}
              </Badge>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRetry}
            className="h-6 w-6 p-0 text-green-600 hover:text-green-700 hover:bg-green-100 dark:hover:bg-green-900/40"
          >
            <RefreshCw className="w-3 h-3" />
          </Button>
        </div>
      )}

      {/* Compact Error State - Single Line with Expandable Details */}
      {validationResult?.errors && validationResult.errors.length > 0 && !validationMutation.isPending && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 py-2 px-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
            <span className="text-sm text-red-700 dark:text-red-300 flex-1">
              Validation failed with {validationResult.errors.length} error{validationResult.errors.length !== 1 ? 's' : ''}.
            </span>
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs border-red-300 text-red-600 dark:border-red-700 dark:text-red-400">
                {validationResult.valid_rows}/{validationResult.total_rows} valid
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDetails(!showDetails)}
                className="h-6 px-2 text-xs text-red-600 hover:text-red-700 hover:bg-red-100 dark:hover:bg-red-900/40"
              >
                {showDetails ? 'Less' : 'Details'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRetry}
                className="h-6 w-6 p-0 text-red-600 hover:text-red-700 hover:bg-red-100 dark:hover:bg-red-900/40"
              >
                <RefreshCw className="w-3 h-3" />
              </Button>
            </div>
          </div>

          {/* Expandable Error Details */}
          {showDetails && (
            <div className="ml-6 space-y-1 p-3 bg-red-50 dark:bg-red-900/10 rounded border border-red-200 dark:border-red-800">
              {validationResult.errors.slice(0, 5).map((error, index) => (
                <div key={index} className="text-xs text-red-600 dark:text-red-400">
                  <strong>{error.field}:</strong> {error.error}
                  {error.row && <span className="text-red-500/70"> (Row {error.row})</span>}
                </div>
              ))}
              {validationResult.errors.length > 5 && (
                <div className="text-xs text-red-500 dark:text-red-400 italic">
                  ... and {validationResult.errors.length - 5} more errors
                </div>
              )}
              {validationResult.summary?.most_common_errors && validationResult.summary.most_common_errors.length > 0 && (
                <div className="mt-2 pt-2 border-t border-red-200 dark:border-red-800">
                  <div className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">Common issues:</div>
                  {validationResult.summary.most_common_errors.slice(0, 3).map((error, index) => (
                    <div key={index} className="text-xs text-red-600 dark:text-red-400">
                      • {error}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Compact Warning State - Single Line */}
      {validationResult?.warnings && validationResult.warnings.length > 0 && validationResult.errors && validationResult.errors.length === 0 && !validationMutation.isPending && (
        <div className="flex items-center gap-2 py-2 px-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
          <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0" />
          <span className="text-sm text-yellow-700 dark:text-yellow-300 flex-1">
            File validation completed with {validationResult.warnings.length} warning{validationResult.warnings.length !== 1 ? 's' : ''}.
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
            className="h-6 px-2 text-xs text-yellow-600 hover:text-yellow-700 hover:bg-yellow-100 dark:hover:bg-yellow-900/40"
          >
            {showDetails ? 'Less' : 'Details'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRetry}
            className="h-6 w-6 p-0 text-yellow-600 hover:text-yellow-700 hover:bg-yellow-100 dark:hover:bg-yellow-900/40"
          >
            <RefreshCw className="w-3 h-3" />
          </Button>
        </div>
      )}
    </div>
  );
}