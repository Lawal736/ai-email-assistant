#!/usr/bin/env python3
"""
Test script to verify Gmail profile functionality
"""

import requests
import json

def test_gmail_profile():
    """Test Gmail profile functionality"""
    print("🔍 Testing Gmail Profile Functionality...")
    print("=" * 50)
    
    # Test the account page
    try:
        response = requests.get('http://localhost:5004/account', timeout=5)
        if response.status_code == 200:
            print("✅ Account page accessible")
            
            # Check if the page contains Gmail profile information
            content = response.text
            
            if 'Profile Email Address' in content:
                print("✅ Profile email section found")
            else:
                print("❌ Profile email section not found")
                
            if 'Linked Gmail Address' in content:
                print("✅ Linked Gmail address section found")
            else:
                print("❌ Linked Gmail address section not found")
                
            if 'Connected' in content or 'Not connected' in content:
                print("✅ Gmail connection status displayed")
            else:
                print("❌ Gmail connection status not displayed")
                
            if 'Your profile email is used for account management' in content:
                print("✅ Informational note found")
            else:
                print("❌ Informational note not found")
                
        else:
            print(f"❌ Account page returned status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing account page: {e}")
    
    print("\n" + "=" * 50)
    print("💡 To test the full functionality:")
    print("1. Visit http://localhost:5004/account")
    print("2. Check that both email addresses are displayed")
    print("3. Verify the informational note is present")
    print("4. If Gmail is connected, you should see the Gmail address")
    print("5. If Gmail is not connected, you should see a 'Connect Gmail' button")

if __name__ == "__main__":
    test_gmail_profile() 