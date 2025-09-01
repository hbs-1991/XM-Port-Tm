"""
Unit tests for CacheService

Tests for Redis-based caching functionality for HS code matching.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from src.services.cache_service import CacheService, NoOpCacheService, cache_service
from src.core.openai_config import HSCodeMatchResult, HSCodeResult


class TestCacheService:
    """Test cases for CacheService"""
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client for testing"""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        return mock_redis
    
    @pytest.fixture
    async def cache_service_instance(self, mock_redis):
        """Create CacheService instance with mocked Redis"""
        service = CacheService()
        service._redis = mock_redis
        return service
    
    @pytest.fixture
    def sample_hs_result(self):
        """Sample HS code result for testing"""
        return HSCodeResult(
            hs_code="8471.30.00",
            code_description="Portable automatic data processing machines",
            confidence=0.95,
            chapter="84",
            section="XVI",
            reasoning="Product matches computer hardware classification"
        )
    
    @pytest.fixture
    def sample_match_result(self, sample_hs_result):
        """Sample HS code match result for testing"""
        return HSCodeMatchResult(
            primary_match=sample_hs_result,
            alternative_matches=[],
            processing_time_ms=1500.0,
            query="laptop computer"
        )
    
    async def test_initialize_success(self):
        """Test successful Redis initialization"""
        with patch('redis.asyncio.ConnectionPool.from_url') as mock_pool, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance
            
            service = CacheService()
            result = await service.initialize()
            
            assert result is True
            assert service._redis is not None
            mock_redis_instance.ping.assert_called_once()
    
    async def test_initialize_failure(self):
        """Test Redis initialization failure"""
        with patch('redis.asyncio.ConnectionPool.from_url') as mock_pool:
            mock_pool.side_effect = Exception("Connection failed")
            
            service = CacheService()
            result = await service.initialize()
            
            assert result is False
            assert service._redis is None
    
    async def test_generate_cache_key(self):
        """Test cache key generation"""
        service = CacheService()
        
        key1 = service._generate_cache_key("laptop computer", "default")
        key2 = service._generate_cache_key("laptop computer", "default")
        key3 = service._generate_cache_key("desktop computer", "default")
        key4 = service._generate_cache_key("laptop computer", "turkmenistan")
        
        # Same inputs should generate same key
        assert key1 == key2
        
        # Different inputs should generate different keys
        assert key1 != key3
        assert key1 != key4
        
        # Keys should follow expected format
        assert key1.startswith("xm_port:hs_match:default:")
        assert key4.startswith("xm_port:hs_match:turkmenistan:")
    
    async def test_cache_miss(self, cache_service_instance, mock_redis):
        """Test cache miss scenario"""
        mock_redis.get.return_value = None
        
        result = await cache_service_instance.get_cached_match("test product")
        
        assert result is None
        mock_redis.get.assert_called_once()
    
    async def test_cache_hit(self, cache_service_instance, mock_redis, sample_match_result):
        """Test cache hit scenario"""
        # Mock Redis return value
        cached_data = sample_match_result.model_dump_json()
        mock_redis.get.return_value = cached_data
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        result = await cache_service_instance.get_cached_match("laptop computer")
        
        assert result is not None
        assert result.primary_match.hs_code == "8471.30.00"
        assert result.primary_match.confidence == 0.95
        mock_redis.get.assert_called_once()
        mock_redis.incr.assert_called_once()  # Stats update
    
    async def test_cache_match_result(self, cache_service_instance, mock_redis, sample_match_result):
        """Test caching match result"""
        mock_redis.setex.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        result = await cache_service_instance.cache_match_result(
            product_description="laptop computer",
            result=sample_match_result,
            country="default"
        )
        
        assert result is True
        mock_redis.setex.assert_called_once()
        
        # Verify the call arguments
        args, kwargs = mock_redis.setex.call_args
        cache_key, ttl, cached_data = args
        
        assert cache_key.startswith("xm_port:hs_match:default:")
        assert isinstance(ttl, timedelta)
        
        # Verify cached data can be deserialized
        deserialized = HSCodeMatchResult.model_validate_json(cached_data)
        assert deserialized.primary_match.hs_code == "8471.30.00"
    
    async def test_batch_caching(self, cache_service_instance, mock_redis):
        """Test batch result caching and retrieval"""
        # Test data
        batch_hash = "test_hash_123"
        sample_results = [
            HSCodeMatchResult(
                primary_match=HSCodeResult(
                    hs_code="8471.30.00",
                    code_description="Computer hardware",
                    confidence=0.9,
                    chapter="84",
                    section="XVI",
                    reasoning="Test reasoning"
                ),
                alternative_matches=[],
                processing_time_ms=1000.0,
                query="laptop"
            )
        ]
        
        # Test caching
        mock_redis.setex.return_value = True
        cache_result = await cache_service_instance.cache_batch_results(batch_hash, sample_results)
        assert cache_result is True
        
        # Test retrieval
        cached_data = json.dumps([result.model_dump() for result in sample_results])
        mock_redis.get.return_value = cached_data
        
        retrieved_results = await cache_service_instance.get_cached_batch_match(batch_hash)
        
        assert retrieved_results is not None
        assert len(retrieved_results) == 1
        assert retrieved_results[0].primary_match.hs_code == "8471.30.00"
    
    async def test_cache_invalidation(self, cache_service_instance, mock_redis):
        """Test cache invalidation by pattern"""
        mock_redis.keys.return_value = ["key1", "key2", "key3"]
        mock_redis.delete.return_value = 3
        
        result = await cache_service_instance.invalidate_cache_by_pattern("test:*")
        
        assert result == 3
        mock_redis.keys.assert_called_once_with("test:*")
        mock_redis.delete.assert_called_once_with("key1", "key2", "key3")
    
    async def test_cache_statistics(self, cache_service_instance, mock_redis):
        """Test cache statistics retrieval"""
        # Mock Redis info and operations
        mock_redis.info.return_value = {
            "used_memory": 1024 * 1024 * 5,  # 5MB
            "connected_clients": 3,
            "total_commands_processed": 1000
        }
        mock_redis.keys.side_effect = [
            ["cache:1", "cache:2", "cache:3"],  # Regular cache entries
            ["batch:1", "batch:2"]              # Batch cache entries
        ]
        mock_redis.get.side_effect = ["150", "50"]  # hits, misses
        
        stats = await cache_service_instance.get_cache_statistics()
        
        assert stats["redis_status"] == "connected"
        assert stats["total_cache_entries"] == 3
        assert stats["batch_cache_entries"] == 2
        assert stats["cache_hits"] == 150
        assert stats["cache_misses"] == 50
        assert stats["hit_ratio_percent"] == 75.0
        assert stats["memory_usage_mb"] == 5.0
    
    async def test_determine_ttl_by_confidence(self):
        """Test TTL determination based on confidence levels"""
        service = CacheService()
        
        # High confidence result
        high_conf_result = HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8471.30.00",
                code_description="Test",
                confidence=0.97,
                chapter="84",
                section="XVI",
                reasoning="High confidence"
            ),
            alternative_matches=[],
            processing_time_ms=1000.0,
            query="test"
        )
        
        # Medium confidence result
        medium_conf_result = HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8471.30.00",
                code_description="Test",
                confidence=0.85,
                chapter="84",
                section="XVI",
                reasoning="Medium confidence"
            ),
            alternative_matches=[],
            processing_time_ms=1000.0,
            query="test"
        )
        
        # Low confidence result
        low_conf_result = HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8471.30.00",
                code_description="Test",
                confidence=0.6,
                chapter="84",
                section="XVI",
                reasoning="Low confidence"
            ),
            alternative_matches=[],
            processing_time_ms=1000.0,
            query="test"
        )
        
        # Test TTL determination
        assert service._determine_ttl(high_conf_result) == service.FREQUENT_MATCH_TTL_HOURS
        assert service._determine_ttl(medium_conf_result) == service.DEFAULT_TTL_HOURS
        assert service._determine_ttl(low_conf_result) == service.DEFAULT_TTL_HOURS // 2
    
    async def test_is_available(self, cache_service_instance, mock_redis):
        """Test cache availability check"""
        # Test available
        mock_redis.ping.return_value = True
        assert await cache_service_instance.is_available() is True
        
        # Test unavailable
        mock_redis.ping.side_effect = Exception("Connection failed")
        assert await cache_service_instance.is_available() is False
    
    async def test_cache_error_handling(self, cache_service_instance, mock_redis):
        """Test error handling in cache operations"""
        # Test get_cached_match with Redis error
        mock_redis.get.side_effect = Exception("Redis error")
        
        result = await cache_service_instance.get_cached_match("test product")
        assert result is None
        
        # Test cache_match_result with Redis error
        mock_redis.setex.side_effect = Exception("Redis error")
        
        sample_result = HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8471.30.00",
                code_description="Test",
                confidence=0.9,
                chapter="84",
                section="XVI",
                reasoning="Test"
            ),
            alternative_matches=[],
            processing_time_ms=1000.0,
            query="test"
        )
        
        cache_result = await cache_service_instance.cache_match_result(
            "test product", sample_result
        )
        assert cache_result is False


