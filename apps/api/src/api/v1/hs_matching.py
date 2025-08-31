"""
HS Code Matching API endpoints
"""
import time
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.auth import get_current_active_user
from src.models.user import User
from src.services.hs_matching_service import hs_matching_service
from src.services.analytics_service import analytics_service
from src.schemas.hs_matching import (
    HSCodeMatchRequest,
    HSCodeBatchMatchRequest,
    HSCodeMatchRequestAPI,
    HSCodeBatchMatchRequestAPI,
    HSCodeBatchProductRequest,
    HSCodeSearchRequest,
    HSCodeMatchResponse,
    HSCodeBatchMatchResponse,
    HSCodeSearchResponse,
    HSCodeSearchResult,
    HealthCheckResponse,
    CacheStatsResponse,
    CacheOperationResponse,
    MatchingMetricsResponse,
    UsageAnalyticsResponse,
    PerformanceMetricsResponse,
    ConfidenceAnalysisResponse,
    SystemHealthResponse
)
from src.middleware.rate_limit import get_user_id_from_request

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiter for HS matching endpoints
limiter = Limiter(key_func=get_user_id_from_request)


@router.post("/match", response_model=HSCodeMatchResponse)
@limiter.limit("20 per minute")  # Limit to 20 HS code matches per minute per user
async def match_single_product(
    request: Request,
    match_request: HSCodeMatchRequestAPI,
    current_user: User = Depends(get_current_active_user)
):
    """
    Match a single product description to HS codes using AI-powered semantic search.
    
    Args:
        request: Product matching request data
        current_user: Authenticated user
        
    Returns:
        HS code matching result with confidence scores
        
    Raises:
        HTTPException: If matching fails or user lacks permissions
    """
    start_time = time.time()
    
    try:
        logger.info(f"HS code match request from user {current_user.id} for product: {match_request.product_description[:50]}...")
        
        # Convert API request to service request
        service_request = HSCodeMatchRequest(
            product_description=match_request.product_description,
            country=match_request.country,
            include_alternatives=match_request.include_alternatives,
            confidence_threshold=match_request.confidence_threshold
        )
        
        # Perform matching using the service
        result = await hs_matching_service.match_single_product(
            product_description=service_request.product_description,
            country=service_request.country,
            include_alternatives=service_request.include_alternatives,
            confidence_threshold=service_request.confidence_threshold
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Successfully matched HS code for user {current_user.id}: "
                   f"Primary {result.primary_match.hs_code} (confidence: {result.primary_match.confidence:.3f})")
        
        return HSCodeMatchResponse(
            success=True,
            data=result,
            processing_time_ms=processing_time
        )
        
    except ValueError as e:
        processing_time = (time.time() - start_time) * 1000
        logger.warning(f"Invalid request from user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(f"HS code matching failed for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to match HS code. Please try again later."
        )


