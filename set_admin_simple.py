#!/usr/bin/env python3
"""
Simple script to set admin status directly with SQL
"""

import os
import psycopg2
import sys

def set_admin_direct(email):
    """Set user as admin using direct SQL"""
    try:
        # Database connection config
        db_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 25060)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'sslmode': os.getenv('DB_SSLMODE', 'require')
        }
        
        print(f"🔧 Connecting to database...")
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Check if is_admin column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'is_admin'
            );
        """)
        column_exists = cur.fetchone()[0]
        
        if not column_exists:
            print("📝 Adding is_admin column to users table...")
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
            """)
            conn.commit()
            print("✅ is_admin column added successfully")
        
        # Find user by email
        cur.execute("SELECT id, email FROM users WHERE email = %s", (email,))
        result = cur.fetchone()
        
        if not result:
            print(f"❌ User with email {email} not found")
            return False
        
        user_id, user_email = result
        print(f"✅ Found user: {user_email} (ID: {user_id})")
        
        # Set admin status
        cur.execute("""
            UPDATE users 
            SET is_admin = TRUE 
            WHERE id = %s 
            RETURNING email
        """, (user_id,))
        conn.commit()
        
        result = cur.fetchone()
        if result:
            print(f"✅ Successfully set {email} as admin")
            print(f"🔄 Please log out and log back in to activate admin privileges")
            return True
        else:
            print(f"❌ Failed to update admin status")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def list_users_direct():
    """List all users directly"""
    try:
        db_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 25060)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'sslmode': os.getenv('DB_SSLMODE', 'require')
        }
        
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Check if is_admin column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'is_admin'
            );
        """)
        column_exists = cur.fetchone()[0]
        
        if column_exists:
            cur.execute("SELECT id, email, is_admin FROM users ORDER BY created_at DESC")
        else:
            cur.execute("SELECT id, email, NULL as is_admin FROM users ORDER BY created_at DESC")
        
        users = cur.fetchall()
        
        if not users:
            print("❌ No users found in database")
            return
        
        print(f"📋 Found {len(users)} users:")
        print("-" * 60)
        for user_id, email, is_admin in users:
            if is_admin is None:
                admin_status = "❓ Unknown (no is_admin column)"
            else:
                admin_status = "👑 ADMIN" if is_admin else "👤 User"
            print(f"{user_id:3} | {email:30} | {admin_status}")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Error listing users: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 set_admin_simple.py <email>     # Set user as admin")
        print("  python3 set_admin_simple.py --list      # List all users")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_users_direct()
    else:
        email = sys.argv[1]
        set_admin_direct(email) 