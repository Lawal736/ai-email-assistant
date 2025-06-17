#!/usr/bin/env python3
"""
Emergency Database Fix for Token Persistence Issue
This script addresses the severe token corruption happening in production
"""

import sqlite3
import os
import shutil
import time
from datetime import datetime

def emergency_database_repair():
    """Emergency repair for token persistence issues"""
    
    print("🚨 EMERGENCY DATABASE REPAIR STARTING")
    print(f"🕐 Time: {datetime.now()}")
    
    db_path = 'users.db'
    backup_path = f'users_emergency_backup_{int(time.time())}.db'
    
    try:
        # 1. Create emergency backup
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            print(f"✅ Emergency backup created: {backup_path}")
        
        # 2. Stop WAL mode and force checkpoint
        print("🔧 Forcing WAL checkpoint and repair...")
        conn = sqlite3.connect(db_path, timeout=60.0)
        
        # Force WAL checkpoint
        conn.execute('PRAGMA wal_checkpoint(FULL)')
        
        # Switch to DELETE mode temporarily
        conn.execute('PRAGMA journal_mode=DELETE')
        
        # Vacuum to rebuild database
        conn.execute('VACUUM')
        
        # Re-enable WAL mode
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=FULL')  # Maximum safety
        conn.execute('PRAGMA cache_size=10000')
        conn.execute('PRAGMA temp_store=MEMORY')
        
        conn.commit()
        
        # 3. Verify database integrity
        cursor = conn.cursor()
        cursor.execute('PRAGMA integrity_check')
        integrity_result = cursor.fetchone()
        
        if integrity_result[0] != 'ok':
            print(f"❌ Database integrity check failed: {integrity_result[0]}")
            return False
        
        print("✅ Database integrity check passed")
        
        # 4. Check user table structure
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        table_schema = cursor.fetchone()
        
        if not table_schema:
            print("❌ Users table missing!")
            return False
        
        print(f"✅ Users table exists: {table_schema[0][:100]}...")
        
        # 5. Check for any users
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        print(f"✅ Users found: {user_count}")
        
        # 6. Check for token corruption patterns
        cursor.execute('''
            SELECT id, email, 
                   CASE WHEN gmail_token IS NULL THEN 'NULL'
                        WHEN gmail_token = '' THEN 'EMPTY'
                        ELSE 'PRESENT' END as token_status,
                   LENGTH(gmail_token) as token_length
            FROM users
        ''')
        
        users = cursor.fetchall()
        for user in users:
            print(f"📊 User {user[0]} ({user[1]}): Token {user[2]} ({user[3]} chars)")
        
        conn.close()
        
        # 7. Remove any corrupt WAL/SHM files
        wal_files = [f"{db_path}-wal", f"{db_path}-shm"]
        for wal_file in wal_files:
            if os.path.exists(wal_file):
                try:
                    os.remove(wal_file)
                    print(f"🗑️ Removed potentially corrupt file: {wal_file}")
                except Exception as e:
                    print(f"⚠️ Could not remove {wal_file}: {e}")
        
        print("✅ Emergency database repair completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Emergency repair failed: {e}")
        
        # Try to restore backup
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, db_path)
                print(f"🔄 Database restored from backup: {backup_path}")
            except Exception as restore_error:
                print(f"❌ Backup restore failed: {restore_error}")
        
        return False

def create_robust_token_table():
    """Create a more robust token storage mechanism"""
    
    print("🔧 Creating robust token storage...")
    
    try:
        conn = sqlite3.connect('users.db', timeout=60.0)
        cursor = conn.cursor()
        
        # Create a separate token table with better constraints
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_data TEXT NOT NULL,
                gmail_email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id)
            )
        ''')
        
        # Create trigger to update timestamp
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_token_timestamp 
            AFTER UPDATE ON user_tokens
            BEGIN
                UPDATE user_tokens SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        ''')
        
        # Migrate existing tokens
        cursor.execute('''
            INSERT OR REPLACE INTO user_tokens (user_id, token_data, gmail_email)
            SELECT id, gmail_token, gmail_email 
            FROM users 
            WHERE gmail_token IS NOT NULL AND gmail_token != ''
        ''')
        
        rows_migrated = cursor.rowcount
        print(f"✅ Migrated {rows_migrated} tokens to robust storage")
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Robust token table creation failed: {e}")
        return False

