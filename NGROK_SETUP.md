# ngrok Setup Guide

## ✅ Backend Server Started

The backend API server is now running on `http://localhost:8000`

## 🔗 Getting Your ngrok URL

### Option 1: Check ngrok Web Interface (Easiest)

1. Open your browser and go to: **http://localhost:4040**
2. You'll see the ngrok dashboard
3. Look for the **"Forwarding"** section
4. Copy the HTTPS URL (looks like: `https://abc123.ngrok-free.app`)

### Option 2: Use Terminal

Run this command to get the URL:
```bash
curl http://localhost:4040/api/tunnels | python3 -m json.tool | grep public_url
```

## 📝 Next Steps

### 1. Get Your ngrok URL

The ngrok URL will look like:
```
https://abc123-def456.ngrok-free.app
```

### 2. Update Vercel Environment Variable

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project: `stitch-frontend`
3. Go to **Settings** → **Environment Variables**
4. Find or add: `NEXT_PUBLIC_API_URL`
5. Set the value to your ngrok URL (e.g., `https://abc123-def456.ngrok-free.app`)
6. **IMPORTANT:** Make sure **"Production"** is checked ✅
7. Click **Save**

### 3. Redeploy Frontend

After updating the environment variable:

**Option A: Via Vercel Dashboard**
- Go to **Deployments** tab
- Click "..." on latest deployment
- Select **"Redeploy"**

**Option B: Via CLI**
```bash
cd stitch-frontend
vercel --prod
```

### 4. Test It

1. Visit: `https://justlifehr.vercel.app/?debug=api`
2. Open browser console (F12)
3. You should see: `[API Debug] NEXT_PUBLIC_API_URL: https://your-ngrok-url.ngrok-free.app`
4. Try the download feature!

## ⚠️ Important Notes

### ngrok Free Tier Limitations

- **URL changes on restart**: If you restart ngrok, you'll get a new URL
- **Limited connections**: Free tier has connection limits
- **Session timeout**: Free tunnels may timeout after inactivity

### Keeping ngrok Running

- Keep both terminals open:
  - Terminal 1: Backend server (`python api_server.py`)
  - Terminal 2: ngrok tunnel (`ngrok http 8000`)
- If either stops, restart it

### For Permanent URL

If you need a permanent URL:
- Upgrade ngrok to paid plan ($8/month) for fixed domain
- Or deploy to Railway/Render for permanent hosting

## 🔧 Troubleshooting

### Backend Not Starting?
```bash
cd /Users/bkocdur/Desktop/JazzHR
source venv/bin/activate
python api_server.py
```

### ngrok Not Working?
1. Check ngrok is running: Visit http://localhost:4040
2. Verify backend is running: Visit http://localhost:8000/docs
3. Restart ngrok: Stop (Ctrl+C) and run `ngrok http 8000` again

### CORS Errors?
- The backend CORS is already configured for `https://justlifehr.vercel.app`
- If you get CORS errors, check the backend logs

## 📊 Current Status

- ✅ Backend server: Running on `localhost:8000`
- ✅ ngrok tunnel: Starting...
- ⏳ Next: Get ngrok URL and update Vercel

## 🎯 Quick Commands

**Start backend:**
```bash
cd /Users/bkocdur/Desktop/JazzHR
source venv/bin/activate
python api_server.py
```

**Start ngrok (in new terminal):**
```bash
ngrok http 8000
```

**Get ngrok URL:**
```bash
curl http://localhost:4040/api/tunnels | python3 -m json.tool | grep public_url
```

**Check backend health:**
```bash
curl http://localhost:8000/docs
```
