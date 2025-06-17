#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from payment_service import PaymentService

def test_subscription_activation():
    """Test the subscription activation process"""
    print("🔍 Testing subscription activation...")
    
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
            
            print(f"🔧 Test using PostgreSQL database: {pg_config['host']}:{pg_config['port']}")
            
            db_manager = PGDatabaseManager(pg_config)
            user_model = PGUser(db_manager)
            plan_model = PGSubscriptionPlan(db_manager)
            payment_model = PGPaymentRecord(db_manager)
        else:
            # Use SQLite (default)
            from models import DatabaseManager, User, SubscriptionPlan, PaymentRecord
            print("🔧 Test using SQLite database")
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
            return
    
    payment_service = PaymentService()
    payment_service.user_model = user_model
    payment_service.plan_model = plan_model
    payment_service.payment_model = payment_model
    
    # Test user ID (lawalmoruf@gmail.com)
    user_id = 1
    plan_name = 'pro'
    
    print(f"🔍 Testing activation for User ID: {user_id}, Plan: {plan_name}")
    
    # Check current user status
    user = user_model.get_user_by_id(user_id)
    print(f"🔍 Current user status: {user}")
    
    # Check if plan exists
    plan = plan_model.get_plan_by_name(plan_name)
    print(f"🔍 Plan details: {plan}")
    
    # Test activation
    success = payment_service.activate_subscription(
        user_id=user_id,
        plan_name=plan_name,
        payment_method='paystack',
        payment_id='test_payment_123',
        billing_period='monthly'
    )
    
    print(f"🔍 Activation result: {success}")
    
    # Check updated user status
    user_after = user_model.get_user_by_id(user_id)
    print(f"🔍 Updated user status: {user_after}")

if __name__ == "__main__":
    test_subscription_activation() 