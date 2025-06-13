#!/usr/bin/env python3
"""
Setup script for AI Email Assistant
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def create_env_file():
    """Create .env file from template"""
    env_file = Path('.env')
    if env_file.exists():
        print("⚠️  .env file already exists, skipping...")
        return True
    
    print("📝 Creating .env file...")
    env_content = """# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_SECRET_KEY=your_flask_secret_key_here
FLASK_ENV=development

# Gmail API Configuration
# Note: You'll need to download credentials.json from Google Cloud Console
# and place it in the project root directory
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ .env file created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'flask',
        'google-auth',
        'google-auth-oauthlib',
        'google-auth-httplib2',
        'google-api-python-client',
        'openai',
        'python-dotenv',
        'flask-cors',
        'requests',
        'python-dateutil',
        'email-validator'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("📦 Installing missing packages...")
        return run_command(f"pip install {' '.join(missing_packages)}", "Installing dependencies")
    else:
        print("✅ All dependencies are installed")
        return True

def check_credentials():
    """Check if Gmail credentials file exists"""
    creds_file = Path('credentials.json')
    if not creds_file.exists():
        print("⚠️  credentials.json not found!")
        print("📋 Please follow these steps:")
        print("   1. Go to https://console.cloud.google.com/")
        print("   2. Create a new project or select existing one")
        print("   3. Enable the Gmail API")
        print("   4. Create OAuth 2.0 credentials")
        print("   5. Download credentials.json and place it in this directory")
        return False
    else:
        print("✅ Gmail credentials found")
        return True

def main():
    """Main setup function"""
    print("🚀 Setting up AI Email Assistant...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install dependencies
    if not check_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        print("❌ Failed to create .env file")
        sys.exit(1)
    
    # Check credentials
    check_credentials()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("   1. Edit .env file and add your OpenAI API key")
    print("   2. Download credentials.json from Google Cloud Console")
    print("   3. Run: python app.py")
    print("   4. Open http://localhost:5000 in your browser")
    print("\n📚 For more information, see README.md")

if __name__ == "__main__":
    main() 