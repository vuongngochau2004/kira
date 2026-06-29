from uuid import uuid4

from src.modules.rag.domain.prompts.generation import build_generation_prompt
from src.modules.evaluation.runners.rag_pipeline_runner import RAGPipelineEvaluationRunner
from src.modules.rag.orchestration.agents.generation_agent import GenerationAgent
from src.modules.rag.orchestration.state.rag_state import DocumentWithScore, GenerationAgentConfig


def test_generation_context_keeps_query_relevant_sentences() -> None:
    agent = GenerationAgent(config=GenerationAgentConfig())
    doc = DocumentWithScore(
        doc_id=uuid4(),
        content=(
            "Phần mở đầu nêu nhiều căn cứ pháp lý không liên quan. "
            "Nhà trường dự kiến mở thêm mới ít nhất 01 chương trình đào tạo "
            "giảng dạy hoàn toàn bằng tiếng Anh. "
            "Các nội dung khác tập trung vào tài chính và cơ sở vật chất."
        ),
        filename="strategy.pdf",
        page_number=3,
        chunk_index=21,
        score=0.9,
    )

    context, compressed_contexts = agent._build_context(
        "Nhà trường dự kiến mở thêm mới bao nhiêu chương trình đào tạo bằng tiếng Anh?",
        [doc],
    )

    assert "ít nhất 01 chương trình" in context
    assert "ít nhất 01 chương trình" in compressed_contexts[0]
    assert len(compressed_contexts[0]) <= len(doc.content)


def test_generation_context_keeps_neighbors_for_responsibility_queries() -> None:
    agent = GenerationAgent(config=GenerationAgentConfig())
    doc = DocumentWithScore(
        doc_id=uuid4(),
        content=(
            "Câu mở đầu giới thiệu phạm vi văn bản. "
            "Phòng Đào tạo chủ trì xây dựng kế hoạch triển khai. "
            "Các khoa có trách nhiệm phối hợp rà soát danh sách sinh viên. "
            "Phòng Công tác sinh viên thực hiện thông báo đến người học. "
            "Bộ phận tài chính cập nhật kinh phí nếu phát sinh. "
            "Phần cuối nói về hiệu lực thi hành."
        ),
        filename="responsibility.pdf",
        page_number=1,
        chunk_index=2,
        score=0.9,
    )

    _, compressed_contexts = agent._build_context(
        "Đơn vị nào chịu trách nhiệm phối hợp rà soát danh sách sinh viên?",
        [doc],
    )

    compressed = compressed_contexts[0]
    assert "Phòng Đào tạo chủ trì" in compressed
    assert "có trách nhiệm phối hợp" in compressed
    assert "thực hiện thông báo" in compressed


def test_generation_prompt_requires_direct_first_sentence() -> None:
    prompt = build_generation_prompt(
        query="Ai chịu trách nhiệm?", context="Phòng A chịu trách nhiệm."
    )

    assert "Câu đầu tiên phải trả lời trực tiếp vào câu hỏi" in prompt


def test_evaluation_runner_separates_raw_and_generation_contexts() -> None:
    compressed_context = "Câu trực tiếp trả lời câu hỏi."
    raw_context = "Nội dung raw dài và nhiễu."
    doc = DocumentWithScore(
        doc_id=uuid4(),
        content=raw_context,
        filename="doc.pdf",
        page_number=1,
        chunk_index=0,
        score=0.9,
    )
    state = {
        "final_response": "answer",
        "generation_metadata": {
            "context_size": len(compressed_context),
            "compressed_contexts": [compressed_context],
        },
        "retrieval_agent_output": {
            "reranked_docs": [doc.model_dump()],
            "retrieved_docs": [],
        },
        "final_citations": [],
        "quality_agent_output": {},
        "agent_results": [],
    }
    sample = type(
        "Sample",
        (),
        {
            "id": "sample-1",
            "query": "question",
            "expected_answer": "answer",
            "reference_contexts": [],
            "expected_citations": [],
            "expected_context_ids": [],
            "should_refuse": False,
            "tags": [],
        },
    )()
    config = type("Config", (), {"retrieval_k": 5, "metrics": [], "threshold": 0.7})()

    request = RAGPipelineEvaluationRunner._request_from_state(
        RAGPipelineEvaluationRunner.__new__(RAGPipelineEvaluationRunner),
        sample,
        state,
        config,
    )

    assert request.contexts == [raw_context]
    assert request.generation_contexts == [compressed_context]
    assert "compressed_contexts" not in request.metadata["generation_metadata"]
    assert request.metadata["generation_metadata"]["compressed_context_count"] == 1
