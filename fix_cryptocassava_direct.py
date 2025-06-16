#!/usr/bin/env python3
"""
Script to directly fix the database for cryptocassava@gmail.com
by manually creating the payment record and updating the subscription.
"""

import os
import sys
from datetime import datetime, timedelta
from models import DatabaseManager, User, PaymentRecord

def fix_cryptocassava_direct():
    """Directly fix the database for cryptocassava@gmail.com"""
    
    print("🔧 Directly fixing database for cryptocassava@gmail.com...")
    
    # Initialize services
    db_manager = DatabaseManager()
    user_model = User(db_manager)
    payment_model = PaymentRecord(db_manager)
    
    # Get user by email
    user = user_model.get_user_by_email('cryptocassava@gmail.com')
    if not user:
        print("❌ User cryptocassava@gmail.com not found!")
        return False
    
    user_id = user['id']
    print(f"✅ Found user: {user['email']} (ID: {user_id})")
    print(f"📊 Current subscription: {user['subscription_plan']}")
    
    # Based on the logs, we know the payment details
    paystack_reference = "sub_3_pro_1749925850_fee850"
    amount = 15324.66  # From the logs
    currency = "NGN"
    plan_name = "pro"
    billing_period = "monthly"
    
    print(f"💰 Payment details:")
    print(f"   Reference: {paystack_reference}")
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
    
    # Update subscription directly
    print("🔧 Updating subscription directly...")
    
    # Calculate subscription end date
    end_date = datetime.now() + timedelta(days=30)
    
    try:
        success = user_model.update_subscription(
            user_id, 
            plan_name, 
            paystack_reference,  # Store payment reference
            end_date
        )
        
        if success:
            print("✅ Subscription updated successfully!")
            
            # Verify the update
            updated_user = user_model.get_user_by_id(user_id)
            print(f"📊 Updated subscription: {updated_user['subscription_plan']}")
            print(f"📅 Expires: {updated_user['subscription_expires']}")
            
            return True
        else:
            print("❌ Failed to update subscription!")
            return False
            
    except Exception as e:
        print(f"❌ Error updating subscription: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Direct Database Fix Script")
    print("=" * 40)
    
    success = fix_cryptocassava_direct()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Database fixed successfully!")
    else:
        print("❌ Failed to fix database!") 