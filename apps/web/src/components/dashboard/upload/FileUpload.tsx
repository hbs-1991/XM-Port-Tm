'use client';

import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/shared/ui/card';
import { Button } from '@/components/shared/ui/button';
import { Progress } from '@/components/shared/ui/progress';
import { Badge } from '@/components/shared/ui/badge';
import { Alert, AlertDescription } from '@/components/shared/ui/alert';
import { Upload, FileText, X, AlertCircle, CheckCircle2 } from 'lucide-react';
import { uploadFile } from '@/services/processing';
import hsMatchingService from '@/services/hsMatching';
import xmlGenerationService from '@/services/xmlGeneration';
import { ProcessingJob, ProcessingStatus } from '@shared/types';
import { FilePreview } from './FilePreview';
import { EditableSpreadsheet } from './EditableSpreadsheet';
import { UploadProgress } from './UploadProgress';
import { UploadValidation } from './UploadValidation';
import { performClientValidation, validateCSVHeaders } from './validation';

interface FileUploadProps {
  onUploadComplete?: (job: ProcessingJob) => void;
  onError?: (error: string) => void;
  countrySchema?: string;
}

interface UploadedFile {
  file: File;
  id: string;
  status: 'pending' | 'validating' | 'validated' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  error?: string;
  job?: ProcessingJob;
  previewData?: any[];
  validationResult?: any;
  xmlGenerating?: boolean;
  xmlDownloadUrl?: string;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_TYPES = {
  'text/csv': ['.csv'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls']
};

export function FileUpload({ onUploadComplete, onError, countrySchema = 'US' }: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onSuccess: (data, variables) => {
      const fileId = variables.fileId;
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                status: 'completed' as const, 
                progress: 100, 
                job: data as ProcessingJob, 
                previewData: data.previewData 
              }
            : f
        )
      );
      onUploadComplete?.(data as ProcessingJob);
    },
    onError: (error: any, variables) => {
      const fileId = variables.fileId;
      const errorMessage = error.response?.data?.message || error.message || 'Upload failed';
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === fileId 
            ? { ...f, status: 'error', error: errorMessage }
            : f
        )
      );
      onError?.(errorMessage);
    }
  });

  // Enhanced file validation with immediate feedback
  const validateFile = useCallback(async (file: File): Promise<string | null> => {
    // Immediate client-side validation
    const clientValidation = performClientValidation(file);
    if (!clientValidation.valid) {
      return clientValidation.errors[0]?.error || 'File validation failed';
    }

    // For CSV files, also check headers
    if (file.name.toLowerCase().endsWith('.csv')) {
      try {
        const headerValidation = await validateCSVHeaders(file);
        if (!headerValidation.hasRequiredColumns) {
          return `Missing required columns: ${headerValidation.missingColumns.join(', ')}`;
        }
        if (headerValidation.warnings.length > 0) {
          console.warn('CSV header validation warnings:', headerValidation.warnings);
        }
      } catch (error) {
        console.warn('Could not validate CSV headers:', error);
      }
    }

    return null;
  }, []);

  // Handle file drop
  const onDrop = useCallback((acceptedFiles: File[]) => {
    acceptedFiles.forEach(async (file) => {
      const validationError = await validateFile(file);
      if (validationError) {
        onError?.(validationError);
        return;
      }

      const fileId = `${file.name}-${Date.now()}`;
      const newFile: UploadedFile = {
        file,
        id: fileId,
        status: 'validating',
        progress: 0
      };

      setUploadedFiles(prev => [...prev, newFile]);
    });
  }, [validateFile, onError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
    onDropAccepted: () => setDragActive(false),
    onDropRejected: () => setDragActive(false)
  });

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleValidationComplete = (fileId: string, result: any) => {
    setUploadedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { 
              ...f, 
              status: result.valid ? 'validated' : 'error',
              validationResult: result,
              error: result.valid ? undefined : 'File validation failed'
            }
          : f
      )
    );
  };

  const initiateUpload = (fileId: string) => {
    const file = uploadedFiles.find(f => f.id === fileId);
    if (!file || !file.validationResult?.valid) return;

    setUploadedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'uploading', progress: 10 }
          : f
      )
    );

    uploadMutation.mutate({
      file: file.file,
      fileId,
      countrySchema,
      onProgress: (progress: number) => {
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === fileId 
              ? { ...f, progress: Math.min(progress, 90) }
              : f
          )
        );
      }
    });
  };

  const retryUpload = (fileId: string) => {
    const file = uploadedFiles.find(f => f.id === fileId);
    if (!file) return;

    setUploadedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'uploading', progress: 10, error: undefined }
          : f
      )
    );

    uploadMutation.mutate({
      file: file.file,
      fileId,
      countrySchema,
      onProgress: (progress: number) => {
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === fileId 
              ? { ...f, progress: Math.min(progress, 90) }
              : f
          )
        );
      }
    });
  };

  const initiateHSMatching = async (jobId: string) => {
    try {
      // Get uploaded file data to create batch matching request
      const file = uploadedFiles.find(f => f.job?.id === jobId);
      if (!file?.previewData) {
        onError?.('No data available for HS matching');
        return;
      }

      // Create batch request from preview data
      const products = file.previewData.map((row: any) => ({
        product_description: row['Product Description'] || '',
        country: countrySchema,
        include_alternatives: true,
        confidence_threshold: 0.7
      }));

      const result = await hsMatchingService.matchBatchProducts({
        products,
        country: countrySchema
      });
      
      console.log('HS matching completed:', result);
      
      // Update the data with HS codes
      const updatedData = file.previewData.map((row: any, index: number) => {
        const match = result[index];
        return {
          ...row,
          'HS Code': match?.primary_match?.hs_code || 'No match',
          'HS Description': match?.primary_match?.code_description || '',
          'Confidence': match?.primary_match?.confidence ? `${(match.primary_match.confidence * 100).toFixed(1)}%` : ''
        };
      });
      
      // Update the file data
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === file.id 
            ? { ...f, previewData: updatedData }
            : f
        )
      );
      
    } catch (error) {
      console.error('Error starting HS matching:', error);
      onError?.('Failed to start HS code matching: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  const initiateXMLGeneration = async (jobId: string) => {
    try {
      const result = await xmlGenerationService.generateXML(jobId, {
        country_schema: countrySchema,
        include_metadata: true,
        validate_output: true
      });
      
      console.log('XML generation started:', result);
      
      if (result.success) {
        // Update the file status to show XML is being generated
        setUploadedFiles(prev => 
          prev.map(f => 
            f.job?.id === jobId 
              ? { ...f, xmlGenerating: true, xmlDownloadUrl: result.download_url }
              : f
          )
        );
        
        // Show success message
        onUploadComplete?.({
          ...result,
          message: 'XML generation started successfully'
        } as any);
      } else {
        throw new Error(result.error_message || 'XML generation failed');
      }
      
    } catch (error) {
      console.error('Error starting XML generation:', error);
      onError?.('Failed to start XML generation: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload Trade Data File
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors max-w-md mx-auto
              ${isDragActive || dragActive 
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' 
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
              }
            `}
          >
            <input {...getInputProps()} ref={fileInputRef} />
            <Upload className="w-8 h-8 mx-auto mb-3 text-gray-400" />
            <p className="text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
              {isDragActive || dragActive 
                ? 'Drop your file here' 
                : 'Drag & drop your file here'
              }
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              or click to select a file
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-4">
              <Badge variant="secondary">CSV</Badge>
              <Badge variant="secondary">XLSX</Badge>
              <Badge variant="secondary">Max 10MB</Badge>
            </div>
            <Button type="button" variant="outline" size="sm">
              Choose File
            </Button>
          </div>

          {/* File Requirements */}
          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <h4 className="font-medium text-sm text-gray-700 dark:text-gray-300 mb-2">
              Required Columns:
            </h4>
            <div className="flex flex-wrap gap-2">
              {[
                'Product Description',
                'Quantity', 
                'Unit',
                'Value',
                'Origin Country',
                'Unit Price'
              ].map(column => (
                <Badge key={column} variant="outline" className="text-xs">
                  {column}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-4">
          {uploadedFiles.map((uploadedFile) => (
            <Card key={uploadedFile.id} className="relative">
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  <FileText className="w-8 h-8 text-blue-500 flex-shrink-0 mt-1" />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                        {uploadedFile.file.name}
                      </h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(uploadedFile.id)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-3">
                      <span>{(uploadedFile.file.size / 1024 / 1024).toFixed(2)} MB</span>
                      <span>{uploadedFile.file.type || 'Unknown type'}</span>
                      <Badge variant={
                        uploadedFile.status === 'completed' ? 'default' :
                        uploadedFile.status === 'error' ? 'destructive' :
                        uploadedFile.status === 'validated' ? 'secondary' :
                        'outline'
                      } className="text-xs">
                        {uploadedFile.status === 'validating' ? 'Validating...' :
                         uploadedFile.status === 'validated' ? 'Validated' :
                         uploadedFile.status === 'uploading' ? 'Uploading...' :
                         uploadedFile.status === 'processing' ? 'Processing...' :
                         uploadedFile.status === 'completed' ? 'Completed' :
                         uploadedFile.status === 'error' ? 'Error' : 'Pending'}
                      </Badge>
                    </div>

                    {/* Real-time Validation */}
                    {(uploadedFile.status === 'validating' || uploadedFile.status === 'validated' || uploadedFile.status === 'error') && (
                      <UploadValidation 
                        file={uploadedFile.file}
                        onValidationComplete={(result) => handleValidationComplete(uploadedFile.id, result)}
                        className="mb-3"
                      />
                    )}

                    {/* Upload Action Button */}
                    {uploadedFile.status === 'validated' && uploadedFile.validationResult?.valid && (
                      <div className="mb-3">
                        <Button
                          onClick={() => initiateUpload(uploadedFile.id)}
                          className="w-full"
                        >
                          Upload File for Processing
                        </Button>
                      </div>
                    )}

                    {/* Upload Progress */}
                    {uploadedFile.status === 'uploading' && (
                      <UploadProgress 
                        progress={uploadedFile.progress}
                        fileName={uploadedFile.file.name}
                        onCancel={() => removeFile(uploadedFile.id)}
                      />
                    )}

                    {/* Status Messages */}
                    {uploadedFile.status === 'completed' && (
                      <Alert className="mb-3">
                        <CheckCircle2 className="w-4 h-4" />
                        <AlertDescription>
                          Upload completed successfully! File processed with{' '}
                          {uploadedFile.job?.total_products || 0} products.
                        </AlertDescription>
                      </Alert>
                    )}

                    {uploadedFile.status === 'error' && (
                      <Alert variant="destructive" className="mb-3">
                        <AlertCircle className="w-4 h-4" />
                        <AlertDescription className="flex items-center justify-between">
                          <span>{uploadedFile.error}</span>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => retryUpload(uploadedFile.id)}
                          >
                            Retry
                          </Button>
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* File Preview and Editable Spreadsheet */}
                    {uploadedFile.previewData && uploadedFile.status === 'completed' && (
                      <div className="mt-4">
                        <EditableSpreadsheet 
                          data={uploadedFile.previewData}
                          fileName={uploadedFile.file.name}
                          jobId={uploadedFile.job?.id}
                          onDataChange={(newData) => {
                            setUploadedFiles(prev => 
                              prev.map(f => 
                                f.id === uploadedFile.id 
                                  ? { ...f, previewData: newData }
                                  : f
                              )
                            );
                          }}
                        />
                        {uploadedFile.job && (
                          <div className="flex gap-3 mt-4">
                            <Button
                              onClick={() => initiateHSMatching(uploadedFile.job?.id!)}
                              className="flex-1 bg-blue-600 hover:bg-blue-700"
                              disabled={!uploadedFile.job}
                            >
                              Start HS Code Matching
                            </Button>
                            <Button
                              onClick={() => initiateXMLGeneration(uploadedFile.job?.id!)}
                              className="flex-1 bg-green-600 hover:bg-green-700"
                              disabled={!uploadedFile.job || uploadedFile.xmlGenerating}
                            >
                              {uploadedFile.xmlGenerating ? 'Generating XML...' : 'Generate XML'}
                            </Button>
                          </div>
                        )}
                        {uploadedFile.xmlDownloadUrl && (
                          <div className="mt-2">
                            <Button
                              onClick={() => window.open(uploadedFile.xmlDownloadUrl, '_blank')}
                              variant="outline"
                              className="w-full"
                            >
                              Download XML File
                            </Button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}