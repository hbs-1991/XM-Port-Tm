"""
Pydantic schemas for HS code matching API endpoints
"""
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field

from ..services.hs_matching_service import HSCodeMatchRequest, HSCodeBatchMatchRequest
from ..core.openai_config import HSCodeMatchResult


class HSCodeMatchRequestAPI(BaseModel):
    """API request schema for single HS code matching"""
    product_description: str = Field(
        ..., 
        min_length=5, 
        max_length=500, 
        description="Product description to match against HS codes",
        example="Organic cotton t-shirt made in Turkey"
    )
    country: str = Field(
        default="default", 
        description="Country code for specific HS code variations",
        example="turkmenistan"
    )
    include_alternatives: bool = Field(
        default=True, 
        description="Whether to include alternative HS code matches"
    )
    confidence_threshold: float = Field(
        default=0.7, 
        ge=0.0, 
        le=1.0, 
        description="Minimum confidence threshold for matches"
    )


class HSCodeBatchMatchRequestAPI(BaseModel):
    """API request schema for batch HS code matching"""
    products: List[HSCodeMatchRequestAPI] = Field(
        ..., 
        min_items=1, 
        max_items=100, 
        description="List of products to match (1-100 items)"
    )
    country: str = Field(
        default="default", 
        description="Default country code for all products if not specified individually"
    )


class HSCodeSearchRequest(BaseModel):
    """API request schema for HS code search"""
    query: str = Field(
        ..., 
        min_length=2, 
        max_length=200, 
        description="Search query for HS codes",
        example="textile"
    )
    limit: int = Field(
        default=10, 
        ge=1, 
        le=50, 
        description="Maximum number of results to return"
    )
    country: str = Field(
        default="default", 
        description="Country code for specific HS code variations"
    )


class HSCodeMatchResponse(BaseModel):
    """API response schema for single HS code matching"""
    success: bool = Field(..., description="Whether the matching was successful")
    data: Optional[HSCodeMatchResult] = Field(None, description="Matching result data")
    error: Optional[str] = Field(None, description="Error message if matching failed")
    processing_time_ms: float = Field(..., description="API processing time in milliseconds")


class HSCodeBatchMatchResponse(BaseModel):
    """API response schema for batch HS code matching"""
    success: bool = Field(..., description="Whether the batch matching was successful")
    data: Optional[List[HSCodeMatchResult]] = Field(None, description="List of matching results")
    error: Optional[str] = Field(None, description="Error message if batch matching failed")
    processing_time_ms: float = Field(..., description="API processing time in milliseconds")
    total_processed: int = Field(..., description="Total number of products processed")
    successful_matches: int = Field(..., description="Number of successful matches")


class HSCodeSearchResult(BaseModel):
    """HS code search result item"""
    hs_code: str = Field(..., description="HS code identifier")
    description: str = Field(..., description="HS code description")
    chapter: str = Field(..., description="HS chapter")
    section: str = Field(..., description="HS section")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Search relevance score")


class HSCodeSearchResponse(BaseModel):
    """API response schema for HS code search"""
    success: bool = Field(..., description="Whether the search was successful")
    data: Optional[List[HSCodeSearchResult]] = Field(None, description="Search results")
    error: Optional[str] = Field(None, description="Error message if search failed")
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results found")
    processing_time_ms: float = Field(..., description="Search processing time in milliseconds")


class HealthCheckResponse(BaseModel):
    """API response schema for health check"""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Health check timestamp")
    openai_response_time_ms: Optional[float] = Field(None, description="OpenAI API response time")
    cache_available: bool = Field(..., description="Whether cache service is available")
    configuration: dict = Field(..., description="Service configuration details")


class CacheStatsResponse(BaseModel):
    """API response schema for cache statistics"""
    cache_available: bool = Field(..., description="Whether cache service is available")
    statistics: dict = Field(..., description="Cache performance statistics")
    timestamp: str = Field(..., description="Statistics timestamp")


class CacheOperationResponse(BaseModel):
    """API response schema for cache operations"""
    success: bool = Field(..., description="Whether the operation was successful")
    operation: str = Field(..., description="Type of cache operation performed")
    details: dict = Field(..., description="Operation details and results")
    timestamp: str = Field(..., description="Operation timestamp")


# Analytics response schemas

class MatchingMetricsResponse(BaseModel):
    """API response schema for matching metrics"""
    success: bool = Field(..., description="Whether metrics retrieval was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Matching metrics data")
    error: Optional[str] = Field(None, description="Error message if retrieval failed")
    period_days: int = Field(..., description="Number of days analyzed")
    timestamp: str = Field(..., description="Metrics timestamp")


class UsageAnalyticsResponse(BaseModel):
    """API response schema for usage analytics"""
    success: bool = Field(..., description="Whether analytics retrieval was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Usage analytics data")
    error: Optional[str] = Field(None, description="Error message if retrieval failed")
    period_days: int = Field(..., description="Number of days analyzed")
    timestamp: str = Field(..., description="Analytics timestamp")


class PerformanceMetricsResponse(BaseModel):
    """API response schema for performance metrics"""
    success: bool = Field(..., description="Whether metrics retrieval was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Performance metrics data")
    error: Optional[str] = Field(None, description="Error message if retrieval failed")
    period_minutes: int = Field(..., description="Number of minutes analyzed")
    timestamp: str = Field(..., description="Metrics timestamp")


class ConfidenceAnalysisResponse(BaseModel):
    """API response schema for confidence score analysis"""
    success: bool = Field(..., description="Whether analysis was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Confidence analysis data")
    error: Optional[str] = Field(None, description="Error message if analysis failed")
    period_days: int = Field(..., description="Number of days analyzed")
    timestamp: str = Field(..., description="Analysis timestamp")


class SystemHealthResponse(BaseModel):
    """API response schema for system health metrics"""
    success: bool = Field(..., description="Whether health check was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="System health data")
    error: Optional[str] = Field(None, description="Error message if health check failed")
    timestamp: str = Field(..., description="Health check timestamp")