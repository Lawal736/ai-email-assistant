#!/usr/bin/env python3
"""
Test script to check authentication status
"""

import requests
import json

def test_auth_status():
    """Test authentication status"""
    base_url = "http://localhost:5001"
    
    print("🔍 Testing Authentication Status...")
    print("=" * 50)
    
    # Test 1: Check if app is running
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ App is running (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ App is not running: {e}")
        return
    
    # Test 2: Check dashboard access
    try:
        response = requests.get(f"{base_url}/dashboard", allow_redirects=False)
        if response.status_code == 302:
            print("⚠️ Dashboard redirects (not authenticated)")
        elif response.status_code == 200:
            print("✅ Dashboard accessible (authenticated)")
        else:
            print(f"❓ Dashboard status: {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
    
    # Test 3: Check API endpoints
    endpoints = [
        "/api/emails",
        "/api/summary", 
        "/api/process-emails"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}")
            if response.status_code == 401:
                print(f"❌ {endpoint}: Not authenticated")
            elif response.status_code == 200:
                print(f"✅ {endpoint}: Working")
                # Try to parse JSON response
                try:
                    data = response.json()
                    if 'error' in data:
                        print(f"   └─ Error: {data['error']}")
                    else:
                        print(f"   └─ Success: {len(data) if isinstance(data, list) else 'Data received'}")
                except:
                    print(f"   └─ Non-JSON response")
            else:
                print(f"❓ {endpoint}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error {e}")
    
    print("\n" + "=" * 50)
    print("💡 To authenticate:")
    print("1. Visit http://localhost:5001/connect-gmail")
    print("2. Click 'Start Gmail Authentication'")
    print("3. Complete the OAuth flow")
    print("4. Return to dashboard and try 'Load AI Analysis'")

if __name__ == "__main__":
    test_auth_status() 