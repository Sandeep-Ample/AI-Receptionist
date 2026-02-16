# CI/CD Pipeline Documentation

This document describes the automated deployment pipeline for the LiveKit Voice Agent.

## Overview

The CI/CD pipeline automatically:
1. Runs tests on every push and pull request
2. Runs database migrations
3. Deploys to LiveKit Cloud
4. Performs health checks
5. Rolls back on failure

## Pipeline Stages

### 1. Test Stage

**Triggers:** All pushes and pull requests

**Actions:**
- Runs configuration tests
- Runs environment validation tests
- Runs database tests
- Runs migration tests

**Requirements:**
- All tests must pass before deployment

### 2. Migration Stage

**Triggers:** Pushes to `main` or `staging` branches

**Actions:**
- Connects to database using `DATABASE_URL` secret
- Runs `alembic upgrade head`
- Rolls back on failure
- Verifies migration with `alembic current`

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string

### 3. Deploy Stage

**Triggers:** After successful tests and migrations

**Actions:**
- Installs LiveKit CLI
- Deploys agent to LiveKit Cloud
- Sets environment variables
- Verifies deployment
- Rolls back on failure

**Environment Variables:**
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `LIVEKIT_URL` - LiveKit server URL
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key
- `DEEPGRAM_API_KEY` - Deepgram API key
- `CARTESIA_API_KEY` - Cartesia API key

### 4. Health Check Stage

**Triggers:** After successful deployment

**Actions:**
- Waits 30 seconds for deployment to stabilize
- Checks agent status
- Verifies agent is running
- Fails if agent is not healthy

### 5. Notify Stage

**Triggers:** After all stages complete

**Actions:**
- Reports deployment success or failure
- Includes environment and commit information

## Environments

### Staging

**Branch:** `staging`

**Purpose:** Pre-production testing

**Deployment:** Automatic on push to `staging` branch

**Configuration:**
- Uses staging database
- Uses staging LiveKit project
- Lower resource limits
- More verbose logging

### Production

**Branch:** `main`

**Purpose:** Live production system

**Deployment:** Automatic on push to `main` branch (consider adding manual approval)

**Configuration:**
- Uses production database
- Uses production LiveKit project
- Full resource allocation
- Standard logging

## GitHub Secrets Configuration

### Required Secrets

Configure these in GitHub Settings → Secrets and variables → Actions:

#### Database
- `DATABASE_URL` - PostgreSQL connection string
  ```
  postgresql://user:pass@host:5432/dbname?sslmode=require
  ```

#### LiveKit
- `LIVEKIT_API_KEY` - From LiveKit Cloud dashboard
- `LIVEKIT_API_SECRET` - From LiveKit Cloud dashboard
- `LIVEKIT_URL` - Your LiveKit Cloud URL
  ```
  wss://your-project.livekit.cloud
  ```

#### AI Services
- `OPENAI_API_KEY` - OpenAI API key (starts with `sk-`)
- `DEEPGRAM_API_KEY` - Deepgram API key
- `CARTESIA_API_KEY` - Cartesia API key

### Environment-Specific Secrets

For staging and production environments, configure separate secrets:

**Staging:**
- Use GitHub Environments feature
- Create "staging" environment
- Add staging-specific secrets

**Production:**
- Create "production" environment
- Add production-specific secrets
- Enable "Required reviewers" for manual approval

## Manual Deployment

You can trigger a manual deployment using the GitHub Actions UI:

1. Go to Actions tab
2. Select "Deploy to LiveKit Cloud" workflow
3. Click "Run workflow"
4. Select environment (staging or production)
5. Click "Run workflow"

## Rollback Procedure

### Automatic Rollback

The pipeline automatically rolls back on:
- Migration failure
- Deployment failure
- Health check failure

### Manual Rollback

To manually rollback a deployment:

```bash
# Install LiveKit CLI
curl -sSL https://get.livekit.io/cli | bash

# Authenticate
livekit-cli cloud auth

# Rollback to previous version
livekit-cli cloud deploy rollback --version previous
```

