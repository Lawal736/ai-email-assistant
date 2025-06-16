#!/usr/bin/env python3
"""
Database migration script to add missing columns to existing databases
"""

import sqlite3
import os

def migrate_database():
    """Add missing columns to the database"""
    db_path = 'users.db'
    
    if not os.path.exists(db_path):
        print("Database file not found. Creating new database...")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if gmail_email column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'gmail_email' not in columns:
            print("Adding gmail_email column to users table...")
            cursor.execute('ALTER TABLE users ADD COLUMN gmail_email TEXT')
            print("✅ gmail_email column added successfully")
        else:
            print("✅ gmail_email column already exists")
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 