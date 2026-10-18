import pytest

from src.config.config import settings
from src.modules.classification.domain.strategies.composite import CompositeClassifier
from src.modules.classification.domain.strategies.keyword import KeywordStrategy
from src.modules.classification.domain.strategies.legal import LegalKeywordStrategy
from src.modules.classification.domain.strategies.llm import LLMStrategy
from src.modules.legal.domain.extraction import DOCUMENT_NUMBER_PATTERN
from src.shared.ports.classification import Intent

KEYWORDS = ["luật", "bộ luật", "nghị định", "thông tư", "pháp luật", "mức phạt", "xử phạt"]


def _strategy() -> LegalKeywordStrategy:
    return LegalKeywordStrategy(KEYWORDS, DOCUMENT_NUMBER_PATTERN)


@pytest.mark.parametrize(
    "question",
    [
        "Mức phạt vượt đèn đỏ hiện nay là bao nhiêu?",
        "Nghị định 168/2024/NĐ-CP quy định gì về nồng độ cồn?",
        "Theo Luật Đất đai, điều kiện cấp sổ đỏ là gì?",
        "Điều 3 của 31/2024/QH15 nói gì?",
        "Nghị định 100/2019/NĐ-CP còn hiệu lực không?",
        "Nghị quyết 18/2024/QH15 quy định gì về đất đai?",
    ],
)
async def test_legal_questions_route_to_legal_qa(question: str) -> None:
    strategy = _strategy()
    assert strategy.can_handle(question, "user-1")
    result = await strategy.classify(question, "user-1")
    assert result.intent is Intent.LEGAL_QA
    assert result.confidence == 0.9
    assert result.handler_hint == "LegalQAHandler"


@pytest.mark.parametrize(
    "question",
    [
        "Tài liệu tôi tải lên nói gì về nghị định này?",
        "File hợp đồng của tôi có điều khoản phạt không?",
        "Quy chế kỷ luật sinh viên quy định thế nào?",
        "Quy luật cung cầu là gì?",
        "Xin chào, bạn là ai?",
        "Quyết định này có hiệu lực từ ngày nào?",
        "Quy chế đào tạo của trường có hiệu lực khi nào?",
        "Khoa Luật tuyển sinh bao nhiêu chỉ tiêu năm nay?",
        "Sinh viên ngành luật cần bao nhiêu tín chỉ để tốt nghiệp?",
        "Trường Đại học Luật Hà Nội ở đâu?",
        "Nghị quyết của Đảng ủy trường về công tác sinh viên",
        "Sinh viên vi phạm quy chế thi bị xử phạt thế nào?",
    ],
)
def test_non_corpus_questions_are_not_claimed(question: str) -> None:
    assert not _strategy().can_handle(question, "user-1")


async def test_legal_strategy_wins_over_broad_file_keywords() -> None:
    classifier = CompositeClassifier(
        strategies=[_strategy(), KeywordStrategy()],
        thresholds={"keyword": 0.7, "cached": 0.6, "llm": 0.5},
    )
    result = await classifier.classify("Điều 5 Nghị định 100/2019/NĐ-CP quy định về gì?", "u1")
    assert result.intent is Intent.LEGAL_QA
    assert result.metadata["strategy_used"] == "LegalKeywordStrategy"


def test_llm_legal_intent_respects_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    strategy = LLMStrategy()
    monkeypatch.setattr(settings, "legal_enabled", True)
    assert strategy._map_intent("legal") is Intent.LEGAL_QA
    assert strategy._get_handler_hint(Intent.LEGAL_QA) == "LegalQAHandler"
    monkeypatch.setattr(settings, "legal_enabled", False)
    assert strategy._map_intent("legal") is Intent.RAG


def test_routing_prompt_offers_legal_intent() -> None:
    from src.modules.classification.domain.prompts.routing import ROUTING_CLASSIFIER_PROMPT

    assert '"intent": "rag|drafting|conversational|legal"' in ROUTING_CLASSIFIER_PROMPT
    assert ROUTING_CLASSIFIER_PROMPT.format(query="x")  # braces stay escaped


def test_legal_qa_settings_defaults() -> None:
    assert "nghị định" in settings.legal_routing_keywords
    assert "hiệu lực" not in settings.legal_routing_keywords
    assert "nghị quyết" not in settings.legal_routing_keywords
    assert settings.legal_min_relevance_score == 0.5
    assert (settings.legal_seed_top_k, settings.legal_final_top_k, settings.legal_max_guides) == (
        20,
        8,
        5,
    )
