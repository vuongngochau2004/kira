"""Where every shared object is built.

Read this file to see how providers, services and chat handlers are wired.
- Providers and stateless services are singletons (``functools.cache``).
- Services that need a database session take ``db`` and are built per request/task.
Feature code never constructs providers itself; it receives them from here.
"""

from collections.abc import Callable
from datetime import date, datetime
from functools import cache
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from kira.admin.repository import SqlAlchemyAdminDashboardRepository
from kira.admin.service import AdminOverview
from kira.auth.repository import SqlAlchemyUserAccountRepository
from kira.auth.security import hash_password, verify_password
from kira.auth.service import IdentityService
from kira.chat.handlers.conversational import ConversationalHandler
from kira.chat.handlers.drafting import AdministrativeDraftingHandler
from kira.chat.handlers.rag import RAGHandler
from kira.chat.intent.base import ClassificationStrategyBase, Intent
from kira.chat.intent.cached import CachedStrategy
from kira.chat.intent.composite import CompositeClassifier
from kira.chat.intent.keyword import KeywordStrategy
from kira.chat.intent.legal import LegalKeywordStrategy
from kira.chat.intent.llm import LLMStrategy
from kira.chat.rag.graph import create_langgraph_pipeline
from kira.chat.rag.pipeline import RAGPipelineService
from kira.chat.rag.state import (
    GenerationAgentConfig,
    OrchestratorAgentConfig,
    QualityAgentConfig,
    RetrievalAgentConfig,
)
from kira.chat.service import ChatUseCase
from kira.config import settings
from kira.db.session import async_session_factory
from kira.documents.cancel import CancelDocument
from kira.documents.delete import DeleteDocument
from kira.documents.process import ProcessDocument
from kira.documents.repository import DocumentRepository
from kira.documents.upload import UploadDocument
from kira.evaluation.dataset import DatasetManager, get_dataset_manager
from kira.evaluation.repository import SqlAlchemyIngestedChunkRepository
from kira.evaluation.service import DeepEvalEvaluationService, get_evaluation_service
from kira.evaluation.use_case import Evaluation
from kira.legal.chat_handler import LegalQAHandler
from kira.legal.extraction.rules import DOCUMENT_NUMBER_PATTERN
from kira.legal.graph.base import LegalGraphPort
from kira.legal.graph.neo4j import Neo4jLegalGraphAdapter
from kira.legal.keyword_index import LegalKeywordIndex
from kira.legal.repository import SqlAlchemyLegalRepository
from kira.legal.reranker import ConfiguredLegalReranker
from kira.legal.scrapers.vbpl import VbplScraper
from kira.legal.search_index import QdrantLegalSearchIndex
from kira.legal.services.answer_question import AnswerLegalQuestion, LegalQAOptions
from kira.legal.services.delete_document import DeleteLegalDocument
from kira.legal.services.ingest_from_url import IngestLegalFromUrl
from kira.legal.services.process_document import ProcessLegalDocument
from kira.legal.services.publish_document import PublishLegalDocument
from kira.legal.services.queries import LegalDocumentQueries
from kira.legal.services.review_relation import ReviewRelationCandidate
from kira.legal.services.temporal import ResolveTemporalQuery
from kira.legal.services.upload_document import UploadLegalDocument
from kira.legal.text_extractor import DocumentModuleTextExtractor
from kira.providers.embedding.base import EmbeddingPort
from kira.providers.embedding.factory import create_embedding_adapter
from kira.providers.llm.base import LLMPort
from kira.providers.llm.client import LLMClient
from kira.providers.llm.traced import TracedLLM
from kira.providers.ocr import PaddleOCR
from kira.providers.storage import MinioStorage
from kira.providers.vector_store import QdrantVectorStore, get_client
from kira.retrieval.bm25 import BM25KeywordIndexAdapter, get_bm25_manager
from kira.retrieval.rerank.service import get_llm_client
from kira.retrieval.search import (
    BM25KeywordSearchAdapter,
    PostgresRetrievalDocumentAdapter,
    SearchUseCase,
)
from kira.worker import CeleryTaskQueue

# ---------------------------------------------------------------------------
# Providers (singletons)
# ---------------------------------------------------------------------------


@cache
def get_llm() -> LLMClient:
    return LLMClient()


