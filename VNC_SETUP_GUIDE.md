# VNC Setup for User Browser Login

## Overview

VNC (Virtual Network Computing) allows users to remotely view and interact with the browser running on Railway, so they can log in directly.

## How It Works

1. **Backend starts browser** in visible mode (not headless)
2. **VNC server** streams the browser display
3. **User connects** via VNC client
4. **User sees browser** and logs in directly
5. **Script detects** login and continues automatically

## Railway Configuration

### Option 1: Expose VNC Port (Recommended)

1. **In Railway Dashboard:**
   - Go to your service → **Settings** → **Networking**
   - Add a new port:
     - **Port:** `5900`
     - **Protocol:** TCP
     - **Public:** Yes (if you want external access)
   - Save

2. **Get VNC URL:**
   - Railway provides: `your-service.railway.app:5900`
   - Or use Railway's public domain

### Option 2: Use Railway's Public Domain

Railway automatically provides a public domain. VNC will be accessible at:
```
your-service.railway.app:5900
```

## User Instructions

When login is required, users will see instructions:

1. **Download VNC Client:**
   - Mac: [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/) or built-in Screen Sharing
   - Windows: [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/)
   - Linux: `sudo apt install remmina` or `sudo apt install tigervnc-viewer`
   - Web: Use noVNC (if we add it)

2. **Connect to VNC:**
   - Open VNC client
   - Enter: `your-service.railway.app:5900`
   - Connect (no password needed in current setup)

3. **Log In:**
   - You'll see the Chrome browser window
   - Navigate to JazzHR login if needed
   - Log in directly in the browser
   - Script will detect login and continue

## Security Note

⚠️ **Current setup has no VNC password** - anyone with the URL can access.

**For production, add VNC password:**
1. Set `VNC_PASSWORD` environment variable in Railway
2. Update Dockerfile to use password-protected VNC

## Alternative: noVNC (Web-Based)

For easier access, we can add noVNC which allows browser-based VNC access:

1. **Add noVNC to Dockerfile:**
   ```dockerfile
   RUN apt-get install -y novnc websockify
   ```

2. **Expose noVNC port:** `6080`

3. **Users access via:** `https://your-service.railway.app:6080/vnc.html`

## Testing Locally

To test VNC locally:

1. **Build Docker image:**
   ```bash
   docker build -t jazzhr-backend .
   ```

2. **Run with VNC:**
   ```bash
   docker run -p 8000:8000 -p 5900:5900 jazzhr-backend
   ```

3. **Connect VNC client to:** `localhost:5900`

4. **Start download** - you'll see browser window in VNC

## Troubleshooting

### VNC Not Accessible
- Check Railway port is exposed (5900)
- Verify Railway public domain is set
- Check firewall/network settings

### Browser Not Visible
- Ensure Xvfb is running (`ps aux | grep Xvfb`)
- Check DISPLAY environment variable (`echo $DISPLAY`)
- Verify VNC server is running (`ps aux | grep x11vnc`)

### Login Not Detected
- Check browser is actually on login page
- Verify `check_login_required()` logic
- Check logs for detection messages
