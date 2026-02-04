FROM python:3.11-slim

# Install system dependencies for Chrome and X11/VNC support
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    x11vnc \
    fluxbox \
    xterm \
    ca-certificates \
    python3-numpy \
    git \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (using modern GPG key method)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
# Note: ChromeDriver version should match Chrome version
# Using webdriver-manager will handle this automatically, but we can also install manually
RUN CHROMEDRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip && \
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

# Create directory for downloads
RUN mkdir -p /app/resumes

# Expose ports
EXPOSE 8000
EXPOSE 5900
EXPOSE 6080

# Set environment variables for Chrome
# Use Xvfb virtual display for GUI support (allows non-headless mode when needed)
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=false
ENV FORCE_HEADLESS=false

# Health check - use the PORT environment variable
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Install noVNC for web-based VNC access
RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc && \
    git clone --depth 1 https://github.com/novnc/websockify.git /opt/novnc/utils/websockify && \
    ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Create startup script - simplified version that starts the API server first
# Xvfb/VNC can be started later if needed for browser automation
RUN cat > /app/start.sh << 'EOF' && chmod +x /app/start.sh
#!/bin/bash
set -e

echo "=== Starting JazzHR Backend ==="
echo "PORT: ${PORT:-8000}"

# Set display for browser automation (will be used when needed)
export DISPLAY=:99

# Start Xvfb in background (non-blocking, for browser automation)
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset > /tmp/xvfb.log 2>&1 &
sleep 2

# Start window manager (for VNC, optional)
fluxbox > /tmp/fluxbox.log 2>&1 &

# Start VNC server (optional, for remote browser access)
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw -xkb -bg > /tmp/vnc.log 2>&1 || true

# Start noVNC (optional)
if [ -f /opt/novnc/utils/websockify/run ]; then
    /opt/novnc/utils/websockify/run --web=/opt/novnc 6080 localhost:5900 > /tmp/novnc.log 2>&1 &
fi

# Test app import with detailed error output
echo "Testing app import..."
python3 -c "
import sys
import traceback
try:
    from api_server import app
    print('✓ App imported successfully')
except Exception as e:
    print('✗ ERROR: Failed to import app!')
    print(f'Error type: {type(e).__name__}')
    print(f'Error message: {str(e)}')
    traceback.print_exc()
    sys.exit(1)
" || {
    echo "App import failed, but continuing to see if server starts anyway..."
}

# Start the API server
echo "=== Starting FastAPI server ==="
echo "Host: 0.0.0.0"
echo "Port: ${PORT:-8000}"
echo "Working directory: $(pwd)"
echo "Python path: $(python3 -c 'import sys; print(sys.path)')"
echo "================================"

# Use exec to replace shell process
# Railway uses PORT env var (usually 8080)
# Use --timeout-keep-alive to prevent connection issues
# Use --workers 1 for single process (Railway doesn't need multiple workers)
exec python3 -m uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 75 --workers 1
EOF

# Run the server with Xvfb and VNC
CMD ["/app/start.sh"]
