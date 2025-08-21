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
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <FileText className="w-4 h-4" />
          Real-time Validation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Section */}
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div className="flex-1">
            <p className="text-sm font-medium">{getStatusMessage()}</p>
            {validationMutation.isPending && (
              <Progress value={65} className="w-full h-2 mt-2" />
            )}
          </div>
          {validationResult && !validationMutation.isPending && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              className="ml-auto"
            >
              <RefreshCw className="w-3 h-3 mr-1" />
              Retry
            </Button>
          )}
        </div>

        {/* Validation Results */}
        {validationResult && !validationMutation.isPending && (
          <div className="space-y-3">
            {/* Summary Stats */}
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">
                {validationResult.total_rows} Total Rows
              </Badge>
              <Badge variant={validationResult.valid_rows === validationResult.total_rows ? "default" : "secondary"}>
                {validationResult.valid_rows} Valid Rows
              </Badge>
              {validationResult.errors.length > 0 && (
                <Badge variant="destructive">
                  {validationResult.errors.length} Error{validationResult.errors.length !== 1 ? 's' : ''}
                </Badge>
              )}
              {validationResult.warnings.length > 0 && (
                <Badge variant="outline" className="border-yellow-500 text-yellow-600">
                  {validationResult.warnings.length} Warning{validationResult.warnings.length !== 1 ? 's' : ''}
                </Badge>
              )}
            </div>

            {/* Data Quality Score */}
            {validationResult.summary && (
              <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <BarChart3 className="w-5 h-5 text-blue-500" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Data Quality Score:</span>
                    <span className={`text-sm font-bold ${getQualityScoreColor(validationResult.summary.data_quality_score)}`}>
                      {Math.round(validationResult.summary.data_quality_score)}%
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {getQualityScoreBadge(validationResult.summary.data_quality_score)}
                    </Badge>
                  </div>
                  <Progress 
                    value={validationResult.summary.data_quality_score} 
                    className="w-full h-2 mt-1"
                  />
                </div>
              </div>
            )}

            {/* Errors */}
            {validationResult.errors.length > 0 && (
              <Alert variant="destructive">
                <AlertCircle className="w-4 h-4" />
                <AlertTitle>Validation Errors</AlertTitle>
                <AlertDescription>
                  <div className="mt-2 space-y-1">
                    {validationResult.errors.slice(0, 3).map((error, index) => (
                      <div key={index} className="text-xs">
                        <strong>{error.field}:</strong> {error.error}
                        {error.row && <span className=" text-gray-500"> (Row {error.row})</span>}
                      </div>
                    ))}
                    {validationResult.errors.length > 3 && (
                      <Button
                        variant="link"
                        size="sm"
                        onClick={() => setShowDetails(!showDetails)}
                        className="p-0 h-auto text-xs underline"
                      >
                        {showDetails ? 'Show Less' : `Show ${validationResult.errors.length - 3} More Errors`}
                      </Button>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Detailed Errors (collapsed by default) */}
            {showDetails && validationResult.errors.length > 3 && (
              <Alert variant="destructive">
                <AlertDescription>
                  <div className="space-y-1">
                    {validationResult.errors.slice(3).map((error, index) => (
                      <div key={index + 3} className="text-xs">
                        <strong>{error.field}:</strong> {error.error}
                        {error.row && <span className=" text-gray-500"> (Row {error.row})</span>}
                      </div>
                    ))}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Warnings */}
            {validationResult.warnings.length > 0 && (
              <Alert>
                <AlertTriangle className="w-4 h-4" />
                <AlertTitle>Warnings</AlertTitle>
                <AlertDescription>
                  <div className="mt-2 space-y-1">
                    {validationResult.warnings.map((warning, index) => (
                      <div key={index} className="text-xs">
                        {warning}
                      </div>
                    ))}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Success Message */}
            {validationResult.valid && validationResult.errors.length === 0 && (
              <Alert>
                <CheckCircle2 className="w-4 h-4" />
                <AlertTitle>Validation Complete</AlertTitle>
                <AlertDescription>
                  Your file is ready for processing. All required columns are present and data validation passed.
                </AlertDescription>
              </Alert>
            )}

            {/* Common Errors Summary */}
            {validationResult.summary?.most_common_errors.length && (
              <Alert>
                <AlertCircle className="w-4 h-4" />
                <AlertTitle>Most Common Issues</AlertTitle>
                <AlertDescription>
                  <div className="mt-2 space-y-1">
                    {validationResult.summary.most_common_errors.slice(0, 3).map((error, index) => (
                      <div key={index} className="text-xs">
                        • {error}
                      </div>
                    ))}
                  </div>
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Loading State */}
        {validationMutation.isPending && (
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-2">
              <Clock className="w-8 h-8 mx-auto text-blue-500 animate-pulse" />
              <p className="text-sm text-gray-500">
                Analyzing your file structure and data...
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}