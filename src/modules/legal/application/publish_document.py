"""Publish a reviewed legal document into the knowledge graph and search index."""

import logging
from dataclasses import dataclass
from uuid import UUID

from src.modules.legal.application.errors import InvalidLegalDocumentState, LegalDocumentNotFound
from src.modules.legal.application.ports import LegalDocumentRepositoryPort, LegalSearchIndexPort
from src.modules.legal.application.records import (
    CandidateStatus,
    LegalDocumentRecord,
    LegalDocumentStatus,
    RelationCandidateRecord,
    utc_now,
)
from src.modules.legal.application.serialization import provisions_from_json
from src.modules.legal.domain.errors import TimelineConflict
from src.modules.legal.domain.models import (
    TIMELINE_RELATION_TYPES,
    BaseProvisionText,
    ParsedProvision,
    ProvisionChange,
    ProvisionVersion,
    RelationType,
)
from src.modules.legal.domain.provision_key import describe_provision_ref, split_provision_key
from src.modules.legal.domain.timeline import build_timeline
from src.shared.ports.legal_graph import (
    GraphRelation,
    GraphVersion,
    LegalDocumentNode,
    LegalGraphPort,
    ProvisionNode,
)

logger = logging.getLogger(__name__)

PUBLISHABLE_STATUSES = frozenset(
    {LegalDocumentStatus.IN_REVIEW, LegalDocumentStatus.PUBLISHED, LegalDocumentStatus.FAILED}
)
_DOCUMENT_SOURCE_TYPES = frozenset({RelationType.REPLACES, RelationType.BASED_ON})


def ensure_publishable(document: LegalDocumentRecord) -> None:
    if document.status not in PUBLISHABLE_STATUSES or document.parsed_structure is None:
        raise InvalidLegalDocumentState(
            f"Document {document.metadata.number} cannot be published in status {document.status}"
        )


@dataclass(frozen=True)
class PublishOutcome:
    document: LegalDocumentRecord
    republish_document_ids: list[UUID]


@dataclass
class _PublishPlan:
    provisions: list[ProvisionNode]
    timelines: dict[str, list[ProvisionVersion]]
    owners: dict[str, LegalDocumentRecord]
    labels: dict[str, str]
    relations: list[GraphRelation]
    removed: list[str]
    foreign_keys: list[str]


class PublishLegalDocument:
    def __init__(
        self,
        repository: LegalDocumentRepositoryPort,
        graph: LegalGraphPort,
        index: LegalSearchIndexPort,
    ) -> None:
        self._repository = repository
        self._graph = graph
        self._index = index

    async def execute(self, document_id: UUID) -> PublishOutcome:
        # Publishes touching the same provisions must not interleave (last writer would win).
        await self._repository.acquire_publish_lock()
        document = await self._repository.get_document(document_id)
        if document is None:
            raise LegalDocumentNotFound(str(document_id))
        ensure_publishable(document)
        first_publish = document.published_at is None

        document.status = LegalDocumentStatus.PUBLISHING
        document.error_detail = None
        await self._repository.save_document(document)

        try:
            plan = await _Planner(self._repository, document).build()
        except TimelineConflict as exc:
            detail = f"Timeline conflict ({exc.reason}): {', '.join(exc.change_ids)}"
            return PublishOutcome(await self._fail(document, detail), [])

        try:
            await self._write(document, plan)
        except Exception as exc:
            logger.exception("Publishing legal document %s failed", document_id)
            return PublishOutcome(await self._fail(document, f"Publish failed: {exc}"), [])

        document.status = LegalDocumentStatus.PUBLISHED
        document.published_at = utc_now()
        document.published_keys = plan.foreign_keys
        await self._repository.save_document(document)
        dependents = await self._dependents(document) if first_publish else []
        return PublishOutcome(document, dependents)

    async def _dependents(self, document: LegalDocumentRecord) -> list[UUID]:
        """Published amenders that could not link to this document before it existed."""
        incoming = await self._repository.list_candidates_targeting(
            document.metadata.number, [CandidateStatus.APPROVED]
        )
        dependents: list[UUID] = []
        for candidate in incoming:
            source_id = candidate.legal_document_id
            if source_id == document.id or source_id in dependents:
                continue
            source = await self._repository.get_document(source_id)
            if source is not None and source.published_at is not None:
                dependents.append(source_id)
        return dependents

    async def _write(self, document: LegalDocumentRecord, plan: _PublishPlan) -> None:
        await self._graph.ensure_schema()
        await self._index.ensure_collection()
        await self._graph.upsert_document(_document_node(document))
        await self._graph.upsert_provisions(plan.provisions)
        for key, versions in plan.timelines.items():
            await self._graph.replace_provision_timeline(key, [_graph_version(v) for v in versions])
            await self._index.replace_provision_versions(
                key, plan.owners[key].metadata, plan.labels[key], versions
            )
        for key in plan.removed:
            await self._index.replace_provision_versions(
                key, plan.owners[key].metadata, plan.labels[key], []
            )
        if plan.removed:
            await self._graph.delete_provisions(plan.removed)
        await self._graph.replace_document_relations(document.metadata.number, plan.relations)

    async def _fail(self, document: LegalDocumentRecord, detail: str) -> LegalDocumentRecord:
        document.status = LegalDocumentStatus.FAILED
        document.error_detail = detail[:1000]
        await self._repository.save_document(document)
        return document


