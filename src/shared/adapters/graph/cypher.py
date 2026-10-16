"""Cypher statements for the legal knowledge graph."""

from typing import Final

RELATION_TYPES: Final = ("AMENDS", "REPEALS", "REPLACES", "GUIDES", "BASED_ON")

SCHEMA_STATEMENTS: Final = (
    "CREATE CONSTRAINT legal_document_number IF NOT EXISTS "
    "FOR (d:LegalDocument) REQUIRE d.number IS UNIQUE",
    "CREATE CONSTRAINT provision_key IF NOT EXISTS "
    "FOR (p:Provision) REQUIRE p.provision_key IS UNIQUE",
    "CREATE CONSTRAINT provision_version_id IF NOT EXISTS "
    "FOR (v:ProvisionVersion) REQUIRE v.version_id IS UNIQUE",
    "CREATE INDEX provision_version_valid_from IF NOT EXISTS "
    "FOR (v:ProvisionVersion) ON (v.valid_from)",
    "CREATE INDEX provision_version_valid_to IF NOT EXISTS "
    "FOR (v:ProvisionVersion) ON (v.valid_to)",
    "CREATE INDEX provision_document_number IF NOT EXISTS FOR (p:Provision) ON (p.document_number)",
)

UPSERT_DOCUMENT: Final = """
MERGE (d:LegalDocument {number: $number})
SET d.doc_id = $doc_id, d.doc_type = $doc_type, d.title = $title, d.issuer = $issuer,
    d.issued_date = $issued_date, d.effective_date = $effective_date,
    d.source_url = $source_url, d.file_key = $file_key, d.sha256 = $sha256
"""

UPSERT_PROVISIONS: Final = """
UNWIND $provisions AS row
MERGE (p:Provision {provision_key: row.provision_key})
SET p.document_number = row.document_number, p.level = row.level, p.label = row.label,
    p.heading = row.heading, p.chapter_label = row.chapter_label
"""

LINK_PROVISIONS: Final = """
UNWIND $provisions AS row
MATCH (p:Provision {provision_key: row.provision_key})
OPTIONAL MATCH (parent:Provision {provision_key: row.parent_key})
OPTIONAL MATCH (d:LegalDocument {number: row.document_number})
WITH p, CASE WHEN row.parent_key IS NULL THEN d ELSE parent END AS owner
WHERE owner IS NOT NULL
MERGE (owner)-[:HAS_PART]->(p)
"""

DELETE_STALE_VERSIONS: Final = """
MATCH (:Provision {provision_key: $provision_key})-[:HAS_VERSION]->(v:ProvisionVersion)
WHERE NOT v.version_id IN $version_ids
DETACH DELETE v
"""

UPSERT_VERSIONS: Final = """
MATCH (p:Provision {provision_key: $provision_key})
UNWIND $versions AS row
MERGE (v:ProvisionVersion {version_id: row.version_id})
SET v.provision_key = $provision_key, v.text = row.text, v.text_hash = row.text_hash,
    v.valid_from = row.valid_from, v.valid_to = row.valid_to, v.page = row.page
MERGE (p)-[:HAS_VERSION]->(v)
WITH v, row
OPTIONAL MATCH (v)-[stale:INTRODUCED_BY]->()
DELETE stale
WITH DISTINCT v, row
OPTIONAL MATCH (source:Provision {provision_key: row.introduced_by})
FOREACH (_ IN CASE WHEN source IS NULL THEN [] ELSE [1] END |
  MERGE (v)-[:INTRODUCED_BY]->(source))
"""

DELETE_DOCUMENT_RELATIONS: Final = """
MATCH ()-[r]->()
WHERE r.source_document = $source_document AND type(r) IN $types
DELETE r
"""


def relation_query(rel_type: str) -> str:
    """Build the MERGE query for one relation type (types cannot be Cypher parameters)."""
    if rel_type not in RELATION_TYPES:
        raise ValueError(f"Unsupported legal relation type: {rel_type}")
    return (
        "UNWIND $relations AS row\n"
        "OPTIONAL MATCH (source_document:LegalDocument {number: row.source_document})\n"
        "OPTIONAL MATCH (source_provision:Provision {provision_key: row.source_key})\n"
        "OPTIONAL MATCH (target_document:LegalDocument {number: row.target_number})\n"
        "OPTIONAL MATCH (target_provision:Provision {provision_key: row.target_key})\n"
        "WITH row,\n"
        "  CASE WHEN row.source_key IS NULL THEN source_document ELSE source_provision END"
        " AS source,\n"
        "  CASE WHEN row.target_key IS NULL THEN target_document ELSE target_provision END"
        " AS target\n"
        "WHERE source IS NOT NULL AND target IS NOT NULL\n"
        f"MERGE (source)-[r:{rel_type} {{review_id: row.review_id}}]->(target)\n"
        "SET r.source_document = row.source_document, r.effective_date = row.effective_date,\n"
        "    r.evidence_text = row.evidence_text, r.evidence_page = row.evidence_page,\n"
        "    r.approved_by = row.approved_by, r.approved_at = row.approved_at\n"
    )


DELETE_PROVISIONS: Final = """
UNWIND $provision_keys AS key
MATCH (p:Provision {provision_key: key})
OPTIONAL MATCH (p)-[:HAS_VERSION]->(v:ProvisionVersion)
DETACH DELETE v, p
"""

EXPAND_CONTEXT: Final = """
UNWIND $keys AS key
MATCH (p:Provision {provision_key: key})
OPTIONAL MATCH (parent:Provision)-[:HAS_PART]->(p)
OPTIONAL MATCH (parent)-[:HAS_VERSION]->(pv:ProvisionVersion)
WHERE pv.valid_from <= $day AND (pv.valid_to IS NULL OR $day < pv.valid_to)
OPTIONAL MATCH (p)-[:HAS_VERSION]->(current:ProvisionVersion)
WHERE current.valid_from <= $day AND (current.valid_to IS NULL OR $day < current.valid_to)
OPTIONAL MATCH (current)-[:INTRODUCED_BY]->(source:Provision)
OPTIONAL MATCH (source_document:LegalDocument {number: source.document_number})
OPTIONAL MATCH (p)-[:HAS_VERSION]->(later:ProvisionVersion)
WHERE later.valid_from > $day
RETURN key, parent.label AS parent_label, pv.text AS parent_text,
       source.provision_key AS introduced_by, source_document.number AS introduced_by_number,
       source_document.title AS introduced_by_title, min(later.valid_from) AS amended_after
"""

GUIDING_DOCUMENTS: Final = """
UNWIND $keys AS key
MATCH (p:Provision {provision_key: key})
OPTIONAL MATCH (d:LegalDocument {number: p.document_number})
OPTIONAL MATCH (by_provision)-[:GUIDES]->(p)
OPTIONAL MATCH (by_document)-[:GUIDES]->(d)
WITH collect(coalesce(by_provision.number, by_provision.document_number))
   + collect(coalesce(by_document.number, by_document.document_number)) AS numbers
UNWIND numbers AS number
RETURN DISTINCT number
ORDER BY number
"""
