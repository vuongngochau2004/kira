"""Retrieval tools for LangChain agent integration.

Enhanced for 4-agent architecture with query expansion, hybrid retrieval,
and support for RAGState format.
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Global store/index references (to be set by application initialization)
_qdrant_store: Any = None
_bm25_index: Any = None
_embedding_fn: Any = None
_llm_client: Any = None


def init_retrieval_tools(
    qdrant_store: Any = None,
    bm25_index: Any = None,
    embedding_fn: Any = None,
    llm_client: Any = None,
) -> None:
    """Initialize global retrieval dependencies.

    Args:
        qdrant_store: Qdrant/vector store instance
        bm25_index: BM25 index instance (optional)
        embedding_fn: Embedding function for query encoding (optional)
        llm_client: LLM client for query expansion (optional)
    """
    global _qdrant_store, _bm25_index, _embedding_fn, _llm_client
    _qdrant_store = qdrant_store
    _bm25_index = bm25_index
    _embedding_fn = embedding_fn
    _llm_client = llm_client


def _get_store() -> Any:
    """Get the global vector store instance.

    Raises:
        RuntimeError: If store has not been initialized
    """
    if _qdrant_store is None:
        raise RuntimeError("Vector store not initialized. Call init_retrieval_tools() first.")
    return _qdrant_store


def _get_bm25_index() -> Any:
    """Get the global BM25 index instance.

    Returns:
        BM25 index or None if not initialized
    """
    return _bm25_index


def _get_embedding_fn() -> Any:
    """Get the global embedding function.

    Raises:
        RuntimeError: If embedding function has not been initialized
    """
    if _embedding_fn is None:
        raise RuntimeError("Embedding function not initialized. Call init_retrieval_tools() first.")
    return _embedding_fn


def _get_llm_client() -> Any:
    """Get the global LLM client.

    Returns:
        LLM client or None if not initialized
    """
    return _llm_client


def _doc_to_dict(doc: dict) -> dict:
    """Normalize document to dict for JSON serialization.

    Args:
        doc: Document dict with various field names

    Returns:
        Normalized document dict
    """
    return {
        "text": doc.get("text", doc.get("content", "")),
        "content": doc.get("text", doc.get("content", "")),
        "metadata": doc.get("metadata", {}),
        "document_id": doc.get("document_id"),
        "chunk_index": doc.get("chunk_index"),
        "score": doc.get("score", 0.0),
    }


@tool
def dense_retrieve(
    query: str,
    k: int = 5,
    user_id: str | None = None,
) -> str:
    """Retrieve documents using dense vector similarity search.

    Use this for semantic search when you need documents
    similar in meaning to the query, regardless of exact keywords.

    Args:
        query: The search query text
        k: Number of documents to retrieve
        user_id: Optional user ID for filtering results

    Returns:
        JSON string of retrieved documents with content and metadata
    """
    from src.modules.retrieval.infrastructure.vector.qdrant_store import search_similar
    from src.ingestion.embedding import embed_single

    # Generate query embedding
    query_embedding = embed_single(query)

    # Search using vector store
    docs = search_similar(
        query_embedding=query_embedding,
        user_id=user_id,
        limit=k,
    )

    return json.dumps([_doc_to_dict(d) for d in docs], ensure_ascii=False)


@tool
def bm25_retrieve(
    query: str,
    k: int = 5,
) -> str:
    """Retrieve documents using BM25 keyword-based search.

    Use this for queries with specific terms, names, or keywords
    that must appear in the documents.

    Args:
        query: The search query text
        k: Number of documents to retrieve

    Returns:
        JSON string of retrieved documents with content and metadata

    Raises:
        RuntimeError: If BM25 index is not available
    """
    bm25_index = _get_bm25_index()
    if bm25_index is None:
        raise RuntimeError("BM25 index not available. Initialize with init_retrieval_tools().")

    docs = bm25_index.search(query, k=k)

    # Normalize format
    normalized = []
    for doc in docs:
        normalized.append({
            "text": doc.get("content", ""),
            "content": doc.get("content", ""),
            "metadata": doc.get("metadata", {}),
            "score": doc.get("score", 0.0),
        })

    return json.dumps(normalized, ensure_ascii=False)


@tool
def hybrid_retrieve(
    query: str,
    k: int = 5,
    rrf_k: int = 60,
    user_id: str | None = None,
) -> str:
    """Retrieve documents using hybrid search (dense + BM25 with RRF).

    Combines semantic and keyword search using Reciprocal Rank Fusion.
    Use this when you want both semantic meaning and keyword matching.

    Args:
        query: The search query text
        k: Number of documents to retrieve
        rrf_k: RRF smoothing constant (higher = more balanced ranking)
        user_id: Optional user ID for filtering results

    Returns:
        JSON string of retrieved documents with RRF scores

    Raises:
        RuntimeError: If BM25 index is not available (falls back to dense only)
    """
    from src.modules.retrieval.infrastructure.vector.qdrant_store import search_similar
    from src.ingestion.embedding import embed_single
    from src.modules.retrieval.domain.services.hybrid_search import reciprocal_rank_fusion

    # Generate query embedding
    query_embedding = embed_single(query)

    # Get dense results
    dense_results = search_similar(
        query_embedding=query_embedding,
        user_id=user_id,
        limit=k * 2,
    )

    # Get BM25 results if available
    bm25_results = []
    bm25_index = _get_bm25_index()
    if bm25_index:
        bm25_docs = bm25_index.search(query, k=k * 2)
        for doc in bm25_docs:
            bm25_results.append({
                "text": doc.get("content", ""),
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {}),
                "score": doc.get("score", 0),
                "document_id": doc.get("metadata", {}).get("document_id"),
                "chunk_index": doc.get("metadata", {}).get("chunk_index"),
            })

    # If no BM25, fall back to dense only
    if not bm25_results:
        return json.dumps([_doc_to_dict(d) for d in dense_results[:k]], ensure_ascii=False)

    # Normalize dense results format for fusion
    dense_formatted = []
    for item in dense_results:
        dense_formatted.append({
            "text": item.get("text", ""),
            "content": item.get("text", ""),
            "metadata": {
                "document_id": item.get("document_id"),
                "user_id": item.get("user_id"),
                "chunk_index": item.get("chunk_index"),
            },
            "score": item.get("score", 0),
            "document_id": item.get("document_id"),
            "chunk_index": item.get("chunk_index"),
        })

    # Fuse with RRF
    fused = reciprocal_rank_fusion([dense_formatted, bm25_results], k=rrf_k)

    return json.dumps(fused[:k], ensure_ascii=False)


@tool
async def query_expansion_tool(
    query: str,
    expansion_count: int = 3,
    use_synonyms: bool = True,
) -> str:
    """Expand query using LLM and basic synonym expansion for better retrieval.

    Use this tool to generate alternative query formulations that may improve
    document retrieval. This is especially useful for ambiguous queries or
    when initial retrieval returns insufficient results.

    Args:
        query: Original user query to expand
        expansion_count: Number of expanded queries to generate (default: 3)
        use_synonyms: Whether to use basic synonym expansion (default: True)

    Returns:
        JSON string with original query and list of expanded queries

    Example:
        >>> result = await query_expansion_tool.ainvoke({
        ...     "query": "hỏi về hợp đồng",
        ...     "expansion_count": 3
        ... })
        >>> queries = json.loads(result)
        >>> # ["hỏi về hợp đồng", "thuê bao dịch vụ", "cam kết pháp lý"]
    """
    try:
        import asyncio

        expanded_queries = [query]  # Always include original

        # LLM-based expansion
        llm_client = _get_llm_client()
        if llm_client:
            expansion_prompt = f"""Tạo {expansion_count} cách diễn đạt khác cho câu hỏi dưới đây để tìm kiếm thông tin hiệu quả hơn.

