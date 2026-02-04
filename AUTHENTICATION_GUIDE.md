# Authentication Guide for Headless Mode

## Problem

In headless mode (deployed on Railway), users cannot interact with the browser to log in manually. The script needs authentication cookies to access JazzHR.

## Solution: Cookie-Based Authentication

The backend now supports cookie-based authentication. You can provide JazzHR session cookies in two ways:

### Option 1: Environment Variable (Recommended for Railway)

Set `JAZZHR_COOKIES` environment variable in Railway with your cookies as JSON:

1. **Get your cookies:**
   - Log in to JazzHR in your browser: https://app.jazz.co
   - Open browser DevTools (F12)
   - Go to **Application** tab → **Cookies** → `https://app.jazz.co`
   - Copy all cookies (especially ones like `session_id`, `auth_token`, etc.)

2. **Format as JSON:**
   ```json
   [
     {
       "name": "session_id",
       "value": "your-session-value",
       "domain": ".jazz.co",
       "path": "/",
       "secure": true,
       "httpOnly": true
     },
     {
       "name": "auth_token",
       "value": "your-auth-token",
       "domain": ".jazz.co",
       "path": "/",
       "secure": true,
       "httpOnly": true
     }
   ]
   ```

3. **Set in Railway:**
   - Go to Railway Dashboard → Your Service → **Variables**
   - Add new variable:
     - **Key:** `JAZZHR_COOKIES`
     - **Value:** Paste your JSON (all on one line or use Railway's multi-line support)
   - Save and redeploy

### Option 2: API Request (For Testing)

Send cookies in the API request:

```bash
curl -X POST https://your-backend.railway.app/api/downloads/start \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "3234",
    "cookies": [
      {
        "name": "session_id",
        "value": "your-session-value",
        "domain": ".jazz.co",
        "path": "/",
        "secure": true
      }
    ]
  }'
```

## How to Get Cookies

### Method 1: Browser DevTools

1. Log in to JazzHR: https://app.jazz.co
2. Open DevTools (F12)
3. Go to **Application** → **Cookies** → `https://app.jazz.co`
4. Right-click on cookies → **Copy** → **Copy all as cURL** or manually copy each cookie
5. Convert to JSON format

### Method 2: Browser Extension

Use a cookie export extension like:
- **EditThisCookie** (Chrome/Edge)
- **Cookie-Editor** (Chrome/Firefox)

Export cookies as JSON and use the format above.

### Method 3: Python Script (Quick Export)

Create a script to export cookies:

```python
from selenium import webdriver
import json

driver = webdriver.Chrome()
driver.get("https://app.jazz.co")
# Log in manually
cookies = driver.get_cookies()
print(json.dumps(cookies, indent=2))
driver.quit()
```

## Cookie Format

Each cookie should have:
- `name`: Cookie name (required)
- `value`: Cookie value (required)
- `domain`: Usually `.jazz.co` (required)
- `path`: Usually `/` (required)
- `secure`: `true` if HTTPS only (optional)
- `httpOnly`: `true` if HTTP-only cookie (optional)

**Important cookies to include:**
- Session cookies (usually `session_id`, `_session`, etc.)
- Authentication tokens
- Any cookies that start with `auth` or `login`

## Testing Authentication

After setting cookies:

1. **Test the backend:**
   ```bash
   curl https://your-backend.railway.app/api/downloads/start \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"job_id": "3234"}'
   ```

2. **Check logs:**
   - Railway Dashboard → Your Service → **Logs**
   - Look for: "Loading authentication cookies..."
   - Should see: "Successfully loaded X cookies"
   - Should NOT see: "Login required" errors

## Troubleshooting

### "Login required but no cookies provided"
- **Cause:** No cookies set and running in headless mode
- **Fix:** Set `JAZZHR_COOKIES` environment variable in Railway

### "Cookies provided but login still required"
- **Cause:** Cookies are invalid or expired
- **Fix:** 
  - Get fresh cookies from browser
  - Ensure cookies include session/auth cookies
  - Check cookie domain matches `.jazz.co`

### "Failed to parse JAZZHR_COOKIES"
- **Cause:** Invalid JSON format
- **Fix:** Validate JSON syntax, ensure proper escaping

## Security Notes

⚠️ **Important:**
- Cookies contain authentication credentials
- Store securely (environment variables, not in code)
- Rotate cookies regularly
- Don't commit cookies to git
- Use Railway's encrypted environment variables

## Alternative: Non-Headless Mode (Local Only)

For local development, you can disable headless mode:

1. **Set environment variable:**
   ```bash
   export HEADLESS=false
   ```

2. **Run backend:**
   ```bash
   python api_server.py
   ```

3. **When login required:**
   - Browser window will open
   - Log in manually
   - Script continues automatically

This only works locally, not on Railway.

## Next Steps

1. Get your JazzHR cookies
2. Set `JAZZHR_COOKIES` in Railway
3. Redeploy backend
4. Test download feature
