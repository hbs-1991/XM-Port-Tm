"""
HS Code Matching Analytics Service

This service provides comprehensive analytics and monitoring for HS code matching operations,
including performance metrics, confidence score distributions, and usage statistics.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from decimal import Decimal
import json

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import async_session_maker
from ..models.product_match import ProductMatch
from ..models.processing_job import ProcessingJob
from ..models.user import User
from .cache_service import get_cache_service


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class MatchingMetrics:
    """Container for matching operation metrics"""
    total_matches: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    average_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    confidence_distribution: Dict[str, int] = field(default_factory=dict)
    popular_hs_codes: List[Tuple[str, int]] = field(default_factory=list)
    processing_time_percentiles: Dict[str, float] = field(default_factory=dict)


@dataclass
class UsageAnalytics:
    """Container for usage analytics"""
    total_users: int = 0
    active_users_today: int = 0
    active_users_week: int = 0
    total_downloads: int = 0
    downloads_today: int = 0
    downloads_this_week: int = 0
    total_processing_jobs: int = 0
    jobs_completed_today: int = 0
    average_products_per_job: float = 0.0
    top_users_by_volume: List[Tuple[str, int]] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    average_processing_time_ms: float = 0.0
    p50_processing_time_ms: float = 0.0
    p95_processing_time_ms: float = 0.0
    p99_processing_time_ms: float = 0.0
    error_rate_percentage: float = 0.0
    timeout_rate_percentage: float = 0.0
    api_calls_per_minute: float = 0.0


class HSCodeAnalyticsService:
    """Service for tracking and analyzing HS code matching operations"""
    
    def __init__(self):
        """Initialize the analytics service"""
        self._cache_service = None
        self._in_memory_metrics: Dict[str, Any] = {
            "recent_matches": [],  # Store recent match results for real-time analytics
            "performance_samples": [],  # Store performance samples
            "api_call_timestamps": [],  # Store API call timestamps for rate calculation
        }
        logger.info("HSCodeAnalyticsService initialized")
    
    async def _get_cache_service(self):
        """Get cache service with lazy initialization"""
        if self._cache_service is None:
            try:
                self._cache_service = await get_cache_service()
            except Exception as e:
                logger.warning(f"Cache service unavailable for analytics: {str(e)}")
        return self._cache_service
    
    async def record_matching_operation(
        self,
        product_description: str,
        hs_code: str,
        confidence_score: float,
        processing_time_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        country: str = "default",
        cache_hit: bool = False
    ) -> None:
        """
        Record a matching operation for analytics
        
        Args:
            product_description: The product description that was matched
            hs_code: The resulting HS code (or 'ERROR' if failed)
            confidence_score: Confidence score of the match (0.0 if failed)
            processing_time_ms: Time taken for the operation in milliseconds
            success: Whether the operation was successful
            error_message: Error message if operation failed
            user_id: ID of the user who performed the operation
            country: Country code used for matching
            cache_hit: Whether the result was served from cache
        """
        try:
            # Record in-memory for real-time analytics
            match_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "product_description": product_description[:100],  # Truncate for privacy
                "hs_code": hs_code,
                "confidence_score": confidence_score,
                "processing_time_ms": processing_time_ms,
                "success": success,
                "error_message": error_message,
                "user_id": user_id,
                "country": country,
                "cache_hit": cache_hit
            }
            
            # Keep only recent records (last 1000)
            self._in_memory_metrics["recent_matches"].append(match_record)
            if len(self._in_memory_metrics["recent_matches"]) > 1000:
                self._in_memory_metrics["recent_matches"] = self._in_memory_metrics["recent_matches"][-1000:]
            
            # Record performance sample
            performance_sample = {
                "timestamp": datetime.utcnow().isoformat(),
                "processing_time_ms": processing_time_ms,
                "success": success,
                "cache_hit": cache_hit
            }
            
            self._in_memory_metrics["performance_samples"].append(performance_sample)
            if len(self._in_memory_metrics["performance_samples"]) > 10000:
                self._in_memory_metrics["performance_samples"] = self._in_memory_metrics["performance_samples"][-10000:]
            
            # Record API call timestamp for rate calculation
            self._in_memory_metrics["api_call_timestamps"].append(datetime.utcnow().timestamp())
            if len(self._in_memory_metrics["api_call_timestamps"]) > 1000:
                self._in_memory_metrics["api_call_timestamps"] = self._in_memory_metrics["api_call_timestamps"][-1000:]
            
            # Try to persist to cache for durability
            cache_service = await self._get_cache_service()
            if cache_service and await cache_service.is_available():
                await self._persist_analytics_to_cache(match_record)
            
            logger.debug(f"Recorded matching operation: success={success}, "
                        f"hs_code={hs_code}, confidence={confidence_score:.3f}, "
                        f"time={processing_time_ms:.0f}ms, cache_hit={cache_hit}")
                        
        except Exception as e:
            logger.error(f"Failed to record matching operation: {str(e)}")
    
    async def get_matching_metrics(
        self, 
        days: int = 7,
        include_real_time: bool = True
    ) -> MatchingMetrics:
        """
        Get comprehensive matching metrics
        
        Args:
            days: Number of days to include in analysis
            include_real_time: Whether to include real-time in-memory data
            
        Returns:
            MatchingMetrics: Comprehensive matching metrics
        """
        try:
            metrics = MatchingMetrics()
            
            # Get database metrics
            async with async_session_maker() as session:
                db_metrics = await self._get_database_metrics(session, days)
                
                metrics.total_matches = db_metrics.get("total_matches", 0)
                metrics.successful_matches = db_metrics.get("successful_matches", 0)
                metrics.failed_matches = metrics.total_matches - metrics.successful_matches
                
                # Get confidence distribution from database
                confidence_dist = await self._get_confidence_distribution(session, days)
                metrics.confidence_distribution = confidence_dist
                
                # Get popular HS codes
                popular_codes = await self._get_popular_hs_codes(session, days)
                metrics.popular_hs_codes = popular_codes
            
            # Combine with real-time metrics if requested
            if include_real_time:
                real_time_metrics = self._get_real_time_metrics()
                metrics = self._merge_metrics(metrics, real_time_metrics)
            
            # Get cache performance metrics
            cache_service = await self._get_cache_service()
            if cache_service and await cache_service.is_available():
                cache_stats = await cache_service.get_cache_statistics()
                metrics.cache_hit_rate = cache_stats.get("hit_rate", 0.0)
            
            # Calculate processing time percentiles from performance samples
            processing_times = [
                sample["processing_time_ms"] 
                for sample in self._in_memory_metrics["performance_samples"]
                if sample["success"]
            ]
            
            if processing_times:
                processing_times.sort()
                n = len(processing_times)
                metrics.processing_time_percentiles = {
                    "p50": processing_times[int(n * 0.5)] if n > 0 else 0.0,
                    "p95": processing_times[int(n * 0.95)] if n > 0 else 0.0,
                    "p99": processing_times[int(n * 0.99)] if n > 0 else 0.0,
                }
                metrics.average_response_time_ms = sum(processing_times) / len(processing_times)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get matching metrics: {str(e)}")
            return MatchingMetrics()  # Return empty metrics on error
    
    async def get_usage_analytics(self, days: int = 30) -> UsageAnalytics:
        """
        Get usage analytics for the specified period
        
        Args:
            days: Number of days to analyze
            
        Returns:
            UsageAnalytics: Usage statistics
        """
        try:
            analytics = UsageAnalytics()
            
            async with async_session_maker() as session:
                # Calculate date thresholds
                now = datetime.utcnow()
                start_date = now - timedelta(days=days)
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                week_start = now - timedelta(days=7)
                
                # Total users
                total_users_result = await session.execute(
                    select(func.count(User.id))
                )
                analytics.total_users = total_users_result.scalar() or 0
                
                # Active users today
                active_today_result = await session.execute(
                    select(func.count(func.distinct(ProcessingJob.user_id)))
                    .where(ProcessingJob.created_at >= today_start)
                )
                analytics.active_users_today = active_today_result.scalar() or 0
                
                # Active users this week
                active_week_result = await session.execute(
                    select(func.count(func.distinct(ProcessingJob.user_id)))
                    .where(ProcessingJob.created_at >= week_start)
                )
                analytics.active_users_week = active_week_result.scalar() or 0
                
                # Total processing jobs in period
                total_jobs_result = await session.execute(
                    select(func.count(ProcessingJob.id))
                    .where(ProcessingJob.created_at >= start_date)
                )
                analytics.total_processing_jobs = total_jobs_result.scalar() or 0
                
                # Jobs completed today
                jobs_today_result = await session.execute(
                    select(func.count(ProcessingJob.id))
                    .where(
                        and_(
                            ProcessingJob.created_at >= today_start,
                            ProcessingJob.status == "completed"
                        )
                    )
                )
                analytics.jobs_completed_today = jobs_today_result.scalar() or 0
                
                # Average products per job
                avg_products_result = await session.execute(
                    select(func.avg(
                        select(func.count(ProductMatch.id))
                        .where(ProductMatch.job_id == ProcessingJob.id)
                        .scalar_subquery()
                    ))
                    .where(ProcessingJob.created_at >= start_date)
                )
                avg_products = avg_products_result.scalar()
                analytics.average_products_per_job = float(avg_products) if avg_products else 0.0
                
                # Top users by volume
                top_users_result = await session.execute(
                    select(
                        User.email,
                        func.count(ProductMatch.id).label("product_count")
                    )
                    .join(ProcessingJob, ProcessingJob.user_id == User.id)
                    .join(ProductMatch, ProductMatch.job_id == ProcessingJob.id)
                    .where(ProcessingJob.created_at >= start_date)
                    .group_by(User.id, User.email)
                    .order_by(func.count(ProductMatch.id).desc())
                    .limit(10)
                )
                
                analytics.top_users_by_volume = [
                    (row.email, row.product_count) 
                    for row in top_users_result.fetchall()
                ]
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get usage analytics: {str(e)}")
            return UsageAnalytics()  # Return empty analytics on error
    
    async def get_performance_metrics(self, minutes: int = 60) -> PerformanceMetrics:
        """
        Get real-time performance metrics
        
        Args:
            minutes: Number of minutes to analyze
            
        Returns:
            PerformanceMetrics: Performance statistics
        """
        try:
            metrics = PerformanceMetrics()
            
            # Calculate time threshold
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Filter recent performance samples
            recent_samples = [
                sample for sample in self._in_memory_metrics["performance_samples"]
                if datetime.fromisoformat(sample["timestamp"]).timestamp() >= cutoff_timestamp
            ]
            
            if recent_samples:
                # Calculate processing times
                processing_times = [
                    sample["processing_time_ms"] 
                    for sample in recent_samples 
                    if sample["success"]
                ]
                
                if processing_times:
                    processing_times.sort()
                    n = len(processing_times)
                    metrics.average_processing_time_ms = sum(processing_times) / n
                    metrics.p50_processing_time_ms = processing_times[int(n * 0.5)] if n > 0 else 0.0
                    metrics.p95_processing_time_ms = processing_times[int(n * 0.95)] if n > 0 else 0.0
                    metrics.p99_processing_time_ms = processing_times[int(n * 0.99)] if n > 0 else 0.0
                
                # Calculate error rates
                total_operations = len(recent_samples)
                failed_operations = len([s for s in recent_samples if not s["success"]])
                metrics.error_rate_percentage = (failed_operations / total_operations) * 100 if total_operations > 0 else 0.0
                
                # Calculate timeout rate (assuming timeouts have very high processing times)
                timeout_threshold_ms = 30000  # 30 seconds
                timeout_operations = len([
                    s for s in recent_samples 
                    if s["processing_time_ms"] >= timeout_threshold_ms
                ])
                metrics.timeout_rate_percentage = (timeout_operations / total_operations) * 100 if total_operations > 0 else 0.0
            
            # Calculate API calls per minute
            recent_api_calls = [
                timestamp for timestamp in self._in_memory_metrics["api_call_timestamps"]
                if timestamp >= cutoff_timestamp
            ]
            metrics.api_calls_per_minute = len(recent_api_calls) / minutes if minutes > 0 else 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {str(e)}")
            return PerformanceMetrics()
    
    async def get_confidence_score_analysis(self, days: int = 7) -> Dict[str, Any]:
        """
        Get detailed confidence score analysis
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict containing confidence score analysis
        """
        try:
            async with async_session_maker() as session:
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # Get confidence score statistics from database
                confidence_stats = await session.execute(
                    select(
                        func.avg(ProductMatch.confidence_score).label("average"),
                        func.min(ProductMatch.confidence_score).label("minimum"),
                        func.max(ProductMatch.confidence_score).label("maximum"),
                        func.count(ProductMatch.id).label("total_matches")
                    )
                    .join(ProcessingJob, ProcessingJob.id == ProductMatch.job_id)
                    .where(ProcessingJob.created_at >= start_date)
                )
                
                stats_row = confidence_stats.fetchone()
                
                # Get confidence distribution
                confidence_distribution = await self._get_detailed_confidence_distribution(session, days)
                
                # Get matches requiring manual review
                manual_review_count = await session.execute(
                    select(func.count(ProductMatch.id))
                    .join(ProcessingJob, ProcessingJob.id == ProductMatch.job_id)
                    .where(
                        and_(
                            ProcessingJob.created_at >= start_date,
                            ProductMatch.requires_manual_review == True
                        )
                    )
                )
                
                manual_review_total = manual_review_count.scalar() or 0
                total_matches = stats_row.total_matches if stats_row else 0
                
                return {
                    "period_days": days,
                    "total_matches": total_matches,
                    "average_confidence": float(stats_row.average) if stats_row and stats_row.average else 0.0,
                    "minimum_confidence": float(stats_row.minimum) if stats_row and stats_row.minimum else 0.0,
                    "maximum_confidence": float(stats_row.maximum) if stats_row and stats_row.maximum else 0.0,
                    "manual_review_required": manual_review_total,
                    "manual_review_percentage": (manual_review_total / total_matches * 100) if total_matches > 0 else 0.0,
                    "confidence_distribution": confidence_distribution
                }
                
        except Exception as e:
            logger.error(f"Failed to get confidence score analysis: {str(e)}")
            return {"error": str(e)}
    
    async def _get_database_metrics(self, session: AsyncSession, days: int) -> Dict[str, Any]:
        """Get metrics from database for specified period"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total matches in period
        total_matches_result = await session.execute(
            select(func.count(ProductMatch.id))
            .join(ProcessingJob, ProcessingJob.id == ProductMatch.job_id)
            .where(ProcessingJob.created_at >= start_date)
        )
        
        total_matches = total_matches_result.scalar() or 0
        
        # Successful matches (assuming non-ERROR HS codes are successful)
        successful_matches_result = await session.execute(
            select(func.count(ProductMatch.id))
            .join(ProcessingJob, ProcessingJob.id == ProductMatch.job_id)
            .where(
                and_(
                    ProcessingJob.created_at >= start_date,
                    ProductMatch.matched_hs_code != "ERROR"
                )
            )
        )
        
        successful_matches = successful_matches_result.scalar() or 0
        
        return {
            "total_matches": total_matches,
            "successful_matches": successful_matches
        }
    
    async def _get_confidence_distribution(self, session: AsyncSession, days: int) -> Dict[str, int]:
        """Get confidence score distribution from database"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get confidence scores
        confidence_scores_result = await session.execute(
            select(ProductMatch.confidence_score)
            .join(ProcessingJob, ProcessingJob.id == ProductMatch.job_id)
            .where(ProcessingJob.created_at >= start_date)
        )
        
        confidence_scores = [float(row[0]) for row in confidence_scores_result.fetchall()]
        
        # Categorize confidence scores
        distribution = {
            "very_high": len([c for c in confidence_scores if c >= 0.95]),
            "high": len([c for c in confidence_scores if 0.8 <= c < 0.95]),
            "medium": len([c for c in confidence_scores if 0.6 <= c < 0.8]),
            "low": len([c for c in confidence_scores if 0.3 <= c < 0.6]),
            "very_low": len([c for c in confidence_scores if c < 0.3])
        }
        
        return distribution
    
    async def _get_detailed_confidence_distribution(self, session: AsyncSession, days: int) -> Dict[str, int]:
        """Get detailed confidence score distribution in 0.1 increments"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        confidence_scores_result = await session.execute(
            select(ProductMatch.confidence_score)
            .join(ProcessingJob, ProcessingJob.id == ProductMatch.job_id)
            .where(ProcessingJob.created_at >= start_date)
        )
        
        confidence_scores = [float(row[0]) for row in confidence_scores_result.fetchall()]
        
        # Create distribution in 0.1 increments
        distribution = {}
        for i in range(11):  # 0.0 to 1.0 in 0.1 increments
            lower = i / 10.0
            upper = (i + 1) / 10.0
            range_key = f"{lower:.1f}-{upper:.1f}"
            distribution[range_key] = len([
                c for c in confidence_scores 
                if lower <= c < upper or (i == 10 and c == 1.0)  # Include 1.0 in the last bucket
            ])
        
        return distribution
    
    async def _get_popular_hs_codes(self, session: AsyncSession, days: int) -> List[Tuple[str, int]]:
        """Get most popular HS codes from database"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        popular_codes_result = await session.execute(
            select(
                ProductMatch.matched_hs_code,
                func.count(ProductMatch.id).label("usage_count")
            )
            .join(ProcessingJob, ProcessingJob.id == ProductMatch.job_id)
            .where(
                and_(
                    ProcessingJob.created_at >= start_date,
                    ProductMatch.matched_hs_code != "ERROR"
                )
            )
            .group_by(ProductMatch.matched_hs_code)
            .order_by(func.count(ProductMatch.id).desc())
            .limit(20)
        )
        
        return [(row.matched_hs_code, row.usage_count) for row in popular_codes_result.fetchall()]
    
    def _get_real_time_metrics(self) -> Dict[str, Any]:
        """Get metrics from in-memory real-time data"""
        recent_matches = self._in_memory_metrics["recent_matches"]
        
        if not recent_matches:
            return {}
        
        total_recent = len(recent_matches)
        successful_recent = len([m for m in recent_matches if m["success"]])
        
        return {
            "recent_total": total_recent,
            "recent_successful": successful_recent,
            "recent_cache_hits": len([m for m in recent_matches if m.get("cache_hit", False)])
        }
    
    def _merge_metrics(self, db_metrics: MatchingMetrics, real_time_data: Dict[str, Any]) -> MatchingMetrics:
        """Merge database metrics with real-time data"""
        # For now, just add real-time data to database metrics
        if real_time_data:
            db_metrics.total_matches += real_time_data.get("recent_total", 0)
            db_metrics.successful_matches += real_time_data.get("recent_successful", 0)
            db_metrics.failed_matches = db_metrics.total_matches - db_metrics.successful_matches
        
        return db_metrics
    
    async def _persist_analytics_to_cache(self, match_record: Dict[str, Any]) -> None:
        """Persist analytics record to cache for durability"""
        try:
            cache_service = await self._get_cache_service()
            if cache_service and await cache_service.is_available():
                # Store in a rolling list of analytics records
                key = "xm_port:analytics:recent_matches"
                
                # Add to cache with expiration
                await cache_service.cache_result(
                    key=f"{key}:{datetime.utcnow().timestamp()}",
                    value=json.dumps(match_record),
                    ttl_seconds=86400  # 24 hours
                )
                
        except Exception as e:
            logger.warning(f"Failed to persist analytics to cache: {str(e)}")
    
    async def record_download_activity(
        self, 
        job_id: str, 
        user_id: str, 
        file_name: str,
        download_success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Record file download activity for analytics tracking
        
        Args:
            job_id: Processing job ID
            user_id: User ID who initiated download
            file_name: Name of downloaded file
            download_success: Whether download was successful
            error_message: Error message if download failed
        """
        try:
            download_record = {
                "job_id": job_id,
                "user_id": user_id,
                "file_name": file_name,
                "download_success": download_success,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat(),
                "download_time_ms": int(time.time() * 1000)
            }
            
            logger.info(f"Download activity recorded - Job: {job_id}, User: {user_id}, Success: {download_success}")
            
            # Store in cache for analytics
            cache_service = await self._get_cache_service()
            if cache_service:
                cache_key = f"analytics:download:{job_id}:{int(time.time())}"
                await cache_service.set_with_expiry(
                    key=cache_key,
                    value=json.dumps(download_record),
                    ttl_seconds=86400  # 24 hours
                )
                
                # Update daily download counters
                today = datetime.utcnow().strftime("%Y-%m-%d")
                download_counter_key = f"analytics:downloads:daily:{today}"
                
                if await cache_service.exists(download_counter_key):
                    await cache_service.increment(download_counter_key)
                else:
                    await cache_service.set_with_expiry(
                        key=download_counter_key,
                        value="1",
                        ttl_seconds=86400
                    )
                
        except Exception as e:
            logger.warning(f"Failed to record download activity: {str(e)}")
    
    async def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system health metrics"""
        try:
            # Get recent performance metrics
            perf_metrics = await self.get_performance_metrics(minutes=30)
            
            # Get cache service status
            cache_service = await self._get_cache_service()
            cache_available = False
            cache_stats = {}
            
            if cache_service:
                cache_available = await cache_service.is_available()
                if cache_available:
                    cache_stats = await cache_service.get_cache_statistics()
            
            # Determine system health status
            status = "healthy"
            alerts = []
            
            if perf_metrics.error_rate_percentage > 10:
                status = "degraded"
                alerts.append(f"High error rate: {perf_metrics.error_rate_percentage:.1f}%")
            
            if perf_metrics.average_processing_time_ms > 10000:  # 10 seconds
                status = "degraded"
                alerts.append(f"Slow response times: {perf_metrics.average_processing_time_ms:.0f}ms")
            
            if not cache_available:
                status = "degraded"
                alerts.append("Cache service unavailable")
            
            return {
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "alerts": alerts,
                "performance": {
                    "average_response_time_ms": perf_metrics.average_processing_time_ms,
                    "error_rate_percentage": perf_metrics.error_rate_percentage,
                    "api_calls_per_minute": perf_metrics.api_calls_per_minute,
                    "p95_response_time_ms": perf_metrics.p95_processing_time_ms
                },
                "cache": {
                    "available": cache_available,
                    "statistics": cache_stats
                },
                "memory_usage": {
                    "recent_matches_count": len(self._in_memory_metrics["recent_matches"]),
                    "performance_samples_count": len(self._in_memory_metrics["performance_samples"]),
                    "api_call_timestamps_count": len(self._in_memory_metrics["api_call_timestamps"])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health metrics: {str(e)}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "alerts": ["System health check failed"]
            }


# Create singleton instance
analytics_service = HSCodeAnalyticsService()