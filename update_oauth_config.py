#!/usr/bin/env python3
"""
Script to help update OAuth configuration in Google Cloud Console
"""

import requests
import sys

def detect_current_port():
    """Detect which port the Flask app is currently running on"""
    print("🔍 Detecting current Flask app port...")
    
    # Try common ports
    for port in ['5004', '5003', '5002', '5001', '5000']:
        try:
            print(f"  Testing port {port}...")
            response = requests.get(f'http://localhost:{port}/', timeout=2)
            if response.status_code == 200:
                print(f"✅ Found Flask app running on port {port}")
                return port
        except requests.exceptions.RequestException:
            continue
    
    print("❌ Could not detect Flask app port")
    return None

def main():
    print("🚀 OAuth Configuration Helper")
    print("=" * 50)
    
    # Detect current port
    current_port = detect_current_port()
    
    if not current_port:
        print("\n❌ Please make sure your Flask app is running first!")
        print("   Run: python3 app.py")
        sys.exit(1)
    
    redirect_uri = f"http://localhost:{current_port}/oauth2callback"
    
    print(f"\n📋 Current OAuth Redirect URI: {redirect_uri}")
    print("\n🔧 To fix the OAuth redirect_uri_mismatch error:")
    print("=" * 50)
    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Select your project")
    print("3. Go to 'APIs & Services' > 'Credentials'")
    print("4. Find your OAuth 2.0 Client ID (Web application)")
    print("5. Click on the client ID to edit it")
    print("6. In the 'Authorized redirect URIs' section:")
    print(f"   - Add: {redirect_uri}")
    print("   - Remove any old redirect URIs with different ports")
    print("7. Click 'Save'")
    print("\n💡 Alternative: Add multiple ports to handle port changes:")
    print("   - http://localhost:5000/oauth2callback")
    print("   - http://localhost:5001/oauth2callback")
    print("   - http://localhost:5002/oauth2callback")
    print("   - http://localhost:5003/oauth2callback")
    print("   - http://localhost:5004/oauth2callback")
    print("\n🔄 After updating, try the OAuth flow again!")
    
    # Test the redirect URI
    print(f"\n🧪 Testing redirect URI...")
    try:
        response = requests.get(f"http://localhost:{current_port}/connect-gmail", timeout=2)
        if response.status_code == 200:
            print("✅ Connect Gmail page is accessible")
        else:
            print(f"⚠️  Connect Gmail page returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing redirect URI: {e}")

if __name__ == "__main__":
    main() 