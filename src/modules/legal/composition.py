"""Dependency composition for the legal module."""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.config import settings
from src.modules.legal.application.answer_question import AnswerLegalQuestion, LegalQAOptions
from src.modules.legal.application.delete_document import DeleteLegalDocument
from src.modules.legal.application.process_document import ProcessLegalDocument
from src.modules.legal.application.publish_document import PublishLegalDocument
from src.modules.legal.application.queries import LegalDocumentQueries
from src.modules.legal.application.review_relation import ReviewRelationCandidate
from src.modules.legal.application.temporal import ResolveTemporalQuery
from src.modules.legal.application.upload_document import UploadLegalDocument
from src.modules.legal.infrastructure.chat_handler import LegalQAHandler
from src.modules.legal.infrastructure.keyword_index import LegalKeywordIndex
from src.modules.legal.infrastructure.repositories import SqlAlchemyLegalRepository
from src.modules.legal.infrastructure.reranker import ConfiguredLegalReranker
from src.modules.legal.infrastructure.search_index import QdrantLegalSearchIndex
from src.modules.legal.infrastructure.text_extractor import DocumentModuleTextExtractor
from src.modules.retrieval.domain.services.reranking_service import get_llm_client
from src.modules.retrieval.infrastructure.vector.qdrant_store import get_client
from src.shared.adapters.embedding import create_embedding_adapter
from src.shared.adapters.graph.neo4j_adapter import Neo4jLegalGraphAdapter
from src.shared.adapters.llm.glm_adapter import GLMAdapter
from src.shared.adapters.storage.minio_adapter import MinIOAdapter
from src.shared.ports.embedding import EmbeddingPort
from src.shared.ports.legal_graph import LegalGraphPort
from src.shared.ports.llm import LLMPort


def legal_repository(db: AsyncSession) -> SqlAlchemyLegalRepository:
    return SqlAlchemyLegalRepository(db)


def upload_legal_document_service(db: AsyncSession) -> UploadLegalDocument:
    return UploadLegalDocument(repository=legal_repository(db), storage=MinIOAdapter())


def process_legal_document_service(db: AsyncSession) -> ProcessLegalDocument:
    return ProcessLegalDocument(
        repository=legal_repository(db),
        storage=MinIOAdapter(),
        extractor=DocumentModuleTextExtractor(),
        llm=GLMAdapter(),
        auto_approve_types=settings.legal_auto_approve_types,
        llm_max_provisions=settings.legal_llm_extraction_max_provisions,
    )


def review_relation_service(db: AsyncSession) -> ReviewRelationCandidate:
    return ReviewRelationCandidate(repository=legal_repository(db))


def legal_graph() -> LegalGraphPort:
    """Create a graph adapter; the caller owns it and must close it."""
    return Neo4jLegalGraphAdapter.from_settings()


def legal_search_index() -> QdrantLegalSearchIndex:
    return QdrantLegalSearchIndex(
        client=get_client(),
        embedding=create_embedding_adapter(),
        collection=settings.legal_qdrant_collection,
    )


def publish_legal_document_service(db: AsyncSession, graph: LegalGraphPort) -> PublishLegalDocument:
    return PublishLegalDocument(
        repository=legal_repository(db), graph=graph, index=legal_search_index()
    )


def legal_queries(db: AsyncSession) -> LegalDocumentQueries:
    return LegalDocumentQueries(repository=legal_repository(db))


def delete_legal_document_service(db: AsyncSession) -> DeleteLegalDocument:
    return DeleteLegalDocument(repository=legal_repository(db), storage=MinIOAdapter())


def vietnam_today() -> date:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def create_answer_legal_question(
    llm: LLMPort,
    embedding: EmbeddingPort,
    today: Callable[[], date] = vietnam_today,
    graph: LegalGraphPort | None = None,
) -> AnswerLegalQuestion:
    """Compose the legal QA use case; evaluations pin `today` and share one graph driver."""
    search = legal_search_index()
    return AnswerLegalQuestion(
        temporal=ResolveTemporalQuery(llm, today),
        embedding=embedding,
        search=search,
        keywords=LegalKeywordIndex(search, ttl_seconds=settings.legal_keyword_index_ttl_seconds),
        graph=graph or legal_graph(),
        reranker=ConfiguredLegalReranker(
            enabled=settings.reranking_enabled,
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


def create_legal_qa_handler(llm: LLMPort, embedding: EmbeddingPort) -> LegalQAHandler:
    """Long-lived handler for the API process (holds one Neo4j driver)."""
    return LegalQAHandler(create_answer_legal_question(llm, embedding))
