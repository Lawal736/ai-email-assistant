#!/usr/bin/env python3
"""
Setup script for Paystack webhook configuration
This script helps configure webhooks for automatic subscription activation
"""

import os
import requests
import json

def setup_paystack_webhook():
    """Setup Paystack webhook for automatic subscription activation"""
    print("🔧 Setting up Paystack webhook for automatic subscription activation...")
    
    # Get Paystack secret key
    paystack_secret_key = os.getenv('PAYSTACK_SECRET_KEY')
    if not paystack_secret_key:
        print("❌ PAYSTACK_SECRET_KEY not found in environment variables")
        print("   Please add your Paystack secret key to your .env file")
        return False
    
    # Webhook URL (update this with your actual domain in production)
    webhook_url = "https://your-domain.com/payment/webhook"  # Replace with your actual domain
    
    print(f"🔍 Webhook URL: {webhook_url}")
    print("⚠️  IMPORTANT: Update the webhook_url variable with your actual domain")
    
    # Events to listen for
    events = [
        "charge.success",
        "subscription.create", 
        "subscription.disable"
    ]
    
    print(f"🔍 Events to listen for: {', '.join(events)}")
    
    # Paystack API endpoint
    url = "https://api.paystack.co/webhook"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {paystack_secret_key}",
        "Content-Type": "application/json"
    }
    
    # Data
    data = {
        "url": webhook_url,
        "events": events
    }
    
    print("🔍 Creating webhook...")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status'):
                webhook_data = result.get('data', {})
                print(f"✅ Webhook created successfully!")
                print(f"   Webhook ID: {webhook_data.get('id')}")
                print(f"   URL: {webhook_data.get('url')}")
                print(f"   Events: {', '.join(webhook_data.get('events', []))}")
                print(f"   Status: {webhook_data.get('status')}")
                return True
            else:
                print(f"❌ Failed to create webhook: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating webhook: {e}")
        return False

def list_existing_webhooks():
    """List existing Paystack webhooks"""
    print("🔍 Listing existing webhooks...")
    
    paystack_secret_key = os.getenv('PAYSTACK_SECRET_KEY')
    if not paystack_secret_key:
        print("❌ PAYSTACK_SECRET_KEY not found")
        return False
    
    url = "https://api.paystack.co/webhook"
    headers = {
        "Authorization": f"Bearer {paystack_secret_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status'):
                webhooks = result.get('data', [])
                if webhooks:
                    print(f"✅ Found {len(webhooks)} webhook(s):")
                    for webhook in webhooks:
                        print(f"   ID: {webhook.get('id')}")
                        print(f"   URL: {webhook.get('url')}")
                        print(f"   Events: {', '.join(webhook.get('events', []))}")
                        print(f"   Status: {webhook.get('status')}")
                        print("   ---")
                else:
                    print("ℹ️  No webhooks found")
                return True
            else:
                print(f"❌ Failed to list webhooks: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error listing webhooks: {e}")
        return False

def delete_webhook(webhook_id):
    """Delete a specific webhook"""
    print(f"🗑️  Deleting webhook {webhook_id}...")
    
    paystack_secret_key = os.getenv('PAYSTACK_SECRET_KEY')
    if not paystack_secret_key:
        print("❌ PAYSTACK_SECRET_KEY not found")
        return False
    
    url = f"https://api.paystack.co/webhook/{webhook_id}"
    headers = {
        "Authorization": f"Bearer {paystack_secret_key}"
    }
    
    try:
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status'):
                print(f"✅ Webhook {webhook_id} deleted successfully")
                return True
            else:
                print(f"❌ Failed to delete webhook: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False

def test_webhook():
    """Test webhook endpoint"""
    print("🧪 Testing webhook endpoint...")
    
    # Test webhook URL (update with your actual domain)
    test_url = "http://localhost:5001/payment/webhook"  # For local testing
    
    print(f"🔍 Testing URL: {test_url}")
    
    # Sample webhook payload
    test_payload = {
        "event": "charge.success",
        "data": {
            "reference": "test_reference_123",
            "metadata": {
                "user_id": 1,
                "plan_name": "pro",
                "billing_period": "monthly",
                "currency": "NGN"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Paystack-Signature": "test_signature"  # In production, this would be a real signature
    }
    
    try:
        response = requests.post(test_url, headers=headers, json=test_payload)
        
        print(f"🔍 Response Status: {response.status_code}")
        print(f"🔍 Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook endpoint is working")
            return True
        else:
            print("❌ Webhook endpoint returned an error")
            return False
            
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Paystack Webhook Setup")
    print("=" * 50)
    
    print("\n📋 Instructions for Automatic Subscription Activation:")
    print("1. Update the webhook_url in this script with your actual domain")
    print("2. Run this script to create the webhook in Paystack")
    print("3. Ensure your server is accessible from the internet")
    print("4. Test the webhook with a payment")
    
    print("\n🔧 Current setup:")
    setup_paystack_webhook()

if __name__ == "__main__":
    main() 