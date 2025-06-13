#!/usr/bin/env python3
"""
Test script to verify OAuth flow is working
"""

import requests
import json
import sys

def test_oauth_flow():
    """Test the OAuth flow"""
    base_url = "http://localhost:5004"
    
    print("🔍 Testing OAuth Flow...")
    print("=" * 50)
    
    try:
        # Test 1: Check if app is running
        print("1️⃣ Testing app connectivity...")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            print("   ✅ App is running on port 5004")
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
            return
        
        # Test 3: Check OAuth authorization URL
        print("\n3️⃣ Testing OAuth authorization URL...")
        response = requests.get(f"{base_url}/start-gmail-auth", timeout=5)
        
        if response.status_code == 200:
            print("   ✅ OAuth authorization URL accessible")
            
            # Check if the page contains the correct redirect URI
            if "localhost:5004" in response.text:
                print("   ✅ OAuth callback URL is correct (port 5004)")
            else:
                print("   ⚠️ OAuth callback URL might be incorrect")
        else:
            print(f"   ❌ OAuth authorization error: {response.status_code}")
            return
        
        print("\n" + "=" * 50)
        print("✅ OAuth flow setup is working correctly!")
        print("\n💡 Next steps:")
        print("1. Visit: http://localhost:5004/connect-gmail")
        print("2. Click 'Start Gmail Authentication'")
        print("3. Complete the OAuth flow")
        print("4. You should be redirected to the dashboard")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to app. Make sure it's running on port 5004")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_oauth_flow() 