@router.post("/batch-match", response_model=HSCodeBatchMatchResponse)
@limiter.limit("5 per minute")  # Limit batch requests to 5 per minute per user
async def match_batch_products(
    request: Request,
    batch_request: HSCodeBatchMatchRequestAPI,
    current_user: User = Depends(get_current_active_user)
):
    """
    Match multiple product descriptions to HS codes in a single batch request.
    
    Args:
        request: Batch matching request data
        current_user: Authenticated user
        
    Returns:
        List of HS code matching results
        
    Raises:
        HTTPException: If batch matching fails or request is invalid
    """
    start_time = time.time()
    
    try:
        logger.info(f"Batch HS code match request from user {current_user.id} for {len(batch_request.products)} products")
        
        # Convert API requests to service requests
        service_requests = []
        for product_request in batch_request.products:
            service_request = HSCodeMatchRequest(
                product_description=product_request.product_description,
                country=product_request.country or batch_request.country,
                include_alternatives=product_request.include_alternatives if product_request.include_alternatives is not None else True,
                confidence_threshold=product_request.confidence_threshold if product_request.confidence_threshold is not None else 0.7
            )
            service_requests.append(service_request)
        
        # Perform batch matching using the service
        results = await hs_matching_service.match_batch_products(
            requests=service_requests,
            max_concurrent=5  # Limit concurrent requests to prevent overload
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Count successful matches
        successful_matches = sum(1 for result in results if result.primary_match.hs_code != "ERROR")
        
        logger.info(f"Batch matching completed for user {current_user.id}: "
                   f"{successful_matches}/{len(results)} successful matches")
        
        return HSCodeBatchMatchResponse(
            success=True,
            data=results,
            processing_time_ms=processing_time,
            total_processed=len(results),
            successful_matches=successful_matches
        )
        
    except ValueError as e:
        processing_time = (time.time() - start_time) * 1000
        logger.warning(f"Invalid batch request from user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(f"Batch HS code matching failed for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process batch matching request. Please try again later."
        )


@router.get("/search", response_model=HSCodeSearchResponse)
@limiter.limit("30 per minute")  # Limit search requests to 30 per minute per user
async def search_hs_codes(
    request: Request,
    search_request: HSCodeSearchRequest = Depends(),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search for HS codes using a query string.
    
    Args:
        request: Search request parameters
        current_user: Authenticated user
        
    Returns:
        List of matching HS codes with relevance scores
        
    Raises:
        HTTPException: If search fails or query is invalid
    """
    start_time = time.time()
    
    try:
        logger.info(f"HS code search request from user {current_user.id} for query: {search_request.query}")
        
        # For now, implement basic search using the matching service
        # In the future, this could be enhanced with a dedicated search endpoint
        
        # Use the matching service to find relevant HS codes
        search_result = await hs_matching_service.match_single_product(
            product_description=search_request.query,
            country=search_request.country,
            include_alternatives=True,
            confidence_threshold=0.1  # Lower threshold for search
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert matching results to search results
        search_results = []
        
        # Add primary match
        if search_result.primary_match.hs_code != "ERROR":
            search_results.append(HSCodeSearchResult(
                hs_code=search_result.primary_match.hs_code,
                description=search_result.primary_match.code_description,
                chapter=search_result.primary_match.chapter,
                section=search_result.primary_match.section,
                relevance_score=search_result.primary_match.confidence
            ))
        
        # Add alternative matches
        for alt_match in search_result.alternative_matches:
            search_results.append(HSCodeSearchResult(
                hs_code=alt_match.hs_code,
                description=alt_match.code_description,
                chapter=alt_match.chapter,
                section=alt_match.section,
                relevance_score=alt_match.confidence
            ))
        
        # Limit results based on request
        search_results = search_results[:search_request.limit]
        
        logger.info(f"HS code search completed for user {current_user.id}: {len(search_results)} results")
        
        return HSCodeSearchResponse(
            success=True,
            data=search_results,
            query=search_request.query,
            total_results=len(search_results),
            processing_time_ms=processing_time
        )
        
    except ValueError as e:
        processing_time = (time.time() - start_time) * 1000
        logger.warning(f"Invalid search request from user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(f"HS code search failed for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search HS codes. Please try again later."
        )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(current_user: User = Depends(get_current_active_user)):
    """
    Check the health status of the HS code matching service.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        Service health status and configuration details
    """
    try:
        health_data = await hs_matching_service.get_service_health()
        
        return HealthCheckResponse(
            status=health_data["status"],
            timestamp=datetime.utcnow().isoformat(),
            openai_response_time_ms=health_data.get("openai_response_time_ms"),
            cache_available=health_data["cache_service"]["available"],
            configuration=health_data["configuration"]
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            openai_response_time_ms=None,
            cache_available=False,
            configuration={"error": str(e)}
        )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_statistics(current_user: User = Depends(get_current_active_user)):
    """
    Get cache performance statistics for HS code matching.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        Cache performance statistics and status
    """
    try:
        stats = await hs_matching_service.get_cache_statistics()
        
        return CacheStatsResponse(
            cache_available=True,
            statistics=stats,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {str(e)}")
        return CacheStatsResponse(
            cache_available=False,
            statistics={"error": str(e)},
            timestamp=datetime.utcnow().isoformat()
        )


@router.post("/cache/warm", response_model=CacheOperationResponse)
async def warm_cache(current_user: User = Depends(get_current_active_user)):
    """
    Warm the cache with common product descriptions for better performance.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        Cache warming operation results
    """
    try:
        result = await hs_matching_service.warm_cache()
        
        return CacheOperationResponse(
            success=True,
            operation="cache_warm",
            details=result,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Cache warming failed: {str(e)}")
        return CacheOperationResponse(
            success=False,
            operation="cache_warm",
            details={"error": str(e)},
            timestamp=datetime.utcnow().isoformat()
        )


@router.delete("/cache/invalidate", response_model=CacheOperationResponse)
async def invalidate_cache(
    pattern: str = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Invalidate cache entries for HS code matching.
    
    Args:
        pattern: Optional pattern to match cache keys
        current_user: Authenticated user
        
    Returns:
        Cache invalidation operation results
    """
    try:
        result = await hs_matching_service.invalidate_cache(pattern)
        
        return CacheOperationResponse(
            success=True,
            operation="cache_invalidate",
            details=result,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Cache invalidation failed: {str(e)}")
        return CacheOperationResponse(
            success=False,
            operation="cache_invalidate",
            details={"error": str(e)},
            timestamp=datetime.utcnow().isoformat()
        )


# Analytics endpoints

@router.get("/analytics/metrics", response_model=MatchingMetricsResponse)
@limiter.limit("10 per minute")  # Limit analytics requests
async def get_matching_metrics(
    request: Request,
    days: int = 7,
    include_real_time: bool = True,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive HS code matching metrics for the specified period.
    
    Args:
        days: Number of days to analyze (default: 7, max: 90)
        include_real_time: Whether to include real-time in-memory data
        current_user: Authenticated user
        
    Returns:
        Comprehensive matching metrics including performance and confidence data
    """
    try:
        # Validate input
        if days < 1 or days > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days parameter must be between 1 and 90"
            )
        
        start_time = time.time()
        metrics = await analytics_service.get_matching_metrics(days, include_real_time)
        processing_time = (time.time() - start_time) * 1000
        
        # Convert dataclass to dict for JSON serialization
        metrics_data = {
            "total_matches": metrics.total_matches,
            "successful_matches": metrics.successful_matches,
            "failed_matches": metrics.failed_matches,
            "success_rate_percentage": (metrics.successful_matches / metrics.total_matches * 100) if metrics.total_matches > 0 else 0.0,
            "average_response_time_ms": metrics.average_response_time_ms,
            "cache_hit_rate": metrics.cache_hit_rate,
            "confidence_distribution": metrics.confidence_distribution,
            "popular_hs_codes": metrics.popular_hs_codes,
            "processing_time_percentiles": metrics.processing_time_percentiles
        }
        
        return MatchingMetricsResponse(
            success=True,
            data=metrics_data,
            period_days=days,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get matching metrics: {str(e)}")
        return MatchingMetricsResponse(
            success=False,
            error=str(e),
            period_days=days,
            timestamp=datetime.utcnow().isoformat()
        )


@router.get("/analytics/usage", response_model=UsageAnalyticsResponse)
@limiter.limit("10 per minute")
async def get_usage_analytics(
    request: Request,
    days: int = 30,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get usage analytics for HS code matching operations.
    
    Args:
        days: Number of days to analyze (default: 30, max: 365)
        current_user: Authenticated user
        
    Returns:
        Usage analytics including user activity and processing job statistics
    """
    try:
        # Validate input
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days parameter must be between 1 and 365"
            )
        
        analytics = await analytics_service.get_usage_analytics(days)
        
        # Convert dataclass to dict for JSON serialization
        analytics_data = {
            "total_users": analytics.total_users,
            "active_users_today": analytics.active_users_today,
            "active_users_week": analytics.active_users_week,
            "total_processing_jobs": analytics.total_processing_jobs,
            "jobs_completed_today": analytics.jobs_completed_today,
            "average_products_per_job": analytics.average_products_per_job,
            "top_users_by_volume": analytics.top_users_by_volume
        }
        
        return UsageAnalyticsResponse(
            success=True,
            data=analytics_data,
            period_days=days,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage analytics: {str(e)}")
        return UsageAnalyticsResponse(
            success=False,
            error=str(e),
            period_days=days,
            timestamp=datetime.utcnow().isoformat()
        )


@router.get("/analytics/performance", response_model=PerformanceMetricsResponse)
@limiter.limit("20 per minute")  # Allow more frequent performance checks
async def get_performance_metrics(
    request: Request,
    minutes: int = 60,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get real-time performance metrics for HS code matching operations.
    
    Args:
        minutes: Number of minutes to analyze (default: 60, max: 1440)
        current_user: Authenticated user
        
    Returns:
        Real-time performance metrics including response times and error rates
    """
    try:
        # Validate input
        if minutes < 1 or minutes > 1440:  # Max 24 hours
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minutes parameter must be between 1 and 1440"
            )
        
        metrics = await analytics_service.get_performance_metrics(minutes)
        
        # Convert dataclass to dict for JSON serialization
        metrics_data = {
            "average_processing_time_ms": metrics.average_processing_time_ms,
            "p50_processing_time_ms": metrics.p50_processing_time_ms,
            "p95_processing_time_ms": metrics.p95_processing_time_ms,
            "p99_processing_time_ms": metrics.p99_processing_time_ms,
            "error_rate_percentage": metrics.error_rate_percentage,
            "timeout_rate_percentage": metrics.timeout_rate_percentage,
            "api_calls_per_minute": metrics.api_calls_per_minute
        }
        
        return PerformanceMetricsResponse(
            success=True,
            data=metrics_data,
            period_minutes=minutes,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {str(e)}")
        return PerformanceMetricsResponse(
            success=False,
            error=str(e),
            period_minutes=minutes,
            timestamp=datetime.utcnow().isoformat()
        )


@router.get("/analytics/confidence", response_model=ConfidenceAnalysisResponse)
@limiter.limit("10 per minute")
async def get_confidence_analysis(
    request: Request,
    days: int = 7,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed confidence score analysis for HS code matching operations.
    
    Args:
        days: Number of days to analyze (default: 7, max: 90)
        current_user: Authenticated user
        
    Returns:
        Detailed confidence score analysis including distributions and accuracy metrics
    """
    try:
        # Validate input
        if days < 1 or days > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days parameter must be between 1 and 90"
            )
        
        analysis = await analytics_service.get_confidence_score_analysis(days)
        
        return ConfidenceAnalysisResponse(
            success=True,
            data=analysis,
            period_days=days,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get confidence analysis: {str(e)}")
        return ConfidenceAnalysisResponse(
            success=False,
            error=str(e),
            period_days=days,
            timestamp=datetime.utcnow().isoformat()
        )


@router.get("/analytics/system-health", response_model=SystemHealthResponse)
@limiter.limit("30 per minute")  # Allow frequent health checks
async def get_system_health(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive system health metrics for HS code matching operations.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        System health metrics including performance, cache status, and alerts
    """
    try:
        health_data = await analytics_service.get_system_health_metrics()
        
        return SystemHealthResponse(
            success=True,
            data=health_data,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get system health: {str(e)}")
        return SystemHealthResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )