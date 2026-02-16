# Quick Reference Guide

**Quick commands and checklists for deploying and managing your LiveKit Voice Agent.**

---

## 🚀 Quick Start Commands

### Initial Setup

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd <your-repo-name>
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file
copy .env.example .env  # Windows
cp .env.example .env    # Mac/Linux

# 4. Edit .env with your API keys
# (Use your text editor)
```

### Database Setup

```bash
# Run migrations
alembic upgrade head

# Load sample data (optional)
python scripts/seed_database.py

# Test database connection
python -c "from database import get_database_connection; import asyncio; db = get_database_connection(); asyncio.run(db.initialize()); print('✓ Database connected')"
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_configuration_files.py -v
pytest tests/test_env_validation.py -v
pytest tests/test_database.py -v
pytest tests/test_logging_metrics.py -v
pytest tests/test_health_check.py -v
pytest tests/test_security.py -v

# Run property-based tests only
pytest tests/ -v -k "property"
```

### Local Development

```bash
# Start agent locally
python main.py dev

# Start Streamlit UI (if available)
streamlit run app.py
```

### Deployment

```bash
# Install LiveKit CLI
curl -sSL https://get.livekit.io/cli | bash  # Mac/Linux
# Windows: Download from GitHub releases

# Authenticate
livekit-cli cloud auth

# Deploy
livekit-cli cloud deploy --project hospital-receptionist --config livekit.yaml

# Check status
livekit-cli cloud agent list

# View logs
livekit-cli cloud logs --follow
```

---

## 📋 Environment Variables Checklist

Copy these to your `.env` file and fill in the values:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require

# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# AI Services
OPENAI_API_KEY=sk-your-key-here
DEEPGRAM_API_KEY=your-key-here
CARTESIA_API_KEY=your-key-here

# Optional
AGENT_TYPE=hospital
LOG_LEVEL=INFO
ENVIRONMENT=development
```

---

## 🔑 Where to Get API Keys

| Service | URL | Free Tier |
|---------|-----|-----------|
| OpenAI | https://platform.openai.com/api-keys | $5 credit |
| Deepgram | https://console.deepgram.com/signup | $200 credit |
| Cartesia | https://cartesia.ai | Check website |
| LiveKit | https://cloud.livekit.io | Limited hours |
| Neon | https://neon.tech | 0.5GB storage |
| Supabase | https://supabase.com | 500MB storage |

---

## 🗄️ Database Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Check current version
alembic current

# Seed database
python scripts/seed_database.py
```

---

## 🧪 Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_database.py -v

# Run specific test function
pytest tests/test_database.py::test_database_connection -v

# Run tests matching pattern
pytest tests/ -v -k "database"

# Run property-based tests with more examples
pytest tests/test_logging_metrics.py -v --hypothesis-show-statistics
```

---

## 📊 Monitoring Commands

```bash
# View agent logs
livekit-cli cloud logs --follow

# View last 100 log lines
livekit-cli cloud logs --tail 100

# List all agents
livekit-cli cloud agent list

# Get agent details
livekit-cli cloud agent describe hospital-receptionist

# View metrics (in LiveKit Cloud dashboard)
# Go to: https://cloud.livekit.io → Your Project → Metrics
```

---

## 🔧 Troubleshooting Commands

### Check Configuration

```bash
# Validate environment variables
python -c "from config import validate_environment; validate_environment()"

# Check database connection
python -c "from database import get_database_connection; import asyncio; db = get_database_connection(); asyncio.run(db.initialize()); print('✓ Connected')"

# Run health checks
python -c "from health_check import verify_startup_connectivity; import asyncio; result = asyncio.run(verify_startup_connectivity()); print('✓ All healthy' if result else '✗ Some services unhealthy')"
```

### Check Logs

```bash
# View agent logs
livekit-cli cloud logs --follow

# Search logs for errors
livekit-cli cloud logs | grep ERROR

# View logs from specific time
livekit-cli cloud logs --since 1h
```

### Database Debugging

```bash
# Connect to database
psql $DATABASE_URL

# List tables
psql $DATABASE_URL -c "\dt"

# Check migration status
alembic current

# View migration history
alembic history
```

---

## 🚨 Emergency Commands

### Rollback Deployment

```bash
# Rollback to previous version
livekit-cli cloud deploy rollback --version previous

# Or redeploy a specific version
livekit-cli cloud deploy --version 1.0.0
```

