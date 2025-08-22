"""
Unit tests for Analytics Service

These tests cover the analytics service functionality including
metrics collection, performance monitoring, and health checks.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.services.analytics_service import (
    HSCodeAnalyticsService,
    MatchingMetrics,
    UsageAnalytics,
    PerformanceMetrics,
    analytics_service
)
from src.models.product_match import ProductMatch
from src.models.processing_job import ProcessingJob
from src.models.user import User


class TestHSCodeAnalyticsService:
    """Test suite for HSCodeAnalyticsService"""

    @pytest.fixture
    def analytics_service_instance(self):
        """Create a fresh analytics service instance for testing"""
        return HSCodeAnalyticsService()

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service"""
        cache_service = AsyncMock()
        cache_service.is_available.return_value = True
        cache_service.get_cache_statistics.return_value = {
            "hit_rate": 0.75,
            "total_hits": 150,
            "total_misses": 50
        }
        return cache_service

    @pytest.fixture
    def sample_match_record(self):
        """Create a sample match record for testing"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "product_description": "Sample product description",
            "hs_code": "12345678",
            "confidence_score": 0.85,
            "processing_time_ms": 1500.0,
            "success": True,
            "error_message": None,
            "user_id": "user-123",
            "country": "default",
            "cache_hit": False
        }

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = AsyncMock()
        
        # Mock database query results
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        mock_result.fetchall.return_value = [
            MagicMock(matched_hs_code="12345678", usage_count=25),
            MagicMock(matched_hs_code="87654321", usage_count=15)
        ]
        mock_result.fetchone.return_value = MagicMock(
            average=Decimal("0.85"),
            minimum=Decimal("0.45"),
            maximum=Decimal("0.99"),
            total_matches=100
        )
        
        session.execute.return_value = mock_result
        return session

    @pytest.mark.asyncio
    async def test_record_matching_operation_success(self, analytics_service_instance, mock_cache_service):
        """Test recording a successful matching operation"""
        # Setup
        with patch.object(analytics_service_instance, '_get_cache_service', return_value=mock_cache_service):
            # Execute
            await analytics_service_instance.record_matching_operation(
                product_description="Test product",
                hs_code="12345678",
                confidence_score=0.85,
                processing_time_ms=1500.0,
                success=True,
                user_id="user-123",
                country="default",
                cache_hit=False
            )
            
            # Verify in-memory storage
            recent_matches = analytics_service_instance._in_memory_metrics["recent_matches"]
            assert len(recent_matches) == 1
            
            match_record = recent_matches[0]
            assert match_record["hs_code"] == "12345678"
            assert match_record["confidence_score"] == 0.85
            assert match_record["success"] is True
            assert match_record["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_record_matching_operation_failure(self, analytics_service_instance, mock_cache_service):
        """Test recording a failed matching operation"""
        # Setup
        with patch.object(analytics_service_instance, '_get_cache_service', return_value=mock_cache_service):
            # Execute
            await analytics_service_instance.record_matching_operation(
                product_description="Test product",
                hs_code="ERROR",
                confidence_score=0.0,
                processing_time_ms=2000.0,
                success=False,
                error_message="Connection timeout",
                user_id="user-123",
                country="default",
                cache_hit=False
            )
            
            # Verify in-memory storage
            recent_matches = analytics_service_instance._in_memory_metrics["recent_matches"]
            assert len(recent_matches) == 1
            
            match_record = recent_matches[0]
            assert match_record["hs_code"] == "ERROR"
            assert match_record["success"] is False
            assert match_record["error_message"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_get_matching_metrics_with_data(self, analytics_service_instance, mock_db_session):
        """Test getting matching metrics with database data"""
        # Setup mock data
        analytics_service_instance._in_memory_metrics["performance_samples"] = [
            {"timestamp": datetime.utcnow().isoformat(), "processing_time_ms": 1000.0, "success": True, "cache_hit": False},
            {"timestamp": datetime.utcnow().isoformat(), "processing_time_ms": 1500.0, "success": True, "cache_hit": True},
            {"timestamp": datetime.utcnow().isoformat(), "processing_time_ms": 2000.0, "success": True, "cache_hit": False}
        ]
        
        with patch('src.services.analytics_service.async_session_maker') as mock_session_maker:
            mock_session_maker.return_value.__aenter__.return_value = mock_db_session
            with patch.object(analytics_service_instance, '_get_cache_service') as mock_get_cache:
                mock_cache = AsyncMock()
                mock_cache.is_available.return_value = True
                mock_cache.get_cache_statistics.return_value = {"hit_rate": 0.75}
                mock_get_cache.return_value = mock_cache
                
                # Execute
                metrics = await analytics_service_instance.get_matching_metrics(days=7)
                
                # Verify
                assert isinstance(metrics, MatchingMetrics)
                assert metrics.total_matches == 100
                assert metrics.successful_matches == 100
                assert metrics.cache_hit_rate == 0.75
                assert len(metrics.processing_time_percentiles) > 0

    @pytest.mark.asyncio
    async def test_get_matching_metrics_empty_data(self, analytics_service_instance):
        """Test getting matching metrics with no data"""
        # Setup - mock empty database results
        with patch('src.services.analytics_service.async_session_maker') as mock_session_maker:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            mock_result.fetchall.return_value = []
            mock_session.execute.return_value = mock_result
            mock_session_maker.return_value.__aenter__.return_value = mock_session
            
            with patch.object(analytics_service_instance, '_get_cache_service') as mock_get_cache:
                mock_cache = AsyncMock()
                mock_cache.is_available.return_value = False
                mock_get_cache.return_value = mock_cache
                
                # Execute
                metrics = await analytics_service_instance.get_matching_metrics(days=7)
                
                # Verify
                assert isinstance(metrics, MatchingMetrics)
                assert metrics.total_matches == 0
                assert metrics.successful_matches == 0
                assert metrics.cache_hit_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_usage_analytics(self, analytics_service_instance, mock_db_session):
        """Test getting usage analytics"""
        # Setup mock data for different queries
        query_results = [100, 15, 25, 150, 50, 5.5]  # Different scalar results for different queries
        query_index = 0
        
        def mock_scalar():
            nonlocal query_index
            result = query_results[query_index] if query_index < len(query_results) else 0
            query_index += 1
            return result
        
        mock_db_session.execute.return_value.scalar.side_effect = mock_scalar
        mock_db_session.execute.return_value.fetchall.return_value = [
            MagicMock(email="user1@example.com", product_count=50),
            MagicMock(email="user2@example.com", product_count=30)
        ]
        
        with patch('src.services.analytics_service.async_session_maker') as mock_session_maker:
            mock_session_maker.return_value.__aenter__.return_value = mock_db_session
            
            # Execute
            analytics = await analytics_service_instance.get_usage_analytics(days=30)
            
            # Verify
            assert isinstance(analytics, UsageAnalytics)
            assert analytics.total_users == 100
            assert analytics.active_users_today == 15
            assert analytics.active_users_week == 25
            assert len(analytics.top_users_by_volume) == 2

    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, analytics_service_instance):
        """Test getting real-time performance metrics"""
        # Setup sample performance data
        current_time = datetime.utcnow()
        analytics_service_instance._in_memory_metrics["performance_samples"] = [
            {
                "timestamp": (current_time - timedelta(minutes=10)).isoformat(),
                "processing_time_ms": 1000.0,
                "success": True,
                "cache_hit": False
            },
            {
                "timestamp": (current_time - timedelta(minutes=5)).isoformat(),
                "processing_time_ms": 1500.0,
                "success": True,
                "cache_hit": True
            },
            {
                "timestamp": (current_time - timedelta(minutes=2)).isoformat(),
                "processing_time_ms": 2000.0,
                "success": False,
                "cache_hit": False
            }
        ]
        
        analytics_service_instance._in_memory_metrics["api_call_timestamps"] = [
            (current_time - timedelta(minutes=10)).timestamp(),
            (current_time - timedelta(minutes=5)).timestamp(),
            (current_time - timedelta(minutes=2)).timestamp()
        ]
        
        # Execute
        metrics = await analytics_service_instance.get_performance_metrics(minutes=60)
        
        # Verify
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.average_processing_time_ms == 1250.0  # Average of 1000 and 1500 (successful only)
        assert metrics.error_rate_percentage == 33.33  # 1 failed out of 3 total (rounded)
        assert metrics.api_calls_per_minute == 3.0 / 60  # 3 calls in 60 minutes

    @pytest.mark.asyncio
    async def test_get_confidence_score_analysis(self, analytics_service_instance, mock_db_session):
        """Test getting confidence score analysis"""
        # Setup mock database results
        mock_db_session.execute.return_value.fetchone.return_value = MagicMock(
            average=Decimal("0.85"),
            minimum=Decimal("0.45"),
            maximum=Decimal("0.99"),
            total_matches=100
        )
        
        # Mock multiple fetchall calls for different queries
        fetchall_results = [
            [
                MagicMock(confidence_score=Decimal("0.95")),
                MagicMock(confidence_score=Decimal("0.85")),
                MagicMock(confidence_score=Decimal("0.75"))
            ],
            [
                MagicMock(confidence_score=Decimal("0.95")),
                MagicMock(confidence_score=Decimal("0.85")),
                MagicMock(confidence_score=Decimal("0.75"))
            ]
        ]
        
        call_count = 0
        def mock_fetchall():
            nonlocal call_count
            result = fetchall_results[call_count] if call_count < len(fetchall_results) else []
            call_count += 1
            return result
        
        mock_db_session.execute.return_value.fetchall.side_effect = mock_fetchall
        mock_db_session.execute.return_value.scalar.return_value = 10  # Manual review count
        
        with patch('src.services.analytics_service.async_session_maker') as mock_session_maker:
            mock_session_maker.return_value.__aenter__.return_value = mock_db_session
            
            # Execute
            analysis = await analytics_service_instance.get_confidence_score_analysis(days=7)
            
            # Verify
            assert isinstance(analysis, dict)
            assert analysis["total_matches"] == 100
            assert analysis["average_confidence"] == 0.85
            assert analysis["manual_review_required"] == 10
            assert "confidence_distribution" in analysis

    @pytest.mark.asyncio
    async def test_get_system_health_metrics(self, analytics_service_instance):
        """Test getting system health metrics"""
        # Setup sample data
        analytics_service_instance._in_memory_metrics["recent_matches"] = [{"test": "data"}] * 10
        analytics_service_instance._in_memory_metrics["performance_samples"] = [{"test": "data"}] * 20
        analytics_service_instance._in_memory_metrics["api_call_timestamps"] = [123456789] * 5
        
        with patch.object(analytics_service_instance, 'get_performance_metrics') as mock_get_perf:
            mock_perf = PerformanceMetrics()
            mock_perf.error_rate_percentage = 5.0
            mock_perf.average_processing_time_ms = 2000.0
            mock_perf.api_calls_per_minute = 10.0
            mock_perf.p95_processing_time_ms = 3000.0
            mock_get_perf.return_value = mock_perf
            
            with patch.object(analytics_service_instance, '_get_cache_service') as mock_get_cache:
                mock_cache = AsyncMock()
                mock_cache.is_available.return_value = True
                mock_cache.get_cache_statistics.return_value = {"hit_rate": 0.75}
                mock_get_cache.return_value = mock_cache
                
                # Execute
                health = await analytics_service_instance.get_system_health_metrics()
                
                # Verify
                assert isinstance(health, dict)
                assert health["status"] == "healthy"
                assert "performance" in health
                assert "cache" in health
                assert "memory_usage" in health
                assert health["cache"]["available"] is True

    @pytest.mark.asyncio
    async def test_record_operation_with_cache_unavailable(self, analytics_service_instance):
        """Test recording operation when cache is unavailable"""
        with patch.object(analytics_service_instance, '_get_cache_service') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.is_available.return_value = False
            mock_get_cache.return_value = mock_cache
            
            # Execute
            await analytics_service_instance.record_matching_operation(
                product_description="Test product",
                hs_code="12345678",
                confidence_score=0.85,
                processing_time_ms=1500.0,
                success=True
            )
            
            # Verify in-memory storage still works
            recent_matches = analytics_service_instance._in_memory_metrics["recent_matches"]
            assert len(recent_matches) == 1

    @pytest.mark.asyncio
    async def test_in_memory_metrics_size_limits(self, analytics_service_instance):
        """Test that in-memory metrics respect size limits"""
        # Add more than the limit of recent matches (1000)
        for i in range(1200):
            await analytics_service_instance.record_matching_operation(
                product_description=f"Test product {i}",
                hs_code="12345678",
                confidence_score=0.85,
                processing_time_ms=1500.0,
                success=True
            )
        
        # Verify size limit is respected
        recent_matches = analytics_service_instance._in_memory_metrics["recent_matches"]
        assert len(recent_matches) == 1000  # Should be trimmed to limit
        
        # Verify performance samples are also limited
        performance_samples = analytics_service_instance._in_memory_metrics["performance_samples"]
        assert len(performance_samples) <= 1000

    @pytest.mark.asyncio
    async def test_error_handling_in_record_operation(self, analytics_service_instance):
        """Test error handling in record_matching_operation"""
        with patch.object(analytics_service_instance, '_get_cache_service', side_effect=Exception("Cache error")):
            # Should not raise exception, just log warning
            await analytics_service_instance.record_matching_operation(
                product_description="Test product",
                hs_code="12345678",
                confidence_score=0.85,
                processing_time_ms=1500.0,
                success=True
            )
            
            # Verify operation still recorded in memory
            recent_matches = analytics_service_instance._in_memory_metrics["recent_matches"]
            assert len(recent_matches) == 1

    @pytest.mark.asyncio
    async def test_error_handling_in_get_metrics(self, analytics_service_instance):
        """Test error handling in get_matching_metrics"""
        with patch('src.services.analytics_service.async_session_maker', side_effect=Exception("Database error")):
            # Should return empty metrics, not raise exception
            metrics = await analytics_service_instance.get_matching_metrics(days=7)
            
            assert isinstance(metrics, MatchingMetrics)
            assert metrics.total_matches == 0

    def test_singleton_analytics_service(self):
        """Test that analytics_service is properly initialized"""
        from src.services.analytics_service import analytics_service
        
        assert isinstance(analytics_service, HSCodeAnalyticsService)
        assert hasattr(analytics_service, '_in_memory_metrics')
        assert "recent_matches" in analytics_service._in_memory_metrics
        assert "performance_samples" in analytics_service._in_memory_metrics
        assert "api_call_timestamps" in analytics_service._in_memory_metrics

    @pytest.mark.asyncio
    async def test_confidence_distribution_calculation(self, analytics_service_instance, mock_db_session):
        """Test confidence score distribution calculation"""
        # Setup mock confidence scores
        confidence_scores = [
            (Decimal("0.95"),),  # very_high
            (Decimal("0.85"),),  # high
            (Decimal("0.75"),),  # medium
            (Decimal("0.45"),),  # low
            (Decimal("0.25"),)   # very_low
        ]
        
        mock_db_session.execute.return_value.fetchall.return_value = confidence_scores
        
        with patch('src.services.analytics_service.async_session_maker') as mock_session_maker:
            mock_session_maker.return_value.__aenter__.return_value = mock_db_session
            
            # Execute
            distribution = await analytics_service_instance._get_confidence_distribution(mock_db_session, 7)
            
            # Verify
            assert distribution["very_high"] == 1
            assert distribution["high"] == 1
            assert distribution["medium"] == 1
            assert distribution["low"] == 1
            assert distribution["very_low"] == 1

    @pytest.mark.asyncio
    async def test_processing_time_percentiles_calculation(self, analytics_service_instance):
        """Test processing time percentiles calculation"""
        # Setup sample data with known values
        analytics_service_instance._in_memory_metrics["performance_samples"] = [
            {"timestamp": datetime.utcnow().isoformat(), "processing_time_ms": 1000.0, "success": True, "cache_hit": False},
            {"timestamp": datetime.utcnow().isoformat(), "processing_time_ms": 2000.0, "success": True, "cache_hit": False},
            {"timestamp": datetime.utcnow().isoformat(), "processing_time_ms": 3000.0, "success": True, "cache_hit": False},
            {"timestamp": datetime.utcnow().isoformat(), "processing_time_ms": 4000.0, "success": True, "cache_hit": False},
            {"timestamp": datetime.utcnow().isoformat(), "processing_time_ms": 5000.0, "success": True, "cache_hit": False}
        ]
        
        with patch('src.services.analytics_service.async_session_maker') as mock_session_maker:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            mock_result.fetchall.return_value = []
            mock_session.execute.return_value = mock_result
            mock_session_maker.return_value.__aenter__.return_value = mock_session
            
            with patch.object(analytics_service_instance, '_get_cache_service') as mock_get_cache:
                mock_cache = AsyncMock()
                mock_cache.is_available.return_value = False
                mock_get_cache.return_value = mock_cache
                
                # Execute
                metrics = await analytics_service_instance.get_matching_metrics(days=7)
                
                # Verify percentiles
                assert "p50" in metrics.processing_time_percentiles
                assert "p95" in metrics.processing_time_percentiles
                assert "p99" in metrics.processing_time_percentiles
                assert metrics.processing_time_percentiles["p50"] == 3000.0  # Median
                assert metrics.average_response_time_ms == 3000.0  # Average