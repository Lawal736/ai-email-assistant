#!/usr/bin/env python3
"""
Test script to verify Gmail email display in account page
"""

import sqlite3
import json

def test_gmail_display():
    """Test Gmail email display by checking database and template data"""
    
    print("🔍 Testing Gmail Email Display...")
    print("=" * 50)
    
    # Connect to database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Check if gmail_email column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'gmail_email' not in columns:
        print("❌ gmail_email column not found in users table")
        return
    
    print("✅ gmail_email column exists")
    
    # Get all users with their Gmail data
    cursor.execute("""
        SELECT id, email, gmail_email, gmail_token 
        FROM users 
        ORDER BY id
    """)
    users = cursor.fetchall()
    
    print(f"\n📊 Found {len(users)} users:")
    print("-" * 50)
    
    for user in users:
        user_id, email, gmail_email, gmail_token = user
        print(f"User ID: {user_id}")
        print(f"Email: {email}")
        print(f"Gmail Email: {gmail_email or 'None'}")
        print(f"Gmail Token: {'Present' if gmail_token else 'None'}")
        print("-" * 30)
    
    # Test specific user (lawalmoruf@gmail.com)
    cursor.execute("""
        SELECT id, email, gmail_email, gmail_token 
        FROM users 
        WHERE email = 'lawalmoruf@gmail.com'
    """)
    user = cursor.fetchone()
    
    if user:
        user_id, email, gmail_email, gmail_token = user
        print(f"\n🎯 Testing lawalmoruf@gmail.com:")
        print(f"User ID: {user_id}")
        print(f"Email: {email}")
        print(f"Gmail Email: {gmail_email or 'None'}")
        print(f"Gmail Token: {'Present' if gmail_token else 'None'}")
        
        if gmail_email:
            print("✅ Gmail email is set in database")
        else:
            print("❌ Gmail email is NOT set in database")
    else:
        print("❌ User lawalmoruf@gmail.com not found")
    
    conn.close()

if __name__ == "__main__":
    test_gmail_display() 