### Rollback Database Migration

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### Restart Agent

```bash
# Redeploy (will restart)
livekit-cli cloud deploy --project hospital-receptionist --config livekit.yaml
```

---

## 📝 Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "Description of changes"

# Push to GitHub
git push origin feature/my-feature

# Merge to main (triggers deployment)
git checkout main
git merge feature/my-feature
git push origin main
```

---

## 🔐 Security Checks

```bash
# Scan for secrets in code
pytest tests/test_security.py::test_scan_python_files_for_secrets -v

# Check .env.example for real secrets
pytest tests/test_security.py::test_env_example_has_no_real_secrets -v

# Verify WSS protocol usage
pytest tests/test_security.py::test_example_8_wss_protocol_usage -v

# Check environment configurations
pytest tests/test_security.py::test_example_7_environment_specific_configuration -v
```

---

## 💰 Cost Monitoring

### Check Current Usage

```bash
# LiveKit usage
# Go to: https://cloud.livekit.io → Billing

# Database usage (Neon)
# Go to: https://console.neon.tech → Your Project → Usage

# Database usage (Supabase)
# Go to: https://supabase.com → Your Project → Settings → Usage

# OpenAI usage
# Go to: https://platform.openai.com/usage

# Deepgram usage
# Go to: https://console.deepgram.com/billing
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `GETTING_STARTED.md` | Complete step-by-step deployment guide |
| `DEPLOYMENT.md` | Detailed deployment documentation |
| `CICD.md` | CI/CD pipeline documentation |
| `ARCHITECTURE.md` | Code architecture overview |
| `IMPLEMENTATION_SUMMARY.md` | Summary of completed tasks |
| `QUICK_REFERENCE.md` | This file - quick command reference |
| `README.md` | Project overview |

---

## 🎯 Common Tasks

### Add a New Doctor

```sql
-- Connect to database
psql $DATABASE_URL

-- Insert doctor
INSERT INTO doctor (name, spec_id, mobile_no, email, is_active)
VALUES ('Dr. Jane Smith', 1, '555-0123', 'jane@clinic.com', true);

-- Add shifts
INSERT INTO doc_shift (doc_id, day_of_week, start_time, end_time)
VALUES 
  (LAST_INSERT_ID(), 1, '09:00', '17:00'),  -- Monday
  (LAST_INSERT_ID(), 2, '09:00', '17:00');  -- Tuesday
```

### Update Agent Behavior

```bash
# 1. Edit agent file
# Edit: agents/hospital.py

# 2. Test locally
python main.py dev

# 3. Commit and push
git add agents/hospital.py
git commit -m "Update agent behavior"
git push origin main

# 4. Deployment happens automatically via CI/CD
```

### View Agent Metrics

```bash
# In Python
python -c "
from logging_config import get_metrics_collector
collector = get_metrics_collector()
print(collector.get_metrics())
"

# Or check LiveKit Cloud dashboard
# https://cloud.livekit.io → Your Project → Metrics
```

---

## ✅ Pre-Deployment Checklist

Before deploying to production:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Environment variables set in LiveKit Cloud
- [ ] Database migrations applied: `alembic upgrade head`
- [ ] Seed data loaded (if needed): `python scripts/seed_database.py`
- [ ] Health checks pass: `python -c "from health_check import verify_startup_connectivity; import asyncio; asyncio.run(verify_startup_connectivity())"`
- [ ] Security scans pass: `pytest tests/test_security.py -v`
- [ ] Documentation updated
- [ ] GitHub secrets configured
- [ ] Monitoring configured
- [ ] Backup strategy in place

---

## 🆘 Getting Help

1. **Check logs first:** `livekit-cli cloud logs --follow`
2. **Run health checks:** See "Troubleshooting Commands" above
3. **Review documentation:** See "Documentation Files" above
4. **Search issues:** Check GitHub issues for similar problems
5. **Ask community:** LiveKit Discord - https://livekit.io/discord

---

## 📞 Support Resources

- **LiveKit Docs:** https://docs.livekit.io/agents/
- **LiveKit Discord:** https://livekit.io/discord
- **Neon Docs:** https://neon.tech/docs
- **Supabase Docs:** https://supabase.com/docs
- **GitHub Issues:** <your-repo-url>/issues

---

**Keep this file handy for quick reference! 📌**
