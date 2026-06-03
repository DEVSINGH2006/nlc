# NLC — Natural Language Compiler
## Deployment Guide

**Last Updated:** 2026-06-03  
**Status:** Production Ready ✅

---

## Quick Start (Local Development)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/nlc.git
cd nlc

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Get API Key
# Visit https://aistudio.google.com/apikey
# Create new project
# Create API key (starts with AIza...)

# 5. Create .env file
echo "GEMINI_API_KEY=AIza..." > .env

# 6. Run locally
uvicorn api:app --reload

# 7. Visit http://localhost:8000
```

---

## Deployment to Render

### Prerequisites

- ✅ GitHub account with repository
- ✅ Render.com account (free tier available)
- ✅ Google Gemini API key (free from aistudio.google.com)

### Step-by-Step Deployment

#### 1. Get Gemini API Key

1. Visit https://aistudio.google.com/apikey
2. Create a new project (or use existing)
3. Click "Create API key" → "Create API key in new project"
4. Copy the API key (format: `AIza...`)
5. Store somewhere safe (we'll use it in step 5)

**Note:** Free tier limits to 15 requests per minute, 1 million tokens per day. Sufficient for demo purposes.

#### 2. Prepare Repository

```bash
# Make sure all files are committed
git add -A
git commit -m "Ready for Render deployment"
git push origin main
```

Ensure these files are in your repository:
- ✅ `api.py` (main FastAPI app)
- ✅ `index.html` (web UI)
- ✅ `requirements.txt` (dependencies)
- ✅ `render.yaml` (deployment config)
- ✅ All Python files in core/, stages/, schemas/, sandbox/

#### 3. Create Render Service

1. Go to https://render.com/dashboard
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Select your `nlc` repository
5. Select branch: `main`

#### 4. Configure Service

**Name:** `nlc-compiler` (or any name you prefer)

**Environment:** `Python 3`

**Build Command:** `pip install -r requirements.txt`

**Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`

**Instance Type:** Free (sufficient for demo)

#### 5. Add Environment Variables

Click **"Advanced"** → **"Environment Variables"**

Add the following:

| Key | Value | Notes |
|-----|-------|-------|
| GEMINI_API_KEY | `AIza...` | Paste your API key here |
| ALLOWED_ORIGINS | `https://nlc-compiler.onrender.com` | Auto-populate with your Render URL |
| LOG_LEVEL | `INFO` | Optional: for logging |

#### 6. Deploy

1. Click **"Create Web Service"**
2. Wait for build to complete (~2-5 minutes)
3. Check logs for any errors
4. Once deployment completes, you'll get a URL like: `https://nlc-compiler.onrender.com`

#### 7. Test Deployment

```bash
# Test health check
curl https://nlc-compiler.onrender.com/health

# Expected response:
# {"status":"online","service":"NLC Compiler"}

# Test in browser
# Visit: https://nlc-compiler.onrender.com
# Enter a test prompt
# Click "Compile"
# Verify blueprint generates
```

---

## Troubleshooting

### Error: "index.html not found"

**Cause:** File is not in the deployment

**Solution:**
1. Verify `index.html` is in repository root
2. Commit and push to GitHub
3. Trigger new Render deployment (go to dashboard → redeploy)

### Error: "GEMINI_API_KEY not set"

**Cause:** Environment variable not configured

**Solution:**
1. Go to Render service → **Settings** → **Environment**
2. Add `GEMINI_API_KEY` with your API key
3. Redeploy service

### Error: "Compilation timed out after 5 minutes"

**Cause:** Gemini API is slow or unavailable

**Solution:**
- Try simpler prompt (fewer features)
- Check https://status.google.com for API status
- Check API quota: https://aistudio.google.com/app/apikey

### Error: "API Key Invalid"

**Cause:** API key is wrong, expired, or quota exhausted

**Solution:**
1. Get fresh key from https://aistudio.google.com/apikey
2. Use different Google account if quota exhausted
3. Update GEMINI_API_KEY in Render environment
4. Redeploy

### Error: "Too many requests"

**Cause:** Rate limiting (15 requests per minute on free tier)

**Solution:**
- Wait 60 seconds before next request
- Upgrade to Gemini Pro tier if needed (paid)

