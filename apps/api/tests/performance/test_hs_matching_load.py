"""
Load tests for HS Code Matching Service

Tests focused on concurrent user scenarios, high-volume batch processing,
and system behavior under sustained load conditions.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest
import httpx
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.hs_matching import router
from src.services.hs_matching_service import (
    HSCodeMatchingService,
    HSCodeMatchRequest,
    HSCodeBatchMatchRequest
)
from src.core.openai_config import HSCodeResult, HSCodeMatchResult
from src.models.user import User, UserRole


class MockRunnerResult:
    """Mock result from Runner.run with variable response times"""
    def __init__(self, hs_code: str = "8517.12", confidence: float = 0.95, delay_ms: int = 500):
        self.delay_ms = delay_ms
        self.final_output = HSCodeResult(
            hs_code=hs_code,
            code_description="Telephones for cellular networks",
            confidence=confidence,
            chapter="85",
            section="XVI",
            reasoning="Product matches telecommunication equipment category"
        )


@pytest.fixture
def app():
    """Create FastAPI test app"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/hs-codes")
    return test_app


@pytest.fixture
def async_client(app):
    """Create async test client"""
    return httpx.AsyncClient(app=app, base_url="http://test")


@pytest.fixture
def hs_service():
    """Create HS matching service instance"""
    return HSCodeMatchingService()


@pytest.fixture
def test_users():
    """Create multiple test users for concurrent testing"""
    users = []
    for i in range(10):
        user = User(
            id=f"load-test-user-{i}",
            email=f"loadtest{i}@example.com",
            first_name=f"LoadTest{i}",
            last_name="User",
            company_name=f"Test Company {i}",
            country="USA",
            role=UserRole.USER,
            is_active=True
        )
        users.append(user)
    return users


class TestConcurrentUsers:
    """Test concurrent user scenarios"""
    
    @pytest.mark.asyncio
    async def test_concurrent_single_requests(self, hs_service):
        """Test multiple users making concurrent single product requests"""
        
        async def mock_run_realistic(agent, query):
            # Simulate realistic OpenAI response times (300-800ms)
            import random
            await asyncio.sleep(random.uniform(0.3, 0.8))
            return MockRunnerResult(
                hs_code=f"8517.{random.randint(10, 99)}",
                confidence=random.uniform(0.8, 0.95)
            )
        
        with patch('src.services.hs_matching_service.Runner.run', side_effect=mock_run_realistic):
            # Simulate 20 concurrent users each making a request
            user_requests = [
                hs_service.match_single_product(
                    product_description=f"User {i} smartphone device",
                    country="default"
                )
                for i in range(20)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*user_requests, return_exceptions=True)
            total_time = (time.time() - start_time) * 1000
            
            # Verify all requests completed successfully
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 20
            
            # With semaphore limiting, should complete within reasonable time
            assert total_time < 15000  # Should complete in under 15 seconds
            
            # Verify service maintained quality under concurrent load
            for result in successful_results:
                assert isinstance(result, HSCodeMatchResult)
                assert result.primary_match.confidence > 0.8
                assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_requests(self, hs_service):
        """Test multiple users making concurrent batch requests"""
        
        async def mock_run_batch(agent, query):
            await asyncio.sleep(0.5)  # Consistent 500ms per request
            return MockRunnerResult(confidence=0.9)
        
        with patch('src.services.hs_matching_service.Runner.run', side_effect=mock_run_batch):
            # Each user submits a batch of 10 products
            batch_requests = []
            for user_id in range(5):  # 5 users
                user_batch = [
                    HSCodeMatchRequest(
                        product_description=f"User {user_id} product {j}",
                        country="default"
                    )
                    for j in range(10)
                ]
                batch_requests.append(
                    hs_service.match_batch_products(user_batch, max_concurrent=3)
                )
            
            start_time = time.time()
            batch_results = await asyncio.gather(*batch_requests, return_exceptions=True)
            total_time = (time.time() - start_time) * 1000
            
            # Verify all batches completed
            successful_batches = [r for r in batch_results if not isinstance(r, Exception)]
            assert len(successful_batches) == 5
            
            # Each batch should have 10 results
            total_products = sum(len(batch) for batch in successful_batches)
            assert total_products == 50
            
            # Should complete in reasonable time (5 users * 10 products with concurrency limiting)
            assert total_time < 25000  # Under 25 seconds


