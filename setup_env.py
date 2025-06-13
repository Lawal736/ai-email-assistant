#!/usr/bin/env python3
"""
Script to set up environment variables for the AI Email Assistant
"""

import os
import subprocess
import sys
import getpass

def setup_environment():
    """Set up environment variables"""
    print("🔧 Setting up environment variables...")
    
    # Prompt for OpenAI API Key
    print("\n📝 Please enter your OpenAI API Key:")
    print("   (You can get this from https://platform.openai.com/api-keys)")
    openai_key = getpass.getpass("OpenAI API Key: ").strip()
    
    if not openai_key:
        print("❌ OpenAI API Key is required!")
        return False
    
    # Set environment variables for current session
    os.environ['OPENAI_API_KEY'] = openai_key
    os.environ['FLASK_SECRET_KEY'] = 'your_flask_secret_key_here_change_this_in_production'
    os.environ['FLASK_ENV'] = 'development'
    
    print("✅ Environment variables set for current session")
    print(f"✅ OPENAI_API_KEY: {openai_key[:20]}...")
    
    return True

def create_env_file():
    """Create .env file"""
    print("\n📝 Creating .env file...")
    
    # Prompt for OpenAI API Key again for .env file
    print("Please enter your OpenAI API Key for the .env file:")
    openai_key = getpass.getpass("OpenAI API Key: ").strip()
    
    if not openai_key:
        print("❌ OpenAI API Key is required!")
        return False
    
    env_content = f"""# OpenAI API Configuration
OPENAI_API_KEY={openai_key}

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here_change_this_in_production
FLASK_ENV=development

# Gmail API Configuration
# Note: credentials.json should be placed in project root directory
# You can also set GOOGLE_CREDENTIALS as an environment variable for deployment

# Optional: Custom port (default is 5001)
PORT=5001

# Optional: Custom host (default is 0.0.0.0)
HOST=0.0.0.0
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ .env file created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def test_openai():
    """Test OpenAI API connection"""
    print("\n🧪 Testing OpenAI API...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("✅ OpenAI API test successful!")
        print(f"✅ Model: {response.model}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 AI Email Assistant - Environment Setup")
    print("=" * 50)
    
    # Set up environment variables
    if not setup_environment():
        print("❌ Failed to set up environment variables")
        return False
    
    # Create .env file
    if not create_env_file():
        print("❌ Failed to create .env file")
        return False
    
    # Test OpenAI API
    if not test_openai():
        print("❌ OpenAI API test failed")
        print("\n🔧 Troubleshooting:")
        print("1. Check if the API key is correct")
        print("2. Check your OpenAI billing and quota")
        print("3. Try generating a new API key")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Environment setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Run: python3 app.py")
    print("2. Open: http://localhost:5001")
    print("3. Connect your Gmail account")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 