# Design Document: LiveKit Agent Deployment

## Overview

This design outlines the deployment architecture for a Python-based LiveKit voice agent application to production. The system leverages LiveKit Cloud Agents for hosting the agent, providing automatic scaling, load balancing, and integration with LiveKit's Agent Sandbox UI for testing. The architecture prioritizes low latency (<200ms end-to-end), cost-effectiveness, and operational simplicity.

The deployment consists of three primary components:
1. **Agent**: Python application deployed to LiveKit Cloud Agents
2. **Database**: Managed PostgreSQL instance with hospital schema
3. **Frontend**: LiveKit Agent Sandbox UI (provided by LiveKit Cloud)

Key design decisions:
- Use LiveKit Cloud Agents for agent hosting (optimal latency to LiveKit Cloud, automatic scaling)
- Use Neon or Supabase for PostgreSQL (serverless, connection pooling, cost-effective)
- Leverage LiveKit Agent Sandbox UI instead of deploying separate Streamlit frontend
- Implement CI/CD via GitHub Actions with LiveKit CLI
- Use LiveKit Cloud's secrets management for API keys

## Architecture

### High-Level Architecture

```mermaid
graph TB
    User[User/Tester] -->|HTTPS| Sandbox[LiveKit Agent Sandbox UI]
    Sandbox -->|WebRTC/WSS| LiveKit[LiveKit Cloud]
    LiveKit -->|Agent Protocol| Agent[Python Agent on LiveKit Cloud Agents]
    Agent -->|SSL/TLS| DB[(PostgreSQL Database)]
    Agent -->|HTTPS| Deepgram[Deepgram STT]
    Agent -->|HTTPS| OpenAI[OpenAI GPT-4o-mini]
    Agent -->|HTTPS| Cartesia[Cartesia TTS]
    
    GitHub[GitHub Repository] -->|Push| Actions[GitHub Actions]
    Actions -->|Deploy| Agent
    Actions -->|Migrate| DB
```

### Component Placement and Latency Optimization

**LiveKit Cloud Agents**: Automatically deployed in regions closest to LiveKit Cloud infrastructure. LiveKit manages region selection for optimal latency.

