-- Migration: Add retry jobs for failed document cleanup
-- Stores cleanup targets that failed after a document was soft-deleted.

CREATE TABLE IF NOT EXISTS document_deletion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    storage_path VARCHAR(512),
    cleanup_targets JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_deletion_job_status
    ON document_deletion_jobs(status, next_retry_at);

CREATE INDEX IF NOT EXISTS idx_document_deletion_job_document
    ON document_deletion_jobs(document_id);

