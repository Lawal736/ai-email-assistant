#!/usr/bin/env python3
"""
Test script to verify Gmail authentication and email functionality
"""

import requests
import json
import sys

def test_gmail_setup():
    """Test Gmail authentication and email functionality"""
    base_url = "http://localhost:5002"
    
    print("🔍 Testing Gmail Setup...")
    print("=" * 50)
    
    try:
        # Test 1: Check if app is running
        print("1️⃣ Testing app connectivity...")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            print("   ✅ App is running")
        else:
            print(f"   ❌ App not responding: {response.status_code}")
            return
        
        # Test 2: Check Gmail connection page
        print("\n2️⃣ Testing Gmail connection page...")
        response = requests.get(f"{base_url}/connect-gmail", timeout=5)
        
        if response.status_code == 200:
            print("   ✅ Gmail connection page accessible")
        else:
            print(f"   ❌ Gmail connection page error: {response.status_code}")
        
        # Test 3: Check dashboard (should redirect if not authenticated)
        print("\n3️⃣ Testing dashboard access...")
        response = requests.get(f"{base_url}/dashboard", timeout=5, allow_redirects=False)
        
        if response.status_code == 302:
            print("   ⚠️ Dashboard redirecting (not authenticated)")
            print("   📝 You need to complete Gmail authentication")
        elif response.status_code == 200:
            print("   ✅ Dashboard accessible (authenticated)")
        else:
            print(f"   ❌ Dashboard error: {response.status_code}")
        
        # Test 4: Check if token.json exists
        print("\n4️⃣ Checking authentication files...")
        import os
        if os.path.exists("token.json"):
            print("   ✅ token.json found (authenticated)")
        else:
            print("   ❌ token.json missing (not authenticated)")
        
        if os.path.exists("credentials.json"):
            print("   ✅ credentials.json found")
        else:
            print("   ❌ credentials.json missing")
        
        print("\n" + "=" * 50)
        print("📋 NEXT STEPS:")
        print("1. Visit: http://localhost:5002/connect-gmail")
        print("2. Click 'Start Gmail Authentication'")
        print("3. Complete the OAuth flow with your Google account")
        print("4. Return to dashboard and try 'Load AI Analysis'")
        print("5. Run this test again to verify everything works")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to app. Make sure it's running on port 5002")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_gmail_setup() 