"""
Tests for KeywordStrategy.
"""

import pytest

from src.classification.strategies.keyword import KeywordStrategy
from src.interfaces.classification import Intent
from src.interfaces.retrieval import Document


@pytest.mark.asyncio
async def test_keyword_strategy_creation():
    """Test KeywordStrategy creation."""
    strategy = KeywordStrategy()

    assert strategy.file_keywords
    assert "tài liệu" in strategy.file_keywords
    assert "pdf" in strategy.file_keywords
    assert strategy.fuzzy_threshold == 0.6


@pytest.mark.asyncio
async def test_keyword_strategy_with_documents():
    """Test KeywordStrategy with user documents."""
    user_docs = {
        "user123": [
            Document(content="Contract text", filename="contract.pdf"),
            Document(content="Report text", filename="report.docx"),
        ]
    }

    strategy = KeywordStrategy(user_documents=user_docs)

    assert "user123" in strategy.user_documents
    assert len(strategy.user_documents["user123"]) == 2


@pytest.mark.asyncio
async def test_keyword_strategy_file_match():
    """Test keyword strategy with filename matching."""
    user_docs = {
        "user123": [
            Document(content="...", filename="contract.pdf"),
        ]
    }

    strategy = KeywordStrategy(user_documents=user_docs)

    result = await strategy.classify("hỏi về contract.pdf", "user123")

    assert result.intent == Intent.RAG
    assert result.confidence > 0.9
    assert "contract.pdf" in result.reason
    assert result.metadata["matched_file"] == "contract.pdf"


@pytest.mark.asyncio
async def test_keyword_strategy_keyword_detection():
    """Test keyword detection without file match."""
    strategy = KeywordStrategy(user_documents={})

    result = await strategy.classify("tài liệu về hợp đồng", "user123")

    assert result.intent == Intent.RAG
    assert result.confidence > 0.8
    assert result.metadata.get("keyword_match")  # Should be truthy (matched keyword)


@pytest.mark.asyncio
async def test_keyword_strategy_no_match():
    """Test keyword strategy with no matches."""
    strategy = KeywordStrategy(user_documents={})

    result = await strategy.classify("xin chào", "user123")

    assert result.intent == Intent.CONVERSATIONAL
    assert result.confidence < 0.5
    assert result.metadata["matched_file"] is None


@pytest.mark.asyncio
async def test_keyword_strategy_empty_query():
    """Test keyword strategy with empty query."""
    strategy = KeywordStrategy()

    result = await strategy.classify("", "user123")

    assert result.confidence < 0.5


@pytest.mark.asyncio
async def test_keyword_strategy_can_handle():
    """Test KeywordStrategy.can_handle() method."""
    strategy = KeywordStrategy()

    # With file keyword
    assert strategy.can_handle("hỏi về tài liệu", "user123")

    # Without keywords
    assert not strategy.can_handle("xin chào", "user123")

    # Empty query
    assert not strategy.can_handle("", "user123")


@pytest.mark.asyncio
async def test_keyword_strategy_update_documents():
    """Test updating user documents."""
    strategy = KeywordStrategy()

    docs = [Document(content="...", filename="new.pdf")]
    strategy.update_user_documents("user456", docs)

    assert "user456" in strategy.user_documents
    assert len(strategy.user_documents["user456"]) == 1


@pytest.mark.asyncio
async def test_keyword_strategy_add_document():
    """Test adding a document."""
    strategy = KeywordStrategy()

    doc = Document(content="...", filename="added.pdf")
    strategy.add_document("user789", doc)

    assert "user789" in strategy.user_documents
    assert len(strategy.user_documents["user789"]) == 1


@pytest.mark.asyncio
async def test_keyword_strategy_remove_document():
    """Test removing a document."""
    user_docs = {
        "user123": [
            Document(content="...", filename="contract.pdf"),
            Document(content="...", filename="report.pdf"),
        ]
    }

    strategy = KeywordStrategy(user_documents=user_docs)

    # Remove existing document
    result = strategy.remove_document("user123", "contract.pdf")
    assert result is True
    assert len(strategy.user_documents["user123"]) == 1

    # Try removing non-existent document
    result = strategy.remove_document("user123", "nonexistent.pdf")
    assert result is False


@pytest.mark.asyncio
async def test_keyword_strategy_fuzzy_filename():
    """Test fuzzy filename matching."""
    user_docs = {
        "user123": [
            Document(content="...", filename="Hợp đồng lao động.pdf"),
        ]
    }

    strategy = KeywordStrategy(user_documents=user_docs)

    # Fuzzy match without extension
    result = await strategy.classify("hợp đồng lao động", "user123")

    assert result.intent == Intent.RAG
    assert result.confidence > 0.9
    assert "Hợp đồng lao động.pdf" in result.metadata.get("matched_file", "")


@pytest.mark.asyncio
async def test_keyword_strategy_custom_keywords():
    """Test KeywordStrategy with custom keywords."""
    custom_keywords = ["custom1", "custom2"]
    strategy = KeywordStrategy(file_keywords=custom_keywords)

    assert "custom1" in strategy.file_keywords
    assert "custom2" in strategy.file_keywords


@pytest.mark.asyncio
async def test_keyword_strategy_with_context():
    """Test KeywordStrategy with context parameter."""
    strategy = KeywordStrategy()
    context = {"conversation_history": []}

    result = await strategy.classify("tài liệu", "user123", context=context)

    assert result.intent == Intent.RAG
