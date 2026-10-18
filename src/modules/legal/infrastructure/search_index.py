"""Qdrant index of legal provision versions with validity payloads."""

import asyncio
from collections.abc import Sequence
from datetime import date
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    HasIdCondition,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    Range,
    VectorParams,
)

from src.modules.legal.application.ports import LegalProvisionSearchPort, LegalSearchIndexPort
from src.modules.legal.application.records import LegalDocumentMetadata
from src.modules.legal.domain.models import ProvisionVersion
from src.modules.legal.domain.qa import ProvisionHit
from src.shared.ports.embedding import EmbeddingPort

OPEN_ENDED_VALID_TO = date(9999, 12, 31)

_PAYLOAD_INDEXES = (
    ("provision_key", PayloadSchemaType.KEYWORD),
    ("number", PayloadSchemaType.KEYWORD),
    ("valid_from_ord", PayloadSchemaType.INTEGER),
    ("valid_to_ord", PayloadSchemaType.INTEGER),
)


def version_payload(
    provision_key: str,
    document: LegalDocumentMetadata,
    label: str,
    version: ProvisionVersion,
) -> dict[str, Any]:
    return {
        "provision_key": provision_key,
        "number": document.number,
        "doc_type": document.doc_type,
        "title": document.title,
        "label": label,
        "text": version.text,
        "page": version.page,
        "version_id": str(version.version_id),
        "valid_from": version.valid_from.isoformat(),
        "valid_to": version.valid_to.isoformat() if version.valid_to else None,
        "valid_from_ord": version.valid_from.toordinal(),
        "valid_to_ord": (version.valid_to or OPEN_ENDED_VALID_TO).toordinal(),
    }


def hit_from_payload(payload: dict[str, Any], score: float = 0.0) -> ProvisionHit:
    valid_to = payload.get("valid_to")
    return ProvisionHit(
        version_id=str(payload["version_id"]),
        provision_key=str(payload["provision_key"]),
        number=str(payload["number"]),
        doc_type=str(payload.get("doc_type", "")),
        title=str(payload.get("title", "")),
        label=str(payload.get("label", "")),
        text=str(payload.get("text", "")),
        page=payload.get("page"),
        valid_from=date.fromisoformat(str(payload["valid_from"])),
        valid_to=date.fromisoformat(str(valid_to)) if valid_to else None,
        score=float(score),
    )


class QdrantLegalSearchIndex(LegalSearchIndexPort, LegalProvisionSearchPort):
    def __init__(
        self,
        client: QdrantClient,
        embedding: EmbeddingPort,
        collection: str,
        vector_size: int | None = None,
    ) -> None:
        self._client = client
        self._embedding = embedding
        self._collection = collection
        self._vector_size = vector_size

    async def ensure_collection(self) -> None:
        if await asyncio.to_thread(self._client.collection_exists, self._collection):
            return
        size = self._vector_size or self._embedding.dimension
        await asyncio.to_thread(
            self._client.create_collection,
            collection_name=self._collection,
            vectors_config=VectorParams(size=size, distance=Distance.COSINE),
        )
        for field_name, schema in _PAYLOAD_INDEXES:
            await asyncio.to_thread(
                self._client.create_payload_index,
                collection_name=self._collection,
                field_name=field_name,
                field_schema=schema,
            )

    async def replace_provision_versions(
        self,
        provision_key: str,
        document: LegalDocumentMetadata,
        label: str,
        versions: Sequence[ProvisionVersion],
    ) -> None:
        keep_ids: list[int | str] = [str(version.version_id) for version in versions]
        if versions:
            vectors = await self._embedding.embed_batch([version.text for version in versions])
            points = [
                PointStruct(
                    id=str(version.version_id),
                    vector=vector,
                    payload=version_payload(provision_key, document, label, version),
                )
                for version, vector in zip(versions, vectors, strict=True)
            ]
            await asyncio.to_thread(
                self._client.upsert, collection_name=self._collection, points=points, wait=True
            )
        stale = Filter(
            must=[FieldCondition(key="provision_key", match=MatchValue(value=provision_key))],
            must_not=[HasIdCondition(has_id=keep_ids)] if keep_ids else None,
        )
        await asyncio.to_thread(
            self._client.delete,
            collection_name=self._collection,
            points_selector=stale,
            wait=True,
        )

    async def search_in_force(
        self,
        vector: Sequence[float],
        day: date,
        limit: int,
        *,
        provision_keys: Sequence[str] | None = None,
        numbers: Sequence[str] | None = None,
        min_score: float | None = None,
    ) -> list[ProvisionHit]:
        if provision_keys is not None and not provision_keys:
            return []
        if numbers is not None and not numbers:
            return []
        if not await asyncio.to_thread(self._client.collection_exists, self._collection):
            return []
        ordinal = day.toordinal()
        must: list[Any] = [
            FieldCondition(key="valid_from_ord", range=Range(lte=ordinal)),
            FieldCondition(key="valid_to_ord", range=Range(gt=ordinal)),
        ]
        if provision_keys is not None:
            must.append(
                FieldCondition(key="provision_key", match=MatchAny(any=list(provision_keys)))
            )
        if numbers is not None:
            must.append(FieldCondition(key="number", match=MatchAny(any=list(numbers))))
        response = await asyncio.to_thread(
            self._client.query_points,
            collection_name=self._collection,
            query=list(vector),
            query_filter=Filter(must=must),
            limit=limit,
            score_threshold=min_score,
            with_payload=True,
        )
        return [hit_from_payload(point.payload or {}, point.score) for point in response.points]

    async def list_versions(self, provision_key: str | None = None) -> list[ProvisionHit]:
        if not await asyncio.to_thread(self._client.collection_exists, self._collection):
            return []
        scroll_filter = (
            Filter(
                must=[FieldCondition(key="provision_key", match=MatchValue(value=provision_key))]
            )
            if provision_key is not None
            else None
        )
        hits: list[ProvisionHit] = []
        offset: Any = None
        while True:
            points, offset = await asyncio.to_thread(
                self._client.scroll,
                collection_name=self._collection,
                scroll_filter=scroll_filter,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            hits.extend(hit_from_payload(point.payload or {}) for point in points)
            if offset is None:
                return hits

    async def count_versions(self) -> int:
        if not await asyncio.to_thread(self._client.collection_exists, self._collection):
            return 0
        result = await asyncio.to_thread(self._client.count, self._collection, exact=True)
        return int(result.count)
