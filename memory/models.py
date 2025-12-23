"""
Database Models and Schema for User Memory

PostgreSQL schema for storing caller information and conversation summaries.
"""

# SQL to create the user_memory table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_memory (
    phone_number VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128),
    last_summary TEXT,
    last_call TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    call_count INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster lookups by last_call for analytics
CREATE INDEX IF NOT EXISTS idx_user_memory_last_call ON user_memory(last_call DESC);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_user_memory_updated_at ON user_memory;
CREATE TRIGGER update_user_memory_updated_at
    BEFORE UPDATE ON user_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

# SQL queries used by the MemoryService
FETCH_USER_SQL = """
SELECT phone_number, name, last_summary, last_call, call_count, metadata
FROM user_memory
WHERE phone_number = $1;
"""

UPSERT_USER_SQL = """
INSERT INTO user_memory (phone_number, name, last_summary, last_call, call_count, metadata)
VALUES ($1, $2, $3, NOW(), 1, $4::jsonb)
ON CONFLICT (phone_number) DO UPDATE SET
    name = COALESCE(EXCLUDED.name, user_memory.name),
    last_summary = EXCLUDED.last_summary,
    last_call = NOW(),
    call_count = user_memory.call_count + 1,
    metadata = user_memory.metadata || EXCLUDED.metadata;
"""

UPDATE_SUMMARY_SQL = """
UPDATE user_memory
SET last_summary = $2, last_call = NOW()
WHERE phone_number = $1;
"""