@cache
def get_embedding() -> EmbeddingPort:
    return create_embedding_adapter()


@cache
def get_storage() -> MinioStorage:
    return MinioStorage()


@cache
def get_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore()


@cache
def get_ocr() -> PaddleOCR:
    return PaddleOCR()


@cache
def get_keyword_index() -> BM25KeywordIndexAdapter:
    return BM25KeywordIndexAdapter(manager=get_bm25_manager())


def get_legal_graph() -> LegalGraphPort:
    """A new Neo4j driver wrapper; callers close it when done."""
    return Neo4jLegalGraphAdapter.from_settings()


# ---------------------------------------------------------------------------
# Auth and admin
# ---------------------------------------------------------------------------


def identity_service(db: AsyncSession) -> IdentityService:
    return IdentityService(
        users=SqlAlchemyUserAccountRepository(db),
        hash_password=hash_password,
        verify_password=verify_password,
    )


def admin_overview(db: AsyncSession) -> AdminOverview:
    return AdminOverview(SqlAlchemyAdminDashboardRepository(db))


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


def document_repository(db: AsyncSession) -> DocumentRepository:
    return DocumentRepository(db=db)


def upload_document_service(db: AsyncSession) -> UploadDocument:
    return UploadDocument(repository=document_repository(db), storage=get_storage())


def process_document_service(db: AsyncSession) -> ProcessDocument:
    return ProcessDocument(
        repository=document_repository(db),
        storage=get_storage(),
        embedding=get_embedding(),
        vector_store=get_vector_store(),
        ocr=get_ocr(),
        keyword_index=get_keyword_index(),
    )


def delete_document_service(db: AsyncSession) -> DeleteDocument:
    return DeleteDocument(
        repository=document_repository(db),
        keyword_index=get_keyword_index(),
        vector_store=get_vector_store(),
        storage=get_storage(),
    )


def cancel_document_service(db: AsyncSession) -> CancelDocument:
    return CancelDocument(
        repository=document_repository(db),
        keyword_index=get_keyword_index(),
        vector_store=get_vector_store(),
        storage=get_storage(),
        task_queue=CeleryTaskQueue(),
    )


# ---------------------------------------------------------------------------
# Retrieval and RAG
# ---------------------------------------------------------------------------


def create_search_use_case(llm_client: LLMPort | None = None) -> SearchUseCase:
    return SearchUseCase(
        vector_store=get_vector_store(),
        keyword_search=BM25KeywordSearchAdapter(get_bm25_manager()),
        documents=PostgresRetrievalDocumentAdapter(),
        llm_client=llm_client,
    )


def create_rag_pipeline_service(
    *,
    embedding: EmbeddingPort | None = None,
    search: SearchUseCase | None = None,
    llm: LLMPort | None = None,
) -> RAGPipelineService:
    traced_llm = TracedLLM(llm or get_llm())
    pipeline = create_langgraph_pipeline(
        orchestrator_config=OrchestratorAgentConfig(),
        retrieval_config=RetrievalAgentConfig(
            top_k=max(settings.retrieval_k, settings.reranking_top_k_before),
            rerank_top_k=settings.reranking_top_k_after,
            rerank_threshold=settings.reranking_min_score_threshold,
            reranker_model=settings.reranking_mode,
        ),
        generation_config=GenerationAgentConfig(),
        quality_config=QualityAgentConfig(),
        embedding=embedding or get_embedding(),
        search=search or create_search_use_case(llm_client=traced_llm),
        llm=traced_llm,
    )
    return RAGPipelineService(pipeline=pipeline)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@cache
def get_classifier() -> ClassificationStrategyBase:
    """Intent routing chain: (legal keywords) -> keywords -> cached LLM."""
    strategies: list[ClassificationStrategyBase] = [
        KeywordStrategy(),
        CachedStrategy(LLMStrategy(), cache_size=1000, ttl=3600),
    ]
    if settings.legal_enabled:
        # Legal corpus cues must win over the broad file keywords ("điều", "về", ...).
        strategies.insert(
            0, LegalKeywordStrategy(settings.legal_routing_keywords, DOCUMENT_NUMBER_PATTERN)
        )
    return CompositeClassifier(
        strategies=strategies,
        thresholds={"keyword": 0.7, "cached": 0.6, "llm": 0.5},
    )


