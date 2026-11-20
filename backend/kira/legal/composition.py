"""Dependency composition for the legal module."""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from kira.config import settings
from kira.legal.chat_handler import LegalQAHandler
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
from kira.providers.llm.adapter import GLMAdapter
from kira.providers.llm.base import LLMPort
from kira.providers.storage.minio import MinIOAdapter
from kira.providers.vector.client import get_client
from kira.retrieval.rerank.service import get_llm_client


def legal_repository(db: AsyncSession) -> SqlAlchemyLegalRepository:
    return SqlAlchemyLegalRepository(db)


def upload_legal_document_service(db: AsyncSession) -> UploadLegalDocument:
    return UploadLegalDocument(repository=legal_repository(db), storage=MinIOAdapter())


def vbpl_scraper() -> VbplScraper:
    return VbplScraper()


def ingest_legal_from_url_service(db: AsyncSession) -> IngestLegalFromUrl:
    return IngestLegalFromUrl(
        scraper=vbpl_scraper(), upload_service=upload_legal_document_service(db)
    )


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
