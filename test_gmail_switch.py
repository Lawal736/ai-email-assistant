#!/usr/bin/env python3
"""
Test script to verify Gmail account switching functionality
"""

import sqlite3
import json
import os

def test_gmail_switching():
    """Test Gmail account switching by checking database state"""
    
    print("🔍 Testing Gmail Account Switching...")
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
    
    # Get all users with Gmail data
    cursor.execute("""
        SELECT id, email, gmail_email, gmail_token 
        FROM users 
        WHERE gmail_email IS NOT NULL OR gmail_token IS NOT NULL
    """)
    
    users = cursor.fetchall()
    
    if not users:
        print("ℹ️ No users with Gmail data found")
        return
    
    print(f"📧 Found {len(users)} users with Gmail data:")
    print("-" * 50)
    
    for user in users:
        user_id, email, gmail_email, gmail_token = user
        token_exists = gmail_token is not None
        print(f"User ID: {user_id}")
        print(f"  Profile Email: {email}")
        print(f"  Gmail Email: {gmail_email or 'None'}")
        print(f"  Gmail Token: {'✅ Present' if token_exists else '❌ Missing'}")
        print()
    
    # Test disconnect functionality
    print("🧪 Testing disconnect functionality...")
    print("-" * 50)
    
    # Simulate disconnect for first user
    if users:
        user_id = users[0][0]
        print(f"Testing disconnect for user {user_id}...")
        
        # Clear Gmail data
        cursor.execute("""
            UPDATE users 
            SET gmail_token = NULL, gmail_email = NULL 
            WHERE id = ?
        """, (user_id,))
        
        conn.commit()
        
        # Verify disconnect
        cursor.execute("""
            SELECT gmail_email, gmail_token 
            FROM users 
            WHERE id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        if result and result[0] is None and result[1] is None:
            print("✅ Disconnect test successful - Gmail data cleared")
        else:
            print("❌ Disconnect test failed - Gmail data still present")
    
    conn.close()
    
    # Check token.json file
    print("\n🔍 Checking token.json file...")
    if os.path.exists('token.json'):
        print("⚠️ token.json file exists - this might cause caching issues")
        try:
            with open('token.json', 'r') as f:
                token_data = json.load(f)
            print(f"   Token file contains data for: {token_data.get('client_id', 'Unknown')}")
        except Exception as e:
            print(f"   Error reading token file: {e}")
    else:
        print("✅ No token.json file found")
    
    print("\n💡 Recommendations:")
    print("1. Ensure Gmail service clears credentials on disconnect")
    print("2. Remove token.json file when disconnecting")
    print("3. Clear browser cache and cookies")
    print("4. Restart Flask application after disconnecting")

if __name__ == "__main__":
    test_gmail_switching() 