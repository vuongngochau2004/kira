-- Migration: Add document cancellation support
-- Stores Celery task IDs so processing can be revoked when a user cancels.

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS processing_task_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_document_processing_task
    ON documents(processing_task_id)
    WHERE processing_task_id IS NOT NULL;