class TestNoOpCacheService:
    """Test cases for NoOpCacheService fallback"""
    
    async def test_noop_cache_operations(self):
        """Test all NoOpCacheService methods return expected fallback values"""
        service = NoOpCacheService()
        
        # Test initialization
        assert await service.initialize() is False
        
        # Test availability
        assert await service.is_available() is False
        
        # Test cache operations
        assert await service.get_cached_match("test") is None
        assert await service.cache_match_result("test", MagicMock(), "default") is False
        assert await service.get_cached_batch_match("hash") is None
        assert await service.cache_batch_results("hash", []) is False
        
        # Test maintenance operations
        assert await service.invalidate_cache_by_pattern("*") == 0
        assert await service.clear_all_cache() == 0
        
        # Test statistics
        stats = await service.get_cache_statistics()
        assert "error" in stats
        
        # Test warming
        warming_result = await service.warm_cache_with_common_products(MagicMock())
        assert warming_result["warmed"] == 0
        
        # Test top products
        top_products = await service.get_top_cached_products()
        assert top_products == []
    
    async def test_noop_close(self):
        """Test NoOpCacheService close method"""
        service = NoOpCacheService()
        # Should not raise exception
        await service.close()


class TestCacheIntegration:
    """Integration tests for cache service"""
    
    @pytest.fixture
    def mock_hs_matching_service(self):
        """Mock HS matching service for cache warming"""
        service = AsyncMock()
        service.match_single_product.return_value = HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8471.30.00",
                code_description="Computer hardware",
                confidence=0.9,
                chapter="84",
                section="XVI",
                reasoning="Test match"
            ),
            alternative_matches=[],
            processing_time_ms=1000.0,
            query="test product"
        )
        return service
    
    async def test_cache_warming_success(self, cache_service_instance, mock_redis, mock_hs_matching_service):
        """Test successful cache warming"""
        # Mock cache operations
        mock_redis.get.return_value = None  # No existing cache
        mock_redis.setex.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        # Test warming
        result = await cache_service_instance.warm_cache_with_common_products(mock_hs_matching_service)
        
        assert result["total_products"] > 0
        assert result["successfully_warmed"] > 0
        assert result["failed"] == 0
        
        # Verify service was called for each product
        assert mock_hs_matching_service.match_single_product.call_count == result["total_products"]
    
    async def test_cache_warming_with_existing_cache(self, cache_service_instance, mock_redis, mock_hs_matching_service):
        """Test cache warming when some products are already cached"""
        # Mock some products already cached
        def mock_get_side_effect(key):
            if "wheat" in key or "cotton" in key:
                return json.dumps({
                    "primary_match": {
                        "hs_code": "1001.90.00",
                        "code_description": "Wheat",
                        "confidence": 0.9,
                        "chapter": "10",
                        "section": "II",
                        "reasoning": "Cached result"
                    },
                    "alternative_matches": [],
                    "processing_time_ms": 0.0,
                    "query": "wheat"
                })
            return None
        
        mock_redis.get.side_effect = mock_get_side_effect
        mock_redis.setex.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        result = await cache_service_instance.warm_cache_with_common_products(mock_hs_matching_service)
        
        assert result["already_cached"] >= 2  # wheat and cotton
        assert result["successfully_warmed"] > 0
        assert result["total_products"] == result["already_cached"] + result["successfully_warmed"] + result["failed"]
    
    async def test_top_cached_products(self, cache_service_instance, mock_redis):
        """Test retrieving top cached products"""
        # Mock Redis keys and get operations
        mock_redis.keys.return_value = [
            "xm_port:hs_stats:hs_code:8471.30.00",
            "xm_port:hs_stats:hs_code:1001.90.00",
            "xm_port:hs_stats:hs_code:5208.11.00"
        ]
        
        # Mock access counts
        def mock_get_side_effect(key):
            if "8471.30.00" in key:
                return "150"
            elif "1001.90.00" in key:
                return "75"
            elif "5208.11.00" in key:
                return "25"
            return "0"
        
        mock_redis.get.side_effect = mock_get_side_effect
        
        top_products = await cache_service_instance.get_top_cached_products(limit=2)
        
        assert len(top_products) == 2
        assert top_products[0]["hs_code"] == "8471.30.00"
        assert top_products[0]["access_count"] == 150
        assert top_products[1]["hs_code"] == "1001.90.00"
        assert top_products[1]["access_count"] == 75
    
    async def test_confidence_bucketing(self):
        """Test confidence bucket classification"""
        service = CacheService()
        
        assert service._get_confidence_bucket(0.98) == "very_high"
        assert service._get_confidence_bucket(0.92) == "high"
        assert service._get_confidence_bucket(0.75) == "medium"
        assert service._get_confidence_bucket(0.55) == "low"
        assert service._get_confidence_bucket(0.25) == "very_low"
    
    async def test_cache_service_close(self, cache_service_instance, mock_redis):
        """Test cache service cleanup"""
        mock_pool = AsyncMock()
        cache_service_instance._connection_pool = mock_pool
        
        await cache_service_instance.close()
        
        mock_redis.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
    
    async def test_cache_service_singleton(self):
        """Test cache service singleton behavior"""
        from src.services.cache_service import cache_service
        
        # Should be same instance
        service1 = cache_service
        service2 = cache_service
        
        assert service1 is service2


