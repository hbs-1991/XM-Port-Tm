"""
Redis-based caching service for HS code matching

This service provides caching functionality for frequently matched HS codes
to improve performance and reduce OpenAI API costs.
"""

import json
import logging
import hashlib
from typing import Optional, List, Dict, Any
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from ..core.config import settings
from ..core.openai_config import HSCodeMatchResult, HSCodeResult


logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for HS code matching results"""
    
    # Cache configuration - Optimized for performance
    DEFAULT_TTL_HOURS = 48  # Increased to 48 hours for better cache hit rate
    FREQUENT_MATCH_TTL_HOURS = 336  # 14 days for frequently accessed matches
    BATCH_CACHE_TTL_HOURS = 24  # 24 hours for batch results
    HOT_CACHE_TTL_HOURS = 720  # 30 days for very high confidence matches
    
    # Cache keys
    CACHE_KEY_PREFIX = "xm_port:hs_match"
    STATS_KEY_PREFIX = "xm_port:hs_stats"
    WARMING_KEY_PREFIX = "xm_port:hs_warming"
    
    # Warming strategies - Extended for better coverage
    COMMON_PRODUCTS = [
        "wheat flour",
        "cotton fabric",
        "steel pipes",
        "automotive parts",
        "computer hardware",
        "textiles",
        "machinery",
        "chemicals",
        "food products",
        "electronics",
        "plastic products",
        "rubber products",
        "metal products",
        "paper products",
        "glass products",
        "ceramic products",
        "leather goods",
        "wood products",
        "pharmaceutical products",
        "cosmetic products"
    ]
    
    def __init__(self):
        """Initialize Redis connection"""
        self._redis: Optional[Redis] = None
        self._connection_pool = None
        
    async def initialize(self) -> bool:
        """Initialize Redis connection with fallback handling"""
        try:
            # Create connection pool with optimized settings
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,  # Increased for high concurrency
                retry_on_timeout=True,
                socket_connect_timeout=2,  # Reduced for faster failure detection
                socket_timeout=3,  # Reduced for faster timeouts
                socket_keepalive=True,  # Keep connections alive
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 3,  # TCP_KEEPCNT
                }
            )
            
            # Create Redis client
            self._redis = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._redis.ping()
            logger.info("Redis cache service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {str(e)}")
            self._redis = None
            return False
    
    async def close(self):
        """Close Redis connection and cleanup resources"""
        if self._redis:
            await self._redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
        logger.info("Redis cache service closed")
    
    def _generate_cache_key(self, product_description: str, country: str = "default") -> str:
        """Generate cache key for product description"""
        # Create hash of description for consistent key generation
        description_hash = hashlib.sha256(
            f"{product_description.lower().strip()}:{country}".encode()
        ).hexdigest()[:16]
        
        return f"{self.CACHE_KEY_PREFIX}:{country}:{description_hash}"
    
    def _generate_batch_cache_key(self, request_hash: str) -> str:
        """Generate cache key for batch requests"""
        return f"{self.CACHE_KEY_PREFIX}:batch:{request_hash}"
    
    def _generate_stats_key(self, metric: str) -> str:
        """Generate cache key for statistics"""
        return f"{self.STATS_KEY_PREFIX}:{metric}"
    
    async def get_cached_match(
        self, 
        product_description: str, 
        country: str = "default"
    ) -> Optional[HSCodeMatchResult]:
        """
        Retrieve cached HS code match result
        
        Args:
            product_description: Product description to lookup
            country: Country code for the match
            
        Returns:
            HSCodeMatchResult if found in cache, None otherwise
        """
        if not self._redis:
            return None
            
        try:
            cache_key = self._generate_cache_key(product_description, country)
            cached_data = await self._redis.get(cache_key)
            
            if cached_data:
                # Update access statistics
                await self._update_access_stats(cache_key)
                
                # Deserialize and return result
                data = json.loads(cached_data)
                result = HSCodeMatchResult(**data)
                
                logger.debug(f"Cache hit for product: {product_description[:50]}...")
                return result
            
            logger.debug(f"Cache miss for product: {product_description[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
    
    async def cache_match_result(
        self,
        product_description: str,
        result: HSCodeMatchResult,
        country: str = "default",
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        Cache HS code match result
        
        Args:
            product_description: Product description
            result: Match result to cache
            country: Country code
            ttl_hours: Custom TTL in hours, uses default if None
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self._redis:
            return False
            
        try:
            cache_key = self._generate_cache_key(product_description, country)
            
            # Serialize result to JSON
            cache_data = result.model_dump_json()
            
            # Set TTL based on confidence and usage patterns
            ttl = timedelta(hours=ttl_hours or self._determine_ttl(result))
            
            # Store in Redis
            await self._redis.setex(cache_key, ttl, cache_data)
            
            # Update caching statistics
            await self._update_cache_stats(cache_key, result)
            
            logger.debug(f"Cached result for product: {product_description[:50]}... "
                        f"(TTL: {ttl.total_seconds()}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error caching result: {str(e)}")
            return False
    
    async def get_cached_batch_match(self, request_hash: str) -> Optional[List[HSCodeMatchResult]]:
        """Retrieve cached batch match results"""
        if not self._redis:
            return None
            
        try:
            cache_key = self._generate_batch_cache_key(request_hash)
            cached_data = await self._redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                results = [HSCodeMatchResult(**item) for item in data]
                
                logger.debug(f"Batch cache hit for hash: {request_hash}")
                return results
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving batch cache: {str(e)}")
            return None
    
    async def cache_batch_results(
        self,
        request_hash: str,
        results: List[HSCodeMatchResult]
    ) -> bool:
        """Cache batch match results"""
        if not self._redis:
            return False
            
        try:
            cache_key = self._generate_batch_cache_key(request_hash)
            
            # Serialize results
            cache_data = json.dumps([result.model_dump() for result in results])
            
            # Cache with shorter TTL for batch results
            ttl = timedelta(hours=self.BATCH_CACHE_TTL_HOURS)
            await self._redis.setex(cache_key, ttl, cache_data)
            
            logger.debug(f"Cached batch results for hash: {request_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching batch results: {str(e)}")
            return False
    
    async def warm_cache_with_common_products(self, hs_matching_service) -> Dict[str, Any]:
        """
        Warm cache with common product descriptions
        
        Args:
            hs_matching_service: Instance of HSCodeMatchingService
            
        Returns:
            Dictionary with warming results and statistics
        """
        if not self._redis:
            return {"error": "Redis not available", "warmed": 0}
        
        warming_results = {
            "total_products": len(self.COMMON_PRODUCTS),
            "successfully_warmed": 0,
            "already_cached": 0,
            "failed": 0,
            "errors": []
        }
        
        logger.info(f"Starting cache warming with {len(self.COMMON_PRODUCTS)} common products")
        
        for product in self.COMMON_PRODUCTS:
            try:
                # Check if already cached
                cached_result = await self.get_cached_match(product)
                
                if cached_result:
                    warming_results["already_cached"] += 1
                    continue
                
                # Match and cache the product
                match_result = await hs_matching_service.match_single_product(
                    product_description=product,
                    country="default",
                    include_alternatives=True,
                    confidence_threshold=0.5
                )
                
                # Cache with longer TTL for warming
                success = await self.cache_match_result(
                    product_description=product,
                    result=match_result,
                    ttl_hours=self.FREQUENT_MATCH_TTL_HOURS
                )
                
                if success:
                    warming_results["successfully_warmed"] += 1
                else:
                    warming_results["failed"] += 1
                    
            except Exception as e:
                error_msg = f"Failed to warm cache for '{product}': {str(e)}"
                logger.error(error_msg)
                warming_results["failed"] += 1
                warming_results["errors"].append(error_msg)
        
        logger.info(f"Cache warming completed: {warming_results}")
        return warming_results
    
    async def invalidate_cache_by_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern
        
        Args:
            pattern: Redis pattern to match keys
            
        Returns:
            Number of keys deleted
        """
        if not self._redis:
            return 0
            
        try:
            # Find matching keys
            keys = await self._redis.keys(pattern)
            
            if keys:
                # Delete all matching keys
                deleted_count = await self._redis.delete(*keys)
                logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
            return 0
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        if not self._redis:
            return {"error": "Redis not available"}
        
        try:
            # Get Redis info
            redis_info = await self._redis.info()
            
            # Get HS code cache statistics
            cache_keys = await self._redis.keys(f"{self.CACHE_KEY_PREFIX}:*")
            batch_keys = await self._redis.keys(f"{self.CACHE_KEY_PREFIX}:batch:*")
            
            # Get hit/miss statistics
            hit_count = await self._redis.get(self._generate_stats_key("hits")) or "0"
            miss_count = await self._redis.get(self._generate_stats_key("misses")) or "0"
            
            total_requests = int(hit_count) + int(miss_count)
            hit_ratio = (int(hit_count) / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "redis_status": "connected",
                "total_cache_entries": len(cache_keys),
                "batch_cache_entries": len(batch_keys),
                "cache_hits": int(hit_count),
                "cache_misses": int(miss_count),
                "hit_ratio_percent": round(hit_ratio, 2),
                "memory_usage_mb": round(redis_info.get("used_memory", 0) / (1024 * 1024), 2),
                "connected_clients": redis_info.get("connected_clients", 0),
                "commands_processed": redis_info.get("total_commands_processed", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {str(e)}")
            return {"error": str(e)}
    
    def _determine_ttl(self, result: HSCodeMatchResult) -> int:
        """Determine appropriate TTL based on result confidence and other factors"""
        confidence = result.primary_match.confidence
        
        if confidence >= 0.95:
            # High confidence matches can be cached longer
            return self.FREQUENT_MATCH_TTL_HOURS
        elif confidence >= 0.8:
            # Medium confidence matches get standard TTL
            return self.DEFAULT_TTL_HOURS
        else:
            # Low confidence matches get shorter TTL
            return self.DEFAULT_TTL_HOURS // 2
    
    async def _update_access_stats(self, cache_key: str):
        """Update access statistics for cache monitoring"""
        try:
            stats_key = self._generate_stats_key("hits")
            await self._redis.incr(stats_key)
            
            # Set expiry on stats key (30 days)
            await self._redis.expire(stats_key, timedelta(days=30))
            
        except Exception as e:
            logger.error(f"Error updating access stats: {str(e)}")
    
    async def _update_cache_stats(self, cache_key: str, result: HSCodeMatchResult):
        """Update caching statistics"""
        try:
            # Track confidence distribution
            confidence_bucket = self._get_confidence_bucket(result.primary_match.confidence)
            confidence_key = self._generate_stats_key(f"confidence:{confidence_bucket}")
            await self._redis.incr(confidence_key)
            await self._redis.expire(confidence_key, timedelta(days=30))
            
            # Track HS code popularity
            hs_code_key = self._generate_stats_key(f"hs_code:{result.primary_match.hs_code}")
            await self._redis.incr(hs_code_key)
            await self._redis.expire(hs_code_key, timedelta(days=30))
            
        except Exception as e:
            logger.error(f"Error updating cache stats: {str(e)}")
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """Get confidence bucket for statistics"""
        if confidence >= 0.95:
            return "very_high"
        elif confidence >= 0.8:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        elif confidence >= 0.4:
            return "low"
        else:
            return "very_low"
    
    async def is_available(self) -> bool:
        """Check if Redis cache is available"""
        if not self._redis:
            return False
            
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False
    
    async def clear_all_cache(self) -> int:
        """Clear all HS code matching cache entries"""
        pattern = f"{self.CACHE_KEY_PREFIX}:*"
        return await self.invalidate_cache_by_pattern(pattern)
    
    async def get_top_cached_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently cached products"""
        if not self._redis:
            return []
        
        try:
            # Get all HS code stats
            pattern = f"{self.STATS_KEY_PREFIX}:hs_code:*"
            keys = await self._redis.keys(pattern)
            
            if not keys:
                return []
            
            # Get counts for all keys
            results = []
            for key in keys:
                count = await self._redis.get(key)
                if count:
                    hs_code = key.split(":")[-1]
                    results.append({
                        "hs_code": hs_code,
                        "access_count": int(count)
                    })
            
            # Sort by access count and return top entries
            results.sort(key=lambda x: x["access_count"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top cached products: {str(e)}")
            return []


# Create singleton instance
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """Get cache service instance for dependency injection"""
    if not await cache_service.is_available():
        # Initialize if not already done
        await cache_service.initialize()
    
    return cache_service


# Fallback mechanism when Redis is unavailable
class NoOpCacheService:
    """No-operation cache service for fallback when Redis is unavailable"""
    
    async def initialize(self) -> bool:
        return False
    
    async def close(self):
        pass
    
    async def get_cached_match(self, product_description: str, country: str = "default") -> Optional[HSCodeMatchResult]:
        return None
    
    async def cache_match_result(self, product_description: str, result: HSCodeMatchResult, country: str = "default", ttl_hours: Optional[int] = None) -> bool:
        return False
    
    async def get_cached_batch_match(self, request_hash: str) -> Optional[List[HSCodeMatchResult]]:
        return None
    
    async def cache_batch_results(self, request_hash: str, results: List[HSCodeMatchResult]) -> bool:
        return False
    
    async def warm_cache_with_common_products(self, hs_matching_service) -> Dict[str, Any]:
        return {"error": "Cache not available", "warmed": 0}
    
    async def invalidate_cache_by_pattern(self, pattern: str) -> int:
        return 0
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        return {"error": "Cache not available"}
    
    async def is_available(self) -> bool:
        return False
    
    async def clear_all_cache(self) -> int:
        return 0
    
    async def get_top_cached_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []


# Fallback instance
noop_cache_service = NoOpCacheService()