class _Planner:
    """Compute every timeline and relation before anything is written."""

    def __init__(
        self, repository: LegalDocumentRepositoryPort, document: LegalDocumentRecord
    ) -> None:
        self._repository = repository
        self._document = document
        self._structures: dict[UUID, dict[str, ParsedProvision]] = {}
        self._incoming: dict[str, list[RelationCandidateRecord]] = {}
        self._live_sources: dict[UUID, bool] = {document.id: True}

    async def build(self) -> _PublishPlan:
        document = self._document
        own = self._structure(document)
        candidates = await self._repository.list_candidates(document.id)

        owners: dict[str, LegalDocumentRecord] = dict.fromkeys(own, document)
        for candidate in candidates:
            if candidate.type not in TIMELINE_RELATION_TYPES:
                continue
            target = await self._published(candidate.target_number)
            if target is not None:
                for key in await self._affected_keys(candidate, target):
                    owners[key] = target
        # Keys written by an earlier publish must be rebuilt even if no candidate points there now.
        for key in document.published_keys:
            owner = await self._published(split_provision_key(key)[0])
            if owner is not None:
                owners.setdefault(key, owner)

        timelines: dict[str, list[ProvisionVersion]] = {}
        labels: dict[str, str] = {}
        inserted: list[ProvisionNode] = []
        removed: list[str] = []
        for key, owner in owners.items():
            parsed = self._structure(owner).get(key)
            changes = await self._changes_for(key, owner)
            if parsed is None and not changes:
                removed.append(key)  # an inserted provision whose amendment was withdrawn
                labels[key] = _inserted_node(key).label
                continue
            base = (
                BaseProvisionText(key, parsed.text, owner.metadata.effective_date, parsed.page)
                if parsed is not None
                else None
            )
            timelines[key] = build_timeline(key, base, changes)
            if parsed is None:
                node = _inserted_node(key)
                inserted.append(node)
                labels[key] = node.label
            else:
                labels[key] = parsed.label

        relations: list[GraphRelation] = []
        for candidate in candidates:
            relation = await self._relation(candidate)
            if relation is not None:
                relations.append(relation)

        number = document.metadata.number
        nodes = [_provision_node(provision, number) for provision in own.values()] + inserted
        foreign_keys = sorted(key for key in timelines if owners[key] is not document)
        return _PublishPlan(nodes, timelines, owners, labels, relations, removed, foreign_keys)

    def _structure(self, owner: LegalDocumentRecord) -> dict[str, ParsedProvision]:
        if owner.id not in self._structures:
            provisions = provisions_from_json(owner.parsed_structure or [])
            self._structures[owner.id] = {p.provision_key: p for p in provisions}
        return self._structures[owner.id]

    async def _published(self, number: str) -> LegalDocumentRecord | None:
        if number == self._document.metadata.number:
            return self._document
        target = await self._repository.get_document_by_number(number)
        # "Has been published": a later failed republish leaves its graph data in place.
        if target is None or target.published_at is None or target.parsed_structure is None:
            return None
        return target

    async def _source_is_live(self, document_id: UUID) -> bool:
        if document_id not in self._live_sources:
            source = await self._repository.get_document(document_id)
            self._live_sources[document_id] = source is not None and source.published_at is not None
        return self._live_sources[document_id]

    async def _incoming_for(self, owner: LegalDocumentRecord) -> list[RelationCandidateRecord]:
        number = owner.metadata.number
        if number not in self._incoming:
            approved = await self._repository.list_candidates_targeting(
                number, [CandidateStatus.APPROVED]
            )
            live: list[RelationCandidateRecord] = []
            for candidate in approved:
                if candidate.type in TIMELINE_RELATION_TYPES and await self._source_is_live(
                    candidate.legal_document_id
                ):
                    live.append(candidate)
            self._incoming[number] = live
        return self._incoming[number]

    async def _known_keys(self, owner: LegalDocumentRecord) -> set[str]:
        keys = set(self._structure(owner))
        for candidate in await self._incoming_for(owner):
            if candidate.type is RelationType.AMENDS and candidate.target_provision_key:
                keys.add(candidate.target_provision_key)
        return keys

    async def _affected_keys(
        self, candidate: RelationCandidateRecord, target: LegalDocumentRecord
    ) -> set[str]:
        known = await self._known_keys(target)
        root = candidate.target_provision_key
        if root is None:
            return known
        return {root} | {key for key in known if key.startswith(f"{root}.")}

    async def _changes_for(self, key: str, owner: LegalDocumentRecord) -> list[ProvisionChange]:
        changes: list[ProvisionChange] = []
        for candidate in await self._incoming_for(owner):
            root = candidate.target_provision_key
            if root is None:
                if candidate.type is not RelationType.AMENDS:
                    changes.append(_terminating_change(candidate, key, candidate.type))
            elif root == key:
                changes.append(
                    ProvisionChange(
                        change_id=str(candidate.id),
                        type=candidate.type,
                        effective_date=candidate.effective_date,
                        new_text=candidate.new_text,
                        source_provision_key=candidate.source_provision_key,
                        page=candidate.evidence_page,
                    )
                )
            elif key.startswith(f"{root}."):
                changes.append(_terminating_change(candidate, key, RelationType.REPLACES))
        return changes

    async def _relation(self, candidate: RelationCandidateRecord) -> GraphRelation | None:
        if candidate.status is not CandidateStatus.APPROVED:
            return None
        if await self._published(candidate.target_number) is None:
            return None
        source_key = (
            None if candidate.type in _DOCUMENT_SOURCE_TYPES else candidate.source_provision_key
        )
        return GraphRelation(
            type=candidate.type.value,
            source_document=self._document.metadata.number,
            source_key=source_key,
            target_number=candidate.target_number,
            target_key=candidate.target_provision_key,
            effective_date=candidate.effective_date,
            evidence_text=candidate.evidence_text,
            evidence_page=candidate.evidence_page,
            review_id=str(candidate.id),
            approved_by=str(candidate.reviewed_by) if candidate.reviewed_by else None,
            approved_at=candidate.reviewed_at,
        )