Câu hỏi gốc: {query}

Yêu cầu:
1. Giữ nguyên ý nghĩa gốc
2. Sử dụng từ đồng nghĩa, liên quan
3. Đa dạng hóa cấu trúc câu
4. Phù hợp với ngữ cảnh tìm kiếm tài liệu

Trả về mỗi câu hỏi trên một dòng, không đánh số:"""

            try:
                messages = [
                    {"role": "system", "content": "Bạn là trợ lý chuyên gia tìm kiếm thông tin."},
                    {"role": "user", "content": expansion_prompt}
                ]

                response = await asyncio.wait_for(
                    llm_client.chat_async(
                        messages=messages,
                        temperature=0.7,
                        max_tokens=200,
                    ),
                    timeout=10,
                )

                content = response.get("content", "")
                llm_expansions = [line.strip() for line in content.split("\n") if line.strip()]
                expanded_queries.extend(llm_expansions[:expansion_count])

            except (asyncio.TimeoutError, Exception) as e:
                logger.debug(f"LLM expansion failed: {e}")

        # Basic synonym expansion (fallback or additional)
        if use_synonyms and not llm_client:
            # Simple word-level expansion as fallback
            synonym_map = {
                "hỏi": ["tìm kiếm", "tra cứu", "xem"],
                "về": ["liên quan", "chủ đề"],
                "hợp đồng": ["thỏa thuận", "cam kết", "thuê bao"],
                "chính sách": ["quy định", "quy tắc"],
                # Add more as needed
            }

            for word, synonyms in synonym_map.items():
                if word in query.lower():
                    for synonym in synonyms:
                        expanded_query = query.lower().replace(word, synonym)
                        if expanded_query != query.lower():
                            expanded_queries.append(expanded_query)

        # Deduplicate while preserving order
        seen = set()
        unique_queries = []
        for q in expanded_queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)

        return json.dumps({
            "success": True,
            "original_query": query,
            "expanded_queries": unique_queries[:expansion_count + 1],
            "total_count": len(unique_queries)
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in query_expansion_tool: {e}", exc_info=True)
        # Fallback to original query
        return json.dumps({
            "success": False,
            "original_query": query,
            "expanded_queries": [query],
            "error": str(e)
        }, ensure_ascii=False)


@tool
async def hybrid_retrieve_with_expansion(
    query: str,
    user_id: str,
    k: int = 10,
    rrf_k: int = 60,
    enable_expansion: bool = True,
    expansion_count: int = 3,
) -> str:
    """Perform hybrid retrieval with optional query expansion.

    This is the recommended retrieval tool for the 4-agent architecture.
    It combines semantic and keyword search with optional LLM-based query
    expansion for comprehensive document retrieval.

    Args:
        query: User query to search for
        user_id: User ID for personalization and filtering
        k: Number of documents to retrieve (default: 10)
        rrf_k: RRF smoothing constant (default: 60)
        enable_expansion: Enable query expansion (default: True)
        expansion_count: Number of query expansions (default: 3)

    Returns:
        JSON string with retrieved documents and retrieval metadata

    Example:
        >>> result = await hybrid_retrieve_with_expansion.ainvoke({
        ...     "query": "hỏi về hợp đồng",
        ...     "user_id": "user123",
        ...     "k": 10
        ... })
        >>> response = json.loads(result)
        >>> docs = response["documents"]
        >>> metadata = response["metadata"]
    """
    try:
        from src.modules.retrieval.infrastructure.vector.qdrant_store import search_similar
        from src.ingestion.embedding import embed_single
        from src.modules.retrieval.domain.services.hybrid_search import reciprocal_rank_fusion

        # Step 1: Query expansion (if enabled)
        queries_to_search = [query]
        if enable_expansion:
            expansion_result = await query_expansion_tool.ainvoke({
                "query": query,
                "expansion_count": expansion_count,
                "use_synonyms": True
            })
            expansion_data = json.loads(expansion_result)
            queries_to_search = expansion_data.get("expanded_queries", [query])

        # Step 2: Retrieve documents for each query
        all_dense_results = []
        all_bm25_results = []

        for search_query in queries_to_search:
            # Generate query embedding
            query_embedding = embed_single(search_query)

            # Dense search
            dense_docs = search_similar(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=k * 2,
            )
            all_dense_results.extend(dense_docs)

            # BM25 search
            bm25_index = _get_bm25_index()
            if bm25_index:
                bm25_docs = bm25_index.search(search_query, k=k * 2)
                all_bm25_results.extend(bm25_docs)

        # Step 3: Normalize and deduplicate results
        seen_docs = set()
        normalized_dense = []
        for item in all_dense_results:
            doc_key = (item.get("document_id"), item.get("chunk_index"))
            if doc_key not in seen_docs:
                seen_docs.add(doc_key)
                normalized_dense.append({
                    "text": item.get("text", ""),
                    "content": item.get("text", ""),
                    "metadata": {
                        "document_id": item.get("document_id"),
                        "user_id": item.get("user_id"),
                        "chunk_index": item.get("chunk_index"),
                    },
                    "score": item.get("score", 0),
                    "document_id": item.get("document_id"),
                    "chunk_index": item.get("chunk_index"),
                })

        normalized_bm25 = []
        for doc in all_bm25_results:
            doc_key = (doc.get("metadata", {}).get("document_id"), doc.get("metadata", {}).get("chunk_index"))
            if doc_key not in seen_docs:
                seen_docs.add(doc_key)
                normalized_bm25.append({
                    "text": doc.get("content", ""),
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("score", 0),
                    "document_id": doc.get("metadata", {}).get("document_id"),
                    "chunk_index": doc.get("metadata", {}).get("chunk_index"),
                })

        # Step 4: Fuse with RRF
        if normalized_bm25:
            fused = reciprocal_rank_fusion([normalized_dense, normalized_bm25], k=rrf_k)
        else:
            fused = normalized_dense

        # Step 5: Format response
        top_docs = fused[:k]

        return json.dumps({
            "success": True,
            "documents": top_docs,
            "metadata": {
                "query": query,
                "user_id": user_id,
                "total_retrieved": len(fused),
                "returned_count": len(top_docs),
                "queries_used": queries_to_search,
                "strategy": "hybrid_with_expansion" if enable_expansion else "hybrid",
                "rrf_k": rrf_k,
                "has_bm25": len(normalized_bm25) > 0
            }
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in hybrid_retrieve_with_expansion: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "documents": [],
            "metadata": {}
        }, ensure_ascii=False)


@tool
async def retrieve_with_rerank(
    query: str,
    user_id: str,
    k: int = 10,
    rerank_top_k: int = 5,
    enable_reranking: bool = True,
) -> str:
    """Retrieve documents and apply LLM reranking for precision.

    This tool combines retrieval and reranking in one call for the
    RetrievalAgent in the 4-agent architecture. First retrieves candidates
    using hybrid search, then reranks using LLM for top precision.

    Args:
        query: User query to search for
        user_id: User ID for personalization
        k: Number of initial documents to retrieve (default: 10)
        rerank_top_k: Number of documents to return after reranking (default: 5)
        enable_reranking: Enable LLM reranking (default: True)

    Returns:
        JSON string with reranked documents

    Example:
        >>> result = await retrieve_with_rerank.ainvoke({
        ...     "query": "chính sách bảo mật",
        ...     "user_id": "user123"
        ... })
        >>> response = json.loads(result)
        >>> docs = response["documents"]  # Already reranked
    """
    try:
        # Step 1: Initial retrieval
        retrieval_result = await hybrid_retrieve_with_expansion.ainvoke({
            "query": query,
            "user_id": user_id,
            "k": k,
            "enable_expansion": False  # No expansion for reranking flow
        })

        retrieval_data = json.loads(retrieval_result)
        initial_docs = retrieval_data.get("documents", [])

        if not initial_docs:
            return json.dumps({
                "success": True,
                "documents": [],
                "metadata": {
                    "query": query,
                    "retrieved_count": 0,
                    "reranked_count": 0,
                    "reranking_applied": False
                }
            }, ensure_ascii=False)

        # Step 2: LLM reranking
        reranked_docs = initial_docs
        reranking_applied = False

        if enable_reranking and len(initial_docs) > rerank_top_k:
            from src.tools.reranking_tools import score_and_rerank

            docs_json = json.dumps(initial_docs, ensure_ascii=False)
            rerank_result = score_and_rerank.invoke({
                "query": query,
                "documents": docs_json,
                "top_k": rerank_top_k,
                "min_score_threshold": 0.3
            })

            reranked_data = json.loads(rerank_result)
            reranked_docs = reranked_data
            reranking_applied = True

        return json.dumps({
            "success": True,
            "documents": reranked_docs[:rerank_top_k],
            "metadata": {
                "query": query,
                "user_id": user_id,
                "retrieved_count": len(initial_docs),
                "reranked_count": len(reranked_docs),
                "reranking_applied": reranking_applied
            }
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in retrieve_with_rerank: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "documents": [],
            "metadata": {}
        }, ensure_ascii=False)


@tool
def format_documents_for_context(
    documents: str,
    max_length: int = 4000,
    include_metadata: bool = True,
) -> str:
    """Format retrieved documents for LLM context generation.

    Use this tool to prepare retrieved documents for the GenerationAgent.
    It formats documents into a coherent context while controlling length.

    Args:
        documents: JSON string of retrieved documents
        max_length: Maximum total character length (default: 4000)
        include_metadata: Whether to include document metadata (default: True)

    Returns:
        Formatted context string for LLM

    Example:
        >>> docs = [{"text": "content 1", "filename": "doc1.pdf"}]
        >>> context = format_documents_for_context.invoke({
        ...     "documents": json.dumps(docs),
        ...     "max_length": 2000
        ... })
    """
    try:
        doc_list = json.loads(documents)
        if not doc_list:
            return "No relevant documents found."

        formatted_parts = []
        total_length = 0

        for idx, doc in enumerate(doc_list):
            text = doc.get("text", doc.get("content", ""))
            filename = doc.get("filename", doc.get("metadata", {}).get("filename", f"Document {idx + 1}"))
            page = doc.get("page_number") or doc.get("metadata", {}).get("page_number")
            score = doc.get("score", doc.get("rerank_score", 0))

            # Format document section
            if include_metadata:
                header = f"[{idx + 1}] {filename}"
                if page:
                    header += f" (Page {page})"
                if score:
                    header += f" [Relevance: {score:.2f}]"
                header += "\n"
            else:
                header = f"[{idx + 1}]\n"

            # Truncate text if needed
            if total_length + len(header) + len(text) > max_length:
                remaining_space = max_length - total_length - len(header)
                if remaining_space > 100:  # Only include if we have meaningful space
                    text = text[:remaining_space] + "..."
                    formatted_parts.append(header + text)
                break

            formatted_parts.append(header + text)
            total_length += len(header) + len(text)

        context = "\n\n".join(formatted_parts)
        return context

    except Exception as e:
        logger.error(f"Error in format_documents_for_context: {e}", exc_info=True)
        return f"Error formatting documents: {str(e)}"


__all__ = [
    "init_retrieval_tools",
    "dense_retrieve",
    "bm25_retrieve",
    "hybrid_retrieve",
    "query_expansion_tool",
    "hybrid_retrieve_with_expansion",
    "retrieve_with_rerank",
    "format_documents_for_context",
]
