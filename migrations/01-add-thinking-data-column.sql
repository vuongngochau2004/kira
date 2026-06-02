-- Migration: Add thinking_data column to messages table
-- This file will be auto-run by PostgreSQL on container init
-- Place in docker-entrypoint-initdb.d/ directory

-- Add thinking_data column to messages table
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS thinking_data JSONB DEFAULT '{}'::jsonb;

-- Add comment for documentation
COMMENT ON COLUMN messages.thinking_data IS 'Thinking data including steps, routing info, retrieval stages';

-- Create index for thinking_data queries (optional, for performance)
CREATE INDEX IF NOT EXISTS idx_message_thinking_data ON messages USING GIN (thinking_data);
