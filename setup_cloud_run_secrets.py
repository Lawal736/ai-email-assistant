#!/usr/bin/env python3
"""
Script to set up Google Cloud Secret Manager values for AI Email Assistant
"""

import subprocess
import sys
import getpass

def run_command(command):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def set_secret_value(secret_name, value):
    """Set a secret value in Google Cloud Secret Manager"""
    command = f'echo "{value}" | gcloud secrets versions add {secret_name} --data-file=-'
    success, stdout, stderr = run_command(command)
    if success:
        print(f"✅ Successfully set {secret_name}")
    else:
        print(f"❌ Failed to set {secret_name}: {stderr}")
    return success

def main():
    print("🔐 Setting up Google Cloud Secret Manager values")
    print("=" * 50)
    
    secrets_to_set = {
        "anthropic-api-key": "ANTHROPIC_API_KEY",
        "openai-api-key": "OPENAI_API_KEY", 
        "paystack-secret-key": "PAYSTACK_SECRET_KEY",
        "paystack-public-key": "PAYSTACK_PUBLIC_KEY",
        "flask-secret-key": "SECRET_KEY"
    }
    
    print("\n📝 Please provide the following secret values:")
    print("(Press Enter to skip if you don't have the value yet)")
    
    for secret_name, env_var in secrets_to_set.items():
        print(f"\n🔑 {env_var} ({secret_name}):")
        value = getpass.getpass(f"Enter your {env_var} (input will be hidden): ")
        
        if value.strip():
            if set_secret_value(secret_name, value):
                print(f"   ✅ {env_var} set successfully")
            else:
                print(f"   ❌ Failed to set {env_var}")
        else:
            print(f"   ⏭️  Skipped {env_var}")
    
    print("\n" + "=" * 50)
    print("🎉 Secret setup complete!")
    print("\nNext steps:")
    print("1. If you skipped any secrets, add them later using:")
    print("   echo 'your-secret-value' | gcloud secrets versions add SECRET_NAME --data-file=-")
    print("2. Update your Cloud Run service with the environment variables")
    print("3. Test your application")

if __name__ == "__main__":
    main() 