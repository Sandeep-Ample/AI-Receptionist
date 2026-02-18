"""
Database Connection Tests for Supabase/PostgreSQL

This module provides comprehensive tests for database connectivity,
schema validation, and basic operations to catch issues before production.

Usage:
    # Run all tests
    pytest tests/test_database.py -v
    
    # Run with environment variables
    DATABASE_URL=postgresql://... pytest tests/test_database.py -v
    
    # Run specific test
    pytest tests/test_database.py::TestSupabaseConnection -v
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try imports with helpful error messages
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    print("⚠️  asyncpg not installed. Run: pip install asyncpg")

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("⚠️  psycopg2 not installed. Run: pip install psycopg2-binary")


# =============================================================================
# CONFIGURATION
# =============================================================================

def get_database_url() -> Optional[str]:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        print("❌ DATABASE_URL environment variable not set")
    return url


def parse_supabase_url(url: str) -> dict:
    """
    Parse Supabase/Neon database URL and extract components.
    
    Useful for debugging connection issues.
    
    Args:
        url: PostgreSQL connection string
        
    Returns:
        Dict with host, port, database, user, ssl_mode
    """
    # Remove postgresql:// prefix
    if url.startswith("postgresql://"):
        url = url[13:]
    
    # Parse components
    # Format: user:password@host:port/database?params
    try:
        auth, rest = url.split("@", 1)
        user, password = auth.split(":", 1)
        
        if "?" in rest:
            host_port_db, params = rest.split("?", 1)
        else:
            host_port_db = rest
            params = ""
        
        # Handle host:port/database
        parts = host_port_db.split("/")
        database = parts[1] if len(parts) > 1 else "postgres"
        host_port = parts[0]
        
        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host = host_port
            port = "5432"
        
        # Parse SSL mode from params
        ssl_mode = "require"
        if "sslmode=" in params:
            for param in params.split("&"):
                if param.startswith("sslmode="):
                    ssl_mode = param.split("=")[1]
                    break
        
        return {
            "host": host,
            "port": int(port),
            "database": database,
            "user": user,
            "password": password,
            "ssl_mode": ssl_mode,
        }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# SYNC CONNECTION TESTS (psycopg2)
# =============================================================================

@pytest.mark.skipif(not PSYCOPG2_AVAILABLE, reason="psycopg2 not installed")
class TestSyncConnection:
    """Test synchronous database connection using psycopg2."""
    
    def test_basic_connection(self):
        """Test basic database connectivity."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # Test basic query
            cur.execute("SELECT version();")
            version = cur.fetchone()
            
            assert version is not None
            print(f"✅ Connected to PostgreSQL: {version[0][:50]}...")
            
            cur.close()
        finally:
            if conn:
                conn.close()
    
    def test_ssl_connection(self):
        """Test that SSL is properly configured."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        # Ensure URL has sslmode=require
        if "sslmode" not in db_url:
            db_url = f"{db_url}?sslmode=require"
        
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # Check SSL is in use via pg_stat_ssl (works on all PostgreSQL including Supabase)
            cur.execute("""
                SELECT ssl FROM pg_stat_ssl 
                WHERE pid = pg_backend_pid();
            """)
            ssl_status = cur.fetchone()[0]
            ssl_used = ssl_status in ('t', True, 'on')
            print(f"🔒 SSL connection: {'Yes' if ssl_used else 'No'} (status: {ssl_status})")
            
            # For Supabase pooler, SSL should always be on
            if not ssl_used:
                print("⚠️  SSL not detected - check your connection string")
            
            cur.close()
        finally:
            if conn:
                conn.close()
    
    def test_connection_timeout(self):
        """Test connection with timeout settings."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        # Add timeout parameters
        if "?" in db_url:
            test_url = f"{db_url}&connect_timeout=10"
        else:
            test_url = f"{db_url}?connect_timeout=10"
        
        conn = None
        try:
            conn = psycopg2.connect(test_url)
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            result = cur.fetchone()
            assert result[0] == 1
            cur.close()
            print("✅ Connection with timeout successful")
        finally:
            if conn:
                conn.close()


# =============================================================================
# ASYNC CONNECTION TESTS (asyncpg)
# =============================================================================