def _terminating_change(
    candidate: RelationCandidateRecord, key: str, change_type: RelationType
) -> ProvisionChange:
    return ProvisionChange(
        change_id=f"{candidate.id}:{key}",
        type=change_type,
        effective_date=candidate.effective_date,
        source_provision_key=candidate.source_provision_key,
        page=candidate.evidence_page,
    )


def _inserted_node(key: str) -> ProvisionNode:
    number, ref = split_provision_key(key)
    level, label, parent_ref = describe_provision_ref(ref)
    return ProvisionNode(
        provision_key=key,
        document_number=number,
        level=level.value,
        label=label,
        heading="",
        chapter_label=None,
        parent_key=f"{number}#{parent_ref}" if parent_ref else None,
    )


def _provision_node(provision: ParsedProvision, number: str) -> ProvisionNode:
    return ProvisionNode(
        provision_key=provision.provision_key,
        document_number=number,
        level=provision.level.value,
        label=provision.label,
        heading=provision.heading,
        chapter_label=provision.chapter_label,
        parent_key=provision.parent_key,
    )


def _document_node(document: LegalDocumentRecord) -> LegalDocumentNode:
    metadata = document.metadata
    return LegalDocumentNode(
        doc_id=str(document.id),
        number=metadata.number,
        doc_type=metadata.doc_type,
        title=metadata.title,
        issuer=metadata.issuer,
        issued_date=metadata.issued_date,
        effective_date=metadata.effective_date,
        source_url=metadata.source_url,
        file_key=document.file_key,
        sha256=document.sha256,
    )


def _graph_version(version: ProvisionVersion) -> GraphVersion:
    return GraphVersion(
        version_id=str(version.version_id),
        text=version.text,
        text_hash=version.text_hash,
        valid_from=version.valid_from,
        valid_to=version.valid_to,
        page=version.page,
        introduced_by=version.introduced_by,
    )
