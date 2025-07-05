#!/usr/bin/env python3
"""
Test script to verify the email not found error handling implementation
"""

import requests
import json
import time

def test_email_not_found_handling():
    """Test the new email not found error handling"""
    
    print("🧪 Testing Email Not Found Error Handling")
    print("=" * 50)
    
    # Test configuration
    base_url = "http://localhost:5004"
    
    # Test 1: Check if app is running
    print("1. Testing app availability...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ App is running")
        else:
            print(f"❌ App returned status {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ App not accessible: {e}")
        return
    
    # Test 2: Test with invalid email ID
    print("\n2. Testing with invalid email ID...")
    invalid_email_id = "invalid_email_id_12345"
    
    test_data = {
        "email_id": invalid_email_id
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/generate-response",
            json=test_data,
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 404:
            data = response.json()
            print("✅ Got 404 response as expected")
            print(f"Error message: {data.get('error', 'No error message')}")
            print(f"Error code: {data.get('error_code', 'No error code')}")
            
            if data.get('error_code') == 'EMAIL_NOT_FOUND':
                print("✅ Correct error code returned")
            else:
                print("❌ Wrong error code returned")
                
            if "Email not available, please refresh" in data.get('error', ''):
                print("✅ Correct error message returned")
            else:
                print("❌ Wrong error message returned")
        else:
            print(f"❌ Expected 404, got {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    # Test 3: Test analyze-email endpoint
    print("\n3. Testing analyze-email endpoint...")
    
    try:
        response = requests.post(
            f"{base_url}/api/analyze-email",
            json=test_data,
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 404:
            data = response.json()
            print("✅ Got 404 response as expected")
            print(f"Error message: {data.get('error', 'No error message')}")
            print(f"Error code: {data.get('error_code', 'No error code')}")
            
            if data.get('error_code') == 'EMAIL_NOT_FOUND':
                print("✅ Correct error code returned")
            else:
                print("❌ Wrong error code returned")
        else:
            print(f"❌ Expected 404, got {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    # Test 4: Test enhanced email analysis endpoint
    print("\n4. Testing enhanced email analysis endpoint...")
    
    try:
        response = requests.post(
            f"{base_url}/api/pro/enhanced-email-analysis",
            json=test_data,
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 404:
            data = response.json()
            print("✅ Got 404 response as expected")
            print(f"Error message: {data.get('error', 'No error message')}")
            print(f"Error code: {data.get('error_code', 'No error code')}")
            
            if data.get('error_code') == 'EMAIL_NOT_FOUND':
                print("✅ Correct error code returned")
            else:
                print("❌ Wrong error code returned")
        else:
            print(f"❌ Expected 404, got {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("- All endpoints should return 404 for invalid email IDs")
    print("- All endpoints should return EMAIL_NOT_FOUND error code")
    print("- All endpoints should return user-friendly error message")
    print("=" * 50)

def test_smart_refresh_logic():
    """Test the smart refresh logic"""
    
    print("\n🧪 Testing Smart Refresh Logic")
    print("=" * 50)
    
    base_url = "http://localhost:5004"
    
    # Test dashboard with refresh parameter
    print("1. Testing dashboard with refresh parameter...")
    
    try:
        timestamp = int(time.time())
        response = requests.get(f"{base_url}/dashboard?refresh={timestamp}", timeout=10)
        
        if response.status_code == 200:
            print("✅ Dashboard accessible with refresh parameter")
            if "refresh" in response.url:
                print("✅ Refresh parameter detected in URL")
            else:
                print("❌ Refresh parameter not in URL")
        else:
            print(f"❌ Dashboard returned status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Email Not Found Fix Tests")
    print("Make sure the app is running on http://localhost:5004")
    print()
    
    test_email_not_found_handling()
    test_smart_refresh_logic()
    
    print("\n✅ Testing complete!")
    print("\nTo test the frontend:")
    print("1. Open http://localhost:5004 in your browser")
    print("2. Log in to your account")
    print("3. Try to generate a response for an email that no longer exists")
    print("4. You should see 'Email not available, please refresh' message")
    print("5. Dashboard should auto-refresh after 3 seconds") 