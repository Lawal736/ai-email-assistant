#!/usr/bin/env python3
"""
Manual Payment Fix Script
This script allows manual verification and processing of Paystack payments 
when webhooks fail or payment records are missing.
"""

import os
import sys
from datetime import datetime, timedelta
import requests
import json

# Force PostgreSQL mode for production
os.environ['DATABASE_TYPE'] = 'postgresql'

def verify_paystack_payment(reference):
    """Verify payment with Paystack API"""
    try:
        paystack_secret = os.getenv('PAYSTACK_SECRET_KEY')
        if not paystack_secret:
            print("❌ PAYSTACK_SECRET_KEY not found in environment")
            return None
        
        headers = {
            'Authorization': f'Bearer {paystack_secret}',
            'Content-Type': 'application/json'
        }
        
        url = f'https://api.paystack.co/transaction/verify/{reference}'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Paystack API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error verifying payment: {e}")
        return None

def manual_fix_payment(reference):
    """Manually fix a payment that wasn't processed by webhooks"""
    
    print(f"🔧 MANUAL FIX: Processing payment {reference}...")
    
    try:
        # Import PostgreSQL models directly
        from models_postgresql import DatabaseManager as PGDatabaseManager, User as PGUser, SubscriptionPlan as PGSubscriptionPlan, PaymentRecord as PGPaymentRecord
        
        # Use PostgreSQL configuration from environment
        pg_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 25060)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'sslmode': os.getenv('DB_SSLMODE', 'require')
        }
        
        print(f"🔧 PostgreSQL Database: {pg_config['host']}:{pg_config['port']}")
        
        db_manager = PGDatabaseManager(pg_config)
        user_model = PGUser(db_manager)
        plan_model = PGSubscriptionPlan(db_manager)
        payment_model = PGPaymentRecord(db_manager)
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

    # Step 1: Verify payment with Paystack
    print(f"\n🔍 Step 1: Verifying payment with Paystack...")
    verification_result = verify_paystack_payment(reference)
    
    if not verification_result:
        print("❌ Payment verification failed")
        return False
    
    if not verification_result.get('status'):
        print(f"❌ Paystack verification failed: {verification_result}")
        return False
    
    data = verification_result.get('data', {})
    if data.get('status') != 'success':
        print(f"❌ Payment was not successful: {data.get('status')}")
        return False
    
    print("✅ Payment verified successfully with Paystack")
    
    # Step 2: Extract payment details
    print(f"\n🔍 Step 2: Extracting payment details...")
    
    amount = float(data.get('amount', 0)) / 100  # Paystack amounts are in kobo
    currency = data.get('currency', 'NGN')
    customer_email = data.get('customer', {}).get('email', '')
    metadata = data.get('metadata', {})
    
    print(f"💰 Amount: {amount} {currency}")
    print(f"📧 Customer: {customer_email}")
    print(f"📋 Metadata: {metadata}")
    
    # Extract subscription details from metadata
    user_id = metadata.get('user_id')
    plan_name = metadata.get('plan_name')
    billing_period = metadata.get('billing_period', 'monthly')
    
    if not user_id:
        # Try to find user by email
        user = user_model.get_user_by_email(customer_email)
        if user:
            user_id = user['id']
            print(f"🔍 Found user by email: {customer_email} -> User ID: {user_id}")
        else:
            print(f"❌ Could not find user for email: {customer_email}")
            return False
    
    if not plan_name:
        # Infer plan from amount (assuming Nigerian prices)
        if amount >= 15000:  # Enterprise monthly
            plan_name = 'enterprise'
        elif amount >= 5000:  # Pro monthly  
            plan_name = 'pro'
        else:
            print(f"❌ Could not determine plan from amount: {amount}")
            return False
        print(f"🔍 Inferred plan from amount: {plan_name}")
    
    print(f"👤 User ID: {user_id}")
    print(f"📋 Plan: {plan_name}")
    print(f"🗓️ Billing: {billing_period}")
    
    # Step 3: Check if payment already exists
    print(f"\n🔍 Step 3: Checking for existing payment record...")
    existing_payment = payment_model.get_payment_by_reference(reference)
    if existing_payment:
        print("⚠️ Payment record already exists in database")
        print(f"   Status: {existing_payment.get('status')}")
        print(f"   Plan: {existing_payment.get('plan_name')}")
        
        if existing_payment.get('status') == 'completed':
            print("✅ Payment already completed, checking subscription status...")
            # Still try to activate subscription in case that failed
        else:
            print("🔧 Updating existing payment to completed...")
            payment_model.update_payment_status(reference, 'completed')
    else:
        # Step 4: Create payment record
        print(f"\n📝 Step 4: Creating payment record...")
        try:
            payment_id = payment_model.create_payment_record(
                user_id=user_id,
                stripe_payment_intent_id=reference,
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
    
    # Step 5: Activate subscription
    print(f"\n🔧 Step 5: Activating subscription...")
    
    # Calculate subscription end date
    if billing_period == 'yearly':
        end_date = datetime.now() + timedelta(days=365)
    else:
        end_date = datetime.now() + timedelta(days=30)
    
    print(f"📅 Subscription end date: {end_date}")
    
    # Update subscription
    success = user_model.update_subscription(
        user_id=user_id,
        plan_name=plan_name,
        stripe_customer_id=reference,
        expires_at=end_date
    )
    
    if success:
        print(f"✅ Subscription activated successfully!")
        
        # Verify the update
        updated_user = user_model.get_user_by_id(user_id)
        print(f"\n📊 Final Status:")
        print(f"   User: {updated_user.get('email')}")
        print(f"   Plan: {updated_user.get('subscription_plan')}")
        print(f"   Status: {updated_user.get('subscription_status')}")
        print(f"   Expires: {updated_user.get('subscription_expires')}")
        
        return True
    else:
        print(f"❌ Failed to activate subscription!")
        return False

def find_recent_paystack_payments(email):
    """Find recent payments for an email in Paystack"""
    try:
        paystack_secret = os.getenv('PAYSTACK_SECRET_KEY')
        if not paystack_secret:
            print("❌ PAYSTACK_SECRET_KEY not found")
            return []
        
        headers = {
            'Authorization': f'Bearer {paystack_secret}',
            'Content-Type': 'application/json'
        }
        
        # Get recent transactions
        url = 'https://api.paystack.co/transaction'
        params = {
            'customer': email,
            'status': 'success',
            'perPage': 10
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('data', [])
            
            print(f"🔍 Found {len(transactions)} successful transactions for {email}:")
            
            for i, txn in enumerate(transactions, 1):
                amount = float(txn.get('amount', 0)) / 100
                currency = txn.get('currency', 'NGN')
                reference = txn.get('reference', '')
                created_at = txn.get('created_at', '')
                
                print(f"  {i}. {reference}")
                print(f"     Amount: {amount} {currency}")
                print(f"     Date: {created_at}")
                print()
            
            return transactions
        else:
            print(f"❌ Paystack API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching transactions: {e}")
        return []

if __name__ == "__main__":
    print("🔧 MANUAL PAYMENT FIX SCRIPT")
    print("=" * 60)
    
    # Check environment variables
    required_env_vars = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'PAYSTACK_SECRET_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        sys.exit(1)
    
    # Check if reference provided as argument
    if len(sys.argv) > 1:
        reference = sys.argv[1]
        print(f"🔍 Processing payment reference: {reference}")
        
        success = manual_fix_payment(reference)
        
        if success:
            print("\n🎉 PAYMENT FIXED SUCCESSFULLY!")
            print("✅ User subscription should now be active")
            print("✅ Billing history should be visible")
        else:
            print("\n❌ FAILED TO FIX PAYMENT")
    else:
        # Interactive mode - find payments for user
        user_email = 'lawalmoruf@gmail.com'
        print(f"🔍 Looking for recent payments for: {user_email}")
        
        transactions = find_recent_paystack_payments(user_email)
        
        if transactions:
            print(f"\n📋 Found {len(transactions)} transactions. To fix a payment, run:")
            print(f"python3 manual_payment_fix.py <REFERENCE>")
            print(f"\nExample:")
            for txn in transactions[:3]:  # Show first 3
                ref = txn.get('reference', '')
                print(f"python3 manual_payment_fix.py {ref}")
        else:
            print("❌ No recent successful payments found")
            print("🔍 Please check:")
            print("1. Payment was actually successful in Paystack dashboard")
            print("2. Payment was made with this email address")
            print("3. PAYSTACK_SECRET_KEY is correct") 