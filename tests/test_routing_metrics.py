"""Tests for routing metrics and logging system."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.routers.logging import (
    RoutingDecision,
    RoutingLogger,
    routing_logger,
)
from src.monitoring.routing_metrics import (
    RoutingMethod,
    RoutingMetrics,
    RoutingMetricsCollector,
    get_metrics_collector,
)


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_to_log_dict(self):
        """Test conversion to log dictionary."""
        decision = RoutingDecision(
            timestamp=1234567890.0,
            user_id="test-user",
            query="test query",
            query_hash="abc123",
            router_selected="RAGRouter",
            confidence=0.85,
            method="quick_filter",
            latency_ms=150.5,
            has_conversation_context=True,
            conversation_length=3,
            intent="rag",
            classification_confidence=0.85,
        )

        log_dict = decision.to_log_dict()

        assert log_dict["event"] == "routing_decision"
        assert log_dict["timestamp"] == 1234567890.0
        assert log_dict["user_id"] == "test-user"
        assert log_dict["query_hash"] == "abc123"
        assert log_dict["router"] == "RAGRouter"
        assert log_dict["confidence"] == 0.85
        assert log_dict["method"] == "quick_filter"
        assert log_dict["latency_ms"] == 150.5
        assert log_dict["has_context"] is True
        assert log_dict["conv_length"] == 3
        assert log_dict["intent"] == "rag"
        assert log_dict["classification_confidence"] == 0.85

    def test_to_json(self):
        """Test JSON serialization."""
        decision = RoutingDecision(
            timestamp=1234567890.0,
            user_id="test-user",
            query="test query",
            query_hash="abc123",
            router_selected="RAGRouter",
            confidence=0.85,
            method="quick_filter",
            latency_ms=150.5,
            has_conversation_context=False,
            conversation_length=0,
        )

        json_str = decision.to_json()
        assert '"event": "routing_decision"' in json_str
        assert '"router": "RAGRouter"' in json_str


class TestRoutingLogger:
    """Tests for RoutingLogger."""

    def test_hash_query(self):
        """Test query hashing."""
        logger = RoutingLogger()

        hash1 = logger.hash_query("test query")
        hash2 = logger.hash_query("test query")
        hash3 = logger.hash_query("different query")

        # Same query should produce same hash
        assert hash1 == hash2

        # Different query should produce different hash
        assert hash1 != hash3

        # Hash should be 16 characters
        assert len(hash1) == 16

    def test_normalize_user_id(self):
        """Test user ID normalization."""
        logger = RoutingLogger()

        # UUID should be converted to string
        user_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        normalized = logger.normalize_user_id(user_uuid)
        assert isinstance(normalized, str)
        assert normalized == "12345678-1234-5678-1234-567812345678"

        # String should remain unchanged
        normalized = logger.normalize_user_id("test-user")
        assert normalized == "test-user"

    @patch("src.agents.routers.logging.logger")
    def test_log_quick_filter_decision(self, mock_logger):
        """Test logging quick filter decision."""
        logger = RoutingLogger(enabled=True)

        logger.log_quick_filter_decision(
            query="test query",
            user_id="test-user",
            router_selected="RAGRouter",
            confidence=0.9,
            latency_ms=150.0,
            conversation_history=[{"role": "user", "content": "hello"}],
        )

        # Verify logger.info was called
        assert mock_logger.info.called

    @patch("src.agents.routers.logging.logger")
    def test_log_llm_classification_decision(self, mock_logger):
        """Test logging LLM classification decision."""
        logger = RoutingLogger(enabled=True)

        logger.log_llm_classification_decision(
            query="test query",
            user_id="test-user",
            router_selected="RAGRouter",
            intent="rag",
            classification_confidence=0.75,
            latency_ms=300.0,
            conversation_history=None,
        )

        # Verify logger.info was called
        assert mock_logger.info.called

    @patch("src.agents.routers.logging.logger")
    def test_log_fallback_decision(self, mock_logger):
        """Test logging fallback decision."""
        logger = RoutingLogger(enabled=True)

        logger.log_fallback_decision(
            query="test query",
            user_id="test-user",
            router_selected="ConversationalRouter",
            latency_ms=100.0,
            conversation_history=None,
            reason="No routers available",
        )

        # Verify logger.info was called
        assert mock_logger.info.called

    def test_disabled_logger(self):
        """Test disabled logger doesn't log."""
        logger = RoutingLogger(enabled=False)

        with patch("src.agents.routers.logging.logger") as mock_logger:
            logger.log_quick_filter_decision(
                query="test query",
                user_id="test-user",
                router_selected="RAGRouter",
                confidence=0.9,
                latency_ms=150.0,
            )

            # Logger should not be called when disabled
            assert not mock_logger.info.called


