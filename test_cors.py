#!/usr/bin/env python3
"""Test script to verify CORS configuration"""
import requests

BACKEND_URL = "https://jazzhr-backend-production.up.railway.app"
FRONTEND_ORIGIN = "https://justlifehr.vercel.app"

print(f"Testing CORS for {FRONTEND_ORIGIN} -> {BACKEND_URL}")

# Test OPTIONS preflight
print("\n1. Testing OPTIONS preflight request...")
try:
    response = requests.options(
        f"{BACKEND_URL}/api/downloads/start",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Headers:")
    for key, value in response.headers.items():
        if "access-control" in key.lower():
            print(f"     {key}: {value}")
    if "Access-Control-Allow-Origin" not in response.headers:
        print("   ❌ CORS headers missing!")
    else:
        print(f"   ✅ CORS headers present: {response.headers.get('Access-Control-Allow-Origin')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test GET root endpoint
print("\n2. Testing GET root endpoint...")
try:
    response = requests.get(f"{BACKEND_URL}/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test actual POST request
print("\n3. Testing POST request with Origin header...")
try:
    response = requests.post(
        f"{BACKEND_URL}/api/downloads/start",
        json={"job_id": "test"},
        headers={"Origin": FRONTEND_ORIGIN}
    )
    print(f"   Status: {response.status_code}")
    print(f"   CORS Headers:")
    for key, value in response.headers.items():
        if "access-control" in key.lower():
            print(f"     {key}: {value}")
except Exception as e:
    print(f"   ❌ Error: {e}")
