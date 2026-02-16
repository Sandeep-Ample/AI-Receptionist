"""Hospital schema using raw SQL

Revision ID: 002
Revises: 
Create Date: 2026-02-10

This migration creates the complete hospital database schema using raw SQL
to avoid SQLAlchemy enum type conflicts.
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables using raw SQL."""
    
    # Create all schema in one SQL block
    op.execute("""
        -- Create ENUM types
        DO $$ BEGIN
            CREATE TYPE appointment_status_enum AS ENUM ('Booked', 'Scheduled', 'Completed', 'Cancelled', 'NoShow', 'Rescheduled');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        
        DO $$ BEGIN
            CREATE TYPE shift_status_enum AS ENUM ('Active', 'Inactive', 'OnLeave');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        
        DO $$ BEGIN
            CREATE TYPE doctor_status_enum AS ENUM ('Active', 'Inactive', 'Retired');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        
        DO $$ BEGIN
            CREATE TYPE gender_enum AS ENUM ('Male', 'Female', 'Other');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        
        DO $$ BEGIN
            CREATE TYPE weekday_enum AS ENUM ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        
        -- Patient Account table
        CREATE TABLE IF NOT EXISTS patient_account (
            account_id SERIAL PRIMARY KEY,
            mobile_no VARCHAR(15) UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        
        -- Patient table
        CREATE TABLE IF NOT EXISTS patient (
            pt_id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES patient_account(account_id),
            name VARCHAR(100) NOT NULL,
            gender gender_enum,
            dob DATE,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        
        -- Specialty table
        CREATE TABLE IF NOT EXISTS specialty (
            spec_id SERIAL PRIMARY KEY,
            spec_name VARCHAR(100) UNIQUE NOT NULL
        );
        
        -- Symptoms table
        CREATE TABLE IF NOT EXISTS symptoms (
            sym_id SERIAL PRIMARY KEY,
            sym_name VARCHAR(100) UNIQUE NOT NULL
        );
        
        -- Doctor table
        CREATE TABLE IF NOT EXISTS doctor (
            doc_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            address TEXT,
            experiences INTEGER CHECK (experiences >= 0),
            degree_doc VARCHAR(100),
            status doctor_status_enum DEFAULT 'Active',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        
        -- Doctor-Specialty junction table
        CREATE TABLE IF NOT EXISTS doctor_specialty (
            doc_id INTEGER NOT NULL REFERENCES doctor(doc_id) ON DELETE CASCADE,
            spec_id INTEGER NOT NULL REFERENCES specialty(spec_id) ON DELETE CASCADE,
            PRIMARY KEY (doc_id, spec_id)
        );
        
        -- Doctor Shift table
        CREATE TABLE IF NOT EXISTS doc_shift (
            shft_id SERIAL PRIMARY KEY,
            doc_id INTEGER NOT NULL REFERENCES doctor(doc_id),
            day_of_week weekday_enum NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            status shift_status_enum DEFAULT 'Active',
            CHECK (start_time < end_time)
        );
        
        -- Appointment table
        CREATE TABLE IF NOT EXISTS appointment (
            app_id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES patient_account(account_id),
            pt_id INTEGER NOT NULL REFERENCES patient(pt_id),
            doc_id INTEGER NOT NULL REFERENCES doctor(doc_id),
            reason TEXT,
            date_time TIMESTAMP NOT NULL,
            app_status appointment_status_enum DEFAULT 'Booked',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        
        -- Patient Memory table
        CREATE TABLE IF NOT EXISTS patient_memory (
            pm_id SERIAL PRIMARY KEY,
            app_id INTEGER REFERENCES appointment(app_id) ON DELETE CASCADE,
            summary TEXT
        );
        
        -- Specialty-Symptoms junction table
        CREATE TABLE IF NOT EXISTS spec_sym (
            spec_id INTEGER NOT NULL REFERENCES specialty(spec_id) ON DELETE CASCADE,
            sym_id INTEGER NOT NULL REFERENCES symptoms(sym_id) ON DELETE CASCADE,
            confidence NUMERIC(3,2) DEFAULT 1.0,
            PRIMARY KEY (spec_id, sym_id)
        );
        
        -- User Memory table
        CREATE TABLE IF NOT EXISTS user_memory (
            phone_number VARCHAR(64) PRIMARY KEY,
            name VARCHAR(128),
            last_summary TEXT,
            last_call TIMESTAMPTZ DEFAULT now(),
            call_count INTEGER DEFAULT 1,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        
        -- Call Session table
        CREATE TABLE IF NOT EXISTS call_session (
            session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            phone_number VARCHAR(64),
            started_at TIMESTAMPTZ DEFAULT now(),
            ended_at TIMESTAMPTZ,
            intent TEXT,
            outcome TEXT,
            transcript TEXT,
            confidence_score NUMERIC(3,2)
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_patient_account_mobile ON patient_account(mobile_no);
        CREATE INDEX IF NOT EXISTS idx_doctor_name ON doctor(name);
        CREATE INDEX IF NOT EXISTS idx_specialty_name ON specialty(spec_name);
        CREATE INDEX IF NOT EXISTS idx_symptoms_name ON symptoms(sym_name);
        CREATE INDEX IF NOT EXISTS idx_appointments_datetime ON appointment(date_time);
        CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointment(pt_id);
        CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointment(doc_id);
        CREATE INDEX IF NOT EXISTS idx_shifts_doctor ON doc_shift(doc_id);
        CREATE INDEX IF NOT EXISTS idx_user_memory_last_call ON user_memory(last_call DESC);
        
        -- Unique index to prevent double booking
        CREATE UNIQUE INDEX IF NOT EXISTS ux_doctor_appointment_time
        ON appointment (doc_id, date_time)
        WHERE app_status NOT IN ('Cancelled', 'NoShow');
        
        -- Create triggers
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        DROP TRIGGER IF EXISTS trg_patient_updated ON patient;
        CREATE TRIGGER trg_patient_updated
        BEFORE UPDATE ON patient
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        DROP TRIGGER IF EXISTS trg_doctor_updated ON doctor;
        CREATE TRIGGER trg_doctor_updated
        BEFORE UPDATE ON doctor
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        DROP TRIGGER IF EXISTS trg_appointment_updated ON appointment;
        CREATE TRIGGER trg_appointment_updated
        BEFORE UPDATE ON appointment
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        DROP TRIGGER IF EXISTS trg_user_memory_updated ON user_memory;
        CREATE TRIGGER trg_user_memory_updated
        BEFORE UPDATE ON user_memory
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop all tables."""
    op.execute("""
        DROP TRIGGER IF EXISTS trg_user_memory_updated ON user_memory;
        DROP TRIGGER IF EXISTS trg_appointment_updated ON appointment;
        DROP TRIGGER IF EXISTS trg_doctor_updated ON doctor;
        DROP TRIGGER IF EXISTS trg_patient_updated ON patient;
        DROP FUNCTION IF EXISTS update_updated_at_column();
        DROP TABLE IF EXISTS call_session CASCADE;
        DROP TABLE IF EXISTS user_memory CASCADE;
        DROP TABLE IF EXISTS spec_sym CASCADE;
        DROP TABLE IF EXISTS patient_memory CASCADE;
        DROP TABLE IF EXISTS appointment CASCADE;
        DROP TABLE IF EXISTS doc_shift CASCADE;
        DROP TABLE IF EXISTS doctor_specialty CASCADE;
        DROP TABLE IF EXISTS doctor CASCADE;
        DROP TABLE IF EXISTS symptoms CASCADE;
        DROP TABLE IF EXISTS specialty CASCADE;
        DROP TABLE IF EXISTS patient CASCADE;
        DROP TABLE IF EXISTS patient_account CASCADE;
        DROP TYPE IF EXISTS weekday_enum;
        DROP TYPE IF EXISTS gender_enum;
        DROP TYPE IF EXISTS doctor_status_enum;
        DROP TYPE IF EXISTS shift_status_enum;
        DROP TYPE IF EXISTS appointment_status_enum;
    """)
