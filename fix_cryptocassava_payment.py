#!/usr/bin/env python3
"""
Script to manually fix the payment record and subscription for cryptocassava@gmail.com
Based on the Paystack transaction reference from the logs.
"""

import os
import sys
from datetime import datetime, timedelta
from models import DatabaseManager, User, PaymentRecord
from payment_service import PaymentService

def fix_cryptocassava_payment():
    """Fix payment record and subscription for cryptocassava@gmail.com"""
    
    print("🔧 Fixing payment record and subscription for cryptocassava@gmail.com...")
    
    # Initialize services
    db_manager = DatabaseManager()
    user_model = User(db_manager)
    payment_model = PaymentRecord(db_manager)
    payment_service = PaymentService()
    
    # Get user by email
    user = user_model.get_user_by_email('cryptocassava@gmail.com')
    if not user:
        print("❌ User cryptocassava@gmail.com not found!")
        return False
    
    user_id = user['id']
    print(f"✅ Found user: {user['email']} (ID: {user_id})")
    print(f"📊 Current subscription: {user['subscription_plan']}")
    
    # Based on the logs, we know the Paystack transaction reference
    # From the logs: sub_3_pro_1749925850_fee850
    paystack_reference = "sub_3_pro_1749925850_fee850"
    
    print(f"🔍 Using Paystack reference: {paystack_reference}")
    
    # Verify the payment with Paystack
    print("🔍 Verifying payment with Paystack...")
    verification_result = payment_service.verify_paystack_transaction(paystack_reference)
    
    if not verification_result.get('status') or verification_result['data']['status'] != 'success':
        print(f"❌ Payment verification failed: {verification_result}")
        return False
    
    print("✅ Payment verified successfully!")
    
    data = verification_result['data']
    metadata = data.get('metadata', {})
    
    # Extract payment details
    amount = float(data['amount']) / 100  # Convert from kobo to Naira
    currency = data.get('currency', 'NGN')
    plan_name = metadata.get('plan_name', 'pro')
    billing_period = metadata.get('billing_period', 'monthly')
    
    print(f"💰 Payment details:")
    print(f"   Amount: {amount} {currency}")
    print(f"   Plan: {plan_name}")
    print(f"   Billing: {billing_period}")
    
    # Check if payment record already exists
    existing_payment = payment_model.get_payment_by_reference(paystack_reference)
    if existing_payment:
        print(f"⚠️ Payment record already exists: {existing_payment}")
    else:
        # Create payment record
        print("📝 Creating payment record...")
        try:
            payment_id = payment_model.create_payment_record(
                user_id=user_id,
                stripe_payment_intent_id=paystack_reference,
                amount=amount,
                plan_name=plan_name,
                billing_period=billing_period,
                status='completed',
                currency=currency,
                payment_method='paystack'
            )
            print(f"✅ Payment record created with ID: {payment_id}")
        except Exception as e:
            print(f"❌ Failed to create payment record: {e}")
            return False
    
    # Activate subscription
    print("🔧 Activating Pro subscription...")
    
    success = payment_service.activate_subscription(
        user_id=user_id,
        plan_name=plan_name,
        payment_method='paystack',
        payment_id=paystack_reference,
        billing_period=billing_period,
        currency=currency
    )
    
    if success:
        print("✅ Pro subscription activated successfully!")
        
        # Verify the update
        updated_user = user_model.get_user_by_id(user_id)
        print(f"📊 Updated subscription: {updated_user['subscription_plan']}")
        print(f"📅 Expires: {updated_user['subscription_expires']}")
        
        return True
    else:
        print("❌ Failed to activate subscription!")
        return False

if __name__ == "__main__":
    print("🔧 Cryptocassava Payment Fix Script")
    print("=" * 40)
    
    success = fix_cryptocassava_payment()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Payment and subscription fixed successfully!")
    else:
        print("❌ Failed to fix payment and subscription!") 