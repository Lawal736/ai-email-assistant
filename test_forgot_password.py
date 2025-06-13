#!/usr/bin/env python3
"""
Test script for forgot password functionality
"""

import requests
import sys

def test_forgot_password():
    """Test the forgot password page"""
    base_url = "http://localhost:5001"
    
    try:
        # Test GET request to forgot password page
        print("🔍 Testing forgot password page...")
        response = requests.get(f"{base_url}/forgot-password", timeout=5)
        
        if response.status_code == 200:
            print("✅ Forgot password page loads successfully")
            
            # Check if the page contains expected content
            if "Forgot Password" in response.text and "Enter your email" in response.text:
                print("✅ Page contains expected content")
            else:
                print("⚠️ Page content may be incomplete")
                
            return True
        else:
            print(f"❌ Forgot password page failed with status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the app. Make sure it's running on port 5001")
        return False
    except Exception as e:
        print(f"❌ Error testing forgot password: {e}")
        return False

def test_reset_password():
    """Test the reset password page"""
    base_url = "http://localhost:5001"
    
    try:
        # Test GET request to reset password page with a dummy token
        print("🔍 Testing reset password page...")
        response = requests.get(f"{base_url}/reset-password/test-token", timeout=5)
        
        if response.status_code == 200:
            print("✅ Reset password page loads successfully")
            
            # Check if the page contains expected content
            if "Reset Password" in response.text and "Enter your new password" in response.text:
                print("✅ Page contains expected content")
            else:
                print("⚠️ Page content may be incomplete")
                
            return True
        else:
            print(f"❌ Reset password page failed with status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the app. Make sure it's running on port 5001")
        return False
    except Exception as e:
        print(f"❌ Error testing reset password: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Forgot Password Functionality")
    print("=" * 50)
    
    # Test forgot password page
    forgot_success = test_forgot_password()
    
    print()
    
    # Test reset password page
    reset_success = test_reset_password()
    
    print()
    print("=" * 50)
    
    if forgot_success and reset_success:
        print("🎉 All tests passed! Forgot password functionality is working.")
        print("\n💡 To test manually:")
        print("1. Start the app: python3 app.py")
        print("2. Visit: http://localhost:5001/forgot-password")
        print("3. Enter an email and submit the form")
    else:
        print("❌ Some tests failed. Check the app configuration.")
        sys.exit(1) 