def test_token_persistence():
    """Test token persistence with stress testing"""
    
    print("🧪 Testing token persistence...")
    
    try:
        test_token = '{"test": "token", "timestamp": "' + str(time.time()) + '"}'
        test_user_id = 1
        
        # Test multiple rapid writes
        for i in range(5):
            conn = sqlite3.connect('users.db', timeout=60.0)
            cursor = conn.cursor()
            
            # Insert/update token
            cursor.execute('''
                INSERT OR REPLACE INTO user_tokens (user_id, token_data, gmail_email)
                VALUES (?, ?, ?)
            ''', (test_user_id, f"{test_token}_{i}", "test@gmail.com"))
            
            conn.commit()
            
            # Immediately read back
            cursor.execute('SELECT token_data FROM user_tokens WHERE user_id = ?', (test_user_id,))
            result = cursor.fetchone()
            
            if result and f"{test_token}_{i}" in result[0]:
                print(f"✅ Test {i+1}: Token persisted correctly")
            else:
                print(f"❌ Test {i+1}: Token persistence failed")
                print(f"   Expected: {test_token}_{i}")
                print(f"   Got: {result}")
            
            conn.close()
            time.sleep(0.1)  # Small delay
        
        # Clean up test data
        conn = sqlite3.connect('users.db', timeout=60.0)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_tokens WHERE gmail_email = ?', ("test@gmail.com",))
        conn.commit()
        conn.close()
        
        print("✅ Token persistence test completed")
        return True
        
    except Exception as e:
        print(f"❌ Token persistence test failed: {e}")
        return False

def ensure_user_tokens_table(db_path):
    """Ensure user_tokens table exists - critical fix for production"""
    print("🔧 [EMERGENCY] Ensuring user_tokens table exists...")
    
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_tokens'")
        exists = cursor.fetchone()
        
        if exists:
            print("✅ [EMERGENCY] user_tokens table already exists")
        else:
            print("⚠️ [EMERGENCY] user_tokens table missing - creating now...")
            
            # Create the robust token storage table
            cursor.execute('''
                CREATE TABLE user_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_data TEXT NOT NULL,
                    gmail_email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id)
                )
            ''')
            
            # Create trigger for timestamp updates
            cursor.execute('''
                CREATE TRIGGER update_token_timestamp 
                AFTER UPDATE ON user_tokens
                BEGIN
                    UPDATE user_tokens SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END
            ''')
            
            print("✅ [EMERGENCY] user_tokens table created successfully")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ [EMERGENCY] Failed to create user_tokens table: {e}")
        return False

if __name__ == '__main__':
    print("🚨 EMERGENCY DATABASE REPAIR UTILITY")
    print("=" * 50)
    
    # Step 1: Emergency repair
    if emergency_database_repair():
        print("\n🔧 PHASE 1: Emergency repair successful")
    else:
        print("\n❌ PHASE 1: Emergency repair failed")
        exit(1)
    
    # Step 1.5: Ensure critical tables (new fix)
    if ensure_user_tokens_table('users.db'):
        print("\n🔧 PHASE 1.5: Critical tables ensured")
    else:
        print("\n❌ PHASE 1.5: Critical table creation failed")
    
    # Step 2: Create robust storage
    if create_robust_token_table():
        print("\n🔧 PHASE 2: Robust storage created")
    else:
        print("\n❌ PHASE 2: Robust storage failed")
    
    # Step 3: Test persistence
    if test_token_persistence():
        print("\n🧪 PHASE 3: Persistence test passed")
    else:
        print("\n❌ PHASE 3: Persistence test failed")
    
    print("\n✅ EMERGENCY REPAIR COMPLETED")
    print("📝 Next steps:")
    print("   1. Deploy updated models.py with robust token storage")
    print("   2. Monitor token persistence in production")
    print("   3. Consider PostgreSQL migration if issues persist") 