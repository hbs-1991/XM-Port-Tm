'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/shared/ui/dialog';
import { Badge } from '@/components/shared/ui/badge';
import { Button } from '@/components/shared/ui/button';
import { Input } from '@/components/shared/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/shared/ui/table';
import { Progress } from '@/components/shared/ui/progress';
import { Alert, AlertDescription } from '@/components/shared/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/shared/ui/tabs';
import { CheckCircle, XCircle, AlertTriangle, Clock, FileText, BarChart3, Settings, Download, Edit3, Save, X, Loader2 } from 'lucide-react';
import { JobDetailsResponse, ProcessingStatus, ProductMatch } from '@shared/types/processing';

interface JobDetailsProps {
  jobId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface JobDetailsState {
  data: JobDetailsResponse | null;
  loading: boolean;
  error: string | null;
}

interface EditingState {
  isEditing: boolean;
  editingMatches: ProductMatch[];
  hasUnsavedChanges: boolean;
  savingChanges: boolean;
}

export function JobDetails({ jobId, isOpen, onClose }: JobDetailsProps) {
  const [state, setState] = useState<JobDetailsState>({
    data: null,
    loading: false,
    error: null
  });

  const [editingState, setEditingState] = useState<EditingState>({
    isEditing: false,
    editingMatches: [],
    hasUnsavedChanges: false,
    savingChanges: false
  });

  const fetchJobDetails = async () => {
    if (!jobId) return;
    
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const response = await fetch(`/api/proxy/processing/jobs/${jobId}/details`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Failed to fetch job details: ${response.status}`);
      }

      const data: JobDetailsResponse = await response.json();
      setState(prev => ({ ...prev, data, loading: false }));
    } catch (error) {
      console.error('Error fetching job details:', error);
      setState(prev => ({ 
        ...prev, 
        error: error instanceof Error ? error.message : 'Failed to load job details',
        loading: false 
      }));
    }
  };

  useEffect(() => {
    if (isOpen && jobId) {
      fetchJobDetails();
    }
  }, [isOpen, jobId]);

  const handleStartEditing = () => {
    if (!state.data?.product_matches) return;
    
    setEditingState({
      isEditing: true,
      editingMatches: [...state.data.product_matches],
      hasUnsavedChanges: false,
      savingChanges: false
    });
  };

  const handleCancelEditing = () => {
    setEditingState({
      isEditing: false,
      editingMatches: [],
      hasUnsavedChanges: false,
      savingChanges: false
    });
  };

  const handleMatchUpdate = (matchId: string, field: keyof ProductMatch, value: any) => {
    const updatedMatches = editingState.editingMatches.map(match =>
      match.id === matchId ? { ...match, [field]: value } : match
    );
    
    setEditingState(prev => ({
      ...prev,
      editingMatches: updatedMatches,
      hasUnsavedChanges: true
    }));
  };

  const handleSaveChanges = async () => {
    setEditingState(prev => ({ ...prev, savingChanges: true }));
    
    try {
      // Here you would typically send the updated matches to the API
      // For now, we'll just update the local state
      setState(prev => ({
        ...prev,
        data: prev.data ? {
          ...prev.data,
          product_matches: editingState.editingMatches
        } : null
      }));
      
      setEditingState({
        isEditing: false,
        editingMatches: [],
        hasUnsavedChanges: false,
        savingChanges: false
      });
      
      // Show success message
      console.log('Changes saved successfully');
    } catch (error) {
      console.error('Error saving changes:', error);
      setEditingState(prev => ({ ...prev, savingChanges: false }));
    }
  };

  const toggleUserConfirmed = (matchId: string) => {
    const match = editingState.editingMatches.find(m => m.id === matchId);
    if (match) {
      handleMatchUpdate(matchId, 'user_confirmed', !match.user_confirmed);
    }
  };

  const getStatusIcon = (status: ProcessingStatus) => {
    switch (status) {
      case ProcessingStatus.COMPLETED:
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case ProcessingStatus.COMPLETED_WITH_ERRORS:
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case ProcessingStatus.FAILED:
        return <XCircle className="h-4 w-4 text-red-500" />;
      case ProcessingStatus.PROCESSING:
        return <Clock className="h-4 w-4 text-blue-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadgeVariant = (status: ProcessingStatus) => {
    switch (status) {
      case ProcessingStatus.COMPLETED:
        return 'default';
      case ProcessingStatus.COMPLETED_WITH_ERRORS:
        return 'secondary';
      case ProcessingStatus.FAILED:
        return 'destructive';
      case ProcessingStatus.PROCESSING:
        return 'outline';
      default:
        return 'secondary';
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatDuration = (ms: number | null) => {
    if (!ms) return 'N/A';
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const handleDownload = () => {
    // Download functionality will be handled by parent component or service
    console.log('Download XML for job:', jobId);
  };

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Job Details
          </DialogTitle>
        </DialogHeader>

        {state.loading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-2">Loading job details...</span>
          </div>
        )}

        {state.error && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertDescription>{state.error}</AlertDescription>
          </Alert>
        )}

        {state.data && (
          <div className="space-y-6">
            {/* Job Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    {getStatusIcon(state.data.job.status as ProcessingStatus)}
                    {state.data.job.input_file_name}
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge variant={getStatusBadgeVariant(state.data.job.status as ProcessingStatus)}>
                      {state.data.job.status}
                    </Badge>
                    {state.data.job.has_xml_output && (
                      <Button size="sm" onClick={handleDownload} className="gap-2">
                        <Download className="h-4 w-4" />
                        Download XML
                      </Button>
                    )}
                  </div>
                </CardTitle>
                <CardDescription>
                  Created: {new Date(state.data.job.created_at).toLocaleDateString()} at {new Date(state.data.job.created_at).toLocaleTimeString()}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">File Size</p>
                    <p className="font-semibold">{formatFileSize(state.data.job.input_file_size)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Processing Time</p>
                    <p className="font-semibold">{formatDuration(state.data.job.processing_time_ms || null)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Credits Used</p>
                    <p className="font-semibold">{state.data.job.credits_used}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Country Schema</p>
                    <p className="font-semibold">{state.data.job.country_schema}</p>
                  </div>
                </div>

                {state.data.job.error_message && (
                  <Alert variant="destructive" className="mt-4">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>{state.data.job.error_message}</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Processing Statistics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Processing Statistics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-blue-600">{state.data.statistics.total_matches}</p>
                    <p className="text-sm text-muted-foreground">Total Products</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-600">{state.data.statistics.high_confidence_matches}</p>
                    <p className="text-sm text-muted-foreground">High Confidence</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-yellow-600">{state.data.statistics.manual_review_required}</p>
                    <p className="text-sm text-muted-foreground">Need Review</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-purple-600">{state.data.statistics.user_confirmed}</p>
                    <p className="text-sm text-muted-foreground">User Confirmed</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold">{Math.round(state.data.statistics.success_rate)}%</p>
                    <p className="text-sm text-muted-foreground">Success Rate</p>
                  </div>
                </div>

                <div className="mt-4 space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Average Confidence</span>
                      <span>{Math.round((state.data.job.average_confidence || 0) * 100)}%</span>
                    </div>
                    <Progress value={(state.data.job.average_confidence || 0) * 100} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Success Rate</span>
                      <span>{Math.round(state.data.statistics.success_rate)}%</span>
                    </div>
                    <Progress value={state.data.statistics.success_rate} className="h-2" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Product Matches */}
            <Tabs defaultValue="matches" className="w-full">
              <TabsList>
                <TabsTrigger value="matches">Product Matches ({state.data.product_matches.length})</TabsTrigger>
                <TabsTrigger value="high-confidence">High Confidence ({state.data.statistics.high_confidence_matches})</TabsTrigger>
                <TabsTrigger value="review">Need Review ({state.data.statistics.manual_review_required})</TabsTrigger>
              </TabsList>

              <TabsContent value="matches" className="space-y-4">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle>All Product Matches</CardTitle>
                        <CardDescription>Complete list of processed products with HS code assignments</CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        {!editingState.isEditing ? (
                          <Button size="sm" onClick={handleStartEditing} className="gap-2">
                            <Edit3 className="h-4 w-4" />
                            Edit Data
                          </Button>
                        ) : (
                          <div className="flex items-center gap-2">
                            <Button 
                              size="sm" 
                              onClick={handleSaveChanges}
                              disabled={!editingState.hasUnsavedChanges || editingState.savingChanges}
                              className="gap-2"
                            >
                              {editingState.savingChanges ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Save className="h-4 w-4" />
                              )}
                              {editingState.savingChanges ? 'Saving...' : 'Save Changes'}
                            </Button>
                            <Button 
                              size="sm" 
                              variant="outline" 
                              onClick={handleCancelEditing}
                              disabled={editingState.savingChanges}
                              className="gap-2"
                            >
                              <X className="h-4 w-4" />
                              Cancel
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Product Description</TableHead>
                            <TableHead>Quantity</TableHead>
                            <TableHead>Value</TableHead>
                            <TableHead>HS Code</TableHead>
                            <TableHead>Confidence</TableHead>
                            <TableHead>Status</TableHead>
                            {editingState.isEditing && <TableHead>Actions</TableHead>}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(editingState.isEditing ? editingState.editingMatches : state.data.product_matches).map((match) => (
                            <TableRow key={match.id}>
                              <TableCell className="max-w-xs">
                                <div className="truncate" title={match.product_description}>
                                  {match.product_description}
                                </div>
                              </TableCell>
                              <TableCell>
                                {match.quantity} {match.unit_of_measure}
                              </TableCell>
                              <TableCell>${match.value.toFixed(2)}</TableCell>
                              <TableCell>
                                {editingState.isEditing ? (
                                  <Input
                                    value={match.matched_hs_code}
                                    onChange={(e) => handleMatchUpdate(match.id, 'matched_hs_code', e.target.value)}
                                    className="w-32 text-sm font-mono"
                                    placeholder="HS Code"
                                  />
                                ) : (
                                  <code className="bg-muted px-2 py-1 rounded text-sm">
                                    {match.matched_hs_code}
                                  </code>
                                )}
                              </TableCell>
                              <TableCell>
                                <span className={`font-semibold ${getConfidenceColor(match.confidence_score)}`}>
                                  {Math.round(match.confidence_score * 100)}%
                                </span>
                              </TableCell>
                              <TableCell>
                                <div className="flex flex-col gap-1">
                                  {match.requires_manual_review && (
                                    <Badge variant="secondary" className="text-xs">
                                      <AlertTriangle className="h-3 w-3 mr-1" />
                                      Review
                                    </Badge>
                                  )}
                                  <div className="flex items-center gap-2">
                                    {editingState.isEditing ? (
                                      <Button
                                        size="sm"
                                        variant={match.user_confirmed ? "default" : "outline"}
                                        onClick={() => toggleUserConfirmed(match.id)}
                                        className="text-xs h-6"
                                      >
                                        {match.user_confirmed ? (
                                          <>
                                            <CheckCircle className="h-3 w-3 mr-1" />
                                            Confirmed
                                          </>
                                        ) : (
                                          'Confirm'
                                        )}
                                      </Button>
                                    ) : (
                                      match.user_confirmed && (
                                        <Badge variant="default" className="text-xs">
                                          <CheckCircle className="h-3 w-3 mr-1" />
                                          Confirmed
                                        </Badge>
                                      )
                                    )}
                                  </div>
                                </div>
                              </TableCell>
                              {editingState.isEditing && (
                                <TableCell>
                                  <div className="flex flex-col gap-1">
                                    {match.alternative_hs_codes.length > 0 && (
                                      <select
                                        value={match.matched_hs_code}
                                        onChange={(e) => handleMatchUpdate(match.id, 'matched_hs_code', e.target.value)}
                                        className="text-xs border rounded px-2 py-1"
                                      >
                                        <option value={match.matched_hs_code}>Current: {match.matched_hs_code}</option>
                                        {match.alternative_hs_codes.map((code, index) => (
                                          <option key={index} value={code}>
                                            Alt: {code}
                                          </option>
                                        ))}
                                      </select>
                                    )}
                                  </div>
                                </TableCell>
                              )}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="high-confidence">
                <Card>
                  <CardHeader>
                    <CardTitle>High Confidence Matches</CardTitle>
                    <CardDescription>Products with confidence scores ≥ 80%</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Product Description</TableHead>
                            <TableHead>HS Code</TableHead>
                            <TableHead>Confidence</TableHead>
                            <TableHead>Reasoning</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {state.data.product_matches
                            .filter(match => match.confidence_score >= 0.8)
                            .map((match) => (
                              <TableRow key={match.id}>
                                <TableCell className="max-w-xs">
                                  <div className="truncate" title={match.product_description}>
                                    {match.product_description}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <code className="bg-muted px-2 py-1 rounded text-sm">
                                    {match.matched_hs_code}
                                  </code>
                                </TableCell>
                                <TableCell>
                                  <span className="font-semibold text-green-600">
                                    {Math.round(match.confidence_score * 100)}%
                                  </span>
                                </TableCell>
                                <TableCell className="max-w-md">
                                  <div className="text-sm text-muted-foreground truncate" title={match.vector_store_reasoning}>
                                    {match.vector_store_reasoning || 'No reasoning provided'}
                                  </div>
                                </TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="review">
                <Card>
                  <CardHeader>
                    <CardTitle>Requires Manual Review</CardTitle>
                    <CardDescription>Products that need human verification</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Product Description</TableHead>
                            <TableHead>Suggested HS Code</TableHead>
                            <TableHead>Confidence</TableHead>
                            <TableHead>Alternative Codes</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {state.data.product_matches
                            .filter(match => match.requires_manual_review)
                            .map((match) => (
                              <TableRow key={match.id}>
                                <TableCell className="max-w-xs">
                                  <div className="truncate" title={match.product_description}>
                                    {match.product_description}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <code className="bg-muted px-2 py-1 rounded text-sm">
                                    {match.matched_hs_code}
                                  </code>
                                </TableCell>
                                <TableCell>
                                  <span className={`font-semibold ${getConfidenceColor(match.confidence_score)}`}>
                                    {Math.round(match.confidence_score * 100)}%
                                  </span>
                                </TableCell>
                                <TableCell>
                                  <div className="flex flex-wrap gap-1">
                                    {match.alternative_hs_codes.slice(0, 3).map((code, index) => (
                                      <code key={index} className="bg-yellow-100 text-yellow-800 px-1 py-0.5 rounded text-xs">
                                        {code}
                                      </code>
                                    ))}
                                    {match.alternative_hs_codes.length > 3 && (
                                      <span className="text-xs text-muted-foreground">
                                        +{match.alternative_hs_codes.length - 3} more
                                      </span>
                                    )}
                                  </div>
                                </TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        )}

        <div className="flex justify-end pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}