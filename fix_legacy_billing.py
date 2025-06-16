#!/usr/bin/env python3
"""
Fix Legacy Billing Records Script

This script fixes legacy payment records in the database to ensure they display
correctly in the billing history with proper currency, payment method, and formatting.
"""

import sqlite3
import json
from datetime import datetime
from currency_service import currency_service

def connect_db():
    """Connect to the database"""
    try:
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def get_payment_records(conn):
    """Get all payment records"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM payment_records 
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Error fetching payment records: {e}")
        return []

def fix_legacy_payment_record(conn, payment_id, record):
    """Fix a single legacy payment record"""
    try:
        cursor = conn.cursor()
        
        # Get the original record data - sqlite3.Row objects use dict-style access
        amount = record['amount']
        currency = record['currency'] if 'currency' in record.keys() else 'USD'
        payment_method = record['payment_method'] if 'payment_method' in record.keys() else 'card'
        plan_name = record['plan_name'] if 'plan_name' in record.keys() else 'Unknown'
        billing_period = record['billing_period'] if 'billing_period' in record.keys() else 'monthly'
        status = record['status'] if 'status' in record.keys() else 'completed'
        
        print(f"🔍 Fixing payment record {payment_id}:")
        print(f"   Original amount: {amount} {currency}")
        print(f"   Payment method: {payment_method}")
        print(f"   Plan: {plan_name} ({billing_period})")
        
        # Fix currency if it's missing or invalid
        if not currency or currency.lower() not in ['usd', 'ngn', 'eur', 'gbp']:
            # Determine currency based on payment method or amount
            if payment_method == 'paystack':
                currency = 'NGN'
            elif payment_method == 'stripe':
                currency = 'USD'
            else:
                currency = 'USD'
            print(f"   Fixed currency: {currency}")
        
        # Fix payment method if it's missing or generic
        if not payment_method or payment_method == 'card':
            # Determine payment method based on other clues
            if currency == 'NGN':
                payment_method = 'Paystack'
            elif currency == 'USD':
                payment_method = 'Stripe'
            else:
                payment_method = 'Credit Card'
            print(f"   Fixed payment method: {payment_method}")
        
        # Format amount properly
        try:
            amount_float = float(amount)
            # Ensure amount is in the correct format (no extra decimals for whole numbers)
            if amount_float == int(amount_float):
                formatted_amount = int(amount_float)
            else:
                formatted_amount = round(amount_float, 2)
        except (ValueError, TypeError):
            formatted_amount = amount
        
        # Update the record
        cursor.execute("""
            UPDATE payment_records 
            SET currency = ?, payment_method = ?, amount = ?
            WHERE id = ?
        """, (currency.upper(), payment_method, formatted_amount, payment_id))
        
        print(f"   ✅ Updated record with currency: {currency.upper()}, method: {payment_method}, amount: {formatted_amount}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error fixing record {payment_id}: {e}")
        return False

def add_missing_columns(conn):
    """Add missing columns if they don't exist"""
    try:
        cursor = conn.cursor()
        
        # Check if payment_method column exists
        cursor.execute("PRAGMA table_info(payment_records)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'payment_method' not in columns:
            print("🔧 Adding payment_method column...")
            cursor.execute("ALTER TABLE payment_records ADD COLUMN payment_method TEXT DEFAULT 'card'")
            print("   ✅ payment_method column added")
        
        if 'currency' not in columns:
            print("🔧 Adding currency column...")
            cursor.execute("ALTER TABLE payment_records ADD COLUMN currency TEXT DEFAULT 'USD'")
            print("   ✅ currency column added")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error adding missing columns: {e}")
        return False

def create_backup(conn):
    """Create a backup of the payment_records table"""
    try:
        cursor = conn.cursor()
        
        # Create backup table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_records_backup AS 
            SELECT * FROM payment_records
        """)
        
        print("✅ Backup created: payment_records_backup")
        return True
        
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return False

def validate_currency_service():
    """Validate that currency service is working"""
    try:
        # Test currency formatting
        test_amount = 9.99
        test_currency = 'USD'
        formatted = currency_service.format_amount(test_amount, test_currency)
        symbol = currency_service.get_currency_symbol(test_currency)
        
        print(f"✅ Currency service test: {symbol}{formatted}")
        return True
        
    except Exception as e:
        print(f"❌ Currency service validation failed: {e}")
        return False

def main():
    """Main function to fix legacy billing records"""
    print("🔧 Starting Legacy Billing Records Fix")
    print("=" * 50)
    
    # Connect to database
    conn = connect_db()
    if not conn:
        print("❌ Cannot proceed without database connection")
        return
    
    try:
        # Validate currency service
        if not validate_currency_service():
            print("⚠️ Currency service issues detected, but continuing...")
        
        # Create backup
        print("\n📦 Creating backup...")
        if not create_backup(conn):
            print("⚠️ Backup failed, but continuing...")
        
        # Add missing columns
        print("\n🔧 Checking for missing columns...")
        add_missing_columns(conn)
        
        # Get all payment records
        print("\n📋 Fetching payment records...")
        records = get_payment_records(conn)
        
        if not records:
            print("ℹ️ No payment records found")
            return
        
        print(f"📊 Found {len(records)} payment records")
        
        # Fix each record
        print("\n🔧 Fixing legacy records...")
        fixed_count = 0
        error_count = 0
        
        for record in records:
            payment_id = record['id']
            if fix_legacy_payment_record(conn, payment_id, record):
                fixed_count += 1
            else:
                error_count += 1
        
        # Commit changes
        conn.commit()
        
        print("\n" + "=" * 50)
        print("📊 Fix Summary:")
        print(f"   Total records: {len(records)}")
        print(f"   Fixed: {fixed_count}")
        print(f"   Errors: {error_count}")
        print(f"   Success rate: {(fixed_count/len(records)*100):.1f}%")
        
        # Show sample of fixed records
        print("\n📋 Sample of fixed records:")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, amount, currency, payment_method, plan_name, billing_period, created_at
            FROM payment_records 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        sample_records = cursor.fetchall()
        for record in sample_records:
            print(f"   ID {record['id']}: {record['amount']} {record['currency']} via {record['payment_method']} - {record['plan_name']} ({record['billing_period']})")
        
        print("\n✅ Legacy billing records fix completed!")
        
    except Exception as e:
        print(f"❌ Error during fix process: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    main() 