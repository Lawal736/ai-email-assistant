#!/usr/bin/env python3
"""
Database Backup and Restore Utility
Helps preserve user data between deployments
"""

import sqlite3
import json
import os
import time
from datetime import datetime

def backup_database(db_path='users.db', backup_file=None):
    """Create a JSON backup of all user data"""
    
    if backup_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'database_backup_{timestamp}.json'
    
    print(f"🔄 Creating database backup: {backup_file}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'version': '1.0',
            'tables': {}
        }
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            print(f"📊 Backing up table: {table}")
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Get all data
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            backup_data['tables'][table] = {
                'columns': columns,
                'rows': rows
            }
        
        conn.close()
        
        # Save to JSON file
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        print(f"✅ Backup created successfully: {backup_file}")
        print(f"📊 Tables backed up: {len(backup_data['tables'])}")
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def restore_database(backup_file, db_path='users.db'):
    """Restore database from JSON backup"""
    
    print(f"🔄 Restoring database from: {backup_file}")
    
    try:
        # Load backup data
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        print(f"📅 Backup timestamp: {backup_data.get('timestamp')}")
        print(f"📋 Tables to restore: {len(backup_data.get('tables', {}))}")
        
        # Create new database connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys=OFF')
        
        for table_name, table_data in backup_data['tables'].items():
            print(f"📊 Restoring table: {table_name}")
            
            columns = table_data['columns']
            rows = table_data['rows']
            
            if rows:
                # Clear existing data
                cursor.execute(f"DELETE FROM {table_name}")
                
                # Insert data
                placeholders = ','.join(['?'] * len(columns))
                insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
                
                cursor.executemany(insert_query, rows)
                print(f"   ✅ Restored {len(rows)} rows")
            else:
                print(f"   ⚠️ No data to restore")
        
        cursor.execute('PRAGMA foreign_keys=ON')
        conn.commit()
        conn.close()
        
        print(f"✅ Database restored successfully")
        return True
        
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

def list_backups():
    """List available backup files"""
    
    backup_files = [f for f in os.listdir('.') if f.startswith('database_backup_') and f.endswith('.json')]
    backup_files.sort(reverse=True)  # Newest first
    
    print(f"📋 Available backups ({len(backup_files)}):")
    for i, backup_file in enumerate(backup_files, 1):
        # Extract timestamp from filename
        try:
            timestamp_str = backup_file.replace('database_backup_', '').replace('.json', '')
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            print(f"   {i}. {backup_file} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
        except:
            print(f"   {i}. {backup_file}")
    
    return backup_files

def get_database_stats(db_path='users.db'):
    """Get current database statistics"""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📊 Database Statistics: {db_path}")
        
        # Get table counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count} rows")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("📖 Database Backup Utility")
        print("Usage:")
        print("   python3 database_backup.py backup [filename]")
        print("   python3 database_backup.py restore <filename>")
        print("   python3 database_backup.py list")
        print("   python3 database_backup.py stats")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'backup':
        backup_file = sys.argv[2] if len(sys.argv) > 2 else None
        backup_database(backup_file=backup_file)
    
    elif command == 'restore':
        if len(sys.argv) < 3:
            print("❌ Please specify backup file to restore")
            list_backups()
        else:
            backup_file = sys.argv[2]
            restore_database(backup_file)
    
    elif command == 'list':
        list_backups()
    
    elif command == 'stats':
        get_database_stats()
    
    else:
        print(f"❌ Unknown command: {command}") 