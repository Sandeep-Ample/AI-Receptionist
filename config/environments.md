# Environment Configuration Guide

This document describes the configuration differences between development, staging, and production environments.

## Environment Overview

| Environment | Purpose | Database | Scaling | Monitoring |
|-------------|---------|----------|---------|------------|
| Development | Local testing | Local/Neon Free | Manual | Basic logs |
| Staging | Pre-production testing | Neon/Supabase | Auto (1-3) | Full monitoring |
| Production | Live system | Supabase/Neon Pro | Auto (1-10) | Full + alerts |

## Development Environment

**Purpose**: Local development and testing

**Configuration**:
```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
AGENT_TYPE=hospital

# Local or free tier database
DATABASE_URL=postgresql://localhost:5432/voice_agent_dev

# LiveKit Cloud (development project)
LIVEKIT_URL=wss://dev-project.livekit.cloud
```

**Characteristics**:
- Verbose logging (DEBUG level)
- Local or free-tier database
- No auto-scaling
- Minimal monitoring
- Fast iteration

**Cost**: ~$0-30/mo (mostly free tiers)

## Staging Environment

**Purpose**: Pre-production testing and QA

**Configuration**:
```bash
ENVIRONMENT=staging
LOG_LEVEL=INFO
AGENT_TYPE=hospital

# Managed database with backups
DATABASE_URL=postgresql://user:pass@staging-db.neon.tech/voice_agent?sslmode=require

# LiveKit Cloud (staging project)
LIVEKIT_URL=wss://staging-project.livekit.cloud
```

**Characteristics**:
- Production-like configuration
- Managed database with backups
- Auto-scaling (1-3 instances)
- Full monitoring and logging
- Separate API keys from production

**Cost**: ~$120-170/mo

## Production Environment

**Purpose**: Live system serving real users

**Configuration**:
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
AGENT_TYPE=hospital

# Production database with HA
DATABASE_URL=postgresql://user:pass@prod-db.supabase.co:5432/voice_agent?sslmode=require

# LiveKit Cloud (production project)
LIVEKIT_URL=wss://prod-project.livekit.cloud
```

**Characteristics**:
- Optimized logging (INFO level)
- High-availability database
- Auto-scaling (1-10 instances)
- Full monitoring with alerts
- Automated backups
- Strict security policies

**Cost**: ~$445-1,150/mo (scales with usage)

## Configuration Differences

### Logging

| Environment | Level | Format | Destination |
|-------------|-------|--------|-------------|
| Development | DEBUG | Plain text | Console |
| Staging | INFO | JSON | Console + File |
| Production | INFO | JSON | Cloud logging service |

### Database

| Environment | Service | Backups | Connection Pool |
|-------------|---------|---------|-----------------|
| Development | Local/Neon Free | Manual | 5 connections |
| Staging | Neon/Supabase | Daily | 10 connections |
| Production | Supabase Pro | Hourly + PITR | 20 connections |

### Scaling

| Environment | Min Instances | Max Instances | CPU Target |
|-------------|---------------|---------------|------------|
| Development | 1 | 1 | N/A |
| Staging | 1 | 3 | 70% |
| Production | 1 | 10 | 70% |

### Security

| Environment | SSL/TLS | Secrets Management | Token Expiry |
|-------------|---------|-------------------|--------------|
| Development | Optional | .env file | 24 hours |
| Staging | Required | Cloud secrets | 1 hour |
| Production | Required | Cloud secrets | 1 hour |

## Setting Up Each Environment

### Development Setup

1. Copy `.env.example` to `.env`
2. Fill in development credentials
3. Use local database or Neon free tier
4. Run: `python main.py dev`

### Staging Setup

1. Create staging project in LiveKit Cloud
2. Set up Neon/Supabase database
3. Configure GitHub secrets for staging
4. Deploy via GitHub Actions to staging branch

### Production Setup

1. Create production project in LiveKit Cloud
2. Set up production database with HA
3. Configure GitHub secrets for production
4. Deploy via GitHub Actions with manual approval
5. Set up monitoring and alerts

## Environment Variables by Environment

### Required in All Environments

- `DATABASE_URL`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`
- `DEEPGRAM_API_KEY`
- `CARTESIA_API_KEY`

### Environment-Specific

**Development**:
- `ENVIRONMENT=development`
- `LOG_LEVEL=DEBUG`

**Staging**:
- `ENVIRONMENT=staging`
- `LOG_LEVEL=INFO`

**Production**:
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`
- Additional monitoring/alerting configuration

## Best Practices

1. **Never share credentials** between environments
2. **Use separate LiveKit projects** for each environment
3. **Test in staging** before deploying to production
4. **Rotate API keys** regularly
5. **Monitor costs** in each environment
6. **Use SSL/TLS** in staging and production
7. **Enable backups** in staging and production
8. **Set up alerts** for production issues

## Troubleshooting

### Development Issues

- Check `.env` file exists and has all required variables
- Verify database is running (if local)
- Check API keys are valid

### Staging Issues

- Verify GitHub secrets are set correctly
- Check database connection from staging environment
- Review deployment logs in GitHub Actions

### Production Issues

- Check monitoring dashboard for alerts
- Review error logs in cloud logging service
- Verify auto-scaling is working correctly
- Check database connection pool usage

## Migration Between Environments

When promoting code from dev → staging → production:

1. **Code**: Merge via Git branches
2. **Database**: Run migrations in order
3. **Configuration**: Update environment variables
4. **Secrets**: Rotate API keys if needed
5. **Testing**: Run full test suite
6. **Monitoring**: Verify metrics after deployment