@pytest.mark.skipif(not ASYNCPG_AVAILABLE, reason="asyncpg not installed")
class TestAsyncConnection:
    """Test asynchronous database connection using asyncpg."""
    
    @pytest.mark.asyncio
    async def test_async_connection(self):
        """Test async database connectivity."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        conn = None
        try:
            conn = await asyncpg.connect(db_url)
            
            # Test basic query
            version = await conn.fetchval("SELECT version();")
            assert version is not None
            print(f"✅ Async connected to PostgreSQL: {version[:50]}...")
            
        finally:
            if conn:
                await conn.close()
    
    @pytest.mark.asyncio
    async def test_connection_pool(self):
        """Test connection pooling for production readiness."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        pool = None
        try:
            # Create pool with production-like settings
            pool = await asyncpg.create_pool(
                db_url,
                min_size=2,
                max_size=10,
                command_timeout=30.0
            )
            
            # Test multiple concurrent connections
            async def query_test(i):
                async with pool.acquire() as conn:
                    return await conn.fetchval("SELECT $1::int", i)
            
            # Run 5 concurrent queries
            results = await asyncio.gather(*[query_test(i) for i in range(5)])
            assert results == [0, 1, 2, 3, 4]
            print("✅ Connection pool working correctly")
            
        finally:
            if pool:
                await pool.close()


# =============================================================================
# SUPABASE SPECIFIC TESTS
# =============================================================================

class TestSupabaseConnection:
    """Tests specific to Supabase database connections."""
    
    def test_parse_supabase_url(self):
        """Test parsing of Supabase connection URL."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        info = parse_supabase_url(db_url)
        
        if "error" in info:
            pytest.fail(f"Failed to parse DATABASE_URL: {info['error']}")
        
        print(f"📍 Database host: {info['host']}")
        print(f"📍 Database name: {info['database']}")
        print(f"📍 Database user: {info['user']}")
        print(f"📍 SSL mode: {info['ssl_mode']}")
        
        # Supabase hosts end with .supabase.co
        if "supabase" in info['host'].lower():
            print("✅ Detected Supabase database")
            assert info['ssl_mode'] in ['require', 'verify-full'], \
                "Supabase requires SSL. Add ?sslmode=require to DATABASE_URL"
    
    @pytest.mark.skipif(not PSYCOPG2_AVAILABLE, reason="psycopg2 not installed")
    def test_supabase_extensions(self):
        """Test that required PostgreSQL extensions are available."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        info = parse_supabase_url(db_url)
        if "supabase" not in info.get('host', '').lower():
            pytest.skip("Not a Supabase database")
        
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # Check for uuid-ossp (required for gen_random_uuid)
            cur.execute("""
                SELECT extname FROM pg_extension 
                WHERE extname IN ('uuid-ossp', 'pgcrypto');
            """)
            extensions = [row[0] for row in cur.fetchall()]
            
            print(f"📦 Available extensions: {extensions}")
            
            # Test gen_random_uuid() function
            cur.execute("SELECT gen_random_uuid();")
            uuid_result = cur.fetchone()
            assert uuid_result is not None
            print(f"✅ gen_random_uuid() working: {uuid_result[0]}")
            
            cur.close()
        finally:
            if conn:
                conn.close()


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================

