#!/usr/bin/env python3
"""
Production script to fix subscription activation issues after successful payment.
This should be run on the Digital Ocean server where the app is deployed.
"""

import os
import sys
from datetime import datetime, timedelta

# Force PostgreSQL mode for production
os.environ['DATABASE_TYPE'] = 'postgresql'

def fix_production_subscription():
    """Fix subscription activation for users who paid but aren't showing as Pro"""
    
    print("🔧 PRODUCTION: Fixing subscription activation issues...")
    print("🌐 Environment: Digital Ocean Production")
    print("💾 Database: PostgreSQL")
    
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
        
        # Mask sensitive info in logs
        masked_config = {k: v if k != 'password' else '*' * 8 for k, v in pg_config.items()}
        print(f"🔧 PostgreSQL Config: {masked_config}")
        
        db_manager = PGDatabaseManager(pg_config)
        user_model = PGUser(db_manager)
        plan_model = PGSubscriptionPlan(db_manager)
        payment_model = PGPaymentRecord(db_manager)
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Target user (lawalmoruf@gmail.com - User ID 1)
    user_id = 1
    user_email = 'lawalmoruf@gmail.com'
    
    print(f"\n🔍 Checking user: {user_email} (ID: {user_id})")
    print("=" * 60)
    
    # Check current user status
    try:
        user = user_model.get_user_by_id(user_id)
        if not user:
            print(f"❌ User {user_id} not found!")
            return False
        
        print(f"📧 Email: {user['email']}")
        print(f"📋 Current Plan: {user.get('subscription_plan', 'free')}")
        print(f"📊 Status: {user.get('subscription_status', 'inactive')}")
        print(f"📅 Expires: {user.get('subscription_expires', 'N/A')}")
        
        # Check payment history
        print(f"\n💳 Payment History:")
        payments = payment_model.get_user_payments(user_id)
        
        if not payments:
            print("❌ No payments found!")
            return False
        
        print(f"Found {len(payments)} payments:")
        
        recent_successful_payment = None
        for i, payment in enumerate(payments, 1):
            print(f"  {i}. ID: {payment['id']}")
            print(f"     Reference: {payment.get('stripe_payment_intent_id', 'N/A')}")
            print(f"     Amount: {payment['amount']} {payment['currency'].upper()}")
            print(f"     Plan: {payment['plan_name']}")
            print(f"     Status: {payment['status']}")
            print(f"     Date: {payment['created_at']}")
            print(f"     Method: {payment.get('payment_method', 'N/A')}")
            
            if payment['status'] == 'completed' and payment['plan_name'] in ['pro', 'enterprise']:
                recent_successful_payment = payment
            print()
        
        if not recent_successful_payment:
            print("❌ No successful Pro/Enterprise payments found!")
            return False
        
        print(f"✅ Found successful payment for {recent_successful_payment['plan_name']} plan")
        print(f"   Reference: {recent_successful_payment.get('stripe_payment_intent_id')}")
        print(f"   Amount: {recent_successful_payment['amount']} {recent_successful_payment['currency'].upper()}")
        
        # Check if subscription needs to be activated
        current_plan = user.get('subscription_plan', 'free')
        target_plan = recent_successful_payment['plan_name']
        
        if current_plan == target_plan:
            print(f"✅ User already has {target_plan} subscription activated!")
            return True
        
        print(f"\n🔧 Activating {target_plan} subscription...")
        print(f"   Current: {current_plan} → Target: {target_plan}")
        
        # Calculate subscription end date
        billing_period = recent_successful_payment.get('billing_period', 'monthly')
        if billing_period == 'yearly':
            end_date = datetime.now() + timedelta(days=365)
        else:
            end_date = datetime.now() + timedelta(days=30)
        
        print(f"   End Date: {end_date}")
        
        # Update subscription
        success = user_model.update_subscription(
            user_id=user_id,
            plan_name=target_plan,
            stripe_customer_id=recent_successful_payment.get('stripe_payment_intent_id'),
            expires_at=end_date
        )
        
        if success:
            print(f"✅ Subscription updated successfully!")
            
            # Verify the update
            updated_user = user_model.get_user_by_id(user_id)
            print(f"\n📊 Updated Status:")
            print(f"   Plan: {updated_user.get('subscription_plan', 'free')}")
            print(f"   Status: {updated_user.get('subscription_status', 'inactive')}")
            print(f"   Expires: {updated_user.get('subscription_expires', 'N/A')}")
            
            # Check billing history
            print(f"\n💳 Billing History Check:")
            all_payments = payment_model.get_user_payments(user_id)
            print(f"   Total payments in database: {len(all_payments)}")
            
            completed_payments = [p for p in all_payments if p['status'] == 'completed']
            print(f"   Completed payments: {len(completed_payments)}")
            
            return True
        else:
            print(f"❌ Failed to update subscription!")
            return False
            
    except Exception as e:
        print(f"❌ Error in subscription fix: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_production_users():
    """Check all users in production database"""
    print("\n" + "=" * 60)
    print("🔍 PRODUCTION: CHECKING ALL USERS")
    print("=" * 60)
    
    try:
        from models_postgresql import DatabaseManager as PGDatabaseManager
        
        pg_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 25060)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'sslmode': os.getenv('DB_SSLMODE', 'require')
        }
        
        db_manager = PGDatabaseManager(pg_config)
        
        # Get database connection for custom query
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Query to get all users with their payment status
        cursor.execute('''
            SELECT u.id, u.email, u.subscription_plan, u.subscription_status, u.subscription_expires,
                   COUNT(pr.id) as payment_count,
                   MAX(pr.created_at) as last_payment_date,
                   MAX(CASE WHEN pr.status = 'completed' THEN pr.plan_name END) as last_completed_plan,
                   MAX(CASE WHEN pr.status = 'completed' THEN pr.amount END) as last_payment_amount,
                   MAX(CASE WHEN pr.status = 'completed' THEN pr.currency END) as last_payment_currency
            FROM users u
            LEFT JOIN payment_records pr ON u.id = pr.user_id
            GROUP BY u.id, u.email, u.subscription_plan, u.subscription_status, u.subscription_expires
            ORDER BY u.id
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        print(f"Found {len(users)} users in production:")
        print()
        
        mismatched_users = []
        
        for user_data in users:
            user_id, email, sub_plan, sub_status, sub_expires, payment_count, last_payment_date, last_completed_plan, last_payment_amount, last_payment_currency = user_data
            
            print(f"👤 User {user_id}: {email}")
            print(f"   📋 Subscription: {sub_plan} ({sub_status})")
            print(f"   📅 Expires: {sub_expires}")
            print(f"   💳 Payments: {payment_count}")
            
            if last_payment_date:
                print(f"   💰 Last Payment: {last_completed_plan} - {last_payment_amount} {last_payment_currency} ({last_payment_date})")
            
            # Check for mismatches
            if last_completed_plan and last_completed_plan != 'free' and sub_plan != last_completed_plan:
                print(f"   ⚠️ MISMATCH: Paid for {last_completed_plan} but subscription is {sub_plan}")
                mismatched_users.append({
                    'user_id': user_id,
                    'email': email,
                    'current_plan': sub_plan,
                    'paid_plan': last_completed_plan,
                    'payment_amount': last_payment_amount,
                    'payment_currency': last_payment_currency
                })
            else:
                print(f"   ✅ Subscription matches payment")
            
            print()
        
        print("=" * 60)
        print(f"📊 PRODUCTION SUMMARY:")
        print(f"   Total Users: {len(users)}")
        print(f"   Mismatched Subscriptions: {len(mismatched_users)}")
        
        if mismatched_users:
            print(f"\n⚠️ Users with subscription mismatches:")
            for user in mismatched_users:
                print(f"   - {user['email']}: Paid {user['payment_amount']} {user['payment_currency']} for {user['paid_plan']}, but has {user['current_plan']}")
        
        return mismatched_users
        
    except Exception as e:
        print(f"❌ Error checking production users: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    print("🚀 PRODUCTION Subscription Fix Script")
    print("🌐 Digital Ocean Production Environment")
    print("=" * 60)
    
    # Check environment variables
    required_env_vars = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("🔧 Make sure you're running this on the production server with proper env vars")
        sys.exit(1)
    
    print("✅ All required environment variables present")
    
    # Check all users first
    mismatched_users = check_production_users()
    
    # Fix subscription
    success = fix_production_subscription()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 PRODUCTION: Subscription fixed successfully!")
        print("✅ User should now see Pro subscription in UI")
        print("✅ Billing history should be visible")
        print("✅ Session data will be updated on next login")
    else:
        print("❌ PRODUCTION: Failed to fix subscription!")
        print("🔍 Check the logs above for details")
    
    print("\n📋 Next Steps:")
    print("1. User should refresh browser or log out/in")
    print("2. Check /account/subscription shows Pro plan")
    print("3. Verify top-right corner shows 'Pro'")
    print("4. Test billing history is displayed")
    print("5. Verify Pro features are accessible") 