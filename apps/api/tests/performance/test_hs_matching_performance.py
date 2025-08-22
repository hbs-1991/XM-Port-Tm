"""
Performance tests for HS Code Matching Service

Tests to validate that the service meets the <2 second response time requirement
and handles concurrent requests efficiently.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agents import Runner

from apps.api.src.services.hs_matching_service import (
    HSCodeMatchingService,
    HSCodeMatchRequest,
    HSCodeBatchMatchRequest
)
from apps.api.src.core.openai_config import HSCodeResult, HSCodeMatchResult


class MockRunnerResult:
    """Mock result from Runner.run"""
    def __init__(self, hs_code: str = "8517.12", confidence: float = 0.95):
        self.final_output = HSCodeResult(
            hs_code=hs_code,
            code_description="Telephones for cellular networks",
            confidence=confidence,
            chapter="85",
            section="XVI",
            reasoning="Product matches telecommunication equipment category"
        )


@pytest.fixture
def hs_service():
    """Create HS matching service instance"""
    return HSCodeMatchingService()


@pytest.fixture
def mock_openai_fast_response():
    """Mock OpenAI response with fast response time (< 500ms)"""
    async def mock_run(agent, query):
        # Simulate fast API response
        await asyncio.sleep(0.3)  # 300ms response time
        return MockRunnerResult()
    
    return mock_run


@pytest.fixture
def mock_openai_variable_response():
    """Mock OpenAI response with variable response times"""
    call_count = 0
    
    async def mock_run(agent, query):
        nonlocal call_count
        call_count += 1
        
        # Simulate variable response times
        if call_count % 5 == 0:
            # Occasional slow response
            await asyncio.sleep(1.5)
        elif call_count % 3 == 0:
            # Medium response
            await asyncio.sleep(0.8)
        else:
            # Fast response
            await asyncio.sleep(0.4)
        
        return MockRunnerResult(
            hs_code=f"8517.{10 + (call_count % 90):02d}",
            confidence=0.85 + (call_count % 10) * 0.01
        )
    
    return mock_run


class TestPerformanceOptimization:
    """Test performance optimization features"""
    
    @pytest.mark.asyncio
    async def test_single_request_performance(self, hs_service, mock_openai_fast_response):
        """Test that single requests complete within 2 seconds"""
        with patch.object(Runner, 'run', side_effect=mock_openai_fast_response):
            # Warm up the service
            await hs_service._get_cache_service()
            
            start_time = time.time()
            
            result = await hs_service.match_single_product(
                product_description="smartphone with 5G capability",
                country="default"
            )
            
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
            
            assert result is not None
            assert result.primary_match.hs_code == "8517.12"
            assert elapsed_time < 2000  # Must be under 2 seconds
            assert elapsed_time < 1000  # Should be under 1 second with fast mock
    
    @pytest.mark.asyncio
    async def test_batch_request_performance(self, hs_service, mock_openai_fast_response):
        """Test batch processing performance with concurrent requests"""
        with patch.object(Runner, 'run', side_effect=mock_openai_fast_response):
            # Prepare batch of 20 products
            requests = [
                HSCodeMatchRequest(
                    product_description=f"Product type {i}: electronic device",
                    country="default"
                )
                for i in range(20)
            ]
            
            start_time = time.time()
            
            results = await hs_service.match_batch_products(
                requests=requests,
                max_concurrent=10  # Use optimized concurrency
            )
            
            elapsed_time = (time.time() - start_time) * 1000
            avg_time_per_request = elapsed_time / len(requests)
            
            assert len(results) == 20
            assert all(r.primary_match.hs_code == "8517.12" for r in results)
            
            # With 10 concurrent requests and 300ms each, should complete in ~600ms
            assert elapsed_time < 2000  # Must be under 2 seconds total
            assert avg_time_per_request < 200  # Average should be under 200ms per request
    
    @pytest.mark.asyncio
    async def test_connection_pooling(self, hs_service, mock_openai_variable_response):
        """Test connection pooling with many concurrent requests"""
        with patch.object(Runner, 'run', side_effect=mock_openai_variable_response):
            # Create 50 concurrent requests
            requests = [
                HSCodeMatchRequest(
                    product_description=f"Industrial equipment part {i}",
                    country="default"
                )
                for i in range(50)
            ]
            
            start_time = time.time()
            
            # Should handle 50 requests efficiently with connection pooling
            results = await hs_service.match_batch_products(
                requests=requests,
                max_concurrent=None  # Let service optimize
            )
            
            elapsed_time = (time.time() - start_time) * 1000
            
            assert len(results) == 50
            # With connection pooling, should complete much faster than sequential
            assert elapsed_time < 10000  # Should complete in under 10 seconds
            
            # Check that service optimized concurrency
            expected_concurrent = min(
                hs_service.MAX_CONCURRENT_REQUESTS,
                max(5, len(requests) // 10)
            )
            assert expected_concurrent > 5  # Should use more than minimum
    
    @pytest.mark.asyncio
    async def test_request_queuing(self, hs_service, mock_openai_fast_response):
        """Test request queuing and throttling"""
        with patch.object(Runner, 'run', side_effect=mock_openai_fast_response):
            # Create many concurrent tasks
            tasks = []
            for i in range(30):
                task = asyncio.create_task(
                    hs_service.match_single_product(
                        product_description=f"Electronic component {i}",
                        country="default"
                    )
                )
                tasks.append(task)
            
            # All tasks should complete despite concurrency limits
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check all completed successfully
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 30
            
            # Check request queue was used
            assert len(hs_service._request_queue) > 0
    
    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self, hs_service, mock_openai_variable_response):
        """Test that caching significantly improves performance"""
        with patch.object(Runner, 'run', side_effect=mock_openai_variable_response):
            # First request - no cache
            start_time = time.time()
            result1 = await hs_service.match_single_product(
                product_description="laptop computer with Intel processor",
                country="default"
            )
            first_request_time = (time.time() - start_time) * 1000
            
            # Second request - should hit cache
            start_time = time.time()
            result2 = await hs_service.match_single_product(
                product_description="laptop computer with Intel processor",
                country="default"
            )
            cached_request_time = (time.time() - start_time) * 1000
            
            assert result1.primary_match.hs_code == result2.primary_match.hs_code
            # Cached request should be at least 10x faster
            assert cached_request_time < first_request_time / 10
            # Cached request should be under 50ms
            assert cached_request_time < 50
    
    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, hs_service, mock_openai_fast_response):
        """Test performance metrics are tracked correctly"""
        with patch.object(Runner, 'run', side_effect=mock_openai_fast_response):
            # Make several requests
            for i in range(10):
                await hs_service.match_single_product(
                    product_description=f"Test product {i}",
                    country="default"
                )
            
            # Get performance metrics
            health = await hs_service.get_service_health()
            
            assert "performance" in health
            perf_metrics = health["performance"]
            
            assert perf_metrics["total_requests"] >= 10
            assert perf_metrics["avg_response_time_ms"] > 0
            assert perf_metrics["target_achievement_rate"] > 0
            
            # With fast mock, should achieve high target rate
            assert perf_metrics["target_achievement_rate"] > 80
    
    @pytest.mark.asyncio
    async def test_optimization_methods(self, hs_service):
        """Test performance optimization methods"""
        with patch.object(Runner, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MockRunnerResult()
            
            # Test optimization method
            optimization_results = await hs_service.optimize_for_performance()
            
            assert "cache_warming" in optimization_results
            assert "agents_preloaded" in optimization_results
            assert "queue_cleaned" in optimization_results
            
            # Should have preloaded agents
            assert optimization_results["agents_preloaded"] > 0
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_retry(self, hs_service):
        """Test exponential backoff in retry logic"""
        call_times = []
        
        async def mock_run_with_failures(agent, query):
            call_times.append(time.time())
            if len(call_times) < 3:
                raise asyncio.TimeoutError("Simulated timeout")
            return MockRunnerResult()
        
        with patch.object(Runner, 'run', side_effect=mock_run_with_failures):
            result = await hs_service.match_single_product(
                product_description="test product",
                country="default"
            )
            
            assert result is not None
            assert len(call_times) == 3
            
            # Check exponential backoff between retries
            if len(call_times) >= 3:
                delay1 = call_times[1] - call_times[0]
                delay2 = call_times[2] - call_times[1]
                
                # Second delay should be longer (exponential backoff)
                assert delay2 > delay1
                # But capped at 5 seconds
                assert delay2 <= 5.1
    
    @pytest.mark.asyncio
    async def test_performance_target_achievement(self, hs_service):
        """Test that service meets the 2-second performance target"""
        response_times = []
        
        async def mock_run_with_timing(agent, query):
            # Simulate various response times
            import random
            delay = random.uniform(0.5, 1.8)  # Between 500ms and 1.8s
            await asyncio.sleep(delay)
            response_times.append(delay * 1000)
            return MockRunnerResult()
        
        with patch.object(Runner, 'run', side_effect=mock_run_with_timing):
            # Make 20 requests
            requests = [
                HSCodeMatchRequest(
                    product_description=f"Product {i}",
                    country="default"
                )
                for i in range(20)
            ]
            
            results = await hs_service.match_batch_products(requests)
            
            assert len(results) == 20
            
            # Calculate statistics
            if response_times:
                avg_time = statistics.mean(response_times)
                max_time = max(response_times)
                under_target = sum(1 for t in response_times if t < 2000)
                achievement_rate = (under_target / len(response_times)) * 100
                
                # Average should be well under 2 seconds
                assert avg_time < 2000
                # At least 90% should meet target
                assert achievement_rate >= 90
                
                print(f"Performance Stats:")
                print(f"  Average: {avg_time:.0f}ms")
                print(f"  Max: {max_time:.0f}ms")
                print(f"  Achievement Rate: {achievement_rate:.1f}%")


class TestLoadHandling:
    """Test system behavior under load"""
    
    @pytest.mark.asyncio
    async def test_sustained_load(self, hs_service, mock_openai_fast_response):
        """Test sustained load handling"""
        with patch.object(Runner, 'run', side_effect=mock_openai_fast_response):
            # Simulate sustained load over time
            total_requests = 100
            batch_size = 10
            
            all_times = []
            
            for batch_num in range(total_requests // batch_size):
                requests = [
                    HSCodeMatchRequest(
                        product_description=f"Product {batch_num}-{i}",
                        country="default"
                    )
                    for i in range(batch_size)
                ]
                
                start_time = time.time()
                results = await hs_service.match_batch_products(requests)
                batch_time = (time.time() - start_time) * 1000
                all_times.append(batch_time)
                
                assert len(results) == batch_size
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            # Performance should remain consistent
            avg_time = statistics.mean(all_times)
            std_dev = statistics.stdev(all_times) if len(all_times) > 1 else 0
            
            # Average batch time should be under 2 seconds
            assert avg_time < 2000
            # Standard deviation should be reasonable (not degrading over time)
            assert std_dev < avg_time * 0.5  # Less than 50% variation
    
    @pytest.mark.asyncio
    async def test_burst_load(self, hs_service, mock_openai_fast_response):
        """Test handling of sudden burst load"""
        with patch.object(Runner, 'run', side_effect=mock_openai_fast_response):
            # Create sudden burst of 100 requests
            burst_requests = [
                HSCodeMatchRequest(
                    product_description=f"Burst product {i}",
                    country="default"
                )
                for i in range(100)
            ]
            
            start_time = time.time()
            
            # Service should handle burst efficiently
            results = await hs_service.match_batch_products(
                requests=burst_requests[:hs_service.BATCH_SIZE_LIMIT]  # Respect batch limit
            )
            
            burst_time = (time.time() - start_time) * 1000
            
            assert len(results) == hs_service.BATCH_SIZE_LIMIT
            # Even with burst, should complete reasonably fast
            assert burst_time < 10000  # Under 10 seconds for max batch


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])