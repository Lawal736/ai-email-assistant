#!/usr/bin/env python3
"""
Script to fix subscription issues for users who paid but didn't get their subscription activated.
This script will manually activate the Pro subscription based on their recent payments.
"""

import os
import sys
from datetime import datetime, timedelta
from models import DatabaseManager, User, PaymentRecord
from payment_service import PaymentService

def fix_user_subscription(email):
    """Fix subscription for a specific user"""
    
    print(f"🔧 Fixing subscription for {email}...")
    
    # Initialize services
    db_manager = DatabaseManager()
    user_model = User(db_manager)
    payment_model = PaymentRecord(db_manager)
    payment_service = PaymentService()
    
    # Get user by email
    user = user_model.get_user_by_email(email)
    if not user:
        print(f"❌ User {email} not found!")
        return False
    
    user_id = user['id']
    print(f"✅ Found user: {user['email']} (ID: {user_id})")
    print(f"📊 Current subscription: {user['subscription_plan']}")
    
    # Get recent payments
    payments = payment_model.get_payments_by_user(user_id)
    print(f"💰 Found {len(payments)} payments")
    
    # Find the most recent Pro payment
    recent_pro_payment = None
    for payment in payments:
        if payment['plan_name'] == 'pro' and payment['status'] == 'completed':
            recent_pro_payment = payment
            break
    
    if not recent_pro_payment:
        print(f"❌ No recent Pro payment found for {email}!")
        return False
    
    print(f"✅ Found Pro payment: {recent_pro_payment['stripe_payment_intent_id']}")
    print(f"   Amount: {recent_pro_payment['amount']} {recent_pro_payment['currency']}")
    print(f"   Date: {recent_pro_payment['created_at']}")
    
    # Check if subscription is already active
    if user['subscription_plan'] == 'pro':
        print(f"✅ Subscription is already Pro for {email}!")
        return True
    
    # Activate Pro subscription
    print(f"🔧 Activating Pro subscription for {email}...")
    
    success = payment_service.activate_subscription(
        user_id=user_id,
        plan_name='pro',
        payment_method=recent_pro_payment['payment_method'],
        payment_id=recent_pro_payment['stripe_payment_intent_id'],
        billing_period=recent_pro_payment['billing_period'],
        currency=recent_pro_payment['currency']
    )
    
    if success:
        print(f"✅ Pro subscription activated successfully for {email}!")
        
        # Verify the update
        updated_user = user_model.get_user_by_id(user_id)
        print(f"📊 Updated subscription: {updated_user['subscription_plan']}")
        print(f"📅 Expires: {updated_user['subscription_expires']}")
        
        return True
    else:
        print(f"❌ Failed to activate subscription for {email}!")
        return False

def list_all_users():
    """List all users and their subscription status"""
    
    print("\n👥 All Users and Subscription Status:")
    print("=" * 60)
    
    db_manager = DatabaseManager()
    user_model = User(db_manager)
    payment_model = PaymentRecord(db_manager)
    
    # Get all users (you might need to add a method to get all users)
    # For now, let's check the specific users we know about
    
    users_to_check = ['cryptocassava@gmail.com', 'lawalmoruf@gmail.com']
    
    for email in users_to_check:
        user = user_model.get_user_by_email(email)
        if user:
            payments = payment_model.get_payments_by_user(user['id'])
            recent_payment = None
            for payment in payments:
                if payment['status'] == 'completed':
                    recent_payment = payment
                    break
            
            print(f"📧 {email}")
            print(f"   ID: {user['id']}")
            print(f"   Subscription: {user['subscription_plan']}")
            print(f"   Status: {user['subscription_status']}")
            print(f"   Expires: {user['subscription_expires']}")
            if recent_payment:
                print(f"   Recent Payment: {recent_payment['plan_name']} - {recent_payment['amount']} {recent_payment['currency']}")
            print()

if __name__ == "__main__":
    print("🔧 Subscription Fix Script")
    print("=" * 40)
    
    # List current status
    list_all_users()
    
    # Fix cryptocassava@gmail.com
    success1 = fix_user_subscription('cryptocassava@gmail.com')
    
    # Fix lawalmoruf@gmail.com
    success2 = fix_user_subscription('lawalmoruf@gmail.com')
    
    print("\n" + "=" * 40)
    print("📊 Summary:")
    print(f"cryptocassava@gmail.com: {'✅ Fixed' if success1 else '❌ Failed'}")
    print(f"lawalmoruf@gmail.com: {'✅ Fixed' if success2 else '❌ Failed'}")
    
    if success1 and success2:
        print("\n🎉 All subscriptions fixed successfully!")
    else:
        print("\n⚠️ Some subscriptions could not be fixed. Check the logs above.") 