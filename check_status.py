#!/usr/bin/env python3
"""
Status check script for AI Email Assistant
"""

import requests
import json

def check_app_status():
    """Check the status of the running application"""
    print("🔍 Checking AI Email Assistant Status")
    print("=" * 50)
    
    try:
        # Check main page
        print("📱 Checking main page...")
        response = requests.get('http://localhost:5001', timeout=5)
        if response.status_code == 200:
            print("✅ Main page is accessible")
        else:
            print(f"❌ Main page returned status {response.status_code}")
            return
        
        # Check dashboard (should redirect to connect-gmail if not authenticated)
        print("\n📊 Checking dashboard...")
        response = requests.get('http://localhost:5001/dashboard', timeout=5, allow_redirects=False)
        if response.status_code == 302:
            print("✅ Dashboard redirecting to Gmail auth (expected)")
        elif response.status_code == 200:
            print("✅ Dashboard accessible (Gmail authenticated)")
        else:
            print(f"❌ Dashboard returned status {response.status_code}")
        
        # Check connect-gmail page
        print("\n🔗 Checking Gmail connection page...")
        response = requests.get('http://localhost:5001/connect-gmail', timeout=5)
        if response.status_code == 200:
            print("✅ Gmail connection page accessible")
        else:
            print(f"❌ Gmail connection page returned status {response.status_code}")
        
        # Check if credentials.json exists
        print("\n🔑 Checking credentials...")
        try:
            with open('credentials.json', 'r') as f:
                creds = json.load(f)
                if 'web' in creds:
                    print("✅ Web application credentials found")
                elif 'installed' in creds:
                    print("✅ Desktop application credentials found")
                else:
                    print("⚠️ Unknown credentials format")
        except FileNotFoundError:
            print("❌ credentials.json not found")
        except Exception as e:
            print(f"❌ Error reading credentials: {e}")
        
        # Check if token.json exists
        try:
            with open('token.json', 'r') as f:
                token = json.load(f)
                print("✅ Gmail authentication token found")
        except FileNotFoundError:
            print("❌ token.json not found (Gmail not authenticated)")
        except Exception as e:
            print(f"❌ Error reading token: {e}")
        
        print("\n📋 Summary:")
        print("- App is running on http://localhost:5001")
        print("- To use the app, you need to:")
        print("  1. Have credentials.json in the project directory")
        print("  2. Click 'Connect Gmail' to authenticate")
        print("  3. Grant permissions to access your Gmail")
        print("  4. View your dashboard with email analysis")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to app. Is it running?")
    except Exception as e:
        print(f"❌ Error checking status: {e}")

if __name__ == "__main__":
    check_app_status() 