#!/usr/bin/env python3
"""
API Key Setup Helper Script
This script helps you get the missing API keys for your AI Email Assistant.
"""

import webbrowser
import os

def open_url(url, description):
    """Open URL in browser and provide instructions"""
    print(f"\n🔗 {description}")
    print(f"   Opening: {url}")
    print("   Instructions:")
    print("   1. Sign up/Login to the service")
    print("   2. Navigate to API keys section")
    print("   3. Create a new API key")
    print("   4. Copy the key and add it to your .env file")
    
    response = input(f"\n   Open {description} in browser? (y/N): ")
    if response.lower() == 'y':
        webbrowser.open(url)

def main():
    print("🚀 AI Email Assistant - API Key Setup Helper")
    print("=" * 60)
    print("\nThis script will help you get the missing API keys for your app.")
    print("\n📋 REQUIRED API Keys (you need these):")
    print("   1. Anthropic API Key (for Claude AI)")
    print("   2. OpenAI API Key (for GPT-4 fallback)")
    print("   3. Paystack Secret Key (for payments)")
    print("   4. Paystack Public Key (for payments)")
    
    print("\n📋 OPTIONAL API Keys (you can skip these):")
    print("   5. Stripe Keys (alternative payment method)")
    print("   6. Infura URL (for cryptocurrency payments)")
    
    print("\n" + "=" * 60)
    
    # Required API Keys
    print("\n🔑 REQUIRED API KEYS:")
    
    # 1. Anthropic
    open_url(
        "https://console.anthropic.com/",
        "Anthropic Console (Claude API)"
    )
    
    # 2. OpenAI
    open_url(
        "https://platform.openai.com/api-keys",
        "OpenAI API Keys"
    )
    
    # 3. Paystack
    open_url(
        "https://dashboard.paystack.com/#/settings/developer",
        "Paystack Developer Settings"
    )
    
    print("\n" + "=" * 60)
    print("\n🔑 OPTIONAL API KEYS:")
    
    # 4. Stripe (Optional)
    open_url(
        "https://dashboard.stripe.com/apikeys",
        "Stripe API Keys (Optional)"
    )
    
    # 5. Infura (Optional)
    open_url(
        "https://infura.io/",
        "Infura (for crypto payments - Optional)"
    )
    
    print("\n" + "=" * 60)
    print("\n📝 NEXT STEPS:")
    print("1. Copy the 'env_complete.txt' file to '.env'")
    print("2. Replace [REQUIRED] placeholders with your actual API keys")
    print("3. Leave [OPTIONAL] values empty if you don't need them")
    print("4. Your Google OAuth credentials are already filled in!")
    
    print("\n💡 TIP: You can also run the setup script:")
    print("   python3 setup_deployment_env.py")
    
    print("\n✅ Your app will work with just the REQUIRED keys!")
    print("   The OPTIONAL keys are for additional features.")

if __name__ == "__main__":
    main() 