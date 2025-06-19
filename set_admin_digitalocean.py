#!/usr/bin/env python3
"""
Script to set a user as admin on Digital Ocean App Platform
Run this on your Digital Ocean app console or via SSH
"""

import os
import sys
from models_postgresql import DatabaseManager

def set_user_as_admin(email):
    """Set a user as admin by email"""
    try:
        # Check if we're on Digital Ocean
        if not os.getenv('DB_HOST'):
            print("❌ Database environment variables not found.")
            print("Make sure you're running this on Digital Ocean App Platform")
            return False
        
        print(f"🔧 Connecting to Digital Ocean database...")
        db = DatabaseManager()
        
        # Get user ID from email
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, email FROM users WHERE email = %s", (email,))
                result = cur.fetchone()
                if not result:
                    print(f"❌ User with email {email} not found")
                    return False
                
                user_id, user_email = result
                print(f"✅ Found user: {user_email} (ID: {user_id})")
                
        # Set user as admin
        success = db.set_user_admin(user_id, True)
        if success:
            print(f"✅ Successfully set {email} as admin")
            print(f"🔄 Please log out and log back in to activate admin privileges")
            return True
        else:
            print(f"❌ Failed to set {email} as admin")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def list_users():
    """List all users in the database"""
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, email, is_admin FROM users ORDER BY created_at DESC")
                users = cur.fetchall()
                
                if not users:
                    print("❌ No users found in database")
                    return
                
                print(f"📋 Found {len(users)} users:")
                print("-" * 60)
                for user_id, email, is_admin in users:
                    admin_status = "👑 ADMIN" if is_admin else "👤 User"
                    print(f"{user_id:3} | {email:30} | {admin_status}")
                print("-" * 60)
                
    except Exception as e:
        print(f"❌ Error listing users: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 set_admin_digitalocean.py <email>     # Set user as admin")
        print("  python3 set_admin_digitalocean.py --list      # List all users")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_users()
    else:
        email = sys.argv[1]
        set_user_as_admin(email) 