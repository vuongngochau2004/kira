-- Migration: Legal knowledge graph staging tables
-- Legal corpus documents and the relation candidates proposed for admin review.
-- Graph data (provisions, versions, approved relations) lives in Neo4j.

CREATE TABLE IF NOT EXISTS legal_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    number VARCHAR(64) NOT NULL UNIQUE,
    doc_type VARCHAR(32) NOT NULL,
    title TEXT NOT NULL,
    issuer VARCHAR(255) NOT NULL,
    issued_date DATE NOT NULL,
    effective_date DATE NOT NULL,
    source_url VARCHAR(1024),
    file_key VARCHAR(512) NOT NULL,
    file_type VARCHAR(16) NOT NULL,
    sha256 VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
    parsed_structure JSONB,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_detail VARCHAR(1000),
    uploaded_by UUID NOT NULL REFERENCES users(id),
    published_at TIMESTAMP,
    published_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_legal_document_status ON legal_documents(status);

CREATE TABLE IF NOT EXISTS legal_relation_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legal_document_id UUID NOT NULL REFERENCES legal_documents(id) ON DELETE CASCADE,
    type VARCHAR(16) NOT NULL,
    source_provision_key VARCHAR(160),
    target_number VARCHAR(64) NOT NULL,
    target_provision_ref VARCHAR(64),
    effective_date DATE NOT NULL,
    new_text TEXT,
    evidence_text TEXT NOT NULL,
    evidence_page INTEGER,
    extractor VARCHAR(16) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP,
    review_note VARCHAR(1000),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_legal_candidate_document
    ON legal_relation_candidates(legal_document_id);
CREATE INDEX IF NOT EXISTS idx_legal_candidate_target
    ON legal_relation_candidates(target_number, status);