### Database Rollback

To rollback a database migration:

```bash
# Set DATABASE_URL
export DATABASE_URL="postgresql://..."

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>

# Rollback all migrations
alembic downgrade base
```

## Monitoring Deployments

### View Deployment Status

**GitHub Actions:**
- Go to Actions tab
- View workflow runs
- Check logs for each stage

**LiveKit Cloud:**
- Go to LiveKit Cloud dashboard
- Navigate to Agents section
- View agent status and logs

### View Agent Logs

```bash
# Real-time logs
livekit-cli cloud logs --follow

# Last 100 lines
livekit-cli cloud logs --tail 100

# Filter by time
livekit-cli cloud logs --since 1h
```

### Check Agent Status

```bash
# List all agents
livekit-cli cloud agent list

# Get agent details
livekit-cli cloud agent get hospital-receptionist
```

## Troubleshooting

### Tests Failing

**Check test logs:**
```bash
# Run tests locally
pytest tests/ -v

# Run specific test file
pytest tests/test_configuration_files.py -v
```

**Common issues:**
- Missing configuration files
- Invalid YAML syntax
- Missing dependencies

### Migration Failing

**Check migration logs:**
```bash
# Test migration locally
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history
```

**Common issues:**
- Database connection failed
- Schema conflicts
- Missing permissions

### Deployment Failing

**Check deployment logs in GitHub Actions**

**Common issues:**
- Invalid LiveKit credentials
- Missing environment variables
- Docker build errors
- Resource limits exceeded

### Health Check Failing

**Check agent logs:**
```bash
livekit-cli cloud logs --tail 100
```

**Common issues:**
- Agent not starting
- Database connection failed
- AI service API keys invalid
- Memory/CPU limits exceeded

## Best Practices

### Before Pushing to Main

1. **Test locally:**
   ```bash
   pytest tests/ -v
   ```

2. **Test migrations:**
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```

3. **Push to staging first:**
   ```bash
   git push origin staging
   ```

4. **Verify staging deployment:**
   - Test in Agent Sandbox UI
   - Check logs for errors
   - Verify database changes

5. **Merge to main:**
   ```bash
   git checkout main
   git merge staging
   git push origin main
   ```

### Deployment Checklist

- [ ] All tests passing locally
- [ ] Migrations tested locally
- [ ] Staging deployment successful
- [ ] Staging testing complete
- [ ] No errors in staging logs
- [ ] Database backup created
- [ ] Team notified of deployment
- [ ] Ready to rollback if needed

### Security Best Practices

- [ ] Never commit secrets to repository
- [ ] Use GitHub Secrets for all credentials
- [ ] Rotate API keys regularly
- [ ] Use separate credentials for staging/production
- [ ] Enable branch protection on main
- [ ] Require pull request reviews
- [ ] Enable required status checks

## Adding Manual Approval for Production

To require manual approval before production deployments:

1. Go to Settings → Environments
2. Select "production" environment
3. Enable "Required reviewers"
4. Add team members as reviewers
5. Save protection rules

Now production deployments will wait for approval before proceeding.

## Monitoring and Alerts

### Set Up Alerts

**GitHub Actions:**
- Enable email notifications for workflow failures
- Set up Slack/Discord webhooks for notifications

**LiveKit Cloud:**
- Configure alerts in LiveKit dashboard
- Set up monitoring for:
  - Agent uptime
  - Error rate
  - Latency
  - Resource usage

### Metrics to Monitor

- **Deployment frequency:** How often you deploy
- **Deployment success rate:** Percentage of successful deployments
- **Mean time to recovery:** Time to fix failed deployments
- **Change failure rate:** Percentage of deployments causing issues

## Support

For issues with:
- **GitHub Actions:** Check workflow logs
- **LiveKit Cloud:** Contact LiveKit support
- **Database:** Check database logs
- **Agent code:** Review application logs

---

**Last Updated:** 2026-02-09
