#!/usr/bin/env python3
"""
Script to check OpenAI API status and quota
"""

import os
import requests
from openai import OpenAI

def check_openai_status():
    """Check OpenAI API status and quota"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not found")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Try a simple API call to check status
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("✅ OpenAI API is working correctly")
        print(f"✅ Model: {response.model}")
        print(f"✅ Usage: {response.usage}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")
        
        # Check for specific error types
        if "quota" in str(e).lower() or "429" in str(e):
            print("\n🔧 Solutions:")
            print("1. Check your OpenAI billing at: https://platform.openai.com/account/billing")
            print("2. Upgrade your plan if needed")
            print("3. Wait for quota reset (usually monthly)")
            print("4. Use a different API key")
        
        elif "invalid" in str(e).lower() or "401" in str(e):
            print("\n🔧 Solutions:")
            print("1. Check if your API key is correct")
            print("2. Generate a new API key at: https://platform.openai.com/api-keys")
            print("3. Make sure the API key has the necessary permissions")
        
        return False

def check_usage():
    """Check API usage (if available)"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        return
    
    try:
        # Note: OpenAI doesn't provide a direct usage API endpoint
        # This is a placeholder for future implementation
        print("\n📊 Usage Information:")
        print("To check detailed usage, visit: https://platform.openai.com/usage")
        print("Note: Detailed usage requires OpenAI Pro plan or higher")
        
    except Exception as e:
        print(f"Could not retrieve usage info: {e}")

if __name__ == "__main__":
    print("🔍 Checking OpenAI API Status...")
    print("=" * 40)
    
    success = check_openai_status()
    check_usage()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Your OpenAI API is ready to use!")
    else:
        print("⚠️  Please fix the API issues before using the email assistant") 