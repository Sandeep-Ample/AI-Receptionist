"""
Database Models and Schema for User Memory

PostgreSQL schema for storing caller information and conversation summaries.
"""

# SQL to create the user_memory table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_memory (
    phone_number VARCHAR(64),
    email VARCHAR(255) UNIQUE,
    name VARCHAR(128),
    last_summary TEXT,
    last_call TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    call_count INTEGER DEFAULT 1,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMP WITH TIME ZONE,
    password_hash VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (phone_number, email)
);

-- Index for faster lookups by email
CREATE INDEX IF NOT EXISTS idx_user_memory_email ON user_memory(email);

-- Index for faster lookups by last_call for analytics
CREATE INDEX IF NOT EXISTS idx_user_memory_last_call ON user_memory(last_call DESC);

-- Index for approval status
CREATE INDEX IF NOT EXISTS idx_user_memory_approved ON user_memory(is_approved) WHERE is_approved = TRUE;

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_user_memory_updated_at ON user_memory;
CREATE TRIGGER update_user_memory_updated_at
    BEFORE UPDATE ON user_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

# SQL queries used by the MemoryService
FETCH_USER_BY_EMAIL_SQL = """
SELECT phone_number, email, name, last_summary, last_call, call_count, is_approved, metadata
FROM user_memory
WHERE email = $1;
"""

FETCH_USER_SQL = """
SELECT phone_number, email, name, last_summary, last_call, call_count, is_approved, metadata
FROM user_memory
WHERE phone_number = $1;
"""

UPSERT_USER_SQL = """
INSERT INTO user_memory (phone_number, email, name, last_summary, call_count, metadata)
VALUES ($1, $2, $3, $4, 1, $5)
ON CONFLICT (phone_number, email) 
DO UPDATE SET 
    name = COALESCE(EXCLUDED.name, user_memory.name),
    last_summary = EXCLUDED.last_summary,
    last_call = now(),
    call_count = user_memory.call_count + 1,
    updated_at = now()
"""

UPSERT_USER_BY_EMAIL_SQL = """
INSERT INTO user_memory (email, name, is_approved)
VALUES ($1, $2, $3)
ON CONFLICT (email) 
DO UPDATE SET 
    name = COALESCE(EXCLUDED.name, user_memory.name),
    is_approved = COALESCE(EXCLUDED.is_approved, user_memory.is_approved),
    approved_at = CASE 
        WHEN EXCLUDED.is_approved = TRUE AND user_memory.is_approved = FALSE THEN NOW()
        ELSE user_memory.approved_at
    END,
    updated_at = now()
"""


UPDATE_SUMMARY_SQL = """
UPDATE user_memory
SET last_summary = $2, last_call = NOW()
WHERE email = $1;
"""

UPDATE_APPROVAL_SQL = """
UPDATE user_memory
SET is_approved = $2, approved_at = NOW()
WHERE email = $1;
"""
