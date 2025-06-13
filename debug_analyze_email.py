#!/usr/bin/env python3
"""
Debug script to test the analyze-email endpoint
"""

import requests
import json

def test_analyze_email():
    """Test the analyze-email endpoint"""
    print("🔍 Testing analyze-email endpoint...")
    print("=" * 50)
    
    # Test data
    test_data = {
        'email_id': 'test_email_id',
        'type': 'summary'
    }
    
    try:
        # Test the endpoint
        response = requests.post(
            'http://localhost:5004/api/analyze-email',
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Text: {response.text[:500]}")
        
        # Check if it's a redirect to login
        if response.status_code == 200 and 'login' in response.text.lower():
            print("⚠️  Response is redirecting to login page (authentication required)")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_ai_service_directly():
    """Test the AI service directly"""
    print("\n🔍 Testing AI service directly...")
    print("=" * 50)
    
    try:
        from ai_service import HybridAIService
        
        ai_service = HybridAIService()
        print("✅ AI service initialized")
        
        # Test with a simple email
        test_email = "This is a test email for analysis."
        test_subject = "Test Subject"
        test_sender = "test@example.com"
        
        print("🔍 Testing generate_email_summary...")
        result = ai_service.generate_email_summary(test_email, test_subject, test_sender)
        print(f"Result: {result}")
        
        if result.get('success'):
            print("✅ AI service is working correctly")
        else:
            print(f"❌ AI service failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ AI service test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analyze_email()
    test_ai_service_directly() 