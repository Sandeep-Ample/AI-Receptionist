# 🚀 Getting Started - Complete Deployment Guide

**You haven't run any commands yet? Perfect! This guide will walk you through everything step-by-step.**

This is your complete guide to deploying the LiveKit Voice Agent from scratch. Follow these steps in order, and you'll have a production-ready voice agent running in the cloud.

---

## 📋 What You'll Need

Before starting, make sure you have:

- [ ] A computer with internet access
- [ ] Git installed
- [ ] Python 3.11+ installed
- [ ] A code editor (VS Code, PyCharm, etc.)
- [ ] A GitHub account
- [ ] Credit card for cloud services (most have free tiers)

---

## 🎯 Overview: What We're Building

```
┌─────────────────────────────────────────────────────────────┐
│                     LiveKit Cloud                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agent Sandbox UI (for testing)                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Your Python Agent (auto-scaling 1-10 instances)     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL Database (Neon or Supabase)                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  AI Services (Deepgram, OpenAI, Cartesia)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Step-by-Step Instructions

### Phase 1: Local Setup (30 minutes)

#### Step 1.1: Clone and Set Up Your Project

```bash
# Navigate to where you want your project
cd ~/projects  # or wherever you keep your code

# If you haven't cloned yet, clone your repository
git clone <your-repo-url>
cd <your-repo-name>

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**✓ Checkpoint:** You should see `(venv)` in your terminal prompt.

#### Step 1.2: Create Your Local Environment File

```bash
# Copy the example environment file
copy .env.example .env  # Windows
# or
cp .env.example .env    # Mac/Linux

# Open .env in your editor
# You'll fill this in as we get API keys
```

**✓ Checkpoint:** You should have a `.env` file in your project root.

---

### Phase 2: Get API Keys (45 minutes)

You'll need API keys from several services. Let's get them one by one.

#### Step 2.1: OpenAI API Key (for LLM)

1. Go to https://platform.openai.com/signup
2. Sign up or log in
3. Go to https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Name it "Hospital Agent"
6. Copy the key (starts with `sk-`)
7. Add to your `.env` file:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

**Cost:** ~$0.50-$5 per 1000 conversations (GPT-4o-mini)

#### Step 2.2: Deepgram API Key (for Speech-to-Text)

1. Go to https://console.deepgram.com/signup
2. Sign up (they have a free tier with $200 credit)
3. Go to https://console.deepgram.com/project/default/keys
4. Copy your API key
5. Add to your `.env` file:
   ```
   DEEPGRAM_API_KEY=your-key-here
   ```

**Cost:** Free tier includes $200 credit, then ~$0.0043/minute

#### Step 2.3: Cartesia API Key (for Text-to-Speech)

1. Go to https://cartesia.ai
2. Sign up for an account
3. Navigate to API Keys section
4. Create a new API key
5. Add to your `.env` file:
   ```
   CARTESIA_API_KEY=your-key-here
   ```

**Cost:** Check their pricing page for current rates

#### Step 2.4: LiveKit Cloud Account

1. Go to https://cloud.livekit.io
2. Sign up for an account
3. Create a new project (name it "hospital-receptionist")
4. Go to Settings → Keys
5. Copy your API Key and API Secret
6. Copy your WebSocket URL (looks like `wss://your-project.livekit.cloud`)
7. Add to your `.env` file:
   ```
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=your-api-key
   LIVEKIT_API_SECRET=your-api-secret
   ```

**Cost:** Free tier available, then ~$20-50/month for development

**✓ Checkpoint:** Your `.env` file should now have all AI service keys.

---

### Phase 3: Set Up Database (30 minutes)

You have two options: Neon (recommended for development) or Supabase (recommended for production).

#### Option A: Neon (Recommended for Getting Started)

1. Go to https://neon.tech
2. Sign up for a free account
3. Click "Create Project"
4. Name it "hospital-agent-db"
5. Select a region close to you
6. Click "Create Project"
7. Copy the connection string (it looks like):
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```
8. Add to your `.env` file:
   ```
   DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```

**Cost:** Free tier includes 0.5GB storage (plenty for development)

#### Option B: Supabase (Alternative)

1. Go to https://supabase.com
2. Sign up for a free account
3. Click "New Project"
4. Name it "hospital-agent-db"
5. Set a database password (save this!)
6. Select a region close to you
7. Click "Create Project" (takes ~2 minutes)
8. Go to Settings → Database
9. Copy the connection string under "Connection string" → "URI"
10. Add to your `.env` file:
    ```
    DATABASE_URL=postgresql://postgres:your-password@db.xxx.supabase.co:5432/postgres?sslmode=require
    ```

**Cost:** Free tier includes 500MB storage

**✓ Checkpoint:** You should have a DATABASE_URL in your `.env` file.

---

### Phase 4: Initialize Database (15 minutes)

Now let's set up your database schema.

#### Step 4.1: Run Migrations

```bash
# Make sure you're in your project directory with venv activated
# You should see (venv) in your prompt

