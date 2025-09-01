"""
HS Code Matching Service using OpenAI Agents SDK

This service provides intelligent HS code matching for product descriptions
using OpenAI's Vector Store and semantic search capabilities with Redis caching.
"""

import asyncio
import time
import logging
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from functools import lru_cache
from collections import deque
from datetime import datetime, timedelta
from agents import Agent, FileSearchTool, Runner

from pydantic import BaseModel, Field

from ..core.openai_config import OpenAIAgentConfig, HSCodeResult, HSCodeMatchResult
from ..schemas.processing import ProductData
from .cache_service import get_cache_service, noop_cache_service
from .analytics_service import analytics_service

# Import request models from schemas to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..schemas.hs_matching import HSCodeMatchRequest, HSCodeBatchMatchRequest


# Configure logging
logger = logging.getLogger(__name__)


class HSCodeMatchingService:
    """Service for matching product descriptions to HS codes using OpenAI Agents SDK"""
    
    # Configuration constants
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 1.0
    BATCH_SIZE_LIMIT = 100  # Increased from 50
    TIMEOUT_SECONDS = 20  # Reduced from 30 for faster failures
    
    # Performance optimization settings
    MAX_CONCURRENT_REQUESTS = 10  # Connection pool size
    REQUEST_QUEUE_SIZE = 200  # Max queued requests
    PERFORMANCE_TARGET_MS = 2000  # 2 second target
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.95
    MEDIUM_CONFIDENCE_THRESHOLD = 0.8
    LOW_CONFIDENCE_THRESHOLD = 0.5
    
    def __init__(self):
        """Initialize the HS Code Matching Service with performance optimizations"""
        self.agent_config = OpenAIAgentConfig()
        self._agents_cache: Dict[str, Any] = {}
        self._cache_service = None
        
        # Performance optimization: Connection pooling and request queuing
        self._request_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        self._request_queue = deque(maxlen=self.REQUEST_QUEUE_SIZE)
        self._performance_metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "avg_response_time_ms": 0,
            "requests_under_target": 0
        }
        
        # Async initialization tracking
        self._initialized = False
        self._initialization_lock = asyncio.Lock()
        
        logger.info("HSCodeMatchingService initialized with performance optimizations")
    
    async def _get_cache_service(self):
        """Get cache service with lazy initialization and connection pooling"""
        if self._cache_service is None:
            async with self._initialization_lock:
                if self._cache_service is None:  # Double-check pattern
                    try:
                        self._cache_service = await get_cache_service()
                        # Pre-warm cache on first initialization
                        if not self._initialized:
                            asyncio.create_task(self._background_cache_warming())
                            self._initialized = True
                    except Exception as e:
                        logger.warning(f"Cache service unavailable, using fallback: {str(e)}")
                        self._cache_service = noop_cache_service
        return self._cache_service
    
    async def _background_cache_warming(self):
        """Background task to warm cache with common products"""
        try:
            await asyncio.sleep(2)  # Wait for service to fully initialize
            result = await self.warm_cache()
            logger.info(f"Background cache warming completed: {result}")
        except Exception as e:
            logger.warning(f"Background cache warming failed: {str(e)}")
    
    async def _get_or_create_agent(self, country: str = "default"):
        """Get or create an agent for the specified country with caching"""
        if country not in self._agents_cache:
            self._agents_cache[country] = await self.agent_config.create_agent(country)
            logger.info(f"Created new agent for country: {country}")
        return self._agents_cache[country]
    
    async def match_single_product(
        self, 
        product_description: str, 
        country: str = "default",
        include_alternatives: bool = True,
        confidence_threshold: float = 0.7
    ) -> HSCodeMatchResult:
        """
        Match a single product description to HS codes with caching
        
        Args:
            product_description: Description of the product to match
            country: Country code for specific HS code variations
            include_alternatives: Whether to include alternative matches
            confidence_threshold: Minimum confidence threshold for matches
            
        Returns:
            HSCodeMatchResult: Matching result with primary and alternative matches
            
        Raises:
            ValueError: If product description is invalid
            ConnectionError: If OpenAI API is unavailable
            TimeoutError: If matching takes too long
        """
        start_time = time.time()
        
        # Validate input
        if not product_description or len(product_description.strip()) < 5:
            raise ValueError("Product description must be at least 5 characters long")
        
        # Clean and prepare the description
        cleaned_description = self._clean_product_description(product_description)
        
        # Get cache service
        cache_service = await self._get_cache_service()
        
        # Try to get cached result first
        cached_result = await cache_service.get_cached_match(cleaned_description, country)
        if cached_result:
            logger.info(f"Cache hit for product: {product_description[:50]}... "
                       f"(Primary: {cached_result.primary_match.hs_code}, "
                       f"Confidence: {cached_result.primary_match.confidence:.3f})")
            return cached_result
        
        # Cache miss - proceed with OpenAI matching
        logger.debug(f"Cache miss for product: {product_description[:50]}... Querying OpenAI")
        
        # Get or create agent for country
        agent = await self._get_or_create_agent(country)
        
        # Build search query with context
        search_query = self._build_search_query(cleaned_description, include_alternatives)
        
        try:
            # Use the enhanced OpenAI Agents SDK matching
            processed_result = await self.agent_config.match_hs_code(cleaned_description, country)
            
            # Update processing time if needed
            processing_time = processed_result.processing_time_ms
            
            # Cache the result for future use
            cache_success = await cache_service.cache_match_result(
                product_description=cleaned_description,
                result=processed_result,
                country=country
            )
            
            if cache_success:
                logger.debug(f"Cached result for product: {product_description[:50]}...")
            
            logger.info(f"Successfully matched HS code for product: {product_description[:50]}... "
                       f"(Primary: {processed_result.primary_match.hs_code}, "
                       f"Confidence: {processed_result.primary_match.confidence:.3f}, "
                       f"Time: {processing_time:.0f}ms)")
            
            # Record analytics for successful match
            try:
                await analytics_service.record_matching_operation(
                    product_description=cleaned_description,
                    hs_code=processed_result.primary_match.hs_code,
                    confidence_score=processed_result.primary_match.confidence,
                    processing_time_ms=processing_time,
                    success=True,
                    country=country,
                    cache_hit=cached_result is not None
                )
            except Exception as analytics_error:
                logger.warning(f"Failed to record analytics: {str(analytics_error)}")
            
            return processed_result
            
        except Exception as e:
            logger.error(f"Failed to match HS code for product: {product_description[:50]}... Error: {str(e)}")
            
            # Record analytics for failed match
            try:
                processing_time = (time.time() - start_time) * 1000
                await analytics_service.record_matching_operation(
                    product_description=cleaned_description,
                    hs_code="ERROR",
                    confidence_score=0.0,
                    processing_time_ms=processing_time,
                    success=False,
                    error_message=str(e),
                    country=country,
                    cache_hit=False
                )
            except Exception as analytics_error:
                logger.warning(f"Failed to record analytics for error case: {str(analytics_error)}")
            
            raise
    
    async def match_batch_products(
        self,
        requests: List["HSCodeMatchRequest"],
        max_concurrent: int = None
    ) -> List[HSCodeMatchResult]:
        """
        Match multiple products to HS codes concurrently with batch caching
        
        Args:
            requests: List of HS code match requests
            max_concurrent: Maximum number of concurrent API calls
            
        Returns:
            List[HSCodeMatchResult]: List of matching results
            
        Raises:
            ValueError: If batch size exceeds limits
        """
        if len(requests) > self.BATCH_SIZE_LIMIT:
            raise ValueError(f"Batch size {len(requests)} exceeds limit of {self.BATCH_SIZE_LIMIT}")
        
        # Optimize concurrency based on batch size
        if max_concurrent is None:
            max_concurrent = min(self.MAX_CONCURRENT_REQUESTS, max(5, len(requests) // 10))
        
        logger.info(f"Starting batch matching for {len(requests)} products with {max_concurrent} concurrent workers")
        
        # Get cache service
        cache_service = await self._get_cache_service()
        
        # Generate batch hash for caching
        batch_hash = self._generate_batch_hash(requests)
        
        # Check for cached batch result
        cached_batch = await cache_service.get_cached_batch_match(batch_hash)
        if cached_batch and len(cached_batch) == len(requests):
            logger.info(f"Batch cache hit for {len(requests)} products")
            self._update_performance_metrics(0, len(requests), True)
            return cached_batch
        
        # Batch cache miss - process individual requests with caching
        logger.debug(f"Batch cache miss - processing {len(requests)} individual requests")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def match_with_semaphore(request: "HSCodeMatchRequest") -> HSCodeMatchResult:
            async with semaphore:
                return await self.match_single_product(
                    product_description=request.product_description,
                    country=request.country,
                    include_alternatives=request.include_alternatives,
                    confidence_threshold=request.confidence_threshold
                )
        
        # Execute all matches concurrently
        try:
            results = await asyncio.gather(
                *[match_with_semaphore(req) for req in requests],
                return_exceptions=True
            )
            
            # Process results and handle exceptions
            processed_results = []
            total_time = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to match product at index {i}: {str(result)}")
                    # Create error result
                    error_result = self._create_error_result(
                        requests[i].product_description,
                        str(result)
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)
                    total_time += result.processing_time_ms
            
            # Update performance metrics
            avg_time = total_time / len(processed_results) if processed_results else 0
            self._update_performance_metrics(avg_time, len(processed_results), False)
            
            # Cache the batch results if all successful
            successful_results = [r for r in processed_results if r.primary_match.hs_code != "ERROR"]
            if len(successful_results) == len(processed_results):
                cache_success = await cache_service.cache_batch_results(batch_hash, processed_results)
                if cache_success:
                    logger.debug(f"Cached batch results for {len(processed_results)} products")
            
            logger.info(f"Completed batch matching: {len(processed_results)} results, avg time: {avg_time:.0f}ms")
            return processed_results
            
        except Exception as e:
            logger.error(f"Batch matching failed: {str(e)}")
            raise
    
    # Note: _execute_with_retry method removed as retry logic is now handled 
    # by the OpenAIAgentConfig.match_hs_code method
    
    def _clean_product_description(self, description: str) -> str:
        """Clean and normalize product description for better matching"""
        # Remove extra whitespace and normalize
        cleaned = " ".join(description.strip().split())
        
        # Remove common noise words that don't help with classification
        noise_words = ["various", "assorted", "mixed", "different", "type", "kind"]
        words = cleaned.split()
        filtered_words = [word for word in words if word.lower() not in noise_words]
        
        return " ".join(filtered_words)
    
    def _build_search_query(self, description: str, include_alternatives: bool) -> str:
        """Build optimized search query for the agent"""
        base_query = f"Find the most appropriate HS code for this product: {description}"
        
        if include_alternatives:
            base_query += "\n\nAlso provide up to 3 alternative HS codes with confidence scores if there are other potentially suitable classifications."
        
        base_query += "\n\nProvide detailed reasoning for your classification decision."
        
        return base_query
    
    # Note: _process_matching_result method removed as structured output 
    # is now handled directly by OpenAIAgentConfig.match_hs_code method
    
    def _create_error_result(self, product_description: str, error_message: str) -> HSCodeMatchResult:
        """Create an error result for failed matches"""
        error_result = HSCodeResult(
            hs_code="ERROR",
            code_description="Failed to match HS code",
            confidence=0.0,
            chapter="ERROR",
            section="ERROR",
            reasoning=f"Error occurred during matching: {error_message}"
        )
        
        return HSCodeMatchResult(
            primary_match=error_result,
            alternative_matches=[],
            processing_time_ms=0.0,
            query=product_description
        )
    
    def get_confidence_level_description(self, confidence: float) -> str:
        """Get human-readable confidence level description"""
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return "High"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return "Medium"
        elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            return "Low"
        else:
            return "Very Low"
    
    def should_require_manual_review(self, confidence: float) -> bool:
        """Determine if match requires manual review based on confidence"""
        return confidence < self.MEDIUM_CONFIDENCE_THRESHOLD
    
    def _generate_batch_hash(self, requests: List["HSCodeMatchRequest"]) -> str:
        """Generate deterministic hash for batch requests for caching"""
        # Create sorted string representation of requests for consistent hashing
        request_strings = []
        for req in requests:
            req_str = f"{req.product_description}:{req.country}:{req.confidence_threshold}:{req.include_alternatives}"
            request_strings.append(req_str)
        
        # Sort to ensure consistent hash regardless of order
        request_strings.sort()
        combined_string = "|".join(request_strings)
        
        # Generate hash
        return hashlib.sha256(combined_string.encode()).hexdigest()[:16]
    
    async def warm_cache(self) -> Dict[str, Any]:
        """
        Warm cache with common product descriptions
        
        Returns:
            Dictionary with warming results and statistics
        """
        cache_service = await self._get_cache_service()
        
        if not await cache_service.is_available():
            return {"error": "Cache service not available", "warmed": 0}
        
        return await cache_service.warm_cache_with_common_products(self)
    
    async def invalidate_cache(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Invalidate cache entries
        
        Args:
            pattern: Optional pattern to match keys, defaults to all HS code matches
            
        Returns:
            Dictionary with invalidation results
        """
        cache_service = await self._get_cache_service()
        
        if not await cache_service.is_available():
            return {"error": "Cache service not available", "invalidated": 0}
        
        # Default pattern for all HS code cache entries
        if pattern is None:
            pattern = f"xm_port:hs_match:*"
        
        invalidated_count = await cache_service.invalidate_cache_by_pattern(pattern)
        
        return {
            "invalidated": invalidated_count,
            "pattern": pattern,
            "status": "success"
        }
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        cache_service = await self._get_cache_service()
        return await cache_service.get_cache_statistics()
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get service health status and configuration including cache status and performance metrics"""
        try:
            # Get cache service and statistics
            cache_service = await self._get_cache_service()
            cache_stats = await cache_service.get_cache_statistics()
            cache_available = await cache_service.is_available()
            
            # Test OpenAI connection with simple query
            start_time = time.time()
            test_result = await asyncio.wait_for(
                self.agent_config.match_hs_code("apple", "default"),
                timeout=10.0
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_summary()
            
            return {
                "status": "healthy",
                "openai_response_time_ms": round(response_time, 2),
                "available_countries": self.agent_config.get_available_countries(),
                "agent_cache_size": len(self._agents_cache),
                "request_queue_size": len(self._request_queue),
                "active_connections": self.MAX_CONCURRENT_REQUESTS - self._request_semaphore._value,
                "cache_service": {
                    "available": cache_available,
                    "statistics": cache_stats
                },
                "performance": performance_metrics,
                "configuration": {
                    "max_retry_attempts": self.MAX_RETRY_ATTEMPTS,
                    "timeout_seconds": self.TIMEOUT_SECONDS,
                    "batch_size_limit": self.BATCH_SIZE_LIMIT,
                    "max_concurrent_requests": self.MAX_CONCURRENT_REQUESTS,
                    "performance_target_ms": self.PERFORMANCE_TARGET_MS,
                    "confidence_thresholds": {
                        "high": self.HIGH_CONFIDENCE_THRESHOLD,
                        "medium": self.MEDIUM_CONFIDENCE_THRESHOLD,
                        "low": self.LOW_CONFIDENCE_THRESHOLD
                    }
                }
            }
            
        except Exception as e:
            # Get cache status even if OpenAI fails
            cache_service = await self._get_cache_service()
            cache_available = await cache_service.is_available()
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "available_countries": self.agent_config.get_available_countries(),
                "agent_cache_size": len(self._agents_cache),
                "cache_service": {
                    "available": cache_available,
                    "statistics": await cache_service.get_cache_statistics() if cache_available else {"error": "Cache unavailable"}
                }
            }


    def _update_performance_metrics(self, response_time_ms: float, batch_size: int, from_cache: bool):
        """Update internal performance metrics"""
        self._performance_metrics["total_requests"] += batch_size
        
        if from_cache:
            self._performance_metrics["cache_hits"] += batch_size
            # Cache hits are always under target
            self._performance_metrics["requests_under_target"] += batch_size
        else:
            # Update average response time (exponential moving average)
            alpha = 0.1  # Smoothing factor
            if self._performance_metrics["avg_response_time_ms"] == 0:
                self._performance_metrics["avg_response_time_ms"] = response_time_ms
            else:
                self._performance_metrics["avg_response_time_ms"] = (
                    alpha * response_time_ms + 
                    (1 - alpha) * self._performance_metrics["avg_response_time_ms"]
                )
            
            # Track requests meeting performance target
            if response_time_ms <= self.PERFORMANCE_TARGET_MS:
                self._performance_metrics["requests_under_target"] += batch_size
    
    def _calculate_performance_summary(self) -> Dict[str, Any]:
        """Calculate performance summary metrics"""
        total = self._performance_metrics["total_requests"]
        if total == 0:
            return {
                "total_requests": 0,
                "cache_hit_rate": 0.0,
                "avg_response_time_ms": 0,
                "target_achievement_rate": 0.0
            }
        
        return {
            "total_requests": total,
            "cache_hit_rate": round(self._performance_metrics["cache_hits"] / total * 100, 2),
            "avg_response_time_ms": round(self._performance_metrics["avg_response_time_ms"], 0),
            "target_achievement_rate": round(
                self._performance_metrics["requests_under_target"] / total * 100, 2
            ),
            "performance_target_ms": self.PERFORMANCE_TARGET_MS
        }
    
    @lru_cache(maxsize=1000)
    def _build_search_query_cached(self, description: str, include_alternatives: bool) -> str:
        """Cached version of query building for frequently requested products"""
        return self._build_search_query(description, include_alternatives)
    
    async def optimize_for_performance(self) -> Dict[str, Any]:
        """Run performance optimization tasks"""
        results = {}
        
        # 1. Warm cache with common products
        logger.info("Starting performance optimization tasks...")
        results["cache_warming"] = await self.warm_cache()
        
        # 2. Pre-create agents for known countries
        for country in self.agent_config.get_available_countries():
            await self._get_or_create_agent(country)
        results["agents_preloaded"] = len(self._agents_cache)
        
        # 3. Clear old request queue entries
        current_time = time.time()
        old_requests = []
        while self._request_queue and (current_time - self._request_queue[0][1]) > 300:
            old_requests.append(self._request_queue.popleft())
        results["queue_cleaned"] = len(old_requests)
        
        logger.info(f"Performance optimization completed: {results}")
        return results


# Create singleton instance
hs_matching_service = HSCodeMatchingService()