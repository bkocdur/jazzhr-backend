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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# Install noVNC for web-based VNC access
RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc && \
    git clone --depth 1 https://github.com/novnc/websockify.git /opt/novnc/utils/websockify && \
    ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Create startup script that starts Xvfb, VNC, noVNC, and the API server
RUN cat > /app/start.sh << 'EOF' && chmod +x /app/start.sh
#!/bin/bash
set -e

echo "=== Starting JazzHR Backend ==="
echo "PORT: ${PORT:-8000}"
echo "DISPLAY: ${DISPLAY:-:99}"

# Start Xvfb virtual display (required for browser automation)
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset > /tmp/xvfb.log 2>&1 &
export DISPLAY=:99

# Wait for Xvfb to start
sleep 3
echo "Xvfb started"

# Start window manager (optional, for VNC)
echo "Starting fluxbox..."
fluxbox > /tmp/fluxbox.log 2>&1 &
sleep 1

# Start VNC server (optional, for remote browser access)
echo "Starting VNC server..."
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw -xkb -bg > /tmp/vnc.log 2>&1 || echo "VNC server failed (non-critical)"

# Start noVNC web server (optional, for web-based VNC access)
if [ -f /opt/novnc/utils/websockify/run ]; then
    echo "Starting noVNC..."
    /opt/novnc/utils/websockify/run --web=/opt/novnc 6080 localhost:5900 > /tmp/novnc.log 2>&1 &
else
    echo "noVNC not found, skipping..."
fi

# Wait for services to stabilize
sleep 2

# Verify Python and uvicorn are available
echo "Checking Python..."
python3 --version || echo "Python check failed"

echo "Checking uvicorn..."
python3 -c "import uvicorn; print('uvicorn OK')" || echo "uvicorn import failed"

# Start the API server
echo "=== Starting FastAPI server ==="
echo "Host: 0.0.0.0"
echo "Port: ${PORT:-8000}"
echo "================================"

# Use exec to replace shell process with uvicorn
exec python3 -m uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
EOF

# Run the server with Xvfb and VNC
CMD ["/app/start.sh"]
