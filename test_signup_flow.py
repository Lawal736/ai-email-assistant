#!/usr/bin/env python3
"""
Test script to verify the signup and authentication flow
"""

import requests
import json
import sys

def test_signup_flow():
    """Test the signup and authentication flow"""
    base_url = "http://localhost:5002"
    
    print("🔍 Testing Signup and Authentication Flow...")
    print("=" * 60)
    
    try:
        # Test 1: Check if app is running
        print("1️⃣ Testing app connectivity...")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            print("   ✅ App is running")
        else:
            print(f"   ❌ App not responding: {response.status_code}")
            return
        
        # Test 2: Check signup page
        print("\n2️⃣ Testing signup page...")
        response = requests.get(f"{base_url}/signup", timeout=5)
        
        if response.status_code == 200:
            print("   ✅ Signup page accessible")
        else:
            print(f"   ❌ Signup page error: {response.status_code}")
        
        # Test 3: Check login page
        print("\n3️⃣ Testing login page...")
        response = requests.get(f"{base_url}/login", timeout=5)
        
        if response.status_code == 200:
            print("   ✅ Login page accessible")
        else:
            print(f"   ❌ Login page error: {response.status_code}")
        
        # Test 4: Check connect-gmail (should redirect to login)
        print("\n4️⃣ Testing Gmail connection (should redirect to login)...")
        response = requests.get(f"{base_url}/connect-gmail", timeout=5, allow_redirects=False)
        
        if response.status_code == 302:
            print("   ✅ Gmail connection properly redirects to login (as expected)")
        else:
            print(f"   ⚠️ Unexpected response: {response.status_code}")
        
        print("\n" + "=" * 60)
        print("📋 NEXT STEPS TO GET EMAIL WORKING:")
        print("1. Visit: http://localhost:5002/signup")
        print("2. Create a new account with your email and password")
        print("3. After signup, you'll be redirected to login")
        print("4. Login with your new account")
        print("5. Then visit: http://localhost:5002/connect-gmail")
        print("6. Click 'Start Gmail Authentication'")
        print("7. Complete the OAuth flow with your Google account")
        print("8. You'll be redirected to the dashboard with email access!")
        print("\n💡 The app requires authentication for security reasons.")
        print("   This ensures only authorized users can access Gmail data.")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to app. Make sure it's running on port 5002")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_signup_flow() 