# Run database migrations

```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial hospital schema
```

**✓ Checkpoint:** Migrations should complete without errors.

#### Step 4.2: Load Sample Data (Optional but Recommended)

```bash
# Load sample doctors, specialties, and appointments
python scripts/seed_database.py
```

**Expected output:**
```
Seeding database...
✓ Created 8 specialties
✓ Created 16 symptoms
✓ Created 10 doctors
✓ Created 50 shifts
✓ Created 3 patient accounts
Database seeded successfully!
```

**✓ Checkpoint:** You should see success messages for each data type.

---

### Phase 5: Test Locally (20 minutes)

Before deploying to the cloud, let's make sure everything works locally.

#### Step 5.1: Run Configuration Tests

```bash
# Run all tests to verify setup
pytest tests/test_configuration_files.py -v
pytest tests/test_env_validation.py -v
```

**Expected output:**
```
tests/test_configuration_files.py::test_livekit_yaml_exists PASSED
tests/test_configuration_files.py::test_dockerfile_exists PASSED
tests/test_env_validation.py::test_all_required_vars_present PASSED
...
========== 10 passed in 2.5s ==========
```

**✓ Checkpoint:** All tests should pass.

#### Step 5.2: Test Database Connection

```bash
# Test database connectivity
python -c "from database import get_database_connection; import asyncio; db = get_database_connection(); asyncio.run(db.initialize()); print('✓ Database connected successfully')"
```

**Expected output:**
```
✓ Database connected successfully
```

**✓ Checkpoint:** Database connection works.

#### Step 5.3: Run the Agent Locally (Optional)

```bash
# Start the agent locally
python main.py dev
```

**Expected output:**
```
INFO - Prewarming: Loading Silero VAD model...
INFO - Prewarming complete. Available agents: ['hospital', 'medical', 'clinic', 'default']
INFO - Agent started on port 7880
```

**To test:** Open http://localhost:7880 in your browser (if you have the Streamlit UI set up).

**✓ Checkpoint:** Agent starts without errors.

---

### Phase 6: Deploy to LiveKit Cloud (30 minutes)

Now let's deploy your agent to the cloud!

#### Step 6.1: Install LiveKit CLI

```bash
# On Mac/Linux:
curl -sSL https://get.livekit.io/cli | bash

# On Windows:
# Download from https://github.com/livekit/livekit-cli/releases
# Extract and add to PATH
```

**✓ Checkpoint:** Run `livekit-cli version` to verify installation.

#### Step 6.2: Authenticate with LiveKit Cloud

```bash
# Login to LiveKit Cloud
livekit-cli cloud auth
```

This will open a browser window. Log in with your LiveKit Cloud account.

**✓ Checkpoint:** You should see "Successfully authenticated".

#### Step 6.3: Configure Environment Variables in LiveKit Cloud

1. Go to https://cloud.livekit.io
2. Select your project
3. Go to Settings → Environment Variables
4. Add each variable from your `.env` file:
   - `DATABASE_URL`
   - `OPENAI_API_KEY`
   - `DEEPGRAM_API_KEY`
   - `CARTESIA_API_KEY`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - `LIVEKIT_URL`
   - `AGENT_TYPE=hospital`
   - `LOG_LEVEL=INFO`
   - `ENVIRONMENT=production`

**✓ Checkpoint:** All environment variables are set in LiveKit Cloud.

#### Step 6.4: Deploy Your Agent

```bash
# Deploy to LiveKit Cloud
livekit-cli cloud deploy --project hospital-receptionist --config livekit.yaml
```

**Expected output:**
```
Building Docker image...
Pushing image to registry...
Deploying agent...
✓ Agent deployed successfully
✓ Agent is running
```

This will take 3-5 minutes the first time.

**✓ Checkpoint:** Deployment completes successfully.

#### Step 6.5: Verify Deployment

```bash
# Check agent status
livekit-cli cloud agent list
```

**Expected output:**
```
NAME                  STATUS    INSTANCES    VERSION
hospital-receptionist running   1            1.0.0
```

**✓ Checkpoint:** Agent shows as "running".

---

### Phase 7: Test Your Deployed Agent (10 minutes)

#### Step 7.1: Access Agent Sandbox

1. Go to https://cloud.livekit.io
2. Select your project
3. Click on "Agents" in the sidebar
4. Click on "Agent Sandbox"
5. Click "Connect"
6. Allow microphone access when prompted

**✓ Checkpoint:** You should see "Connected" status.

#### Step 7.2: Test Voice Interaction

Try these test phrases:

1. **Say:** "Hello"
   - **Expected:** Agent greets you and asks how it can help

2. **Say:** "I have a fever"
   - **Expected:** Agent suggests seeing a specialist

3. **Say:** "I need to book an appointment"
   - **Expected:** Agent asks for details