class TestHighVolumeProcessing:
    """Test high-volume batch processing scenarios"""
    
    @pytest.mark.asyncio
    async def test_large_batch_processing(self, hs_service):
        """Test processing of maximum allowed batch size"""
        
        async def mock_run_fast(agent, query):
            await asyncio.sleep(0.2)  # Fast responses
            return MockRunnerResult(confidence=0.85)
        
        with patch('src.services.hs_matching_service.Runner.run', side_effect=mock_run_fast):
            # Create maximum allowed batch size
            max_batch = [
                HSCodeMatchRequest(
                    product_description=f"Large batch product {i}",
                    country="default"
                )
                for i in range(hs_service.BATCH_SIZE_LIMIT)
            ]
            
            start_time = time.time()
            results = await hs_service.match_batch_products(
                max_batch, 
                max_concurrent=10  # Optimal concurrency
            )
            processing_time = (time.time() - start_time) * 1000
            
            assert len(results) == hs_service.BATCH_SIZE_LIMIT
            
            # Should process within performance targets
            avg_time_per_product = processing_time / len(results)
            assert avg_time_per_product < 100  # Under 100ms per product on average
            
            # Verify all results are valid
            for result in results:
                assert result.primary_match.confidence > 0.8
                assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_sustained_high_volume(self, hs_service):
        """Test sustained high-volume processing over time"""
        
        async def mock_run_variable(agent, query):
            import random
            # Variable response times simulating real API behavior
            await asyncio.sleep(random.uniform(0.3, 1.2))
            return MockRunnerResult(confidence=random.uniform(0.75, 0.95))
        
        with patch('src.services.hs_matching_service.Runner.run', side_effect=mock_run_variable):
            batch_times = []
            total_processed = 0
            
            # Process 10 batches of 20 products each over time
            for batch_num in range(10):
                batch_requests = [
                    HSCodeMatchRequest(
                        product_description=f"Sustained batch {batch_num} product {i}",
                        country="default"
                    )
                    for i in range(20)
                ]
                
                start_time = time.time()
                results = await hs_service.match_batch_products(
                    batch_requests, 
                    max_concurrent=5
                )
                batch_time = (time.time() - start_time) * 1000
                batch_times.append(batch_time)
                total_processed += len(results)
                
                assert len(results) == 20
                
                # Small delay between batches to simulate real usage
                await asyncio.sleep(0.5)
            
            # Verify consistent performance across all batches
            avg_batch_time = statistics.mean(batch_times)
            batch_time_stddev = statistics.stdev(batch_times) if len(batch_times) > 1 else 0
            
            assert total_processed == 200
            assert avg_batch_time < 15000  # Average batch under 15 seconds
            # Performance should remain stable (low variance)
            assert batch_time_stddev < avg_batch_time * 0.4  # Less than 40% variation


