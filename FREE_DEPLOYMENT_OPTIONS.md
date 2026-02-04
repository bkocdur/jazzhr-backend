# Free Backend Deployment Options

## 🆓 Free Tier Options

### Option 1: Railway (Best for Selenium) ⭐ Recommended

**Free Tier:**
- $5 credit/month (enough for light usage)
- 512MB RAM
- 1GB storage
- Can handle Docker + Chrome

**Limitations:**
- Limited to ~100 hours/month
- May need to upgrade for heavy usage
- Sleeps after inactivity (wakes on request)

**Setup:**
1. Sign up at [railway.app](https://railway.app) (free)
2. Connect GitHub repo
3. Deploy (uses Dockerfile automatically)
4. Add env vars: `HEADLESS=true`

**Cost:** Free for light usage, $5-20/month for regular use

---

### Option 2: Render

**Free Tier:**
- 750 hours/month
- 512MB RAM
- Sleeps after 15 minutes inactivity

**Limitations:**
- Spins down when idle (takes ~30s to wake)
- May struggle with Chrome/Selenium
- Limited CPU for browser automation

**Setup:**
1. Sign up at [render.com](https://render.com) (free)
2. Create "Web Service"
3. Connect GitHub repo
4. Use Dockerfile
5. Add env vars

**Cost:** Free, but slow wake-up times

---

### Option 3: Fly.io

**Free Tier:**
- 3 shared-cpu VMs
- 256MB RAM per VM
- 3GB storage

**Limitations:**
- 256MB RAM may not be enough for Chrome
- Need to optimize Docker image
- More complex setup

**Setup:**
1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Sign up: `fly auth signup`
3. Create app: `fly launch`
4. Deploy: `fly deploy`

**Cost:** Free for small apps, may need paid plan for Chrome

---

### Option 4: Google Cloud Run (Free Tier)

**Free Tier:**
- 2 million requests/month
- 360,000 GB-seconds compute
- 180,000 vCPU-seconds

**Limitations:**
- 60-minute timeout per request
- May need to optimize for cold starts
- Requires Google Cloud account setup

**Setup:**
1. Create Google Cloud account (free $300 credit)
2. Enable Cloud Run API
3. Build and deploy Docker image
4. Set up billing (but free tier covers usage)

**Cost:** Free tier generous, but requires credit card

---

### Option 5: Keep It Local + ngrok (100% Free) 💡 Best for Testing

**How it works:**
- Run backend locally on your machine
- Use ngrok to create public tunnel
- Update Vercel env var to ngrok URL

**Setup:**
1. Install ngrok: `brew install ngrok` (Mac) or download from [ngrok.com](https://ngrok.com)
2. Run backend locally:
   ```bash
   python api_server.py
   ```
3. In another terminal, create tunnel:
   ```bash
   ngrok http 8000
   ```
4. Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)
5. Update Vercel: `NEXT_PUBLIC_API_URL=https://abc123.ngrok.io`
6. Redeploy frontend

**Limitations:**
- Your computer must be running
- ngrok free tier: URL changes on restart
- ngrok free tier: Limited connections
- Not suitable for production

**Cost:** 100% free, but requires your machine running

---

### Option 6: Replit (Free but Not Recommended)

**Free Tier:**
- Always-on option available
- Limited resources
- Can run Python apps

**Limitations:**
- Not ideal for production
- Resource limits
- May struggle with Chrome/Selenium

**Cost:** Free, but not production-ready

---

## 🎯 Recommendations

### For Testing/Development:
**Use ngrok (Option 5)** - 100% free, easy setup, perfect for testing

### For Light Production Use:
**Use Railway (Option 1)** - Best balance of free tier and Selenium support

### For Regular Production Use:
**Railway paid ($5-20/month)** - Most reliable for browser automation

## ⚠️ Important Considerations

### Memory Requirements
- Chrome + Selenium needs ~300-500MB RAM minimum
- Free tiers often have 256-512MB RAM
- May need to optimize or upgrade

### Time Limits
- Free tiers often have request timeouts (60s-300s)
- Downloads can take longer
- May need to implement chunking/streaming

### Cold Starts
- Free tiers sleep when idle
- First request after sleep can be slow (30s-60s)
- Consider keeping it "warm" with health checks

## 💡 Optimization Tips for Free Tiers

1. **Reduce Chrome memory:**
   ```python
   chrome_options.add_argument("--memory-pressure-off")
   chrome_options.add_argument("--max_old_space_size=256")
   ```

2. **Use lighter browser:**
   - Consider Playwright instead of Selenium (lighter)
   - Or use headless Chrome with minimal extensions

3. **Implement request queuing:**
   - Don't process multiple downloads simultaneously
   - Queue requests to stay within limits

4. **Add health checks:**
   - Keep service warm with periodic pings
   - Prevents cold starts

## 🚀 Quick Start: Free ngrok Setup

```bash
# Terminal 1: Start backend
cd /path/to/JazzHR
python api_server.py

# Terminal 2: Start ngrok tunnel
ngrok http 8000

# Copy the Forwarding URL (e.g., https://abc123.ngrok.io)
# Update Vercel: NEXT_PUBLIC_API_URL=https://abc123.ngrok.io
# Redeploy frontend
```

**Note:** ngrok free URLs change on restart. For permanent URL, upgrade to ngrok paid ($8/month) or use Railway free tier.

## 📊 Comparison Table

| Option | Free Tier | Chrome Support | Reliability | Setup Difficulty |
|--------|-----------|----------------|-------------|------------------|
| Railway | $5 credit/month | ✅ Good | ⭐⭐⭐⭐ | Easy |
| Render | 750 hrs/month | ⚠️ Limited | ⭐⭐⭐ | Easy |
| Fly.io | 3 VMs | ⚠️ Limited RAM | ⭐⭐⭐ | Medium |
| Cloud Run | Generous | ✅ Good | ⭐⭐⭐⭐ | Medium |
| ngrok | Unlimited | ✅ Perfect | ⭐⭐ | Very Easy |
| Replit | Always-on | ⚠️ Limited | ⭐⭐ | Easy |

## 🎯 My Recommendation

**Start with ngrok for testing** (free, instant setup), then **move to Railway free tier** when ready for production (better reliability, still free for light usage).

Would you like me to help you set up ngrok for immediate testing, or guide you through Railway deployment?
