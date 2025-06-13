#!/usr/bin/env python3
"""
Test script for Gmail authentication
"""

import os
from gmail_service import GmailService

def test_gmail_auth():
    """Test Gmail authentication"""
    print("🧪 Testing Gmail Authentication")
    print("=" * 40)
    
    try:
        # Initialize Gmail service
        gmail_service = GmailService()
        print("✅ GmailService initialized successfully")
        
        # Test getting authorization URL
        auth_url = gmail_service.get_authorization_url()
        print("✅ Authorization URL generated successfully")
        print(f"🔗 Auth URL: {auth_url[:100]}...")
        
        print("\n🎉 Gmail authentication is ready!")
        print("\n📋 Next steps:")
        print("1. Go to http://localhost:5001")
        print("2. Click 'Connect Gmail'")
        print("3. Follow the authentication process")
        print("4. If you see a verification warning, click 'Advanced' and 'Go to AI Email Assistant (unsafe)'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure credentials.json exists in the project directory")
        print("2. Check that the credentials are valid")
        print("3. Ensure Gmail API is enabled in Google Cloud Console")

if __name__ == "__main__":
    test_gmail_auth() 