class TestSystemLimits:
    """Test system behavior at limits"""
    
    @pytest.mark.asyncio
    async def test_connection_pool_limits(self, hs_service):
        """Test behavior when connection pool is saturated"""
        
        request_count = 0
        max_concurrent_reached = 0
        current_concurrent = 0
        max_concurrent_lock = threading.Lock()
        
        async def mock_run_with_tracking(agent, query):
            nonlocal request_count, max_concurrent_reached, current_concurrent
            
            with max_concurrent_lock:
                current_concurrent += 1
                max_concurrent_reached = max(max_concurrent_reached, current_concurrent)
                request_count += 1
            
            try:
                await asyncio.sleep(0.8)  # Longer processing time
                return MockRunnerResult()
            finally:
                with max_concurrent_lock:
                    current_concurrent -= 1
        
        with patch('src.services.hs_matching_service.Runner.run', side_effect=mock_run_with_tracking):
            # Create more concurrent requests than the service can handle simultaneously
            concurrent_requests = [
                hs_service.match_single_product(
                    product_description=f"Connection pool test {i}",
                    country="default"
                )
                for i in range(30)  # More than typical concurrent limit
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*concurrent_requests, return_exceptions=True)
            total_time = (time.time() - start_time) * 1000
            
            # All requests should complete successfully despite limits
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 30
            
            # Should have limited concurrency appropriately
            expected_max_concurrent = min(
                hs_service.MAX_CONCURRENT_REQUESTS, 
                30
            )
            assert max_concurrent_reached <= expected_max_concurrent + 2  # Allow small variance
            
            # Should queue requests rather than failing them
            assert request_count == 30
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, hs_service):
        """Test memory usage remains stable under load"""
        
        async def mock_run_memory_test(agent, query):
            # Simulate processing that might cause memory issues
            await asyncio.sleep(0.1)
            return MockRunnerResult()
        
        with patch('src.services.hs_matching_service.Runner.run', side_effect=mock_run_memory_test):
            # Process multiple batches to test memory stability
            for iteration in range(5):
                large_batch = [
                    HSCodeMatchRequest(
                        product_description=f"Memory test iteration {iteration} product {i}",
                        country="default"
                    )
                    for i in range(25)
                ]
                
                results = await hs_service.match_batch_products(large_batch)
                assert len(results) == 25
                
                # Check that agent cache doesn't grow unbounded
                cache_size = len(hs_service._agents_cache)
                assert cache_size <= 10  # Should not cache more than reasonable number
                
                # Clear some cache entries to simulate memory management
                if iteration > 2:
                    # In a real implementation, this might be automatic
                    pass
    
    @pytest.mark.asyncio
    async def test_error_recovery_under_load(self, hs_service):
        """Test error recovery when under heavy load"""
        
        call_count = 0
        
        async def mock_run_with_failures(agent, query):
            nonlocal call_count
            call_count += 1
            
            # Fail every 5th request to simulate intermittent issues
            if call_count % 5 == 0:
                raise ConnectionError("Simulated connection failure")
            
            await asyncio.sleep(0.3)
            return MockRunnerResult()
        
        with patch('src.services.hs_matching_service.Runner.run', side_effect=mock_run_with_failures):
            # Submit many concurrent requests with some failures expected
            load_requests = [
                hs_service.match_single_product(
                    product_description=f"Error recovery test {i}",
                    country="default"
                )
                for i in range(25)
            ]
            
            results = await asyncio.gather(*load_requests, return_exceptions=True)
            
            # Count successful vs failed results
            successful = [r for r in results if isinstance(r, HSCodeMatchResult)]
            failed = [r for r in results if isinstance(r, Exception)]
            
            # Should have some successes and handle failures gracefully
            assert len(successful) >= 15  # At least 60% success rate
            assert len(failed) <= 10  # Not more than 40% failures
            
            # Failed requests should be proper exceptions, not corrupted results
            for failure in failed:
                assert isinstance(failure, (ConnectionError, Exception))


class TestAPILoadTesting:
    """Test API endpoints under load using HTTP client"""
    
    @pytest.mark.asyncio
    async def test_api_concurrent_requests(self, app):
        """Test API endpoints handling concurrent HTTP requests"""
        
        with patch('src.api.v1.hs_matching.get_current_active_user') as mock_auth:
            with patch('src.api.v1.hs_matching.hs_matching_service.match_single_product') as mock_match:
                # Setup mocks
                mock_user = User(
                    id="api-load-test",
                    email="apiload@test.com",
                    first_name="API",
                    last_name="LoadTest",
                    role=UserRole.USER,
                    is_active=True
                )
                mock_auth.return_value = mock_user
                
                mock_result = HSCodeMatchResult(
                    primary_match=HSCodeResult(
                        hs_code="8517.12.00",
                        code_description="Test product",
                        confidence=0.9,
                        chapter="85",
                        section="XVI",
                        reasoning="Test reasoning"
                    ),
                    alternative_matches=[],
                    processing_time_ms=500.0,
                    query="Test product"
                )
                mock_match.return_value = mock_result
                
                # Create concurrent HTTP requests
                async def make_api_request(client, request_id):
                    request_data = {
                        "product_description": f"API load test product {request_id}",
                        "country": "default",
                        "include_alternatives": True,
                        "confidence_threshold": 0.7
                    }
                    
                    response = await client.post(
                        "/api/v1/hs-codes/match",
                        json=request_data,
                        headers={"Authorization": "Bearer test-token"}
                    )
                    return response.status_code, response.json() if response.status_code == 200 else None
                
                # Execute concurrent API requests
                async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                    start_time = time.time()
                    
                    # 15 concurrent API requests
                    tasks = [
                        make_api_request(client, i) 
                        for i in range(15)
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    api_time = (time.time() - start_time) * 1000
                
                # Analyze results
                successful_responses = [
                    r for r in results 
                    if not isinstance(r, Exception) and r[0] == 200
                ]
                
                assert len(successful_responses) >= 12  # At least 80% success
                assert api_time < 10000  # Complete within 10 seconds
                
                # Verify response structure
                for status_code, response_data in successful_responses:
                    if response_data:
                        assert response_data["success"] is True
                        assert "data" in response_data
                        assert "processing_time_ms" in response_data


if __name__ == "__main__":
    # Run load tests with specific configuration
    pytest.main([
        __file__, 
        "-v", 
        "-s", 
        "--tb=short",
        "-x"  # Stop on first failure for load tests
    ])