@cache
def get_chat_use_case() -> ChatUseCase:
    llm, embedding = get_llm(), get_embedding()
    handlers = {
        Intent.CONVERSATIONAL: ConversationalHandler(llm=llm),
        Intent.RAG: RAGHandler(
            rag_service=create_rag_pipeline_service(
                embedding=embedding,
                search=create_search_use_case(llm_client=llm),
                llm=llm,
            )
        ),
        Intent.DRAFTING: AdministrativeDraftingHandler(
            embedding=embedding,
            search=create_search_use_case(llm_client=llm),
            llm=llm,
            storage=get_storage(),
        ),
    }
    if settings.legal_enabled:
        handlers[Intent.LEGAL_QA] = LegalQAHandler(create_answer_legal_question(llm, embedding))
    return ChatUseCase(classifier=get_classifier(), handlers=handlers)


# ---------------------------------------------------------------------------
# Legal
# ---------------------------------------------------------------------------


def vietnam_today() -> date:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def legal_repository(db: AsyncSession) -> SqlAlchemyLegalRepository:
    return SqlAlchemyLegalRepository(db)


def legal_search_index() -> QdrantLegalSearchIndex:
    return QdrantLegalSearchIndex(
        client=get_client(),
        embedding=get_embedding(),
        collection=settings.legal_qdrant_collection,
    )


def upload_legal_document_service(db: AsyncSession) -> UploadLegalDocument:
    return UploadLegalDocument(repository=legal_repository(db), storage=get_storage())


def ingest_legal_from_url_service(db: AsyncSession) -> IngestLegalFromUrl:
    return IngestLegalFromUrl(
        scraper=VbplScraper(), upload_service=upload_legal_document_service(db)
    )


def process_legal_document_service(db: AsyncSession) -> ProcessLegalDocument:
    return ProcessLegalDocument(
        repository=legal_repository(db),
        storage=get_storage(),
        extractor=DocumentModuleTextExtractor(),
        llm=get_llm(),
        auto_approve_types=settings.legal_auto_approve_types,
        llm_max_provisions=settings.legal_llm_extraction_max_provisions,
    )


def publish_legal_document_service(db: AsyncSession, graph: LegalGraphPort) -> PublishLegalDocument:
    return PublishLegalDocument(
        repository=legal_repository(db), graph=graph, index=legal_search_index()
    )


def review_relation_service(db: AsyncSession) -> ReviewRelationCandidate:
    return ReviewRelationCandidate(repository=legal_repository(db))


def legal_queries(db: AsyncSession) -> LegalDocumentQueries:
    return LegalDocumentQueries(repository=legal_repository(db))


def delete_legal_document_service(db: AsyncSession) -> DeleteLegalDocument:
    return DeleteLegalDocument(repository=legal_repository(db), storage=get_storage())


def create_answer_legal_question(
    llm: LLMPort,
    embedding: EmbeddingPort,
    today: Callable[[], date] = vietnam_today,
    graph: LegalGraphPort | None = None,
) -> AnswerLegalQuestion:
    search = legal_search_index()
    return AnswerLegalQuestion(
        temporal=ResolveTemporalQuery(llm, today),
        embedding=embedding,
        search=search,
        keywords=LegalKeywordIndex(search, ttl_seconds=settings.legal_keyword_index_ttl_seconds),
        graph=graph or get_legal_graph(),
        reranker=ConfiguredLegalReranker(
            mode=settings.reranking_mode,
            llm_client_provider=get_llm_client,
        ),
        llm=llm,
        options=LegalQAOptions(
            seed_top_k=settings.legal_seed_top_k,
            final_top_k=settings.legal_final_top_k,
            max_guides=settings.legal_max_guides,
            snippet_length=settings.snippet_length,
            min_score=settings.legal_min_relevance_score,
        ),
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluation_service() -> DeepEvalEvaluationService:
    return get_evaluation_service()


def dataset_manager() -> DatasetManager:
    return get_dataset_manager()


def ingested_chunk_repository() -> SqlAlchemyIngestedChunkRepository:
    return SqlAlchemyIngestedChunkRepository(async_session_factory)


def evaluation_use_case(service: DeepEvalEvaluationService | None = None) -> Evaluation:
    return Evaluation(service=service or evaluation_service())
