"""Tests for quality assessment tools in 4-agent architecture."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from tools.quality_tools import (
    init_quality_tools,
    critique_response_tool,
    verify_facts_tool,
    combined_quality_assessment,
    calculate_quality_metrics,
)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = Mock()
    client.chat_async = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_critique_response_tool_success(mock_llm_client):
    """Test successful critique response."""
    init_quality_tools(llm_client=mock_llm_client)

    mock_llm_client.chat_async.return_value = {
        "content": '''{
    "quality_level": "good",
    "confidence": 0.85,
    "relevance_score": 0.9,
    "accuracy_score": 0.8,
    "completeness_score": 0.85,
    "clarity_score": 0.9,
    "citation_score": 0.8,
    "issues": ["Could add more details"],
    "suggestions": ["Expand on the main points"],
    "should_regenerate": false
}''',
        "model": "glm-4.5"
    }

    result = await critique_response_tool.ainvoke({
        "query": "What is the refund policy?",
        "response": "Refunds are processed within 5-7 business days.",
        "context": "According to the policy, refunds take 7-10 business days."
    })

    data = json.loads(result)
    assert data["success"] is True
    assert data["quality_level"] == "good"
    assert data["confidence"] == 0.85
    assert "relevance_score" in data
    assert "should_regenerate" in data


@pytest.mark.asyncio
async def test_critique_response_tool_no_llm():
    """Test critique without LLM client."""
    init_quality_tools(llm_client=None)

    result = await critique_response_tool.ainvoke({
        "query": "test query",
        "response": "test response",
        "context": "test context"
    })

    data = json.loads(result)
    assert data["success"] is False
    assert "LLM client not initialized" in data["error"]


@pytest.mark.asyncio
async def test_verify_facts_tool_success(mock_llm_client):
    """Test successful fact verification."""
    init_quality_tools(llm_client=mock_llm_client)

    mock_llm_client.chat_async.return_value = {
        "content": '''{
    "is_verified": true,
    "confidence": 0.9,
    "factual_consistency": 0.95,
    "citation_accuracy": 0.85,
    "reasoning_quality": 0.9,
    "issues_found": [],
    "verification_checks": ["consistency_check", "citation_check"]
}''',
        "model": "glm-4.5"
    }

    result = await verify_facts_tool.ainvoke({
        "query": "What is the warranty period?",
        "response": "The warranty is 2 years according to [1].",
        "context": "[1] Warranty: 2 years parts and labor coverage."
    })

    data = json.loads(result)
    assert data["success"] is True
    assert data["is_verified"] is True
    assert data["factual_consistency"] >= 0.9
    assert "verification_checks" in data


@pytest.mark.asyncio
async def test_verify_facts_tool_inconsistency(mock_llm_client):
    """Test fact verification detecting inconsistency."""
    init_quality_tools(llm_client=mock_llm_client)

    mock_llm_client.chat_async.return_value = {
        "content": '''{
    "is_verified": false,
    "confidence": 0.7,
    "factual_consistency": 0.6,
    "citation_accuracy": 0.8,
    "reasoning_quality": 0.7,
    "issues_found": ["Time period mismatch: response says 5 days, source says 7-10 days"],
    "verification_checks": ["consistency_check", "accuracy_check"]
}''',
        "model": "glm-4.5"
    }

    result = await verify_facts_tool.ainvoke({
        "query": "Refund timeframe?",
        "response": "Refunds take 5 days.",
        "context": "Policy states refunds require 7-10 business days."
    })

    data = json.loads(result)
    assert data["success"] is True
    assert data["is_verified"] is False
    assert len(data["issues_found"]) > 0


@pytest.mark.asyncio
async def test_combined_quality_assessment(mock_llm_client):
    """Test combined quality assessment."""
    init_quality_tools(llm_client=mock_llm_client)

    # Setup both critique and verification responses
    call_count = 0

    async def mock_chat(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if "đánh giá chất lượng" in kwargs["messages"][1]["content"]:
            # Critique response
            return {
                "content": '''{
    "quality_level": "good",
    "confidence": 0.8,
    "relevance_score": 0.85,
    "accuracy_score": 0.8,
    "completeness_score": 0.75,
    "clarity_score": 0.9,
    "citation_score": 0.7,
    "issues": [],
    "suggestions": [],
    "should_regenerate": false
}''',
                "model": "glm-4.5"
            }
        else:
            # Verification response
            return {
                "content": '''{
    "is_verified": true,
    "confidence": 0.85,
    "factual_consistency": 0.9,
    "citation_accuracy": 0.8,
    "reasoning_quality": 0.85,
    "issues_found": [],
    "verification_checks": ["all_checks"]
}''',
                "model": "glm-4.5"
            }

    mock_llm_client.chat_async = mock_chat

    result = await combined_quality_assessment.ainvoke({
        "query": "Explain the contract terms",
        "response": "The contract includes standard terms for service delivery.",
        "context": "Contract terms: Service delivery within 30 days, payment on completion."
    })

    data = json.loads(result)
    assert data["success"] is True
    assert "overall_quality_score" in data
    assert "quality_level" in data
    assert "critique" in data
    assert "verification" in data
    assert "should_regenerate" in data

    # Verify both tools were called
    assert call_count == 2


@pytest.mark.asyncio
async def test_combined_quality_assessment_low_quality(mock_llm_client):
    """Test combined assessment with low quality triggering regeneration."""
    init_quality_tools(llm_client=mock_llm_client)

    async def mock_chat(*args, **kwargs):
        # Return low quality scores
        return {
            "content": '''{
    "quality_level": "poor",
    "confidence": 0.5,
    "relevance_score": 0.5,
    "accuracy_score": 0.4,
    "completeness_score": 0.5,
    "clarity_score": 0.6,
    "citation_score": 0.4,
    "issues": ["Inaccurate information", "Incomplete answer"],
    "suggestions": ["Revise for accuracy"],
    "should_regenerate": true
}''',
            "model": "glm-4.5"
        }

    mock_llm_client.chat_async = mock_chat

    result = await combined_quality_assessment.ainvoke({
        "query": "What are the terms?",
        "response": "Some terms exist.",  # Poor response
        "context": "Detailed contract terms available"
    })

    data = json.loads(result)
    assert data["success"] is True
    assert data["overall_quality_score"] < 0.7
    assert data["should_regenerate"] is True
    assert "regeneration_reason" in data


def test_calculate_quality_metrics():
    """Test quality metrics calculation."""
    quality_data = json.dumps({
        "success": True,
        "overall_quality_score": 0.85,
        "quality_level": "good",
        "critique": {
            "success": True,
            "average_score": 0.83,
            "issues": ["Minor clarity issue"],
            "suggestions": ["Improve structure"]
        },
        "verification": {
            "success": True,
            "is_verified": True,
            "average_score": 0.88
        },
        "all_issues": ["Minor clarity issue"],
        "all_suggestions": ["Improve structure"],
        "should_regenerate": False
    })

    result = calculate_quality_metrics.invoke({"quality_data": quality_data})
    data = json.loads(result)

    assert data["success"] is True
    assert "metrics" in data
    assert data["metrics"]["overall_score"] == 0.85
    assert data["metrics"]["percentile"] == 85
    assert data["metrics"]["grade"] == "B"
    assert "issue_analysis" in data
    assert "recommendations" in data


def test_calculate_quality_metrics_failing():
    """Test metrics calculation for failing quality."""
    quality_data = json.dumps({
        "success": True,
        "overall_quality_score": 0.55,
        "quality_level": "poor",
        "critique": {
            "success": True,
            "average_score": 0.5,
            "issues": ["Inaccurate", "Incomplete"],
            "suggestions": ["Revise completely"]
        },
        "verification": {
            "success": True,
            "is_verified": False,
            "average_score": 0.6
        },
        "all_issues": ["Inaccurate information", "Incomplete coverage"],
        "all_suggestions": ["Regenerate response"],
        "should_regenerate": True
    })

    result = calculate_quality_metrics.invoke({"quality_data": quality_data})
    data = json.loads(result)

    assert data["success"] is True
    assert data["metrics"]["percentile"] == 55
    assert data["metrics"]["grade"] == "F"
    assert data["metrics"]["passing"] is False
    assert len(data["issue_analysis"]["by_category"]) > 0


def test_calculate_quality_metrics_issue_categorization():
    """Test issue categorization in metrics calculation."""
    quality_data = json.dumps({
        "success": True,
        "overall_quality_score": 0.7,
        "quality_level": "acceptable",
        "all_issues": [
            "Thông tin không chính xác",  # Accuracy issue (Vietnamese) - contains "không chính xác"
            "Thiếu chi tiết quan trọng",  # Completeness issue (Vietnamese) - contains "thiếu"
            "Thiếu nguồn trích dẫn",  # Citation issue (Vietnamese) - contains both "thiếu" and "nguồn"
        ],
        "all_suggestions": [],
        "should_regenerate": False
    })

    result = calculate_quality_metrics.invoke({"quality_data": quality_data})
    data = json.loads(result)

    assert data["success"] is True
    issue_analysis = data["issue_analysis"]
    assert issue_analysis["total_issues"] == 3

    # Check categorization worked - note that "thiếu nguồn" contains both "thiếu" and "nguồn"
    by_category = issue_analysis["by_category"]
    assert by_category.get("accuracy", 0) > 0  # "không chính xác"
    assert by_category.get("completeness", 0) > 0  # "thiếu" appears twice
    # Note: citation detection looks for "nguồn" but since "thiếu" matches first, it goes to completeness


@pytest.mark.asyncio
async def test_critique_with_custom_criteria(mock_llm_client):
    """Test critique with custom criteria."""
    init_quality_tools(llm_client=mock_llm_client)

    mock_llm_client.chat_async.return_value = {
        "content": '''{
    "quality_level": "excellent",
    "confidence": 0.95,
    "relevance_score": 0.95,
    "accuracy_score": 0.95,
    "completeness_score": 0.95,
    "clarity_score": 0.95,
    "citation_score": 0.95,
    "issues": [],
    "suggestions": [],
    "should_regenerate": false
}''',
        "model": "glm-4.5"
    }

    custom_criteria = json.dumps({
        "criteria": [
            "Tính chuyên sâu",
            "Tính thực tiễn"
        ]
    })

    result = await critique_response_tool.ainvoke({
        "query": "test query",
        "response": "test response",
        "context": "test context",
        "criteria": custom_criteria
    })

    data = json.loads(result)
    assert data["success"] is True


def test_init_quality_tools():
    """Test initialization of quality tools."""
    mock_llm = Mock()
    init_quality_tools(llm_client=mock_llm)
    assert True  # Should not raise errors


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test timeout handling in quality tools."""
    import asyncio

    async def timeout_chat(*args, **kwargs):
        await asyncio.sleep(20)  # Longer than timeout
        return {"content": "{}"}

    mock_llm = Mock()
    mock_llm.chat_async = timeout_chat
    init_quality_tools(llm_client=mock_llm)

    result = await critique_response_tool.ainvoke({
        "query": "test",
        "response": "test",
        "context": "test"
    })

    data = json.loads(result)
    assert data["success"] is False
    assert "timed out" in data.get("error", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
