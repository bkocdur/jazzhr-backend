# User Login Flow - How Users Authenticate

## Overview

Users authenticate themselves through the frontend interface. No cookies are stored in Railway - each user provides their own JazzHR login credentials when needed.

## How It Works

### Flow 1: Login Required at Start

1. **User starts download:**
   - Enters Job ID on the home page
   - Clicks "Start Download"

2. **Backend detects login required:**
   - Backend tries to access JazzHR
   - Detects login page
   - Returns `LOGIN_REQUIRED` status

3. **Frontend shows login modal:**
   - Modal appears with instructions
   - User sees step-by-step guide to get cookies

4. **User provides cookies:**
   - User logs in to JazzHR in their browser
   - Gets cookies from DevTools
   - Pastes cookies into modal
   - Clicks "Continue Download"

5. **Download starts with cookies:**
   - Frontend sends cookies with download request
   - Backend uses cookies to authenticate
   - Download proceeds

### Flow 2: Login Required During Download

1. **Download is running:**
   - User is on active download page
   - Download progress is shown

2. **Login expires or required:**
   - Backend detects login needed mid-download
   - Sets status to `login_required`
   - Progress updates show authentication needed

3. **Frontend detects login required:**
   - Active download page shows login modal
   - User provides cookies

4. **Download restarts:**
   - Frontend calls `/api/downloads/{id}/authenticate`
   - Backend restarts download with new cookies
   - Download continues

## User Instructions (Shown in Modal)

When login is required, users see:

1. **Open JazzHR:** Click link to open https://app.jazz.co in new tab
2. **Log in:** Enter your JazzHR credentials
3. **Get cookies:**
   - Press F12 to open DevTools
   - Go to **Application** tab → **Cookies** → `https://app.jazz.co`
   - Copy cookies (especially session cookies)
4. **Paste cookies:** Paste JSON array of cookies into the modal
5. **Continue:** Click "Continue Download"

## Cookie Format

Users paste cookies in this format:

```json
[
  {
    "name": "session_id",
    "value": "your-session-value",
    "domain": ".jazz.co",
    "path": "/",
    "secure": true
  },
  {
    "name": "auth_token",
    "value": "your-auth-token",
    "domain": ".jazz.co",
    "path": "/",
    "secure": true
  }
]
```

## Security

- **No cookies stored:** Cookies are only used for the specific download request
- **Per-user authentication:** Each user provides their own credentials
- **No Railway env vars:** No need to store cookies in Railway
- **Session-based:** Cookies are only valid for that user's session

## Technical Details

### Backend Changes

- Detects `login_required` status
- Accepts cookies in download request
- New endpoint: `POST /api/downloads/{id}/authenticate` to provide cookies mid-download
- Cookies are only used for that specific download, not stored

### Frontend Changes

- `LoginModal` component for cookie input
- Detects `LOGIN_REQUIRED` errors
- Shows modal automatically when login needed
- Sends cookies with download request or authenticate endpoint

## Benefits

1. **User privacy:** Each user authenticates with their own account
2. **No admin setup:** No need to configure cookies in Railway
3. **Flexible:** Works for any JazzHR user
4. **Secure:** Cookies not stored, only used per-request
5. **User-friendly:** Clear instructions in the UI

## Testing

To test the flow:

1. Start a download without being logged in
2. Modal should appear
3. Get cookies from JazzHR
4. Paste and continue
5. Download should proceed