class TestCacheServiceErrorScenarios:
    """Test error scenarios and edge cases"""
    
    async def test_redis_unavailable_fallback(self):
        """Test behavior when Redis is completely unavailable"""
        service = CacheService()
        service._redis = None
        
        # All operations should return safe defaults
        assert await service.get_cached_match("test") is None
        assert await service.cache_match_result("test", MagicMock()) is False
        assert await service.get_cached_batch_match("hash") is None
        assert await service.cache_batch_results("hash", []) is False
        assert await service.invalidate_cache_by_pattern("*") == 0
        assert await service.is_available() is False
    
    async def test_redis_operation_failures(self, cache_service_instance, mock_redis):
        """Test handling of Redis operation failures"""
        # Test get operation failure
        mock_redis.get.side_effect = Exception("Redis get failed")
        result = await cache_service_instance.get_cached_match("test")
        assert result is None
        
        # Test set operation failure
        mock_redis.setex.side_effect = Exception("Redis set failed")
        sample_result = MagicMock()
        cache_result = await cache_service_instance.cache_match_result("test", sample_result)
        assert cache_result is False
        
        # Test stats operation failure
        mock_redis.info.side_effect = Exception("Redis info failed")
        stats = await cache_service_instance.get_cache_statistics()
        assert "error" in stats
    
    async def test_malformed_cached_data(self, cache_service_instance, mock_redis):
        """Test handling of malformed cached data"""
        # Return invalid JSON
        mock_redis.get.return_value = "invalid json data"
        
        result = await cache_service_instance.get_cached_match("test product")
        assert result is None
    
    async def test_empty_batch_requests(self):
        """Test batch hash generation with edge cases"""
        service = CacheService()
        
        # Empty requests should still generate valid hash
        empty_requests = []
        hash_result = service._generate_batch_hash(empty_requests)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 16  # Should be 16 char hash