#!/usr/bin/env python3
"""
Test script to verify AI Email Assistant setup
"""

import os
import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    modules = [
        'flask',
        'google.auth',
        'google_auth_oauthlib',
        'googleapiclient',
        'openai',
        'dotenv'
    ]
    
    failed_imports = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    return len(failed_imports) == 0

def test_files():
    """Test if required files exist"""
    print("\n📁 Testing required files...")
    
    required_files = [
        'app.py',
        'gmail_service.py',
        'ai_service.py',
        'email_processor.py',
        'requirements.txt',
        'README.md'
    ]
    
    missing_files = []
    
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            missing_files.append(file)
    
    return len(missing_files) == 0

def test_config():
    """Test configuration files"""
    print("\n⚙️  Testing configuration...")
    
    # Test .env file
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file exists")
        
        # Check if OpenAI key is set
        with open('.env', 'r') as f:
            content = f.read()
            if 'your_openai_api_key_here' in content:
                print("⚠️  OpenAI API key not configured")
            else:
                print("✅ OpenAI API key configured")
    else:
        print("❌ .env file missing")
        return False
    
    # Test credentials.json
    creds_file = Path('credentials.json')
    if creds_file.exists():
        print("✅ credentials.json exists")
    else:
        print("❌ credentials.json missing")
        return False
    
    return True

def test_services():
    """Test service initialization"""
    print("\n🔧 Testing services...")
    
    try:
        from gmail_service import GmailService
        print("✅ GmailService imported")
    except Exception as e:
        print(f"❌ GmailService import failed: {e}")
        return False
    
    try:
        from email_processor import EmailProcessor
        print("✅ EmailProcessor imported")
    except Exception as e:
        print(f"❌ EmailProcessor import failed: {e}")
        return False
    
    try:
        from ai_service import AIService
        print("✅ AIService imported")
    except Exception as e:
        print(f"❌ AIService import failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🧪 AI Email Assistant Setup Test")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Files", test_files),
        ("Configuration", test_config),
        ("Services", test_services)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed! Your setup is ready.")
        print("\n🚀 You can now run: python app.py")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        print("\n📚 See SETUP_GUIDE.md for detailed setup instructions.")

if __name__ == "__main__":
    main() 