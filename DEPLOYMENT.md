# LiveKit Voice Agent - Deployment Guide

This guide walks you through deploying your hospital receptionist voice agent to production using LiveKit Cloud Agents.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Deployment Architecture](#deployment-architecture)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Database Setup](#database-setup)
6. [LiveKit Cloud Configuration](#livekit-cloud-configuration)
7. [Testing Your Deployment](#testing-your-deployment)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Cost Estimates](#cost-estimates)

## Prerequisites

Before deploying, ensure you have:

- [ ] LiveKit Cloud account ([sign up here](https://cloud.livekit.io))
- [ ] PostgreSQL database (Neon or Supabase recommended)
- [ ] API keys for:
  - OpenAI (GPT-4o-mini)
  - Deepgram (Speech-to-Text)
  - Cartesia (Text-to-Speech)
- [ ] Git repository (for CI/CD)
- [ ] GitHub account (for GitHub Actions)

## Quick Start

### 1. Clone and Configure

```bash
# Clone your repository
git clone <your-repo-url>
cd <your-repo>

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Set Up Database

Choose one of these options:

**Option A: Neon (Recommended for Development)**
```bash
# Sign up at https://neon.tech
# Create a new project
# Copy the connection string to .env
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require
```

**Option B: Supabase (Recommended for Production)**
```bash
# Sign up at https://supabase.com
# Create a new project
# Copy the connection string to .env
DATABASE_URL=postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres?sslmode=require
```

### 3. Deploy to LiveKit Cloud

```bash
# Install LiveKit CLI
curl -sSL https://get.livekit.io/cli | bash

# Login to LiveKit Cloud
livekit-cli cloud auth

# Deploy your agent
livekit-cli cloud deploy \
  --project hospital-receptionist \
  --config livekit.yaml
```

### 4. Test Your Agent

1. Go to LiveKit Cloud dashboard
2. Navigate to "Agents" section
3. Click on "Agent Sandbox"
4. Click "Connect" and start talking!

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     LiveKit Cloud                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agent Sandbox UI (Testing Interface)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LiveKit Cloud Agents (Auto-scaling)                 │   │
│  │  - Python Agent (main.py)                            │   │
│  │  - Auto-restart on failure                           │   │
│  │  - 1-10 instances based on load                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL Database (Neon/Supabase)                        │
│  - Patient data                                              │
│  - Doctor schedules                                          │
│  - Appointments                                              │
│  - User memory                                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  External AI Services                                        │
│  - Deepgram (STT)                                           │
│  - OpenAI GPT-4o-mini (LLM)                                 │
│  - Cartesia (TTS)                                           │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Deployment

### Step 1: Prepare Your Environment

1. **Validate Configuration**
   ```bash
   # Test environment validation
   python -c "from config import validate_environment; validate_environment()"
   ```

2. **Run Tests**
   ```bash
   # Install test dependencies
   pip install -r requirements.txt
   
   # Run configuration tests
   pytest tests/test_configuration_files.py -v
   pytest tests/test_env_validation.py -v
   ```

### Step 2: Set Up Database

1. **Create Database**
   - Sign up for Neon or Supabase
   - Create a new PostgreSQL database
   - Note the connection string

2. **Run Migrations**
   ```bash
   # Initialize Alembic (if not done)
   alembic init migrations
   
   # Create initial migration
   alembic revision --autogenerate -m "Initial schema"
   
   # Apply migrations
   alembic upgrade head
   ```

3. **Load Seed Data** (Optional)
   ```bash
   # Run seed script (to be created)
   python scripts/seed_database.py
   ```

### Step 3: Configure LiveKit Cloud

1. **Create LiveKit Project**
   - Go to [LiveKit Cloud](https://cloud.livekit.io)
   - Create a new project
   - Note your API Key and Secret

2. **Set Environment Variables in LiveKit Cloud**
   - Go to Project Settings → Environment Variables
   - Add all required variables:
     ```
     DATABASE_URL=<your-database-url>
     OPENAI_API_KEY=<your-openai-key>
     DEEPGRAM_API_KEY=<your-deepgram-key>
     CARTESIA_API_KEY=<your-cartesia-key>
     AGENT_TYPE=hospital
     LOG_LEVEL=INFO
     ENVIRONMENT=production
     ```

### Step 4: Deploy Agent

1. **Install LiveKit CLI**
   ```bash
   curl -sSL https://get.livekit.io/cli | bash
   ```

2. **Authenticate**
   ```bash
   livekit-cli cloud auth
   ```

3. **Deploy**
   ```bash
   livekit-cli cloud deploy \
     --project hospital-receptionist \
     --config livekit.yaml
   ```

4. **Verify Deployment**
   ```bash
   # Check agent status
   livekit-cli cloud agent list
   
   # View logs
   livekit-cli cloud logs --follow
   ```

### Step 5: Test Your Agent

1. **Access Agent Sandbox**
   - Go to LiveKit Cloud dashboard
   - Navigate to "Agents" → "Agent Sandbox"
   - Click "Connect"

2. **Test Interactions**
   - Say: "Hello"
   - Say: "I need to book an appointment"
   - Say: "I have a fever"
   - Verify the agent responds correctly

## Database Setup

### Neon Setup (Development/Staging)

1. Sign up at [neon.tech](https://neon.tech)
2. Create a new project
3. Copy connection string:
   ```
   postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```
4. Features:
   - Free tier: 0.5GB storage
   - Auto-scaling
   - Automatic backups
   - Database branching

### Supabase Setup (Production)

1. Sign up at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Settings → Database
4. Copy connection string:
   ```
   postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres?sslmode=require
   ```
5. Features:
   - Built-in connection pooling
   - Real-time subscriptions
   - Automatic backups
   - PostGIS support

### Database Schema

Your database includes:
- `patient_account` - Phone-based accounts
- `patient` - Individual patients
- `doctor` - Medical professionals
- `specialty` - Medical specialties
- `symptoms` - Symptom vocabulary
- `appointment` - Scheduled visits
- `doc_shift` - Doctor availability
- `user_memory` - AI conversation memory
- `call_session` - Call logs

## LiveKit Cloud Configuration

### livekit.yaml Explained

```yaml
agent:
  name: hospital-receptionist  # Your agent name
  version: 1.0.0               # Version for tracking

build:
  dockerfile: Dockerfile        # Build configuration
  context: .                    # Build context

runtime:
  python_version: "3.11"       # Python version

resources:
  cpu: 1                       # CPU cores
  memory: 2Gi                  # Memory allocation

scaling:
  min_instances: 1             # Always-on instances
  max_instances: 10            # Scale up to 10
  target_cpu_utilization: 70   # Scale at 70% CPU
```

### Environment Variables

Set these in LiveKit Cloud dashboard:

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `LIVEKIT_API_KEY` - From LiveKit dashboard
- `LIVEKIT_API_SECRET` - From LiveKit dashboard
- `OPENAI_API_KEY` - OpenAI API key
- `DEEPGRAM_API_KEY` - Deepgram API key
- `CARTESIA_API_KEY` - Cartesia API key

**Optional:**
- `AGENT_TYPE` - Agent type (default: hospital)
- `LOG_LEVEL` - Logging level (default: INFO)
- `ENVIRONMENT` - Environment name (default: production)

## Testing Your Deployment

### Manual Testing

1. **Basic Conversation**
   ```
   User: "Hello"
   Agent: "Thank you for calling City Health Clinic..."
   ```

2. **Symptom Check**
   ```
   User: "I have a fever"
   Agent: "For 'fever', you should see a..."
   ```

3. **Appointment Booking**
   ```
   User: "I need to book an appointment"
   Agent: "I can help you with that..."
   ```

### Automated Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_env_validation.py -v
pytest tests/test_configuration_files.py -v
```

## Monitoring and Maintenance

### LiveKit Cloud Dashboard

Monitor your agent through the dashboard:
- **Metrics**: CPU, memory, request count
- **Logs**: Real-time agent logs
- **Alerts**: Set up alerts for failures
- **Scaling**: View auto-scaling events

### Database Monitoring

**Neon:**
- Dashboard → Metrics
- Monitor: Connections, queries, storage

**Supabase:**
- Dashboard → Database → Metrics
- Monitor: Connection pool, query performance

### Health Checks

The agent performs startup checks for:
- Database connectivity
- LiveKit connection
- AI service availability

## Troubleshooting

### Agent Won't Start

**Check environment variables:**
```bash
livekit-cli cloud env list
```

**View logs:**
```bash
livekit-cli cloud logs --follow
```

**Common issues:**
- Missing environment variables
- Invalid database URL
- Incorrect API keys

### Database Connection Issues

**Test connection:**
```bash
psql $DATABASE_URL -c "SELECT 1"
```

**Common issues:**
- SSL mode not set (`?sslmode=require`)
- Firewall blocking connection
- Invalid credentials

### Agent Not Responding

**Check agent status:**
```bash
livekit-cli cloud agent list
```

**Check logs for errors:**
```bash
livekit-cli cloud logs --tail 100
```

**Common issues:**
- AI service API key invalid
- Database query timeout
- Memory/CPU limits reached

### High Latency

**Check metrics:**
- Agent → Database latency
- AI service response times
- Network latency

**Solutions:**
- Deploy database in same region
- Increase agent resources
- Optimize database queries

## Cost Estimates

### Development Environment
- LiveKit Cloud: Free tier or ~$20/mo
- Database (Neon): Free tier
- AI Services: ~$10-50/mo (usage-based)
- **Total: ~$30-70/mo**

### Staging Environment
- LiveKit Cloud: ~$50/mo
- Database (Neon Pro): ~$20/mo
- AI Services: ~$50-100/mo
- **Total: ~$120-170/mo**

### Production Environment
- LiveKit Cloud: ~$200-500/mo (auto-scaling)
- Database (Supabase Pro): ~$25-100/mo
- AI Services: ~$200-500/mo
- Monitoring: ~$20-50/mo
- **Total: ~$445-1,150/mo**

## Next Steps

1. **Set up CI/CD** - Automate deployments with GitHub Actions
2. **Add monitoring** - Set up alerts and dashboards
3. **Load testing** - Test with concurrent users
4. **Optimize costs** - Review usage and adjust resources
5. **Add features** - Extend agent capabilities

## Support

- **LiveKit Docs**: https://docs.livekit.io/agents/
- **LiveKit Discord**: https://livekit.io/discord
- **GitHub Issues**: <your-repo-url>/issues

## Security Checklist

- [ ] All API keys stored as environment variables
- [ ] Database uses SSL/TLS (`sslmode=require`)
- [ ] LiveKit uses WSS protocol (`wss://`)
- [ ] No secrets in code or git history
- [ ] Environment variables not logged
- [ ] Regular API key rotation
- [ ] Database backups enabled
- [ ] Monitoring and alerts configured

---

**Congratulations!** Your voice agent is now deployed and ready to handle calls. 🎉
