#!/usr/bin/env python3
"""
Test script to verify Gmail credentials setup
"""

import os
import json
from gmail_service import GmailService

def test_credentials_availability():
    """Test if credentials are available from environment or file"""
    print("🔍 Testing Gmail Credentials Setup...")
    print("=" * 50)
    
    # Test 1: Check environment variable
    print("1. Checking GOOGLE_CREDENTIALS_JSON environment variable...")
    credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if credentials_json:
        try:
            creds_data = json.loads(credentials_json)
            print("   ✅ Environment variable found and valid JSON")
            print(f"   📋 Client ID: {creds_data.get('web', {}).get('client_id', 'Not found')[:30]}...")
        except json.JSONDecodeError as e:
            print(f"   ❌ Invalid JSON in environment variable: {e}")
    else:
        print("   ⚠️  Environment variable not found")
    
    # Test 2: Check credentials file
    print("\n2. Checking credentials.json file...")
    if os.path.exists('credentials.json'):
        try:
            with open('credentials.json', 'r') as f:
                creds_data = json.load(f)
            print("   ✅ credentials.json file found and valid JSON")
            print(f"   📋 Client ID: {creds_data.get('web', {}).get('client_id', 'Not found')[:30]}...")
        except Exception as e:
            print(f"   ❌ Error reading credentials file: {e}")
    else:
        print("   ⚠️  credentials.json file not found")
    
    # Test 3: Test GmailService credentials loading
    print("\n3. Testing GmailService credentials loading...")
    try:
        gmail_service = GmailService()
        credentials_data = gmail_service._get_credentials_data()
        print("   ✅ GmailService can load credentials successfully")
        print(f"   📋 Client ID: {credentials_data.get('web', {}).get('client_id', 'Not found')[:30]}...")
    except Exception as e:
        print(f"   ❌ GmailService failed to load credentials: {e}")
    
    # Test 4: Check if we can get authorization URL
    print("\n4. Testing authorization URL generation...")
    try:
        gmail_service = GmailService()
        auth_url = gmail_service.get_authorization_url()
        print("   ✅ Authorization URL generated successfully")
        print(f"   🔗 URL: {auth_url[:80]}...")
    except Exception as e:
        print(f"   ❌ Failed to generate authorization URL: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Credentials Setup Test Complete!")

if __name__ == "__main__":
    test_credentials_availability() 