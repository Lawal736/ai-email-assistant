#!/usr/bin/env python3
"""
Script to fix inconsistent Gmail data in the database
"""

import sqlite3
import json

def fix_gmail_data():
    """Fix inconsistent Gmail data in the database"""
    
    print("🔧 Fixing Gmail Data Inconsistencies...")
    print("=" * 50)
    
    # Connect to database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Get current state
    cursor.execute("""
        SELECT id, email, gmail_email, gmail_token 
        FROM users 
        ORDER BY id
    """)
    users = cursor.fetchall()
    
    print("📊 Current database state:")
    print("-" * 50)
    for user in users:
        user_id, email, gmail_email, gmail_token = user
        print(f"User {user_id}: {email}")
        print(f"  Gmail Email: {gmail_email or 'None'}")
        print(f"  Gmail Token: {'Present' if gmail_token else 'None'}")
        print("-" * 30)
    
    # Fix inconsistencies
    print("\n🔧 Fixing inconsistencies...")
    
    for user in users:
        user_id, email, gmail_email, gmail_token = user
        
        # If user has a token but no email, clear the token
        if gmail_token and not gmail_email:
            print(f"❌ User {user_id} has token but no email - clearing token")
            cursor.execute('UPDATE users SET gmail_token = NULL WHERE id = ?', (user_id,))
        
        # If user has an email but no token, clear the email
        elif gmail_email and not gmail_token:
            print(f"❌ User {user_id} has email but no token - clearing email")
            cursor.execute('UPDATE users SET gmail_email = NULL WHERE id = ?', (user_id,))
        
        # If user has both token and email, validate the token
        elif gmail_token and gmail_email:
            try:
                token_data = json.loads(gmail_token)
                if not token_data or 'refresh_token' not in token_data:
                    print(f"❌ User {user_id} has invalid token - clearing both")
                    cursor.execute('UPDATE users SET gmail_token = NULL, gmail_email = NULL WHERE id = ?', (user_id,))
                else:
                    print(f"✅ User {user_id} has valid token and email")
            except json.JSONDecodeError:
                print(f"❌ User {user_id} has corrupted token - clearing both")
                cursor.execute('UPDATE users SET gmail_token = NULL, gmail_email = NULL WHERE id = ?', (user_id,))
    
    # Commit changes
    conn.commit()
    
    # Show final state
    print("\n📊 Final database state:")
    print("-" * 50)
    cursor.execute("""
        SELECT id, email, gmail_email, gmail_token 
        FROM users 
        ORDER BY id
    """)
    users = cursor.fetchall()
    
    for user in users:
        user_id, email, gmail_email, gmail_token = user
        print(f"User {user_id}: {email}")
        print(f"  Gmail Email: {gmail_email or 'None'}")
        print(f"  Gmail Token: {'Present' if gmail_token else 'None'}")
        print("-" * 30)
    
    conn.close()
    print("\n✅ Gmail data inconsistencies fixed!")

if __name__ == "__main__":
    fix_gmail_data() 