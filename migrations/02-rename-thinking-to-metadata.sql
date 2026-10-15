-- Migration: Rename thinking_data to metadata and remove reasoning content
-- Rename column
ALTER TABLE messages RENAME COLUMN thinking_data TO metadata;

-- Update column comment
COMMENT ON COLUMN messages.metadata IS 'Metadata including steps, routing info, retrieval stages, and rejection flags';

-- Rename the index
ALTER INDEX IF EXISTS idx_message_thinking_data RENAME TO idx_message_metadata;

-- Update existing records to delete 'thinking' key from metadata
UPDATE messages SET metadata = metadata - 'thinking';
