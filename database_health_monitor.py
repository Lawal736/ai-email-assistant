#!/usr/bin/env python3
"""
Database Health Monitor
Proactive monitoring system to detect and prevent database corruption
"""

import sqlite3
import time
import os
import threading
from datetime import datetime, timedelta
import logging

class DatabaseHealthMonitor:
    """Monitor database health and detect corruption early"""
    
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self.last_check = None
        self.alerts = []
        self.monitoring = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def check_database_integrity(self):
        """Comprehensive database integrity check"""
        issues = []
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # 1. PRAGMA integrity_check
            cursor.execute('PRAGMA integrity_check')
            integrity_result = cursor.fetchone()
            if integrity_result[0] != 'ok':
                issues.append(f"Integrity check failed: {integrity_result[0]}")
            
            # 2. Check table existence
            required_tables = ['users', 'subscription_plans', 'payment_records', 'usage_tracking']
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            for table in required_tables:
                if table not in existing_tables:
                    issues.append(f"Required table missing: {table}")
            
            # 3. Check for orphaned sessions (users in session but not in DB)
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                issues.append("CRITICAL: No users found in database")
            
            # 4. Check for corrupted user records
            cursor.execute('''
                SELECT id, email, password_hash 
                FROM users 
                WHERE email IS NULL OR password_hash IS NULL OR password_hash = ''
            ''')
            corrupted_users = cursor.fetchall()
            
            if corrupted_users:
                issues.append(f"Corrupted user records found: {len(corrupted_users)}")
            
            # 5. Check database file size and growth
            db_size = os.path.getsize(self.db_path)
            if db_size < 1024:  # Less than 1KB is suspicious
                issues.append(f"Database file suspiciously small: {db_size} bytes")
            
            # 6. Check WAL file issues
            wal_file = f"{self.db_path}-wal"
            if os.path.exists(wal_file):
                wal_size = os.path.getsize(wal_file)
                if wal_size > db_size * 2:  # WAL file larger than DB is concerning
                    issues.append(f"WAL file unusually large: {wal_size} bytes")
            
            conn.close()
            
        except Exception as e:
            issues.append(f"Database check failed: {str(e)}")
        
        return issues
    
    def check_user_session_consistency(self):
        """Check for user/session mismatches that could indicate corruption"""
        issues = []
        
        try:
            # This would require access to active sessions
            # For now, we'll check for common patterns that indicate issues
            
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Check for users with missing critical data
            cursor.execute('''
                SELECT id, email, password_hash, created_at
                FROM users
                WHERE password_hash = 'EMERGENCY_RECOVERY_NO_PASSWORD'
            ''')
            
            emergency_users = cursor.fetchall()
            if emergency_users:
                issues.append(f"Emergency recovered users found: {len(emergency_users)}")
                for user in emergency_users:
                    self.logger.warning(f"User {user[0]} ({user[1]}) was emergency recovered")
            
            conn.close()
            
        except Exception as e:
            issues.append(f"Session consistency check failed: {str(e)}")
        
        return issues
    
    def run_health_check(self):
        """Run comprehensive health check"""
        self.logger.info("Starting database health check...")
        
        all_issues = []
        
        # Check database integrity
        integrity_issues = self.check_database_integrity()
        all_issues.extend(integrity_issues)
        
        # Check user/session consistency
        consistency_issues = self.check_user_session_consistency()
        all_issues.extend(consistency_issues)
        
        # Log results
        if all_issues:
            self.logger.error(f"Health check found {len(all_issues)} issues:")
            for issue in all_issues:
                self.logger.error(f"  - {issue}")
        else:
            self.logger.info("Health check passed - no issues found")
        
        self.last_check = datetime.now()
        return all_issues
    
    def start_monitoring(self, check_interval=300):  # 5 minutes
        """Start continuous monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.logger.info(f"Starting database health monitoring (interval: {check_interval}s)")
        
        def monitor_loop():
            while self.monitoring:
                try:
                    issues = self.run_health_check()
                    
                    # Alert on critical issues
                    critical_keywords = ['CRITICAL', 'missing', 'failed', 'corrupted']
                    critical_issues = [issue for issue in issues 
                                     if any(keyword.lower() in issue.lower() 
                                           for keyword in critical_keywords)]
                    
                    if critical_issues:
                        self.logger.critical(f"CRITICAL DATABASE ISSUES DETECTED: {critical_issues}")
                        # Here you could send alerts, emails, etc.
                    
                    time.sleep(check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Monitoring error: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        self.logger.info("Database health monitoring stopped")
    
    def backup_database(self, backup_path=None):
        """Create a backup of the database"""
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"backup_users_{timestamp}.db"
        
        try:
            # Use SQLite backup API for consistent backup
            source = sqlite3.connect(self.db_path)
            backup = sqlite3.connect(backup_path)
            
            source.backup(backup)
            
            source.close()
            backup.close()
            
            self.logger.info(f"Database backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return None
    
    def repair_database(self):
        """Attempt to repair database corruption"""
        self.logger.info("Attempting database repair...")
        
        try:
            # Create backup first
            backup_path = self.backup_database()
            if not backup_path:
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Run VACUUM to rebuild database
            cursor.execute('VACUUM')
            
            # Reindex all tables
            cursor.execute('REINDEX')
            
            conn.close()
            
            # Run integrity check after repair
            issues = self.check_database_integrity()
            if not issues:
                self.logger.info("Database repair successful")
                return True
            else:
                self.logger.error(f"Database repair incomplete, issues remain: {issues}")
                return False
                
        except Exception as e:
            self.logger.error(f"Database repair failed: {e}")
            return False

def main():
    """CLI interface for database health monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Health Monitor')
    parser.add_argument('--check', action='store_true', help='Run one-time health check')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--backup', action='store_true', help='Create database backup')
    parser.add_argument('--repair', action='store_true', help='Attempt database repair')
    parser.add_argument('--db-path', default='users.db', help='Database file path')
    
    args = parser.parse_args()
    
    monitor = DatabaseHealthMonitor(args.db_path)
    
    if args.check:
        issues = monitor.run_health_check()
        if issues:
            print(f"Found {len(issues)} issues:")
            for issue in issues:
                print(f"  - {issue}")
            exit(1)
        else:
            print("Database health check passed")
            exit(0)
    
    elif args.monitor:
        try:
            monitor.start_monitoring()
            print("Monitoring started. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop_monitoring()
            print("\nMonitoring stopped")
    
    elif args.backup:
        backup_path = monitor.backup_database()
        if backup_path:
            print(f"Backup created: {backup_path}")
        else:
            print("Backup failed")
            exit(1)
    
    elif args.repair:
        success = monitor.repair_database()
        if success:
            print("Database repair completed successfully")
        else:
            print("Database repair failed")
            exit(1)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 