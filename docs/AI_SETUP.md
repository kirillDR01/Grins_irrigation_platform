# AI Assistant Environment Setup

## Required Environment Variables

Add these variables to your `.env` file to enable AI features.

## OpenAI Configuration

```bash
# OpenAI API Key (required for AI features)
OPENAI_API_KEY=sk-proj-...your-key-here...

# OpenAI Model (optional, defaults to gpt-4o-mini)
OPENAI_MODEL=gpt-4o-mini

# OpenAI Organization ID (optional)
OPENAI_ORG_ID=org-...your-org-id...
```

### Getting Your OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-`)
5. Add to `.env` file

### Model Options

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| `gpt-4o-mini` | Fast | Low | Most features (recommended) |
| `gpt-4o` | Medium | Medium | Complex estimates |
| `gpt-4-turbo` | Slow | High | Maximum accuracy |

**Recommendation:** Use `gpt-4o-mini` for production. It's 60% cheaper than GPT-4 and handles all features well.

### Cost Estimates

Based on typical usage:
- **Chat queries:** $0.01-0.02 per query
- **Schedule generation:** $0.03-0.05 per week
- **Job categorization:** $0.02-0.04 per batch (10-20 jobs)
- **Communication drafts:** $0.01 per draft
- **Estimate generation:** $0.02-0.03 per estimate

**Monthly estimate:** $10-30 for typical usage (100 requests/day)

---

## Twilio Configuration (SMS)

```bash
# Twilio Account SID (required for SMS features)
TWILIO_ACCOUNT_SID=AC...your-account-sid...

# Twilio Auth Token (required for SMS features)
TWILIO_AUTH_TOKEN=...your-auth-token...

# Twilio Phone Number (required for SMS features)
TWILIO_PHONE_NUMBER=+16125551234

# Twilio Webhook URL (for production)
TWILIO_WEBHOOK_URL=https://your-domain.com/api/v1/sms/webhook
```

### Getting Your Twilio Credentials

1. Go to https://www.twilio.com/console
2. Sign in or create an account
3. Find your Account SID and Auth Token on the dashboard
4. Buy a phone number (Phone Numbers → Buy a Number)
5. Configure webhook URL in phone number settings

### Webhook Configuration

1. Go to Phone Numbers → Manage → Active Numbers
2. Click your phone number
3. Under "Messaging", set:
   - **A MESSAGE COMES IN:** Webhook
   - **URL:** `https://your-domain.com/api/v1/sms/webhook`
   - **HTTP:** POST
4. Save

### SMS Costs

- **Outbound SMS:** $0.0075 per message (US)
- **Inbound SMS:** $0.0075 per message (US)
- **Phone number:** $1.15/month

**Monthly estimate:** $20-50 for typical usage (200-500 messages/month)

---

## Rate Limiting Configuration

```bash
# AI rate limit per user per day (optional, default: 100)
AI_RATE_LIMIT_DAILY=100

# AI rate limit reset hour UTC (optional, default: 0)
AI_RATE_LIMIT_RESET_HOUR=0
```

### Adjusting Rate Limits

- **Low usage:** Set to 50 for cost control
- **High usage:** Set to 200 for power users
- **Development:** Set to 1000 to avoid limits during testing

---

## Redis Configuration (for rate limiting)

```bash
# Redis URL (required for rate limiting)
REDIS_URL=redis://localhost:6379/0

# Or for Redis Cloud
REDIS_URL=redis://:password@host:port/0
```

### Local Redis Setup

```bash
# macOS (via Homebrew)
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Redis Cloud (Production)

1. Go to https://redis.com/try-free/
2. Create a free account (30MB free tier)
3. Create a database
4. Copy the connection string
5. Add to `.env` file

---

## Complete .env Example

```bash
# Application
APP_NAME="Grin's Irrigation Platform"
DEBUG=False
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/grins_platform

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI (AI Features)
OPENAI_API_KEY=sk-proj-...your-key-here...
OPENAI_MODEL=gpt-4o-mini