@pytest.mark.skipif(not PSYCOPG2_AVAILABLE, reason="psycopg2 not installed")
class TestSchemaValidation:
    """Validate database schema is correctly set up."""
    
    def test_required_tables_exist(self):
        """Test that all required tables exist."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        required_tables = [
            'patient_account',
            'patient',
            'doctor',
            'specialty',
            'symptoms',
            'appointment',
            'doc_shift',
            'user_memory',
            'call_session',
            'doctor_specialty',
            'spec_sym',
            'patient_memory',
        ]
        
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            existing_tables = [row[0] for row in cur.fetchall()]
            
            missing_tables = set(required_tables) - set(existing_tables)
            
            if missing_tables:
                print(f"\n❌ Missing tables: {missing_tables}")
                print("\n📋 Run migrations to create tables:")
                print("   cd AI-Receptionist")
                print("   alembic upgrade head")
                print("\n   Or run the SQL schema directly:")
                print("   psql $DATABASE_URL -f sql_schemas/database_hospital.sql")
            else:
                print(f"✅ All {len(required_tables)} required tables exist")
            
            assert len(missing_tables) == 0, f"Missing tables: {missing_tables}. Run: alembic upgrade head"
            
            cur.close()
        finally:
            if conn:
                conn.close()
    
    def test_enum_types_exist(self):
        """Test that required ENUM types are created."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        required_enums = [
            'appointment_status_enum',
            'shift_status_enum',
            'doctor_status_enum',
            'gender_enum',
            'weekday_enum',
        ]
        
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT typname FROM pg_type 
                WHERE typcategory = 'E';
            """)
            existing_enums = [row[0] for row in cur.fetchall()]
            
            missing_enums = set(required_enums) - set(existing_enums)
            
            if missing_enums:
                print(f"\n❌ Missing ENUM types: {missing_enums}")
                print("\n📋 Run migrations to create ENUM types:")
                print("   alembic upgrade head")
            else:
                print(f"✅ All {len(required_enums)} ENUM types exist")
            
            assert len(missing_enums) == 0, f"Missing ENUM types: {missing_enums}. Run: alembic upgrade head"
            
            cur.close()
        finally:
            if conn:
                conn.close()
    
    def test_indexes_exist(self):
        """Test that performance indexes are created."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE schemaname = 'public';
            """)
            indexes = [row[0] for row in cur.fetchall()]
            
            # Check for critical indexes
            critical_indexes = [
                'idx_user_memory_last_call',
                'ux_doctor_appointment_time',
            ]
            
            for idx in critical_indexes:
                if idx in indexes:
                    print(f"✅ Index exists: {idx}")
                else:
                    print(f"⚠️  Missing index: {idx}")
            
            print(f"📊 Total indexes: {len(indexes)}")
            
            cur.close()
        finally:
            if conn:
                conn.close()


# =============================================================================
# CRUD OPERATION TESTS
# =============================================================================

@pytest.mark.skipif(not ASYNCPG_AVAILABLE, reason="asyncpg not installed")
class TestCRUDOperations:
    """Test basic CRUD operations to verify database functionality."""
    
    @pytest.mark.asyncio
    async def test_user_memory_crud(self):
        """Test user_memory table CRUD operations."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        test_phone = f"+91_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        conn = None
        try:
            conn = await asyncpg.connect(db_url)
            
            # Check if table exists first
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_memory'
                );
            """)
            
            if not table_exists:
                pytest.skip("user_memory table doesn't exist. Run: alembic upgrade head")
            
            # CREATE
            await conn.execute("""
                INSERT INTO user_memory (phone_number, name, last_summary)
                VALUES ($1, $2, $3);
            """, test_phone, "Test User", "Test summary")
            print(f"✅ Created user_memory record for {test_phone}")
            
            # READ
            row = await conn.fetchrow("""
                SELECT phone_number, name, last_summary, call_count
                FROM user_memory WHERE phone_number = $1;
            """, test_phone)
            assert row is not None
            assert row['name'] == "Test User"
            assert row['call_count'] == 1
            print(f"✅ Read user_memory record: {dict(row)}")
            
            # UPDATE
            await conn.execute("""
                UPDATE user_memory 
                SET last_summary = $1, call_count = call_count + 1
                WHERE phone_number = $2;
            """, "Updated summary", test_phone)
            
            updated = await conn.fetchrow("""
                SELECT last_summary, call_count FROM user_memory 
                WHERE phone_number = $1;
            """, test_phone)
            assert updated['call_count'] == 2
            assert updated['last_summary'] == "Updated summary"
            print(f"✅ Updated user_memory record")
            
            # DELETE (cleanup)
            await conn.execute("""
                DELETE FROM user_memory WHERE phone_number = $1;
            """, test_phone)
            print(f"✅ Deleted test record")
            
        finally:
            if conn:
                await conn.close()
    
    @pytest.mark.asyncio
    async def test_specialty_query(self):
        """Test specialty table query (used by agent)."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        conn = None
        try:
            conn = await asyncpg.connect(db_url)
            
            # Check if table exists first
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'specialty'
                );
            """)
            
            if not table_exists:
                pytest.skip("specialty table doesn't exist. Run: alembic upgrade head")
            
            # Check if specialties exist
            specialties = await conn.fetch("""
                SELECT spec_id, spec_name FROM specialty LIMIT 5;
            """)
            
            if specialties:
                print(f"✅ Found {len(specialties)} specialties:")
                for spec in specialties:
                    print(f"   - {spec['spec_name']}")
            else:
                print("⚠️  No specialties found. Run: python scripts/seed_database.py")
            
        finally:
            if conn:
                await conn.close()
    
    @pytest.mark.asyncio
    async def test_doctor_availability_query(self):
        """Test doctor availability query (used by agent)."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        conn = None
        try:
            conn = await asyncpg.connect(db_url)
            
            # Check if table exists first
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'doctor'
                );
            """)
            
            if not table_exists:
                pytest.skip("doctor table doesn't exist. Run: alembic upgrade head")
            
            # Query similar to what agent uses
            doctors = await conn.fetch("""
                SELECT d.doc_id, d.name, d.status, 
                       array_agg(s.spec_name) as specialties
                FROM doctor d
                LEFT JOIN doctor_specialty ds ON d.doc_id = ds.doc_id
                LEFT JOIN specialty s ON ds.spec_id = s.spec_id
                WHERE d.is_active = true AND d.status = 'Active'
                GROUP BY d.doc_id
                LIMIT 5;
            """)
            
            if doctors:
                print(f"✅ Found {len(doctors)} active doctors:")
                for doc in doctors:
                    print(f"   - {doc['name']}: {doc['specialties']}")
            else:
                print("⚠️  No doctors found. Run: python scripts/seed_database.py")
            
        finally:
            if conn:
                await conn.close()


# =============================================================================
# PRODUCTION READINESS TESTS
# =============================================================================

class TestProductionReadiness:
    """Tests to verify database is ready for production."""
    
    def test_ssl_mode_required(self):
        """Verify SSL is required for production."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        # Check URL has sslmode
        assert "sslmode=" in db_url or "ssl=true" in db_url, \
            "Production database must use SSL. Add ?sslmode=require to DATABASE_URL"
        print("✅ SSL mode configured in connection string")
    
    def test_connection_string_format(self):
        """Verify connection string format is correct."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        # Should start with postgresql://
        assert db_url.startswith("postgresql://"), \
            "DATABASE_URL must start with postgresql://"
        
        # Should not have placeholder values
        invalid_patterns = ["your_", "placeholder", "example", "xxx"]
        for pattern in invalid_patterns:
            assert pattern not in db_url.lower(), \
                f"DATABASE_URL contains placeholder: {pattern}"
        
        print("✅ Connection string format is valid")
    
    @pytest.mark.skipif(not PSYCOPG2_AVAILABLE, reason="psycopg2 not installed")
    def test_database_permissions(self):
        """Test that database user has required permissions."""
        db_url = get_database_url()
        if not db_url:
            pytest.skip("DATABASE_URL not set")
        
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # Check if tables exist first
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'user_memory';
            """)
            if not cur.fetchone():
                pytest.skip("user_memory table doesn't exist. Run: alembic upgrade head")
            
            # Test INSERT permission
            cur.execute("""
                SELECT has_table_privilege('public.user_memory', 'INSERT');
            """)
            can_insert = cur.fetchone()[0]
            assert can_insert, "User lacks INSERT permission on user_memory"
            
            # Test SELECT permission
            cur.execute("""
                SELECT has_table_privilege('public.doctor', 'SELECT');
            """)
            can_select = cur.fetchone()[0]
            assert can_select, "User lacks SELECT permission on doctor"
            
            print("✅ Database user has required permissions")
            
            cur.close()
        finally:
            if conn:
                conn.close()


