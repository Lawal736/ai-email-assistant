#!/usr/bin/env python3
"""
Script to fix subscription activation issues after successful payment
"""

import os
import sys
from datetime import datetime, timedelta

def fix_subscription_activation():
    """Fix subscription activation for users who paid but aren't showing as Pro"""
    
    print("🔧 Fixing subscription activation issues...")
    
    # Initialize services with database detection
    try:
        # Check if we should use PostgreSQL
        database_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()
        
        if database_type == 'postgresql':
            # Import PostgreSQL models
            from models_postgresql import DatabaseManager as PGDatabaseManager, User as PGUser, SubscriptionPlan as PGSubscriptionPlan, PaymentRecord as PGPaymentRecord
            
            # Use PostgreSQL configuration
            pg_config = {
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT', 25060)),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'database': os.getenv('DB_NAME'),
                'sslmode': os.getenv('DB_SSLMODE', 'require')
            }
            
            print(f"🔧 Fix using PostgreSQL database: {pg_config['host']}:{pg_config['port']}")
            
            db_manager = PGDatabaseManager(pg_config)
            user_model = PGUser(db_manager)
            plan_model = PGSubscriptionPlan(db_manager)
            payment_model = PGPaymentRecord(db_manager)
        else:
            # Use SQLite (default)
            from models import DatabaseManager, User, SubscriptionPlan, PaymentRecord
            print("🔧 Fix using SQLite database")
            db_manager = DatabaseManager()
            user_model = User(db_manager)
            plan_model = SubscriptionPlan(db_manager)
            payment_model = PaymentRecord(db_manager)
            
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")
        # Fallback to SQLite if PostgreSQL fails
        try:
            print("🔄 Falling back to SQLite...")
            from models import DatabaseManager, User, SubscriptionPlan, PaymentRecord
            db_manager = DatabaseManager()
            user_model = User(db_manager)
            plan_model = SubscriptionPlan(db_manager)
            payment_model = PaymentRecord(db_manager)
            print("✅ SQLite fallback successful")
        except Exception as fallback_error:
            print(f"❌ SQLite fallback also failed: {fallback_error}")
            return False

    # Get the current user (lawalmoruf@gmail.com - User ID 1)
    user_id = 1
    user_email = 'lawalmoruf@gmail.com'
    
    print(f"\n🔍 Checking user: {user_email} (ID: {user_id})")
    print("=" * 60)
    
    # Check current user status
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
    try:
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
        print(f"❌ Error updating subscription: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_all_users_subscription_status():
    """Check subscription status for all users"""
    print("\n" + "=" * 60)
    print("🔍 CHECKING ALL USERS SUBSCRIPTION STATUS")
    print("=" * 60)
    
    try:
        # Use the same database detection logic
        database_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()
        
        if database_type == 'postgresql':
            from models_postgresql import DatabaseManager as PGDatabaseManager, User as PGUser, PaymentRecord as PGPaymentRecord
            
            pg_config = {
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT', 25060)),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'database': os.getenv('DB_NAME'),
                'sslmode': os.getenv('DB_SSLMODE', 'require')
            }
            
            db_manager = PGDatabaseManager(pg_config)
            user_model = PGUser(db_manager)
            payment_model = PGPaymentRecord(db_manager)
        else:
            from models import DatabaseManager, User, PaymentRecord
            db_manager = DatabaseManager()
            user_model = User(db_manager)
            payment_model = PaymentRecord(db_manager)
        
        # Get database connection for custom query
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Query to get all users with their payment status
        if database_type == 'postgresql':
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
        else:
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
        
        print(f"Found {len(users)} users:")
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
        print(f"📊 SUMMARY:")
        print(f"   Total Users: {len(users)}")
        print(f"   Mismatched Subscriptions: {len(mismatched_users)}")
        
        if mismatched_users:
            print(f"\n⚠️ Users with subscription mismatches:")
            for user in mismatched_users:
                print(f"   - {user['email']}: Paid {user['payment_amount']} {user['payment_currency']} for {user['paid_plan']}, but has {user['current_plan']}")
        
        return mismatched_users
        
    except Exception as e:
        print(f"❌ Error checking users: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    print("🔧 Subscription Activation Fix Script")
    print("=" * 60)
    
    # First check all users to see the full picture
    mismatched_users = check_all_users_subscription_status()
    
    # Fix the main user's subscription
    success = fix_subscription_activation()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Subscription fixed successfully!")
        print("✅ User should now see Pro subscription in UI")
        print("✅ Billing history should be visible")
    else:
        print("❌ Failed to fix subscription!")
        print("🔍 Check the logs above for details")
    
    print("\n📋 Next Steps:")
    print("1. Refresh the browser and check /account/subscription")
    print("2. Check that user shows 'Pro' in top-right corner")
    print("3. Verify billing history is displayed")
    print("4. Test Pro features work properly") 