class TestRoutingMetricsCollector:
    """Tests for RoutingMetricsCollector."""

    def test_add_decision(self):
        """Test adding routing decision."""
        collector = RoutingMetricsCollector()

        decision = {
            "event": "routing_decision",
            "timestamp": 1234567890.0,
            "user_id": "test-user",
            "query_hash": "abc123",
            "router": "RAGRouter",
            "confidence": 0.85,
            "method": "quick_filter",
            "latency_ms": 150.5,
            "has_context": True,
            "conv_length": 3,
        }

        collector.add_decision(decision)
        assert len(collector._decisions) == 1

    def test_get_metrics_summary_empty(self):
        """Test metrics summary with no data."""
        collector = RoutingMetricsCollector()
        metrics = collector.get_metrics_summary()

        assert metrics.total_requests == 0
        assert metrics.method_distribution == {}

    def test_get_metrics_summary_with_data(self):
        """Test metrics summary with data."""
        collector = RoutingMetricsCollector()

        # Add some decisions
        decisions = [
            {
                "event": "routing_decision",
                "timestamp": 1234567890.0,
                "user_id": "user1",
                "query_hash": "abc",
                "router": "RAGRouter",
                "confidence": 0.9,
                "method": "quick_filter",
                "latency_ms": 100.0,
                "has_context": False,
                "conv_length": 0,
            },
            {
                "event": "routing_decision",
                "timestamp": 1234567891.0,
                "user_id": "user2",
                "query_hash": "def",
                "router": "ConversationalRouter",
                "confidence": 0.75,
                "method": "llm_classification",
                "latency_ms": 300.0,
                "has_context": True,
                "conv_length": 2,
                "intent": "conversational",
            },
        ]

        for decision in decisions:
            collector.add_decision(decision)

        metrics = collector.get_metrics_summary()

        assert metrics.total_requests == 2
        assert metrics.method_distribution.get("quick_filter") == 1
        assert metrics.method_distribution.get("llm_classification") == 1
        assert metrics.llm_classification_rate == 0.5
        assert metrics.quick_filter_coverage == 0.5
        assert metrics.context_usage == 0.5

    def test_clear_old_data(self):
        """Test clearing old data."""
        collector = RoutingMetricsCollector()

        # Add old decision (1 hour ago)
        import time
        old_timestamp = time.time() - 4000  # More than 1 hour

        old_decision = {
            "event": "routing_decision",
            "timestamp": old_timestamp,
            "user_id": "user1",
            "query_hash": "abc",
            "router": "RAGRouter",
            "confidence": 0.9,
            "method": "quick_filter",
            "latency_ms": 100.0,
            "has_context": False,
            "conv_length": 0,
        }

        # Add recent decision
        recent_decision = {
            "event": "routing_decision",
            "timestamp": time.time(),
            "user_id": "user2",
            "query_hash": "def",
            "router": "RAGRouter",
            "confidence": 0.9,
            "method": "quick_filter",
            "latency_ms": 100.0,
            "has_context": False,
            "conv_length": 0,
        }

        collector.add_decision(old_decision)
        collector.add_decision(recent_decision)

        # Clear data older than 1 hour
        cleared = collector.clear_old_data(retention_seconds=3600)

        assert cleared == 1  # Old decision cleared
        assert len(collector._decisions) == 1  # Recent decision remains


class TestMetricsCollectorIntegration:
    """Integration tests for metrics collector."""

    @patch("src.monitoring.routing_metrics.get_metrics_collector")
    def test_logger_integration_with_metrics(self, mock_get_collector):
        """Test that routing logger integrates with metrics collector."""
        from unittest.mock import Mock

        mock_collector = Mock()
        mock_get_collector.return_value = mock_collector

        logger = RoutingLogger(enabled=True)

        with patch("src.agents.routers.logging.logger"):
            logger.log_quick_filter_decision(
                query="test query",
                user_id="test-user",
                router_selected="RAGRouter",
                confidence=0.9,
                latency_ms=150.0,
            )

            # Verify metrics collector was called
            assert mock_collector.add_decision.called


@pytest.mark.asyncio
class TestRoutingMetricsAPI:
    """Tests for routing metrics API endpoints."""

    async def test_get_routing_metrics_summary(self):
        """Test GET /api/v1/metrics/routing/summary endpoint."""
        from fastapi.testclient import TestClient
        from src.main import app

        client = TestClient(app)

        # Note: This requires authentication, so we'll need to mock it
        with patch("src.api.metrics.get_current_user") as mock_auth:
            mock_user = MagicMock()
            mock_user.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
            mock_auth.return_value = mock_user

            response = client.get("/api/v1/metrics/routing/summary")

            # Should return metrics summary
            assert response.status_code == 200
            data = response.json()
            assert "total_requests" in data

    async def test_get_routing_analysis(self):
        """Test GET /api/v1/metrics/routing/analysis endpoint."""
        from fastapi.testclient import TestClient
        from src.main import app

        client = TestClient(app)

        with patch("src.api.metrics.get_current_user") as mock_auth:
            mock_user = MagicMock()
            mock_user.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
            mock_auth.return_value = mock_user

            response = client.get("/api/v1/metrics/routing/analysis")

            # Should return analysis
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert "analysis" in data
            assert "recommendations" in data
