# ngrok Setup - Step by Step

## ⚠️ ngrok Requires Authentication

ngrok 3.x requires you to sign up (free) and get an authentication token.

## Quick Setup (5 minutes)

### Step 1: Sign Up for ngrok (Free)

1. Go to: https://dashboard.ngrok.com/signup
2. Sign up with email (or GitHub/Google)
3. It's **100% free** for basic use

### Step 2: Get Your Auth Token

1. After signing up, go to: https://dashboard.ngrok.com/get-started/your-authtoken
2. Copy your authtoken (looks like: `2abc123def456ghi789jkl012mno345pqr678stu901vwx234yz`)

### Step 3: Configure ngrok

Run this command (replace with your actual token):
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
```

### Step 4: Start ngrok

Open a **new terminal** and run:
```bash
cd /Users/bkocdur/Desktop/JazzHR
ngrok http 8000
```

You should see output like:
```
Session Status                online
Account                       your-email@example.com
Version                       3.20.0
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123-def456.ngrok-free.app -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

### Step 5: Copy Your ngrok URL

Look for the **"Forwarding"** line:
```
Forwarding    https://abc123-def456.ngrok-free.app -> http://localhost:8000
```

Copy the HTTPS URL: `https://abc123-def456.ngrok-free.app`

### Step 6: Update Vercel

1. Go to: https://vercel.com/dashboard
2. Select your project: `stitch-frontend`
3. Go to **Settings** → **Environment Variables**
4. Add/Update: `NEXT_PUBLIC_API_URL`
5. Value: Your ngrok URL (from Step 5)
6. **Check "Production"** ✅
7. Click **Save**

### Step 7: Redeploy Frontend

**Option A: Via Dashboard**
- Go to **Deployments** → Latest → "..." → **Redeploy**

**Option B: Via CLI**
```bash
cd stitch-frontend
vercel --prod
```

### Step 8: Test

1. Visit: `https://justlifehr.vercel.app/?debug=api`
2. Open browser console (F12)
3. You should see: `[API Debug] NEXT_PUBLIC_API_URL: https://your-ngrok-url.ngrok-free.app`

## 🎯 Quick Commands Reference

**Start backend (Terminal 1):**
```bash
cd /Users/bkocdur/Desktop/JazzHR
source venv/bin/activate
python api_server.py
```

**Start ngrok (Terminal 2 - AFTER authentication):**
```bash
cd /Users/bkocdur/Desktop/JazzHR
ngrok http 8000
```

**Get ngrok URL (after it's running):**
- Visit: http://localhost:4040
- Or run: `curl http://localhost:4040/api/tunnels | python3 -m json.tool | grep public_url`

## ⚠️ Important Notes

1. **Keep both terminals open:**
   - Terminal 1: Backend server
   - Terminal 2: ngrok tunnel

2. **ngrok URL changes:**
   - Free tier: URL changes every time you restart ngrok
   - Paid tier ($8/month): Fixed domain

3. **If ngrok stops:**
   - Restart it: `ngrok http 8000`
   - Get new URL from http://localhost:4040
   - Update Vercel with new URL
   - Redeploy frontend

## 🔧 Troubleshooting

### "ngrok: command not found"
```bash
# Install via Homebrew
brew install ngrok/ngrok/ngrok

# Or download from: https://ngrok.com/download
```

### "authtoken not configured"
Run: `ngrok config add-authtoken YOUR_TOKEN`

### "port 8000 already in use"
Make sure backend is running: `curl http://localhost:8000/docs`

### Can't access http://localhost:4040
- Make sure ngrok is running
- Check: `ps aux | grep ngrok`
- Restart ngrok if needed

## 📝 Summary

1. ✅ Sign up at https://dashboard.ngrok.com/signup (free)
2. ✅ Get authtoken from dashboard
3. ✅ Run: `ngrok config add-authtoken YOUR_TOKEN`
4. ✅ Start backend: `python api_server.py` (Terminal 1)
5. ✅ Start ngrok: `ngrok http 8000` (Terminal 2)
6. ✅ Copy URL from http://localhost:4040
7. ✅ Update Vercel: `NEXT_PUBLIC_API_URL` = your ngrok URL
8. ✅ Redeploy frontend
9. ✅ Test!

Need help? The backend is already running, you just need to authenticate ngrok and start the tunnel!
