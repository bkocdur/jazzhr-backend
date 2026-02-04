# Backend API Server Deployment Guide

## Current Status

❌ **Backend is NOT deployed yet** - It's currently only configured for local development.

## The Challenge

The backend (`api_server.py`) uses **Selenium** for browser automation, which requires:
- Chrome/Chromium browser installed
- ChromeDriver available
- Display server (for headless mode)
- Sufficient memory and CPU for browser instances

This makes deployment more complex than a standard Python API.

## Deployment Options

### Option 1: Railway (Recommended for Selenium)

Railway supports Docker containers and can handle browser automation.

**Steps:**

1. **Create a Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install Chrome and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
    wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY api_server.py .
COPY download_resumes_browser.py .

# Expose port
EXPOSE 8000

# Set environment variables for headless Chrome
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Run the server
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Create a `.railwayignore` file:**
```
node_modules/
.next/
__pycache__/
*.pyc
.env.local
stitch-frontend/
```

3. **Deploy to Railway:**
   - Go to [railway.app](https://railway.app)
   - Create new project
   - Connect your GitHub repo
   - Select the root directory (not `stitch-frontend`)
   - Railway will detect the Dockerfile
   - Set environment variables:
     - `CORS_ORIGINS` (optional): `https://justlifehr.vercel.app`
   - Deploy

4. **Get your backend URL:**
   - Railway will provide a URL like: `https://your-app.railway.app`
   - Use this as your `NEXT_PUBLIC_API_URL` in Vercel

### Option 2: Render

Render also supports Docker and browser automation.

**Steps:**

1. Use the same Dockerfile as above
2. Go to [render.com](https://render.com)
3. Create new "Web Service"
4. Connect GitHub repo
5. Configure:
   - **Build Command**: (Render will use Dockerfile)
   - **Start Command**: (Already in Dockerfile)
   - **Environment Variables**: Add `CORS_ORIGINS` if needed
6. Deploy

### Option 3: Docker + Your Own Server

If you have a server/VPS:

1. Build the Docker image:
```bash
docker build -t jazzhr-backend .
```

2. Run the container:
```bash
docker run -d \
  -p 8000:8000 \
  -e CORS_ORIGINS=https://justlifehr.vercel.app \
  --name jazzhr-backend \
  jazzhr-backend
```

### Option 4: Keep It Local (For Testing)

If you only need it occasionally:
- Run locally: `python api_server.py`
- Use a tunneling service like [ngrok](https://ngrok.com):
  ```bash
  ngrok http 8000
  ```
- Use the ngrok URL as `NEXT_PUBLIC_API_URL` (temporary)

## Important Notes

### Environment Variables Needed

**Backend (`api_server.py`):**
- `CORS_ORIGINS` (optional): Comma-separated list of allowed origins
- `JAZZHR_API_KEY` (if needed by download script)

**Frontend (Vercel):**
- `NEXT_PUBLIC_API_URL`: Your deployed backend URL (e.g., `https://your-backend.railway.app`)

### After Deployment

1. **Update Vercel environment variable:**
   - Go to Vercel Dashboard → Settings → Environment Variables
   - Set `NEXT_PUBLIC_API_URL` to your backend URL
   - Make sure "Production" is checked
   - Redeploy frontend

2. **Test the connection:**
   ```bash
   curl https://your-backend.railway.app/api/downloads/start \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"job_id": "test"}'
   ```

3. **Verify CORS:**
   - The backend should allow `https://justlifehr.vercel.app`
   - Check backend logs if CORS errors occur

## Troubleshooting

### Chrome/ChromeDriver Issues

If browser automation fails:
- Ensure Chrome is installed in the container
- Check ChromeDriver version matches Chrome version
- Verify headless mode is enabled in `download_resumes_browser.py`

### Memory Issues

Browser automation is memory-intensive:
- Railway/Render free tier may not be sufficient
- Consider upgrading to paid plan
- Or optimize to use less memory

### Timeout Issues

Downloads can take a long time:
- Ensure your hosting provider allows long-running requests
- Consider implementing job queue (Redis/Celery) for better scalability

## Next Steps

1. Choose a deployment option (Railway recommended)
2. Create the Dockerfile
3. Deploy the backend
4. Update `NEXT_PUBLIC_API_URL` in Vercel
5. Redeploy frontend
6. Test the download feature

Would you like me to create the Dockerfile and help you deploy it?