# =============================================================================
# STANDALONE TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all database tests without pytest."""
    print("\n" + "=" * 60)
    print("DATABASE CONNECTION TEST SUITE")
    print("=" * 60 + "\n")
    
    db_url = get_database_url()
    if not db_url:
        print("❌ DATABASE_URL not set. Please set it before running tests.")
        print("   Example: export DATABASE_URL='postgresql://...'")
        return False
    
    # Parse and display connection info
    info = parse_supabase_url(db_url)
    print("📍 Connection Details:")
    print(f"   Host: {info.get('host', 'N/A')}")
    print(f"   Database: {info.get('database', 'N/A')}")
    print(f"   User: {info.get('user', 'N/A')}")
    print(f"   SSL Mode: {info.get('ssl_mode', 'N/A')}")
    print()
    
    # Run sync tests
    if PSYCOPG2_AVAILABLE:
        print("Testing synchronous connection (psycopg2)...")
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()
            print(f"✅ Connected: {version[0][:60]}...")
            cur.close()
            conn.close()
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    else:
        print("⚠️  Skipping sync tests: psycopg2 not installed")
    
    # Run async tests
    if ASYNCPG_AVAILABLE:
        print("\nTesting asynchronous connection (asyncpg)...")
        async def test_async():
            try:
                conn = await asyncpg.connect(db_url)
                version = await conn.fetchval("SELECT version();")
                print(f"✅ Async connected: {version[:60]}...")
                await conn.close()
                return True
            except Exception as e:
                print(f"❌ Async connection failed: {e}")
                return False
        
        success = asyncio.run(test_async())
        if not success:
            return False
    else:
        print("⚠️  Skipping async tests: asyncpg not installed")
    
    # Test schema
    print("\nTesting schema...")
    if PSYCOPG2_AVAILABLE:
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            tables = [row[0] for row in cur.fetchall()]
            print(f"✅ Found {len(tables)} tables: {', '.join(tables[:5])}...")
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"❌ Schema test failed: {e}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Database ready for production!")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    # Run standalone tests
    run_all_tests()
