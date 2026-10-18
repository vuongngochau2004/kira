"""Neo4j implementation of the legal knowledge graph port."""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncManagedTransaction

from src.config.config import settings
from src.shared.adapters.graph import cypher
from src.shared.ports.legal_graph import (
    GraphRelation,
    GraphVersion,
    LegalDocumentNode,
    LegalGraphPort,
    ProvisionContext,
    ProvisionNode,
)

logger = logging.getLogger(__name__)

Statement = tuple[str, dict[str, Any]]


def document_params(document: LegalDocumentNode) -> dict[str, Any]:
    return asdict(document)


def provision_rows(provisions: Sequence[ProvisionNode]) -> list[dict[str, Any]]:
    return [asdict(provision) for provision in provisions]


def version_rows(versions: Sequence[GraphVersion]) -> list[dict[str, Any]]:
    return [asdict(version) for version in versions]


def relation_rows(relations: Sequence[GraphRelation]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for relation in relations:
        grouped.setdefault(relation.type, []).append(asdict(relation))
    return grouped


def _native(value: Any) -> Any:
    return value.to_native() if hasattr(value, "to_native") else value


def context_from_record(record: Mapping[str, Any]) -> ProvisionContext:
    return ProvisionContext(
        provision_key=record["key"],
        parent_label=record["parent_label"],
        parent_text=record["parent_text"],
        introduced_by=record["introduced_by"],
        introduced_by_number=record["introduced_by_number"],
        introduced_by_title=record["introduced_by_title"],
        amended_after=_native(record["amended_after"]),
    )


class Neo4jLegalGraphAdapter(LegalGraphPort):
    def __init__(self, driver: AsyncDriver, database: str) -> None:
        self._driver = driver
        self._database = database

    @classmethod
    def from_settings(cls) -> "Neo4jLegalGraphAdapter":
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        return cls(driver, settings.neo4j_database)

    async def ensure_schema(self) -> None:
        for statement in cypher.SCHEMA_STATEMENTS:
            await self._driver.execute_query(statement, database_=self._database)

    async def upsert_document(self, document: LegalDocumentNode) -> None:
        await self._driver.execute_query(
            cypher.UPSERT_DOCUMENT, document_params(document), database_=self._database
        )

    async def upsert_provisions(self, provisions: Sequence[ProvisionNode]) -> None:
        rows = provision_rows(provisions)
        if not rows:
            return
        await self._write(
            [
                (cypher.UPSERT_PROVISIONS, {"provisions": rows}),
                (cypher.LINK_PROVISIONS, {"provisions": rows}),
            ]
        )

    async def replace_provision_timeline(
        self, provision_key: str, versions: Sequence[GraphVersion]
    ) -> None:
        rows = version_rows(versions)
        await self._write(
            [
                (
                    cypher.DELETE_STALE_VERSIONS,
                    {
                        "provision_key": provision_key,
                        "version_ids": [row["version_id"] for row in rows],
                    },
                ),
                (cypher.UPSERT_VERSIONS, {"provision_key": provision_key, "versions": rows}),
            ]
        )

    async def replace_document_relations(
        self, source_document: str, relations: Sequence[GraphRelation]
    ) -> None:
        statements: list[Statement] = [
            (
                cypher.DELETE_DOCUMENT_RELATIONS,
                {"source_document": source_document, "types": list(cypher.RELATION_TYPES)},
            )
        ]
        for rel_type, rows in relation_rows(relations).items():
            statements.append((cypher.relation_query(rel_type), {"relations": rows}))
        await self._write(statements)

    async def delete_provisions(self, provision_keys: Sequence[str]) -> None:
        if provision_keys:
            await self._write(
                [(cypher.DELETE_PROVISIONS, {"provision_keys": list(provision_keys)})]
            )

    async def expand_context(
        self, provision_keys: Sequence[str], day: date
    ) -> dict[str, ProvisionContext]:
        if not provision_keys:
            return {}
        records, _, _ = await self._driver.execute_query(
            cypher.EXPAND_CONTEXT,
            {"keys": list(provision_keys), "day": day},
            database_=self._database,
        )
        return {record["key"]: context_from_record(record) for record in records}

    async def guiding_documents(self, provision_keys: Sequence[str]) -> list[str]:
        if not provision_keys:
            return []
        records, _, _ = await self._driver.execute_query(
            cypher.GUIDING_DOCUMENTS, {"keys": list(provision_keys)}, database_=self._database
        )
        return [record["number"] for record in records]

    async def health_check(self) -> bool:
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.warning("Neo4j health check failed: %s", exc)
            return False

    async def close(self) -> None:
        await self._driver.close()

    async def _write(self, statements: Sequence[Statement]) -> None:
        async def work(tx: AsyncManagedTransaction) -> None:
            for query, params in statements:
                result = await tx.run(query, params)
                await result.consume()

        async with self._driver.session(database=self._database) as session:
            await session.execute_write(work)