# Twilio (SMS Features)
TWILIO_ACCOUNT_SID=AC...your-account-sid...
TWILIO_AUTH_TOKEN=...your-auth-token...
TWILIO_PHONE_NUMBER=+16125551234
TWILIO_WEBHOOK_URL=https://your-domain.com/api/v1/sms/webhook

# AI Rate Limiting
AI_RATE_LIMIT_DAILY=100
AI_RATE_LIMIT_RESET_HOUR=0

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
```

---

## Verification

### Test OpenAI Connection

```bash
# Run this command to test OpenAI API
uv run python -c "
from openai import OpenAI
import os
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.chat.completions.create(
    model='gpt-4o-mini',
    messages=[{'role': 'user', 'content': 'Hello!'}]
)
print('OpenAI connection successful!')
print(response.choices[0].message.content)
"
```

### Test Twilio Connection

```bash
# Run this command to test Twilio API
uv run python -c "
from twilio.rest import Client
import os
client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)
account = client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
print('Twilio connection successful!')
print(f'Account status: {account.status}')
"
```

### Test Redis Connection

```bash
# Run this command to test Redis
uv run python -c "
import redis
import os
r = redis.from_url(os.getenv('REDIS_URL'))
r.ping()
print('Redis connection successful!')
"
```

---

## Troubleshooting

### "OpenAI API key not found"
- Check `.env` file has `OPENAI_API_KEY=sk-proj-...`
- Restart the application after adding the key
- Verify key is valid at https://platform.openai.com/api-keys

### "Twilio authentication failed"
- Check `TWILIO_ACCOUNT_SID` starts with `AC`
- Check `TWILIO_AUTH_TOKEN` is correct
- Verify credentials at https://www.twilio.com/console

### "Redis connection refused"
- Check Redis is running: `redis-cli ping` (should return `PONG`)
- Check `REDIS_URL` format: `redis://localhost:6379/0`
- For Redis Cloud, verify connection string includes password

### "Rate limit exceeded immediately"
- Check Redis is working (stores rate limit counters)
- Clear Redis: `redis-cli FLUSHDB` (development only!)
- Verify `AI_RATE_LIMIT_DAILY` is set correctly

---

## Security Best Practices

### API Keys
- ✅ Never commit `.env` file to git
- ✅ Use different keys for development and production
- ✅ Rotate keys every 90 days
- ✅ Restrict API key permissions (OpenAI dashboard)
- ❌ Never share keys in Slack, email, or screenshots

### Twilio
- ✅ Enable webhook signature validation (already implemented)
- ✅ Use HTTPS for webhook URL in production
- ✅ Monitor usage for unexpected spikes
- ❌ Never expose auth token in client-side code

### Redis
- ✅ Use password authentication in production
- ✅ Bind to localhost in development
- ✅ Use Redis Cloud or managed service in production
- ❌ Never expose Redis port to internet without auth

---

## Cost Monitoring

### OpenAI Usage
- Dashboard: https://platform.openai.com/usage
- Set usage limits to prevent overages
- Enable email alerts for high usage

### Twilio Usage
- Dashboard: https://www.twilio.com/console/usage
- Set usage alerts
- Monitor for spam or abuse

### Application Monitoring
- Check `/api/v1/ai/usage` endpoint for per-user usage
- Review audit logs for AI request patterns
- Monitor Redis for rate limit hits

---

## Production Checklist

Before deploying to production:

- [ ] OpenAI API key configured and tested
- [ ] Twilio credentials configured and tested
- [ ] Redis configured and accessible
- [ ] Webhook URL configured in Twilio
- [ ] Rate limits set appropriately
- [ ] Usage monitoring enabled
- [ ] Cost alerts configured
- [ ] API keys rotated from development
- [ ] `.env` file not committed to git
- [ ] Backup Redis data regularly

---

## Support

### OpenAI Support
- Documentation: https://platform.openai.com/docs
- Community: https://community.openai.com
- Status: https://status.openai.com

### Twilio Support
- Documentation: https://www.twilio.com/docs
- Support: https://support.twilio.com
- Status: https://status.twilio.com

### Redis Support
- Documentation: https://redis.io/docs
- Community: https://redis.io/community
- Redis Cloud Support: https://redis.com/support