### Web UI Not Loading

**Cause:** CORS or file serving issue

**Solution:**
1. Check browser console for CORS errors
2. Verify ALLOWED_ORIGINS includes your Render domain
3. Check Render logs for file not found errors
4. Redeploy

### Logs Not Showing

**Location:** Render Dashboard → Your Service → **Logs**

**To view:**
- Click your service name
- Scroll down to "Logs" section
- Watch real-time logs as requests come in

---

## Monitoring & Maintenance

### Health Check

Monitor service health:
```bash
# Check every 30 seconds
watch -n 30 'curl -s https://nlc-compiler.onrender.com/health'
```

### Logs

Monitor logs for errors:
```bash
# Follow logs (you can only do this from Render dashboard)
# Or check for errors in deployment history
```

### API Quota Monitoring

- Free tier: 15 requests/minute, 1M tokens/day
- Check usage: https://aistudio.google.com/app/apikey
- Current usage updates in real-time

### Common Maintenance Tasks

#### Restarting the Service
1. Go to Render Dashboard
2. Click your service
3. Click "..." menu → "Restart latest deployment"

#### Updating Code
1. Make changes locally
2. Commit to GitHub: `git push origin main`
3. Render auto-deploys (watch the dashboard)

#### Updating Dependencies
1. Update `requirements.txt` locally
2. Commit and push
3. Render rebuilds and redeploys

#### Changing Environment Variables
1. Go to service **Settings** → **Environment**
2. Update value
3. Redeploy (button appears automatically)

---

## Performance Optimization

### For Free Tier

**Current Config:**
- Instance Type: Free (1 shared CPU, 512 MB RAM)
- Workers: 1 (suitable for CPU-intensive pipeline)
- Timeout: 30 minutes (Render limit)

**To handle more traffic:**
1. Upgrade to Starter tier ($7/month)
   - Dedicated CPU
   - 512 MB → 2 GB RAM
   - Better performance

2. Enable auto-scaling
   - Go to **Settings** → **Advanced**
   - Enable auto-scaling for burst traffic

### Reduce Latency

**Currently:**
- Cold start: ~30 seconds (first request after restart)
- Warm start: ~10 seconds (subsequent requests)

**To improve:**
- Use Starter+ instance ($25/month)
- Enable "Always On" to prevent sleep

### Caching (Future Enhancement)

Add Redis for caching identical prompts:
```bash
# In Render, create Redis service
# Connect URL to NLC service
# Implement caching in api.py
```

---

## Security Best Practices

### Protect Your API Key

- ✅ Never commit `.env` to Git (uses .gitignore)
- ✅ Always use environment variables
- ✅ Rotate key if compromised
- ✅ Use different keys for dev/staging/production

### Rate Limiting

Already implemented! Details:
- 5 requests per minute per IP address
- Returns 429 status if exceeded
- Prevents DOS attacks
- Prevents API quota exhaustion

### CORS Configuration

Production config:
```
ALLOWED_ORIGINS=https://nlc-compiler.onrender.com
```

Only allows your Render domain. Other origins are blocked.

### Input Validation

All user inputs are validated:
- Prompt: 10-5000 characters
- No empty/whitespace-only prompts
- Rejects malformed JSON requests

### Monitoring Suspicious Activity

Check Render logs for:
- 429 errors (rate limit hits) → might indicate attack
- 422 errors (validation fails) → malformed requests
- 500 errors → actual errors

---

## Cost Estimation

### Gemini API (Free Tier)

| Metric | Limit | Cost |
|--------|-------|------|
| Requests/minute | 15 RPM | Free |
| Tokens/day | 1M TPM | Free |
| Typical use | ~5K tokens per request | ~0.2 requests/day |

**Cost:** $0/month

### Render Hosting

| Tier | CPU | RAM | Cost |
|------|-----|-----|------|
| Free | Shared | 512 MB | $0/month (sleeps after 15 min inactivity) |
| Starter | Dedicated | 512 MB | $7/month |
| Starter+ | Dedicated | 2 GB | $25/month |

**Recommended for demo:** Free tier  
**Recommended for production:** Starter ($7/month)

### Total Monthly Cost

