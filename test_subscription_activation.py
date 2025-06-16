#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from payment_service import PaymentService
from models import DatabaseManager, User, SubscriptionPlan, PaymentRecord

def test_subscription_activation():
    """Test the subscription activation process"""
    print("🔍 Testing subscription activation...")
    
    # Initialize services
    db_manager = DatabaseManager()
    user_model = User(db_manager)
    plan_model = SubscriptionPlan(db_manager)
    payment_model = PaymentRecord(db_manager)
    
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