**Database**: Deploy in the same cloud provider region as LiveKit Cloud Agents when possible. Based on [research](https://seenode.com/blog/top-managed-postgresql-services-compared), recommended options:
- **Neon**: Serverless PostgreSQL with auto-scaling, available on AWS and Azure regions
- **Supabase**: Developer-friendly with built-in connection pooling, available on AWS regions

**Target Latencies**:
- Agent ↔ LiveKit Cloud: <50ms (managed by LiveKit Cloud Agents)
- Agent ↔ Database: <20ms (same region deployment)
- Agent ↔ STT/LLM/TTS: <100ms (external services)
- End-to-end voice processing: <200ms

### Deployment Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant Actions as GitHub Actions
    participant LK as LiveKit CLI
    participant Cloud as LiveKit Cloud Agents
    participant DB as Database
    
    Dev->>GH: Push code to main branch
    GH->>Actions: Trigger workflow
    Actions->>DB: Run migrations
    Actions->>LK: livekit-cli deploy
    LK->>Cloud: Build container & deploy
    Cloud->>Cloud: Health check
    Cloud->>Actions: Deployment success
    Actions->>Dev: Notify completion
```

## Components and Interfaces

### 1. Python Agent

**Structure**:
```
project/
├── main.py              # Agent entry point
├── app.py               # Streamlit UI (optional, for local testing)
├── agents/              # Modular agent components
│   ├── __init__.py
│   ├── receptionist.py
│   └── appointment.py
├── memory/              # Database service layer
│   ├── __init__.py
│   └── db_service.py
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
└── livekit.yaml         # LiveKit agent configuration
```

**Key Interfaces**:

```python
# Agent entry point (main.py)
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from agents.receptionist import ReceptionistAgent

async def entrypoint(ctx: JobContext):
    """Main entry point for LiveKit agent"""
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Initialize agent with database connection
    agent = ReceptionistAgent(
        db_url=os.getenv("DATABASE_URL"),
        openai_key=os.getenv("OPENAI_API_KEY"),
        deepgram_key=os.getenv("DEEPGRAM_API_KEY"),
        cartesia_key=os.getenv("CARTESIA_API_KEY")
    )
    
    await agent.start(ctx.room)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

**Database Service Interface**:

```python
# memory/db_service.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import asyncpg

class DatabaseService:
    def __init__(self, database_url: str):
        # Use connection pooling for efficiency
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before use
            connect_args={"ssl": "require"}
        )
    
    async def get_available_appointments(self, doctor_id: int, date: str):
        """Query available appointment slots"""
        pass
    
    async def book_appointment(self, patient_id: int, doctor_id: int, 
                              datetime: str):
        """Book an appointment"""
        pass
    
    async def get_patient_info(self, patient_id: int):
        """Retrieve patient information"""
        pass
```

### 2. LiveKit Agent Configuration

**livekit.yaml**:
```yaml
# Agent configuration for LiveKit Cloud
agent:
  name: hospital-receptionist
  version: 1.0.0
  
# Build configuration
build:
  dockerfile: Dockerfile
  context: .
  
# Runtime configuration
runtime:
  python_version: "3.11"
  
# Resource limits
resources:
  cpu: 1
  memory: 2Gi
  
# Auto-scaling configuration
scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 70
```

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the agent
CMD ["python", "main.py", "start"]
```

### 3. Database Schema Management

**Migration Tool**: Alembic for schema versioning

**Directory Structure**:
```
migrations/
├── alembic.ini
├── env.py
├── script.py.mako
└── versions/
    ├── 001_initial_schema.py
    ├── 002_add_appointments.py
    └── 003_add_shifts.py
```

**Migration Example**:
```python
# migrations/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'patients',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('email', sa.String(255)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    op.create_table(
        'doctors',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('specialty', sa.String(100)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Additional tables...

def downgrade():
    op.drop_table('doctors')
    op.drop_table('patients')
```

### 4. CI/CD Pipeline

**GitHub Actions Workflow** (.github/workflows/deploy.yml):

```yaml
name: Deploy to LiveKit Cloud

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install alembic psycopg2-binary
      
      - name: Run database migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          alembic upgrade head
      
      - name: Install LiveKit CLI
        run: |
          curl -sSL https://get.livekit.io/cli | bash
      
      - name: Deploy to LiveKit Cloud
        env:
          LIVEKIT_API_KEY: ${{ secrets.LIVEKIT_API_KEY }}
          LIVEKIT_API_SECRET: ${{ secrets.LIVEKIT_API_SECRET }}
        run: |
          livekit-cli deploy \
            --project hospital-receptionist \
            --config livekit.yaml
      
      - name: Verify deployment
        run: |
          livekit-cli agent list
```

## Data Models

### Database Schema

**Core Tables**:

```sql
-- Patients table
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Doctors table
CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    specialty VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Appointments table
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id),
    doctor_id INTEGER REFERENCES doctors(id),
    appointment_datetime TIMESTAMP NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    status VARCHAR(20) DEFAULT 'scheduled',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_status CHECK (status IN ('scheduled', 'completed', 'cancelled', 'no_show'))
);