4. **Say:** "When is Dr. Smith available?"
   - **Expected:** Agent lists available times

**✓ Checkpoint:** Agent responds appropriately to all test phrases.

---

### Phase 8: Set Up CI/CD (Optional but Recommended) (20 minutes)

Automate deployments with GitHub Actions.

#### Step 8.1: Add GitHub Secrets

1. Go to your GitHub repository
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret:
   - `DATABASE_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - `LIVEKIT_URL`
   - `OPENAI_API_KEY`
   - `DEEPGRAM_API_KEY`
   - `CARTESIA_API_KEY`

**✓ Checkpoint:** All secrets are added to GitHub.

#### Step 8.2: Test CI/CD Pipeline

```bash
# Commit and push your changes
git add .
git commit -m "Initial deployment setup"
git push origin main
```

1. Go to your GitHub repository
2. Click "Actions" tab
3. Watch the deployment workflow run

**Expected:** All steps complete successfully (green checkmarks).

**✓ Checkpoint:** CI/CD pipeline runs successfully.

---

## 🎉 Congratulations!

You've successfully deployed your LiveKit Voice Agent! Here's what you've accomplished:

✅ Set up all required API keys and services
✅ Configured and initialized your database
✅ Deployed your agent to LiveKit Cloud
✅ Tested your agent with voice interactions
✅ (Optional) Set up automated deployments

---

## 📊 What's Next?

### Immediate Next Steps

1. **Monitor Your Agent**
   - Check logs: `livekit-cli cloud logs --follow`
   - View metrics in LiveKit Cloud dashboard

2. **Customize Your Agent**
   - Edit `agents/hospital.py` to change behavior
   - Update prompts in the agent file
   - Add new tools/functions

3. **Add More Data**
   - Add more doctors to your database
   - Add more specialties and symptoms
   - Customize for your use case

### Production Readiness

Before going to production, consider:

- [ ] Set up monitoring and alerts
- [ ] Configure backup and disaster recovery
- [ ] Set up staging environment
- [ ] Add error tracking (e.g., Sentry)
- [ ] Implement rate limiting
- [ ] Add authentication for admin functions
- [ ] Set up log aggregation
- [ ] Configure auto-scaling rules
- [ ] Add health check monitoring
- [ ] Set up cost alerts

---

## 🆘 Troubleshooting

### Common Issues

#### "Database connection failed"
- **Check:** Is your DATABASE_URL correct in `.env`?
- **Check:** Does it include `?sslmode=require` at the end?
- **Fix:** Copy the connection string again from Neon/Supabase

#### "Agent won't start"
- **Check:** Are all environment variables set?
- **Fix:** Run `python -c "from config import validate_environment; validate_environment()"`

#### "No audio in Agent Sandbox"
- **Check:** Did you allow microphone access?
- **Check:** Is your microphone working in other apps?
- **Fix:** Refresh the page and allow microphone again

#### "Deployment failed"
- **Check:** Are environment variables set in LiveKit Cloud?
- **Check:** Is your `livekit.yaml` file correct?
- **Fix:** Check logs with `livekit-cli cloud logs`

#### "Tests failing"
- **Check:** Is your virtual environment activated?
- **Check:** Did you install all dependencies?
- **Fix:** Run `pip install -r requirements.txt` again

---

## 📚 Additional Resources

- **LiveKit Docs:** https://docs.livekit.io/agents/
- **LiveKit Discord:** https://livekit.io/discord
- **Neon Docs:** https://neon.tech/docs
- **Supabase Docs:** https://supabase.com/docs
- **Project Documentation:**
  - `DEPLOYMENT.md` - Detailed deployment guide
  - `CICD.md` - CI/CD pipeline documentation
  - `ARCHITECTURE.md` - Code architecture
  - `README.md` - Project overview

---

## 💰 Cost Tracking

Keep track of your monthly costs:

| Service | Free Tier | Estimated Cost |
|---------|-----------|----------------|
| LiveKit Cloud | Limited hours | $20-50/month |
| Neon/Supabase | 0.5GB-500MB | $0-25/month |
| OpenAI | $5 credit | $5-50/month |
| Deepgram | $200 credit | $0-20/month |
| Cartesia | Varies | $10-30/month |
| **Total** | | **$35-175/month** |

**Tip:** Start with free tiers and scale up as needed.

---

## ✅ Final Checklist

Before considering your deployment complete:

- [ ] All API keys are set and working
- [ ] Database is initialized with schema
- [ ] Agent deploys successfully to LiveKit Cloud
- [ ] Voice interactions work in Agent Sandbox
- [ ] CI/CD pipeline is set up (optional)
- [ ] Monitoring is configured
- [ ] Documentation is updated
- [ ] Team members have access
- [ ] Backup strategy is in place
- [ ] Cost alerts are configured

---

**Need help?** Check the troubleshooting section above or reach out to the LiveKit community on Discord.

**Happy deploying! 🚀**
