#!/usr/bin/env python3
"""
Verify email functionality after Gmail authentication
"""

import requests
import json
import os

def verify_email_functionality():
    """Verify that email functionality is working"""
    base_url = "http://localhost:5002"
    
    print("🔍 Verifying Email Functionality...")
    print("=" * 50)
    
    # Check if authenticated
    if not os.path.exists("token.json"):
        print("❌ Not authenticated. Please complete Gmail OAuth first:")
        print("   1. Visit: http://localhost:5002/connect-gmail")
        print("   2. Click 'Start Gmail Authentication'")
        print("   3. Complete the OAuth flow")
        return
    
    print("✅ Gmail authenticated (token.json found)")
    
    try:
        # Test dashboard access
        print("\n1️⃣ Testing dashboard access...")
        response = requests.get(f"{base_url}/dashboard", timeout=10)
        
        if response.status_code == 200:
            print("   ✅ Dashboard accessible")
        else:
            print(f"   ❌ Dashboard error: {response.status_code}")
            return
        
        # Test email API
        print("\n2️⃣ Testing email API...")
        response = requests.get(f"{base_url}/api/emails", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            email_count = len(data.get('emails', []))
            print(f"   ✅ Email API working - Found {email_count} emails")
            
            if email_count > 0:
                print("   📧 Sample email subjects:")
                for i, email in enumerate(data['emails'][:3]):
                    subject = email.get('subject', 'No subject')
                    sender = email.get('sender', 'Unknown')
                    print(f"      {i+1}. {subject[:50]}... (from: {sender})")
            else:
                print("   ⚠️ No emails found (check your Gmail inbox)")
        else:
            print(f"   ❌ Email API error: {response.status_code}")
        
        # Test summary API
        print("\n3️⃣ Testing summary API...")
        response = requests.get(f"{base_url}/api/summary", timeout=15)
        
        if response.status_code == 200:
            print("   ✅ Summary API working")
        else:
            print(f"   ❌ Summary API error: {response.status_code}")
        
        print("\n" + "=" * 50)
        print("🎉 Email functionality verification complete!")
        print("📝 If everything shows ✅, your email assistant is working!")
        print("🌐 Visit: http://localhost:5002/dashboard to use the full interface")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to app. Make sure it's running on port 5002")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_email_functionality() 