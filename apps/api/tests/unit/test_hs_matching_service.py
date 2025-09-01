"""Unit tests for HS Code Matching Service."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal

from src.services.hs_matching_service import HSCodeMatchingService, HSCodeMatchRequest, HSCodeBatchMatchRequest
from src.core.openai_config import HSCodeResult, HSCodeMatchResult
from src.services.cache_service import CacheService


@pytest.fixture
def hs_service():
    """Create an HS matching service instance for testing."""
    return HSCodeMatchingService()


@pytest.fixture
def mock_hs_code_result():
    """Create a mock HS code result for testing."""
    return HSCodeResult(
        hs_code="8471.30.00",
        code_description="Portable automatic data processing machines, not exceeding 10 kg",
        confidence=0.92,
        chapter="84",
        section="XVI",
        reasoning="Product matches criteria for portable computing devices under 10kg"
    )


@pytest.fixture
def mock_openai_runner_result(mock_hs_code_result):
    """Create a mock OpenAI Runner result."""
    result = MagicMock()
    result.final_output = mock_hs_code_result
    return result


class TestHSCodeMatchingServiceInitialization:
    """Test service initialization and configuration."""
    
    def test_service_initialization(self, hs_service):
        """Test service initializes correctly with default configuration."""
        assert hs_service.MAX_RETRY_ATTEMPTS == 3
        assert hs_service.RETRY_DELAY_SECONDS == 1.0
        assert hs_service.BATCH_SIZE_LIMIT == 50
        assert hs_service.TIMEOUT_SECONDS == 30
        assert hs_service.HIGH_CONFIDENCE_THRESHOLD == 0.85
        assert hs_service.MEDIUM_CONFIDENCE_THRESHOLD == 0.7
        assert hs_service.LOW_CONFIDENCE_THRESHOLD == 0.5
        assert hs_service._agents_cache == {}


class TestSingleProductMatching:
    """Test single product HS code matching functionality."""
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_match_single_product_success(self, mock_runner, hs_service, mock_openai_runner_result):
        """Test successful single product matching."""
        mock_runner.return_value = mock_openai_runner_result
        
        result = await hs_service.match_single_product(
            product_description="MacBook Pro laptop computer",
            country="default",
            include_alternatives=True,
            confidence_threshold=0.7
        )
        
        assert isinstance(result, HSCodeMatchResult)
        assert result.primary_match.hs_code == "8471.30.00"
        assert result.primary_match.confidence == 0.92
        assert result.query == "MacBook Pro laptop computer"
        assert result.processing_time_ms > 0
        assert mock_runner.call_count == 1
    
    async def test_match_single_product_invalid_description(self, hs_service):
        """Test matching with invalid product description."""
        with pytest.raises(ValueError, match="Product description must be at least 5 characters long"):
            await hs_service.match_single_product("")
        
        with pytest.raises(ValueError, match="Product description must be at least 5 characters long"):
            await hs_service.match_single_product("   ")
        
        with pytest.raises(ValueError, match="Product description must be at least 5 characters long"):
            await hs_service.match_single_product("abc")
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_match_single_product_with_retry_success(self, mock_runner, hs_service, mock_openai_runner_result):
        """Test successful matching after retry on first failure."""
        # First call fails, second succeeds
        mock_runner.side_effect = [
            ConnectionError("Network error"), 
            mock_openai_runner_result
        ]
        
        result = await hs_service.match_single_product("laptop computer")
        
        assert isinstance(result, HSCodeMatchResult)
        assert result.primary_match.hs_code == "8471.30.00"
        assert mock_runner.call_count == 2
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_match_single_product_timeout_error(self, mock_runner, hs_service):
        """Test matching with timeout error."""
        mock_runner.side_effect = asyncio.TimeoutError("Request timed out")
        
        with pytest.raises(TimeoutError, match="HS code matching timed out after 3 attempts"):
            await hs_service.match_single_product("laptop computer")
        
        assert mock_runner.call_count == 3  # All retry attempts
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_match_single_product_connection_error(self, mock_runner, hs_service):
        """Test matching with persistent connection error."""
        mock_runner.side_effect = ConnectionError("Cannot connect to OpenAI API")
        
        with pytest.raises(ConnectionError, match="Failed to connect to OpenAI API"):
            await hs_service.match_single_product("laptop computer")
        
        assert mock_runner.call_count == 3  # All retry attempts


class TestBatchProductMatching:
    """Test batch product HS code matching functionality."""
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_match_batch_products_success(self, mock_runner, hs_service, mock_openai_runner_result):
        """Test successful batch matching."""
        mock_runner.return_value = mock_openai_runner_result
        
        requests = [
            HSCodeMatchRequest(product_description="laptop computer"),
            HSCodeMatchRequest(product_description="smartphone device"),
            HSCodeMatchRequest(product_description="wireless headphones")
        ]
        
        results = await hs_service.match_batch_products(requests, max_concurrent=2)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, HSCodeMatchResult)
            assert result.primary_match.hs_code == "8471.30.00"
            assert result.primary_match.confidence == 0.92
        
        assert mock_runner.call_count == 3
    
    async def test_match_batch_products_exceeds_limit(self, hs_service):
        """Test batch matching with size exceeding limit."""
        requests = [
            HSCodeMatchRequest(product_description=f"product {i}") 
            for i in range(51)  # Exceeds BATCH_SIZE_LIMIT of 50
        ]
        
        with pytest.raises(ValueError, match="Batch size 51 exceeds limit of 50"):
            await hs_service.match_batch_products(requests)
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_match_batch_products_with_failures(self, mock_runner, hs_service, mock_openai_runner_result):
        """Test batch matching with some failures."""
        # First request succeeds, second fails, third succeeds
        mock_runner.side_effect = [
            mock_openai_runner_result,
            ConnectionError("API error"),
            mock_openai_runner_result
        ]
        
        requests = [
            HSCodeMatchRequest(product_description="laptop computer"),
            HSCodeMatchRequest(product_description="smartphone device"),
            HSCodeMatchRequest(product_description="wireless headphones")
        ]
        
        results = await hs_service.match_batch_products(requests, max_concurrent=1)
        
        assert len(results) == 3
        
        # First and third should be successful
        assert results[0].primary_match.hs_code == "8471.30.00"
        assert results[2].primary_match.hs_code == "8471.30.00"
        
        # Second should be error result
        assert results[1].primary_match.hs_code == "ERROR"
        assert results[1].primary_match.confidence == 0.0


class TestUtilityMethods:
    """Test utility and helper methods."""
    
    def test_clean_product_description(self, hs_service):
        """Test product description cleaning."""
        # Test whitespace normalization
        assert hs_service._clean_product_description("  laptop   computer  ") == "laptop computer"
        
        # Test noise word removal
        assert hs_service._clean_product_description("various laptop computers") == "laptop computers"
        assert hs_service._clean_product_description("assorted mixed type of products") == "of products"
        
        # Test combined cleaning
        assert hs_service._clean_product_description("  various   laptop   computers  ") == "laptop computers"
    
    def test_build_search_query(self, hs_service):
        """Test search query building."""
        # Without alternatives
        query = hs_service._build_search_query("laptop computer", False)
        assert "laptop computer" in query
        assert "alternative HS codes" not in query
        assert "detailed reasoning" in query
        
        # With alternatives
        query = hs_service._build_search_query("laptop computer", True)
        assert "laptop computer" in query
        assert "alternative HS codes" in query
        assert "detailed reasoning" in query
    
    def test_get_confidence_level_description(self, hs_service):
        """Test confidence level descriptions."""
        assert hs_service.get_confidence_level_description(0.95) == "High"
        assert hs_service.get_confidence_level_description(0.80) == "Medium"
        assert hs_service.get_confidence_level_description(0.60) == "Low"
        assert hs_service.get_confidence_level_description(0.40) == "Very Low"
    
    def test_should_require_manual_review(self, hs_service):
        """Test manual review requirement logic."""
        assert hs_service.should_require_manual_review(0.90) is False  # High confidence
        assert hs_service.should_require_manual_review(0.75) is False  # Medium confidence
        assert hs_service.should_require_manual_review(0.65) is True   # Below medium threshold
        assert hs_service.should_require_manual_review(0.40) is True   # Low confidence
    
    def test_create_error_result(self, hs_service):
        """Test error result creation."""
        result = hs_service._create_error_result("test product", "Test error message")
        
        assert isinstance(result, HSCodeMatchResult)
        assert result.primary_match.hs_code == "ERROR"
        assert result.primary_match.confidence == 0.0
        assert result.primary_match.code_description == "Failed to match HS code"
        assert "Test error message" in result.primary_match.reasoning
        assert result.query == "test product"
        assert result.processing_time_ms == 0.0
        assert len(result.alternative_matches) == 0


class TestAgentCaching:
    """Test agent caching functionality."""
    
    def test_agent_caching(self, hs_service):
        """Test that agents are cached properly."""
        # Initially cache should be empty
        assert len(hs_service._agents_cache) == 0
        
        # Get or create agent for default country
        agent1 = hs_service._get_or_create_agent("default")
        assert len(hs_service._agents_cache) == 1
        assert "default" in hs_service._agents_cache
        
        # Get same agent again - should return cached version
        agent2 = hs_service._get_or_create_agent("default")
        assert agent1 is agent2
        assert len(hs_service._agents_cache) == 1
        
        # Get agent for different country - should create new one
        agent3 = hs_service._get_or_create_agent("turkmenistan")
        assert agent3 is not agent1
        assert len(hs_service._agents_cache) == 2
        assert "turkmenistan" in hs_service._agents_cache


class TestServiceHealth:
    """Test service health monitoring."""
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_get_service_health_healthy(self, mock_runner, hs_service, mock_openai_runner_result):
        """Test service health check when service is healthy."""
        mock_runner.return_value = mock_openai_runner_result
        
        health = await hs_service.get_service_health()
        
        assert health["status"] == "healthy"
        assert "response_time_ms" in health
        assert health["response_time_ms"] > 0
        assert "available_countries" in health
        assert "cache_size" in health
        assert "configuration" in health
        
        # Verify configuration includes expected values
        config = health["configuration"]
        assert config["max_retry_attempts"] == 3
        assert config["timeout_seconds"] == 30
        assert config["batch_size_limit"] == 50
        assert "confidence_thresholds" in config
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_get_service_health_unhealthy(self, mock_runner, hs_service):
        """Test service health check when service is unhealthy."""
        mock_runner.side_effect = ConnectionError("Cannot connect to OpenAI API")
        
        health = await hs_service.get_service_health()
        
        assert health["status"] == "unhealthy"
        assert "error" in health
        assert "Cannot connect to OpenAI API" in health["error"]
        assert "available_countries" in health
        assert "cache_size" in health


class TestRequestValidation:
    """Test request validation and schemas."""
    
    def test_hs_code_match_request_valid(self):
        """Test valid HS code match request creation."""
        request = HSCodeMatchRequest(
            product_description="laptop computer",
            country="default",
            include_alternatives=True,
            confidence_threshold=0.8
        )
        
        assert request.product_description == "laptop computer"
        assert request.country == "default"
        assert request.include_alternatives is True
        assert request.confidence_threshold == 0.8
    
    def test_hs_code_match_request_defaults(self):
        """Test HS code match request with default values."""
        request = HSCodeMatchRequest(product_description="laptop computer")
        
        assert request.product_description == "laptop computer"
        assert request.country == "default"
        assert request.include_alternatives is True
        assert request.confidence_threshold == 0.7
    
    def test_hs_code_match_request_validation_errors(self):
        """Test HS code match request validation errors."""
        # Too short product description
        with pytest.raises(ValueError):
            HSCodeMatchRequest(product_description="abc")
        
        # Too long product description  
        with pytest.raises(ValueError):
            HSCodeMatchRequest(product_description="x" * 501)
        
        # Invalid confidence threshold
        with pytest.raises(ValueError):
            HSCodeMatchRequest(product_description="laptop", confidence_threshold=1.5)
        
        with pytest.raises(ValueError):
            HSCodeMatchRequest(product_description="laptop", confidence_threshold=-0.1)
    
    def test_hs_code_batch_request_valid(self):
        """Test valid batch request creation."""
        requests = [
            HSCodeMatchRequest(product_description="laptop computer"),
            HSCodeMatchRequest(product_description="smartphone device")
        ]
        
        batch_request = HSCodeBatchMatchRequest(
            products=requests,
            country="turkmenistan"
        )
        
        assert len(batch_request.products) == 2
        assert batch_request.country == "turkmenistan"
    
    def test_hs_code_batch_request_validation_errors(self):
        """Test batch request validation errors."""
        # Empty products list
        with pytest.raises(ValueError):
            HSCodeBatchMatchRequest(products=[])
        
        # Too many products
        requests = [HSCodeMatchRequest(product_description=f"product {i}") for i in range(101)]
        with pytest.raises(ValueError):
            HSCodeBatchMatchRequest(products=requests)


@pytest.mark.asyncio
class TestAsyncBehavior:
    """Test async behavior and concurrency."""
    
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_concurrent_requests_semaphore(self, mock_runner, hs_service, mock_openai_runner_result):
        """Test that concurrent requests are properly limited by semaphore."""
        # Simulate slow API calls
        async def slow_api_call(*args, **kwargs):
            await asyncio.sleep(0.1)
            return mock_openai_runner_result
        
        mock_runner.side_effect = slow_api_call
        
        requests = [
            HSCodeMatchRequest(product_description=f"product {i}") 
            for i in range(10)
        ]
        
        start_time = asyncio.get_event_loop().time()
        results = await hs_service.match_batch_products(requests, max_concurrent=3)
        end_time = asyncio.get_event_loop().time()
        
        # With max_concurrent=3 and 0.1s per request, should take at least 4 batches
        # 10 requests / 3 concurrent = 4 batches (3,3,3,1) * 0.1s = ~0.4s minimum
        assert end_time - start_time >= 0.3  # Allow some tolerance
        assert len(results) == 10
        assert mock_runner.call_count == 10


@pytest.mark.asyncio
class TestCacheIntegration:
    """Test cache integration with HS matching service."""
    
    @pytest.fixture
    async def mock_cache_service(self):
        """Mock cache service for testing."""
        cache_service = AsyncMock()
        cache_service.is_available.return_value = True
        cache_service.get_cached_match.return_value = None  # Default to cache miss
        cache_service.cache_match_result.return_value = True
        cache_service.get_cached_batch_match.return_value = None
        cache_service.cache_batch_results.return_value = True
        return cache_service
    
    @patch('src.services.hs_matching_service.get_cache_service')
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_cache_hit_single_product(self, mock_runner, mock_get_cache_service, hs_service, mock_hs_code_result):
        """Test cache hit for single product matching."""
        # Setup cache service mock
        mock_cache_service = AsyncMock()
        cached_result = HSCodeMatchResult(
            primary_match=mock_hs_code_result,
            alternative_matches=[],
            processing_time_ms=0.0,
            query="laptop computer"
        )
        mock_cache_service.get_cached_match.return_value = cached_result
        mock_get_cache_service.return_value = mock_cache_service
        
        result = await hs_service.match_single_product("laptop computer")
        
        # Should return cached result without calling OpenAI
        assert result == cached_result
        assert mock_runner.call_count == 0  # OpenAI not called
        mock_cache_service.get_cached_match.assert_called_once()
    
    @patch('src.services.hs_matching_service.get_cache_service')
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_cache_miss_and_cache_result(self, mock_runner, mock_get_cache_service, hs_service, mock_openai_runner_result):
        """Test cache miss scenario with subsequent caching."""
        # Setup cache service mock
        mock_cache_service = AsyncMock()
        mock_cache_service.get_cached_match.return_value = None  # Cache miss
        mock_cache_service.cache_match_result.return_value = True
        mock_get_cache_service.return_value = mock_cache_service
        
        # Setup OpenAI mock
        mock_runner.return_value = mock_openai_runner_result
        
        result = await hs_service.match_single_product("laptop computer")
        
        # Should call OpenAI and cache result
        assert mock_runner.call_count == 1
        mock_cache_service.get_cached_match.assert_called_once()
        mock_cache_service.cache_match_result.assert_called_once()
        
        # Verify cache call arguments
        cache_args = mock_cache_service.cache_match_result.call_args
        assert cache_args[1]['product_description'] == "laptop computer"
        assert cache_args[1]['country'] == "default"
    
    @patch('src.services.hs_matching_service.get_cache_service')
    async def test_batch_cache_hit(self, mock_get_cache_service, hs_service, mock_hs_code_result):
        """Test batch cache hit scenario."""
        # Setup cache service mock
        mock_cache_service = AsyncMock()
        cached_results = [
            HSCodeMatchResult(
                primary_match=mock_hs_code_result,
                alternative_matches=[],
                processing_time_ms=0.0,
                query=f"product {i}"
            ) for i in range(3)
        ]
        mock_cache_service.get_cached_batch_match.return_value = cached_results
        mock_get_cache_service.return_value = mock_cache_service
        
        requests = [HSCodeMatchRequest(product_description=f"product {i}") for i in range(3)]
        results = await hs_service.match_batch_products(requests)
        
        # Should return cached results
        assert len(results) == 3
        assert results == cached_results
        mock_cache_service.get_cached_batch_match.assert_called_once()
    
    @patch('src.services.hs_matching_service.get_cache_service')
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_batch_cache_miss_and_cache(self, mock_runner, mock_get_cache_service, hs_service, mock_openai_runner_result):
        """Test batch cache miss with subsequent individual caching."""
        # Setup cache service mock
        mock_cache_service = AsyncMock()
        mock_cache_service.get_cached_batch_match.return_value = None  # Batch cache miss
        mock_cache_service.get_cached_match.return_value = None  # Individual cache miss
        mock_cache_service.cache_match_result.return_value = True
        mock_cache_service.cache_batch_results.return_value = True
        mock_get_cache_service.return_value = mock_cache_service
        
        # Setup OpenAI mock
        mock_runner.return_value = mock_openai_runner_result
        
        requests = [HSCodeMatchRequest(product_description=f"product {i}") for i in range(2)]
        results = await hs_service.match_batch_products(requests)
        
        # Should call OpenAI for each product and cache results
        assert len(results) == 2
        assert mock_runner.call_count == 2
        mock_cache_service.get_cached_batch_match.assert_called_once()
        mock_cache_service.cache_batch_results.assert_called_once()
    
    @patch('src.services.hs_matching_service.get_cache_service')
    async def test_cache_service_unavailable_fallback(self, mock_get_cache_service, hs_service):
        """Test fallback behavior when cache service is unavailable."""
        # Setup unavailable cache service
        mock_cache_service = AsyncMock()
        mock_cache_service.is_available.return_value = False
        mock_get_cache_service.side_effect = Exception("Cache unavailable")
        
        # Should use NoOpCacheService fallback
        cache_service = await hs_service._get_cache_service()
        assert cache_service is not None
        
        # Fallback service should return appropriate defaults
        assert await cache_service.get_cached_match("test") is None
        assert await cache_service.cache_match_result("test", MagicMock()) is False
    
    async def test_batch_hash_generation(self, hs_service):
        """Test batch hash generation for consistent caching."""
        requests1 = [
            HSCodeMatchRequest(product_description="laptop", country="default", confidence_threshold=0.7),
            HSCodeMatchRequest(product_description="mouse", country="default", confidence_threshold=0.8)
        ]
        
        requests2 = [
            HSCodeMatchRequest(product_description="mouse", country="default", confidence_threshold=0.8),
            HSCodeMatchRequest(product_description="laptop", country="default", confidence_threshold=0.7)
        ]
        
        # Different order should produce same hash
        hash1 = hs_service._generate_batch_hash(requests1)
        hash2 = hs_service._generate_batch_hash(requests2)
        
        assert hash1 == hash2
        assert len(hash1) == 16  # Should be 16 character hash
    
    @patch('src.services.hs_matching_service.get_cache_service')
    async def test_cache_warming(self, mock_get_cache_service, hs_service):
        """Test cache warming functionality."""
        mock_cache_service = AsyncMock()
        mock_cache_service.is_available.return_value = True
        mock_cache_service.warm_cache_with_common_products.return_value = {
            "total_products": 10,
            "successfully_warmed": 8,
            "already_cached": 1,
            "failed": 1,
            "errors": ["Error with one product"]
        }
        mock_get_cache_service.return_value = mock_cache_service
        
        result = await hs_service.warm_cache()
        
        assert result["total_products"] == 10
        assert result["successfully_warmed"] == 8
        assert result["already_cached"] == 1
        assert result["failed"] == 1
        mock_cache_service.warm_cache_with_common_products.assert_called_once_with(hs_service)
    
    @patch('src.services.hs_matching_service.get_cache_service')
    async def test_cache_invalidation(self, mock_get_cache_service, hs_service):
        """Test cache invalidation functionality."""
        mock_cache_service = AsyncMock()
        mock_cache_service.is_available.return_value = True
        mock_cache_service.invalidate_cache_by_pattern.return_value = 25
        mock_get_cache_service.return_value = mock_cache_service
        
        result = await hs_service.invalidate_cache()
        
        assert result["invalidated"] == 25
        assert result["pattern"] == "xm_port:hs_match:*"
        assert result["status"] == "success"
        mock_cache_service.invalidate_cache_by_pattern.assert_called_once_with("xm_port:hs_match:*")
    
    @patch('src.services.hs_matching_service.get_cache_service')
    async def test_cache_statistics(self, mock_get_cache_service, hs_service):
        """Test cache statistics retrieval."""
        mock_cache_service = AsyncMock()
        mock_stats = {
            "redis_status": "connected",
            "total_cache_entries": 150,
            "cache_hits": 1200,
            "cache_misses": 300,
            "hit_ratio_percent": 80.0
        }
        mock_cache_service.get_cache_statistics.return_value = mock_stats
        mock_get_cache_service.return_value = mock_cache_service
        
        result = await hs_service.get_cache_statistics()
        
        assert result == mock_stats
        mock_cache_service.get_cache_statistics.assert_called_once()
    
    @patch('src.services.hs_matching_service.get_cache_service')
    @patch('src.services.hs_matching_service.Runner.run')
    async def test_service_health_with_cache(self, mock_runner, mock_get_cache_service, hs_service, mock_openai_runner_result):
        """Test service health check including cache status."""
        # Setup cache service mock
        mock_cache_service = AsyncMock()
        mock_cache_service.is_available.return_value = True
        mock_cache_service.get_cache_statistics.return_value = {
            "redis_status": "connected",
            "hit_ratio_percent": 75.0
        }
        mock_get_cache_service.return_value = mock_cache_service
        
        # Setup OpenAI mock
        mock_runner.return_value = mock_openai_runner_result
        
        health = await hs_service.get_service_health()
        
        assert health["status"] == "healthy"
        assert "openai_response_time_ms" in health
        assert health["cache_service"]["available"] is True
        assert health["cache_service"]["statistics"]["redis_status"] == "connected"
        mock_cache_service.get_cache_statistics.assert_called_once()
    
    @patch('src.services.hs_matching_service.get_cache_service')
    async def test_service_health_openai_failure_cache_available(self, mock_get_cache_service, hs_service):
        """Test service health when OpenAI fails but cache is available."""
        # Setup cache service mock
        mock_cache_service = AsyncMock()
        mock_cache_service.is_available.return_value = True
        mock_cache_service.get_cache_statistics.return_value = {"redis_status": "connected"}
        mock_get_cache_service.return_value = mock_cache_service
        
        # Mock OpenAI failure
        with patch('src.services.hs_matching_service.Runner.run', side_effect=Exception("OpenAI failed")):
            health = await hs_service.get_service_health()
        
        assert health["status"] == "unhealthy"
        assert "error" in health
        assert health["cache_service"]["available"] is True
        assert health["cache_service"]["statistics"]["redis_status"] == "connected"