-- Doctor shifts table
CREATE TABLE doctor_shifts (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctors(id),
    day_of_week INTEGER CHECK (day_of_week BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_time_range CHECK (end_time > start_time)
);

-- Indexes for performance
CREATE INDEX idx_appointments_datetime ON appointments(appointment_datetime);
CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX idx_shifts_doctor ON doctor_shifts(doctor_id);
```

**Connection Pooling Configuration**:

```python
# Database connection settings
DATABASE_CONFIG = {
    "pool_size": 10,           # Base connections
    "max_overflow": 20,        # Additional connections under load
    "pool_timeout": 30,        # Wait time for connection
    "pool_recycle": 3600,      # Recycle connections every hour
    "pool_pre_ping": True,     # Verify connection health
    "connect_args": {
        "ssl": "require",
        "connect_timeout": 10,
        "application_name": "hospital-receptionist-agent"
    }
}
```

### Environment Variables

**Required Secrets** (stored in LiveKit Cloud secrets management):

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require

# LiveKit
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# AI Services
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## Platform Recommendations

### Database Hosting Comparison

Based on [research comparing managed PostgreSQL services](https://seenode.com/blog/top-managed-postgresql-services-compared), here are the recommended options:

| Platform | Pros | Cons | Cost (Est.) | Best For |
|----------|------|------|-------------|----------|
| **Neon** | - Serverless auto-scaling<br>- Pay-per-use (idle = $0)<br>- 30-day PITR<br>- Database branching<br>- AWS & Azure regions | - Newer platform<br>- Limited track record | Free tier: 0.5GB<br>Pro: ~$20/mo | Development, staging, cost-sensitive production |
| **Supabase** | - Developer-friendly<br>- Built-in connection pooling<br>- PostGIS, pgvector support<br>- GitHub integration<br>- Multiple AWS regions | - Fixed instance pricing<br>- No true serverless | Free tier: 500MB<br>Pro: $25/mo | Development with real-time features, production |
| **Railway** | - Simple setup<br>- GitHub integration<br>- Fast deployment | - Limited extensions<br>- Fewer regions<br>- Manual scaling | Free: $5 credit<br>Paid: ~$10-20/mo | Quick prototypes, development |
| **Render** | - PITR backups<br>- PostGIS, pgvector<br>- Multi-zone HA | - Manual scaling<br>- Limited regions | Free tier: 90 days<br>Starter: $7/mo | Small production apps |

**Recommendation**: 
- **Development/Staging**: Neon (free tier, auto-scaling, cost-effective)
- **Production**: Supabase or Neon Pro (proven reliability, connection pooling, good extension support)

### Cost Estimates

**Development Environment**:
- LiveKit Cloud Agents: Free tier (limited hours) or ~$20/mo
- Database (Neon): Free tier
- External APIs (STT/LLM/TTS): Pay-per-use (~$10-50/mo depending on usage)
- **Total**: ~$30-70/mo

**Staging Environment**:
- LiveKit Cloud Agents: ~$50/mo
- Database (Neon Pro): ~$20/mo
- External APIs: ~$50-100/mo
- **Total**: ~$120-170/mo

**Production Environment** (estimated for moderate usage):
- LiveKit Cloud Agents: ~$200-500/mo (auto-scaling)
- Database (Supabase Pro): ~$25-100/mo
- External APIs: ~$200-500/mo
- Monitoring/Logging: ~$20-50/mo
- **Total**: ~$445-1,150/mo

## Error Handling

### Agent Error Handling

**Connection Failures**:
```python
class ReceptionistAgent:
    async def start(self, room):
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                # Verify all service connections
                await self._verify_database_connection()
                await self._verify_ai_services()
                
                # Start agent
                await self._run_agent_loop(room)
                break
                
            except DatabaseConnectionError as e:
                logger.error(f"Database connection failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    # Fail gracefully
                    await self._send_error_message(room, 
                        "I'm having trouble connecting to our system. Please try again later.")
                    raise
                    
            except AIServiceError as e:
                logger.error(f"AI service error: {e}")
                # Continue with degraded functionality
                await self._run_fallback_mode(room)
```

**Database Query Errors**:
```python
async def get_available_appointments(self, doctor_id: int, date: str):
    try:
        async with self.engine.begin() as conn:
            result = await conn.execute(query, params)
            return result.fetchall()
            
    except OperationalError as e:
        logger.error(f"Database operational error: {e}")
        # Retry with exponential backoff
        await asyncio.sleep(1)
        return await self._retry_query(query, params)
        
    except IntegrityError as e:
        logger.error(f"Data integrity error: {e}")
        raise ValidationError("Invalid data provided")
        
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        raise DatabaseError("Unable to process request")
```

**AI Service Timeouts**:
```python
async def process_speech(self, audio_data):
    try:
        # Set timeout for STT
        async with asyncio.timeout(5.0):
            transcript = await self.stt_service.transcribe(audio_data)
        
        # Set timeout for LLM
        async with asyncio.timeout(10.0):
            response = await self.llm_service.generate(transcript)
        
        # Set timeout for TTS
        async with asyncio.timeout(5.0):
            audio = await self.tts_service.synthesize(response)
        
        return audio
        
    except asyncio.TimeoutError:
        logger.warning("AI service timeout, using fallback")
        return await self._generate_fallback_response()
```

### Deployment Error Handling

**Migration Failures**:
```yaml
# In GitHub Actions
- name: Run database migrations
  run: |
    alembic upgrade head || {
      echo "Migration failed, rolling back"
      alembic downgrade -1
      exit 1
    }
```

**Deployment Rollback**:
```yaml
- name: Deploy to LiveKit Cloud
  id: deploy
  run: |
    livekit-cli deploy --config livekit.yaml
  
- name: Rollback on failure
  if: failure()
  run: |
    livekit-cli deploy rollback --version previous
```

**Health Checks**:
```python
# Health check endpoint for monitoring
async def health_check():
    checks = {
        "database": await check_database(),
        "livekit": await check_livekit_connection(),
        "ai_services": await check_ai_services()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Testing Strategy

### Unit Testing

**Database Service Tests**:
```python
# tests/test_db_service.py
import pytest
from memory.db_service import DatabaseService

@pytest.fixture
async def db_service():
    # Use test database
    service = DatabaseService(os.getenv("TEST_DATABASE_URL"))
    yield service
    await service.cleanup()

async def test_get_available_appointments(db_service):
    # Test specific example
    appointments = await db_service.get_available_appointments(
        doctor_id=1,
        date="2025-02-01"
    )
    assert len(appointments) > 0
    assert all(apt.status == "available" for apt in appointments)

async def test_book_appointment_invalid_time(db_service):
    # Test error condition
    with pytest.raises(ValidationError):
        await db_service.book_appointment(
            patient_id=1,
            doctor_id=1,
            datetime="2025-02-01 25:00:00"  # Invalid time
        )
```

**Agent Tests**:
```python
# tests/test_agent.py
async def test_agent_handles_greeting():
    # Test specific interaction
    agent = ReceptionistAgent(mock_db, mock_services)
    response = await agent.process_input("Hello")
    assert "welcome" in response.lower()

async def test_agent_handles_connection_failure():
    # Test error condition
    agent = ReceptionistAgent(failing_db, mock_services)
    response = await agent.process_input("Book appointment")
    assert "trouble" in response.lower()
```

### Property-Based Testing

Property-based tests will be defined in the Correctness Properties section below and implemented using the Hypothesis library for Python. Each property test will run a minimum of 100 iterations with randomly generated inputs to verify universal correctness properties.

**Test Configuration**:
```python
# conftest.py
from hypothesis import settings, Verbosity

# Configure Hypothesis for property tests
settings.register_profile("ci", max_examples=100, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=50)
settings.load_profile("ci" if os.getenv("CI") else "dev")
```

**Test Tagging**:
Each property test will include a comment tag referencing the design document:
```python
# Feature: livekit-agent-deployment, Property 1: Database connection pooling
@given(...)
async def test_property_1_connection_pooling(...):
    pass
```

### Integration Testing

**End-to-End Flow Tests**:
```python
# tests/integration/test_e2e.py
async def test_complete_appointment_booking_flow():
    # Test complete user journey
    agent = create_test_agent()
    
    # User greets
    response1 = await agent.process("Hello")
    assert agent.state == "greeting"
    
    # User requests appointment
    response2 = await agent.process("I need to book an appointment")
    assert agent.state == "collecting_info"
    
    # User provides details
    response3 = await agent.process("Dr. Smith on Monday at 2pm")
    assert agent.state == "confirming"
    
    # Verify database state
    appointments = await db.get_appointments(patient_id=test_patient_id)
    assert len(appointments) == 1
```

### Load Testing

**Concurrent Connection Tests**:
```python
# tests/load/test_concurrent_connections.py
async def test_concurrent_database_connections():
    # Simulate multiple agents accessing database
    tasks = [
        db_service.get_available_appointments(doctor_id=i, date="2025-02-01")
        for i in range(50)
    ]
    
    results = await asyncio.gather(*tasks)
    assert all(r is not None for r in results)
    
    # Verify connection pool didn't exhaust
    assert db_service.engine.pool.size() <= 30  # pool_size + max_overflow
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Environment Variable Validation

*For any* agent startup, all required environment variables (DATABASE_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, OPENAI_API_KEY, DEEPGRAM_API_KEY, CARTESIA_API_KEY) must be present and non-empty, or the agent should fail to start with a clear error message.

**Validates: Requirements 1.3, 5.3**

### Property 2: Event Logging Completeness

*For any* system event (agent startup, voice interaction, database query, error), a corresponding log entry must be created with a timestamp, event type, and relevant context (session ID for interactions, stack trace for errors).

**Validates: Requirements 1.5, 7.1, 7.6**

### Property 3: Secret Detection in Codebase

*For any* file in the codebase or git history, it should not contain patterns matching API keys, tokens, passwords, or other secrets (e.g., strings starting with "sk-", "Bearer ", connection strings with passwords).

**Validates: Requirements 5.1, 5.5, 8.7**

### Property 4: Database Connection Pool Handling

*For any* number of concurrent database requests up to the configured limit (pool_size + max_overflow = 30), all requests should complete successfully without connection exhaustion errors.

**Validates: Requirements 2.7**

### Property 5: Health Check Accuracy

*For any* system state (all services healthy, database down, AI service unavailable), the health check endpoint should return a status that accurately reflects the actual state of all dependencies.

**Validates: Requirements 6.4**

### Property 6: Connection Pool Metrics Exposure

*For any* state of the database connection pool (idle, partially used, near capacity), the system should be able to query and return accurate metrics about current usage, available connections, and wait times.

**Validates: Requirements 7.3**

### Property 7: Latency Tracking

*For any* voice processing operation (STT, LLM, TTS, end-to-end), the system should measure and record the latency with millisecond precision, making it available for monitoring and alerting.

**Validates: Requirements 7.4**

### Property 8: Migration Rollback Support

*For any* database migration that has been applied, there must exist a corresponding downgrade function that can reverse the changes, and running upgrade followed by downgrade should return the schema to its original state.

**Validates: Requirements 9.4**

### Example Tests

The following are specific examples and edge cases that should be tested:

**Example 1: Agent Startup Connectivity Verification**
- Test that agent startup performs connectivity checks to all required services (Database, LiveKit, STT, LLM, TTS)
- **Validates: Requirements 1.6**

**Example 2: Database Migration Execution**
- Test that Alembic migrations can be run successfully using `alembic upgrade head`
- **Validates: Requirements 2.4**

**Example 3: Seed Data Loading**
- Test that running the seed data script populates the database with expected test data (patients, doctors, appointments)
- **Validates: Requirements 2.5**

**Example 4: SSL Connection Enforcement**
- Test that database connections without SSL are rejected
- Test that the connection string includes `sslmode=require`
- **Validates: Requirements 2.6, 8.1**

**Example 5: Agent Configuration Validation**
- Test that livekit.yaml contains all required fields (agent name, version, build config, runtime config)
- **Validates: Requirements 3.4**

**Example 6: Configuration Files Presence**
- Test that configuration files exist for target platforms (livekit.yaml, Dockerfile, requirements.txt)
- **Validates: Requirements 5.2**

**Example 7: Environment-Specific Configuration**
- Test that separate configuration exists for dev, staging, and production environments
- Test that production config has stricter settings (e.g., debug=false, higher resource limits)
- **Validates: Requirements 5.4**

**Example 8: WSS Protocol Usage**
- Test that LiveKit connection URL uses wss:// protocol, not ws://
- **Validates: Requirements 8.2**

**Example 9: Migration Tool Configuration**
- Test that Alembic is configured with correct database URL and migration directory
- **Validates: Requirements 9.1**

**Example 10: Migration Versioning**
- Test that migration files follow naming convention (e.g., 001_description.py, 002_description.py)
- Test that each migration has a unique version identifier
- **Validates: Requirements 9.2**

**Example 11: Schema Integrity Validation**
- Test that after running all migrations, the database schema matches the expected structure (all tables, columns, indexes, constraints present)
- **Validates: Requirements 9.5**