- **Development:** $0 (free tier everything)
- **Small production:** $7/month (Render Starter)
- **High-traffic production:** $25-50/month + scaled Render

---

## Scaling Strategy

### If Traffic Increases

1. **First:** Monitor Render dashboard for resource usage
2. **If CPU high:** Upgrade instance type (Starter+)
3. **If requests blocked by rate limit:** Implement queue system or upgrade Gemini tier
4. **If database needed:** Add PostgreSQL database service in Render

### Load Testing

To test capacity:
```bash
# Install Apache Bench
# Mac: brew install httpd
# Linux: sudo apt-get install apache2-utils

# Test 100 requests, 5 concurrent
ab -n 100 -c 5 \
  -p payload.json \
  -T application/json \
  https://nlc-compiler.onrender.com/compile
```

---

## Support & Resources

### Documentation

- 📖 [NLC README](./README.md) - Feature overview
- 📖 [Technical Audit](./TECHNICAL_AUDIT_REPORT.md) - Architecture deep-dive
- 📖 [This File](./DEPLOYMENT.md) - Deployment guide

### External Resources

- 🔑 **Gemini API:** https://aistudio.google.com/apikey
- 🚀 **Render Docs:** https://render.com/docs
- ❓ **FastAPI Docs:** https://fastapi.tiangolo.com
- 🐍 **Python:** https://python.org

### Getting Help

**For API key issues:**
- Visit https://aistudio.google.com/app/apikey
- Check error message in Render logs
- Try different Google account if quota exhausted

**For Render issues:**
- Check https://render.com/status
- Visit Render support: https://render.com/support
- Check service logs in dashboard

**For NLC issues:**
- Review [TECHNICAL_AUDIT_REPORT.md](./TECHNICAL_AUDIT_REPORT.md)
- Check code comments in source files

---

## Frequently Asked Questions

### Q: Can I use this with other LLM APIs?

**A:** Yes! Replace the `LLMClient` class in `core/llm_client.py` to use OpenAI, Claude, or any other API. The pipeline is agnostic.

### Q: How do I add custom stages?

**A:** Create a new file in `stages/` following the same pattern. Pass output to next stage. Update `core/pipeline.py` to include it.

### Q: Can I scale to handle 1000 users?

**A:** With current free tier, no. You'd need:
1. Upgrade Gemini to paid tier
2. Upgrade Render to Starter+ or higher
3. Add caching with Redis
4. Implement request queue with Celery

### Q: What happens if API key quota is exhausted?

**A:** User sees error: "Gemini API quota exhausted. Try again tomorrow."  
Free tier resets daily at midnight UTC.

### Q: Can I export blueprint in other formats?

**A:** Not yet. Currently exports JSON. Could add YAML, Markdown, etc. as future enhancement.

### Q: How long does compilation take?

**A:** Typically 10-30 seconds depending on:
- Prompt complexity
- Gemini API latency
- System load

---

## Deployment Checklist

Before deploying to production, verify:

```
PRE-DEPLOYMENT
==============
Code:
  ☑ All files committed to Git
  ☑ No untracked files
  ☑ .env in .gitignore
  ☑ Latest code on main branch

Configuration:
  ☑ render.yaml has Python 3.11.7
  ☑ render.yaml has health check path
  ☑ All environment variables documented

Testing:
  ☑ Tested locally with 3+ prompts
  ☑ Health check works: /health
  ☑ UI loads: /
  ☑ Compile endpoint works: POST /compile
  ☑ Error handling tested

Render Setup:
  ☑ Service created
  ☑ GitHub connected
  ☑ Build command correct
  ☑ Start command correct
  ☑ GEMINI_API_KEY set

POST-DEPLOYMENT
===============
  ☑ Service deployed successfully
  ☑ Health check passes
  ☑ UI loads in browser
  ☑ Sample compilation works
  ☑ Error responses helpful
  ☑ Logs show no errors
  ☑ API key working
```

---

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 1.0.0 | 2026-06-03 | Production Ready | Initial release with all critical fixes |

---

**Need help?** Check [TECHNICAL_AUDIT_REPORT.md](./TECHNICAL_AUDIT_REPORT.md) for detailed architecture and troubleshooting.
