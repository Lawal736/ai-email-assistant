from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import threading
import time

class DatabaseManager:
    """Database manager for user authentication and payments"""
    
    def __init__(self, db_path=None):
        # Use persistent path for production, local path for development
        if db_path is None:
            import os
            if os.getenv('DIGITALOCEAN_APP_PLATFORM'):
                # Production: Use persistent volume mount
                db_path = '/app/data/users.db'
                # Ensure directory exists
                os.makedirs('/app/data', exist_ok=True)
                print(f"🔧 Using persistent database path: {db_path}")
            else:
                # Development: Use local file
                db_path = 'users.db'
                print(f"🔧 Using local database path: {db_path}")
        
        self.db_path = db_path
        self._lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                subscription_plan TEXT DEFAULT 'free',
                subscription_status TEXT DEFAULT 'active',
                subscription_expires DATETIME,
                stripe_customer_id TEXT,
                gmail_token TEXT,
                gmail_email TEXT,
                api_usage_count INTEGER DEFAULT 0,
                monthly_usage_limit INTEGER DEFAULT 100,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create subscription_plans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscription_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                price_monthly DECIMAL(10,2) NOT NULL,
                price_yearly DECIMAL(10,2) NOT NULL,
                email_limit INTEGER NOT NULL,
                features TEXT,
                stripe_price_id_monthly TEXT,
                stripe_price_id_yearly TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create payment_records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stripe_payment_intent_id TEXT UNIQUE,
                amount DECIMAL(10,2) NOT NULL,
                currency TEXT DEFAULT 'usd',
                plan_name TEXT NOT NULL,
                billing_period TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                payment_method TEXT DEFAULT 'card',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create password_reset_tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at DATETIME NOT NULL,
                used BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create usage_tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                email_count INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create user_tokens table for robust token storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                token_data TEXT NOT NULL,
                gmail_email TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create processed_emails table for unique email tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_id TEXT NOT NULL,
                email_hash TEXT NOT NULL,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                month_year TEXT NOT NULL,
                action_type TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, email_id, month_year, action_type)
            )
        ''')

        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_processed_emails_lookup 
            ON processed_emails(user_id, month_year, action_type)
        ''')
        
        # Insert default subscription plans if they don't exist
        cursor.execute('''
          INSERT OR IGNORE INTO subscription_plans 
          (name, price_monthly, price_yearly, email_limit, features, stripe_price_id_monthly, stripe_price_id_yearly)
          VALUES 
             ('free', 0.00, 0.00, 100, 'Basic email analysis, Daily AI-generated summaries, Action items extraction, Email limit: 100/month', NULL, NULL),
             ('pro', 19.99, 199.99, 500, 'Everything in Free plus Advanced AI analysis, Document processing, Priority support, Custom insights, Email limit: 500/month', NULL, NULL),
             ('enterprise', 49.99, 499.99, 2000, 'Everything in Pro plus Unlimited AI-powered analysis, Team collaboration, API access, Custom integrations, Email limit: 2,000/month', NULL, NULL)
          ''')
        
        conn.commit()
        conn.close()
        print("Database initialized with all tables including unique email tracking")
    
    def get_connection(self):
        """Get database connection with proper timeout and retry logic"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                # Enable WAL mode for better concurrency
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️ Database locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
            except Exception as e:
                print(f"❌ Database connection error: {e}")
                raise
        
        raise sqlite3.OperationalError("Database connection failed after all retries")

class User:
    """User model for authentication and subscription management"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_user(self, email, password, first_name=None, last_name=None):
        """Create a new user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (email, password_hash, first_name, last_name, gmail_email)
                VALUES (?, ?, ?, ?, NULL)
            ''', (email, password_hash, first_name, last_name))
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None  # Email already exists
        finally:
            conn.close()
    
    def authenticate_user(self, email, password):
        """Authenticate user with email and password"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, password_hash, first_name, last_name, subscription_plan, 
                   subscription_status, subscription_expires, api_usage_count, monthly_usage_limit
            FROM users WHERE email = ? AND is_active = 1
        ''', (email,))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            # Update last login
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_data[0],))
            conn.commit()
            conn.close()
            
            return {
                'id': user_data[0],
                'email': user_data[1],
                'first_name': user_data[3],
                'last_name': user_data[4],
                'subscription_plan': user_data[5],
                'subscription_status': user_data[6],
                'subscription_expires': user_data[7],
                'api_usage_count': user_data[8],
                'monthly_usage_limit': user_data[9]
            }
        return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, first_name, last_name, subscription_plan, 
                   subscription_status, subscription_expires, api_usage_count, monthly_usage_limit, gmail_email,
                   created_at, last_login
            FROM users WHERE id = ? AND is_active = 1
        ''', (user_id,))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                'id': user_data[0],
                'email': user_data[1],
                'first_name': user_data[2],
                'last_name': user_data[3],
                'subscription_plan': user_data[4],
                'subscription_status': user_data[5],
                'subscription_expires': user_data[6],
                'api_usage_count': user_data[7],
                'monthly_usage_limit': user_data[8],
                'gmail_email': user_data[9],
                'created_at': user_data[10],
                'last_login': user_data[11]
            }
        return None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, first_name, last_name, subscription_plan, 
                   subscription_status, subscription_expires, api_usage_count, monthly_usage_limit, gmail_email,
                   created_at, last_login
            FROM users WHERE email = ? AND is_active = 1
        ''', (email,))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                'id': user_data[0],
                'email': user_data[1],
                'first_name': user_data[2],
                'last_name': user_data[3],
                'subscription_plan': user_data[4],
                'subscription_status': user_data[5],
                'subscription_expires': user_data[6],
                'api_usage_count': user_data[7],
                'monthly_usage_limit': user_data[8],
                'gmail_email': user_data[9],
                'created_at': user_data[10],
                'last_login': user_data[11]
            }
        return None
    
    def update_gmail_token(self, user_id, token_data, gmail_email=None):
        """Update user's Gmail token and optionally Gmail email address with robust persistence"""
        print(f"🔍 [DEBUG] update_gmail_token called for user_id: {user_id}")
        print(f"🔍 [DEBUG] token_data length: {len(str(token_data)) if token_data else 0}")
        print(f"🔍 [DEBUG] gmail_email: {gmail_email}")
        
        max_retries = 5  # Increased retries
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                
                # First, verify the user exists
                cursor.execute('SELECT id, email FROM users WHERE id = ?', (user_id,))
                user_check = cursor.fetchone()
                
                if not user_check:
                    print(f"❌ [DEBUG] User {user_id} not found in database during token update (attempt {attempt + 1})")
                    conn.close()
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return False
                
                print(f"✅ [DEBUG] User {user_id} found: {user_check[1]} (attempt {attempt + 1})")
                
                # Use explicit transaction to ensure atomicity
                cursor.execute('BEGIN IMMEDIATE')
                
                # 1. Update legacy users table
                cursor.execute('''
                    UPDATE users 
                    SET gmail_token = ?, gmail_email = ?, last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (token_data, gmail_email, user_id))
                
                legacy_rows = cursor.rowcount
                print(f"🔍 [DEBUG] Legacy table rows affected: {legacy_rows}")
                
                # 2. Update robust user_tokens table (with fallback)
                robust_rows = 0
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_tokens (user_id, token_data, gmail_email, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (user_id, token_data, gmail_email))
                    robust_rows = cursor.rowcount
                    print(f"🔍 [DEBUG] Robust table rows affected: {robust_rows}")
                except sqlite3.OperationalError as e:
                    if "no such table: user_tokens" in str(e):
                        print(f"⚠️ [DEBUG] user_tokens table missing - using legacy storage only")
                    else:
                        raise
                
                # Commit the transaction
                cursor.execute('COMMIT')
                
                # Dual verification - check both storage locations
                cursor.execute('SELECT gmail_token FROM users WHERE id = ?', (user_id,))
                legacy_verification = cursor.fetchone()
                legacy_ok = legacy_verification and legacy_verification[0] == token_data
                
                # Try robust verification (with fallback)
                robust_ok = False
                try:
                    cursor.execute('SELECT token_data FROM user_tokens WHERE user_id = ?', (user_id,))
                    robust_verification = cursor.fetchone()
                    robust_ok = robust_verification and robust_verification[0] == token_data
                except sqlite3.OperationalError as e:
                    if "no such table: user_tokens" in str(e):
                        print(f"⚠️ [DEBUG] user_tokens table missing during verification")
                    else:
                        raise
                
                # Accept success from either storage system
                if robust_ok or legacy_ok:
                    if robust_ok:
                        print(f"✅ [DEBUG] Robust token storage verified (attempt {attempt + 1})")
                    if legacy_ok:
                        print(f"✅ [DEBUG] Legacy token storage verified (attempt {attempt + 1})")
                    conn.close()
                    return True
                else:
                    print(f"❌ [DEBUG] Token verification failed - Legacy OK: {legacy_ok}, Robust OK: {robust_ok}")
                    conn.close()
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return False
                
            except sqlite3.OperationalError as e:
                if 'conn' in locals():
                    try:
                        cursor.execute('ROLLBACK')
                    except:
                        pass
                    conn.close()
                
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️ Database locked during update, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"❌ [DEBUG] Database operational error in update_gmail_token: {e}")
                    if attempt == max_retries - 1:
                        raise
            except Exception as e:
                if 'conn' in locals():
                    try:
                        cursor.execute('ROLLBACK')
                    except:
                        pass
                    conn.close()
                
                print(f"❌ [DEBUG] Error in update_gmail_token (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                retry_delay *= 2
        
        print(f"❌ [DEBUG] Failed to update Gmail token after {max_retries} attempts")
        return False
    
    def get_gmail_token(self, user_id):
        """Get user's Gmail token with enhanced retry logic and debugging"""
        print(f"🔍 [DEBUG] get_gmail_token called for user_id: {user_id}")
        
        max_retries = 5  # Increased retries to match update_gmail_token
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                # Force a fresh connection each time to avoid caching issues
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                
                # First check if user exists at all
                cursor.execute('SELECT id, email FROM users WHERE id = ?', (user_id,))
                user_check = cursor.fetchone()
                
                if not user_check:
                    print(f"❌ [DEBUG] User {user_id} not found in database during token retrieval (attempt {attempt + 1})")
                    conn.close()
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return None
                
                print(f"✅ [DEBUG] User {user_id} found: {user_check[1]} (attempt {attempt + 1})")
                
                # Try dual storage - robust first, then legacy (with fallback)
                robust_token = None
                try:
                    cursor.execute('SELECT token_data FROM user_tokens WHERE user_id = ? AND is_active = 1', (user_id,))
                    robust_result = cursor.fetchone()
                    robust_token = robust_result[0] if robust_result else None
                except sqlite3.OperationalError as e:
                    if "no such table: user_tokens" in str(e):
                        print(f"⚠️ [DEBUG] user_tokens table missing - using legacy storage only")
                    else:
                        raise
                
                cursor.execute('SELECT gmail_token FROM users WHERE id = ?', (user_id,))
                legacy_result = cursor.fetchone()
                legacy_token = legacy_result[0] if legacy_result else None
                
                conn.close()
                
                # Prefer robust storage
                if robust_token:
                    print(f"🔍 [DEBUG] Token found in ROBUST storage: Yes (attempt {attempt + 1})")
                    print(f"🔍 [DEBUG] Token length: {len(str(robust_token))}")
                    return robust_token
                elif legacy_token:
                    print(f"🔍 [DEBUG] Token found in LEGACY storage: Yes (attempt {attempt + 1})")
                    print(f"🔍 [DEBUG] Token length: {len(str(legacy_token))}")
                    # Migrate to robust storage
                    try:
                        conn_migrate = self.db_manager.get_connection()
                        cursor_migrate = conn_migrate.cursor()
                        cursor_migrate.execute('''
                            INSERT OR REPLACE INTO user_tokens (user_id, token_data, gmail_email, updated_at)
                            SELECT id, gmail_token, gmail_email, CURRENT_TIMESTAMP 
                            FROM users WHERE id = ?
                        ''', (user_id,))
                        conn_migrate.commit()
                        conn_migrate.close()
                        print(f"🔄 [DEBUG] Migrated token from legacy to robust storage")
                    except Exception as e:
                        print(f"⚠️ [DEBUG] Failed to migrate token: {e}")
                    return legacy_token
                else:
                    print(f"🔍 [DEBUG] Token found: No in both storages (attempt {attempt + 1})")
                    if attempt == max_retries - 1:
                        # On final attempt, log the complete database state
                        self.check_database_state(user_id)
                        return None
                    else:
                        # Retry with delay
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                
            except sqlite3.OperationalError as e:
                if 'conn' in locals():
                    conn.close()
                
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️ Database locked during retrieval, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"❌ [DEBUG] Database operational error in get_gmail_token: {e}")
                    if attempt == max_retries - 1:
                        raise
            except Exception as e:
                if 'conn' in locals():
                    conn.close()
                
                print(f"❌ [DEBUG] Error in get_gmail_token (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                retry_delay *= 2
        
        print(f"❌ [DEBUG] Failed to get Gmail token after {max_retries} attempts")
        return None
    
    def verify_gmail_token_persistence(self, user_id, expected_token_data=None):
        """Verify that Gmail token was properly saved and can be retrieved"""
        print(f"🔍 [DEBUG] verify_gmail_token_persistence called for user_id: {user_id}")
        
        # Wait a moment for any pending transactions
        time.sleep(0.1)
        
        # Try to retrieve the token multiple times
        for attempt in range(3):
            token = self.get_gmail_token(user_id)
            if token:
                print(f"✅ [DEBUG] Token verification successful on attempt {attempt + 1}")
                if expected_token_data:
                    # Compare token data if provided
                    try:
                        import json
                        if isinstance(token, str):
                            token_dict = json.loads(token)
                        else:
                            token_dict = token
                        
                        if isinstance(expected_token_data, str):
                            expected_dict = json.loads(expected_token_data)
                        else:
                            expected_dict = expected_token_data
                        
                        if token_dict.get('refresh_token') == expected_dict.get('refresh_token'):
                            print("✅ [DEBUG] Token data matches expected value")
                            return True
                        else:
                            print("⚠️ [DEBUG] Token data doesn't match expected value")
                    except Exception as e:
                        print(f"⚠️ [DEBUG] Could not compare token data: {e}")
                
                return True
            else:
                print(f"⚠️ [DEBUG] Token verification failed on attempt {attempt + 1}")
                if attempt < 2:
                    time.sleep(0.2)  # Wait before retry
        
        print("❌ [DEBUG] Token verification failed after all attempts")
        return False
    
    def get_gmail_email(self, user_id):
        """Get user's linked Gmail email address"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT gmail_email FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def update_subscription(self, user_id, plan_name, stripe_customer_id=None, expires_at=None):
        """Update user's subscription and automatically set correct quota"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get the correct email limit for the plan
            from models import SubscriptionPlan
            plan_model = SubscriptionPlan(self.db_manager)
            plan_data = plan_model.get_plan_by_name(plan_name)
            
            if plan_data:
                email_limit = plan_data['email_limit']
                print(f"🔍 Setting quota for {plan_name} plan: {email_limit} emails/month")
            else:
                # Fallback to free plan
                free_plan = plan_model.get_plan_by_name('free')
                email_limit = free_plan['email_limit'] if free_plan else 50
                print(f"⚠️ Plan '{plan_name}' not found, using fallback quota: {email_limit}")
            
            cursor.execute('''
                UPDATE users 
                SET subscription_plan = ?, subscription_status = 'active', 
                    subscription_expires = ?, stripe_customer_id = ?,
                    monthly_usage_limit = ?
                WHERE id = ?
            ''', (plan_name, expires_at, stripe_customer_id, email_limit, user_id))
            
            conn.commit()
            conn.close()
            
            # Check if any rows were affected
            if cursor.rowcount > 0:
                print(f"✅ Subscription updated: {plan_name} with {email_limit} emails/month quota")
                return True
            else:
                print(f"❌ No rows affected in subscription update")
                return False
            
        except Exception as e:
            print(f"❌ [DEBUG] Error in update_subscription: {e}")
            return False
    
    def increment_usage(self, user_id, action_type, email_count=1):
        """Track usage with backward compatibility"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Legacy usage tracking (for backwards compatibility)
        cursor.execute('''
            INSERT INTO usage_tracking (user_id, action_type, email_count)
            VALUES (?, ?, ?)
        ''', (user_id, action_type, email_count))
        
        # Update user's usage count
        cursor.execute('''
            UPDATE users 
            SET api_usage_count = api_usage_count + ?
            WHERE id = ?
        ''', (email_count, user_id))
        
        conn.commit()
        conn.close()

    def increment_usage_for_unique_emails(self, user_id, action_type, email_ids):
        """Track usage for unique emails only - each email counted once per month"""
        if not email_ids:
            return 0
            
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get current month-year
        from datetime import datetime
        current_month = datetime.now().strftime('%Y-%m')
        
        new_emails_count = 0
        
        for email_id in email_ids:
            # Create a hash of the email content for deduplication
            import hashlib
            email_hash = hashlib.md5(f"{email_id}_{action_type}".encode()).hexdigest()
            
            try:
                # Try to insert the email as processed
                cursor.execute('''
                    INSERT INTO processed_emails (user_id, email_id, email_hash, month_year, action_type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, email_id, email_hash, current_month, action_type))
                
                # If successful, this is a new unique email
                new_emails_count += 1
                
            except sqlite3.IntegrityError:
                # Email already processed this month for this action type
                pass
        
        if new_emails_count > 0:
            # Legacy usage tracking (for backwards compatibility) 
            cursor.execute('''
                INSERT INTO usage_tracking (user_id, action_type, email_count)
                VALUES (?, ?, ?)
            ''', (user_id, action_type, new_emails_count))
            
            # Update user's usage count with only new emails
            cursor.execute('''
                UPDATE users 
                SET api_usage_count = api_usage_count + ?
                WHERE id = ?
            ''', (new_emails_count, user_id))
            
            print(f"✅ Tracked {new_emails_count} new unique emails for user {user_id} ({action_type})")
        else:
            print(f"📊 No new unique emails to track for user {user_id} ({action_type}) - all already processed this month")
        
        conn.commit()
        conn.close()
        
        return new_emails_count

    def get_unique_emails_processed_this_month(self, user_id, action_type=None):
        """Get count of unique emails processed this month"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        current_month = datetime.now().strftime('%Y-%m')
        
        if action_type:
            cursor.execute('''
                SELECT COUNT(DISTINCT email_id) 
                FROM processed_emails 
                WHERE user_id = ? AND month_year = ? AND action_type = ?
            ''', (user_id, current_month, action_type))
        else:
            cursor.execute('''
                SELECT COUNT(DISTINCT email_id) 
                FROM processed_emails 
                WHERE user_id = ? AND month_year = ?
            ''', (user_id, current_month))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def check_usage_limit(self, user_id):
        """Check if user has exceeded their usage limit using unique emails processed this month"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT subscription_plan
            FROM users WHERE id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            plan = result[0]
            
            # Get actual unique emails processed this month
            unique_emails_count = self.get_unique_emails_processed_this_month(user_id)
            
            # Get dynamic limit from subscription plan
            from models import SubscriptionPlan
            plan_model = SubscriptionPlan(self.db_manager)
            plan_data = plan_model.get_plan_by_name(plan or 'free')
            
            # Use plan's email_limit as the usage limit
            if plan_data:
                limit = plan_data['email_limit']
                print(f"🔍 Dynamic usage limit for {plan}: {limit} emails/month")
            else:
                # Fallback to free plan limit
                free_plan = plan_model.get_plan_by_name('free')
                limit = free_plan['email_limit'] if free_plan else 100
                print(f"⚠️ Plan '{plan}' not found, using free plan limit: {limit}")
            
            print(f"📊 Unique emails processed this month: {unique_emails_count}/{limit}")
            
            return {
                'usage_count': unique_emails_count,
                'limit': limit,
                'plan': plan,
                'remaining': max(0, limit - unique_emails_count),
                'exceeded': unique_emails_count >= limit
            }
        return None
    
    def update_password(self, user_id, new_password):
        """Update user's password"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        password_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        conn.commit()
        conn.close()
        
        return True
    
    def create_password_reset_token(self, user_id, token, expires_at):
        """Create a password reset token"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, token, expires_at))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Token already exists
        finally:
            conn.close()
    
    def get_user_by_reset_token(self, token):
        """Get user by reset token"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.email, u.first_name, u.last_name, prt.expires_at, prt.used
            FROM users u
            JOIN password_reset_tokens prt ON u.id = prt.user_id
            WHERE prt.token = ? AND prt.used = 0 AND prt.expires_at > CURRENT_TIMESTAMP
        ''', (token,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'email': result[1],
                'first_name': result[2],
                'last_name': result[3],
                'expires_at': result[4],
                'used': result[5]
            }
        return None
    
    def mark_reset_token_used(self, token):
        """Mark a reset token as used"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE password_reset_tokens SET used = 1 WHERE token = ?', (token,))
        conn.commit()
        conn.close()

    def check_database_state(self, user_id):
        """Check the current database state for debugging"""
        print(f"🔍 [DEBUG] check_database_state called for user_id: {user_id}")
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, gmail_email, gmail_token, 
                       subscription_plan, subscription_status
                FROM users WHERE id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                user_id, email, gmail_email, gmail_token, plan, status = result
                print(f"🔍 [DEBUG] Database state for user {user_id}:")
                print(f"   Email: {email}")
                print(f"   Gmail Email: {gmail_email or 'None'}")
                print(f"   Gmail Token: {'Present' if gmail_token else 'None'}")
                print(f"   Plan: {plan}")
                print(f"   Status: {status}")
                
                if gmail_token:
                    try:
                        import json
                        token_data = json.loads(gmail_token)
                        print(f"   Token has refresh_token: {'Yes' if token_data.get('refresh_token') else 'No'}")
                    except:
                        print("   Token is not valid JSON")
                
                return True
            else:
                print(f"❌ [DEBUG] User {user_id} not found in database")
                return False
                
        except Exception as e:
            print(f"❌ [DEBUG] Error checking database state: {e}")
            return False

    def check_database_connectivity(self):
        """Check database connectivity and health"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Test basic connectivity
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
            
            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            users_table = cursor.fetchone()
            
            conn.close()
            
            print(f"🔍 [DEBUG] Database connectivity:")
            print(f"   Basic query: {'✅ Success' if result else '❌ Failed'}")
            print(f"   Users table: {'✅ Exists' if users_table else '❌ Missing'}")
            
            return bool(result and users_table)
            
        except Exception as e:
            print(f"❌ [DEBUG] Database connectivity error: {e}")
            return False

    def force_database_sync(self):
        """Force database synchronization to ensure all pending writes are committed"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Force checkpoint to ensure WAL is synced
            cursor.execute('PRAGMA wal_checkpoint(FULL)')
            
            # Force synchronous mode temporarily
            cursor.execute('PRAGMA synchronous=FULL')
            cursor.execute('PRAGMA synchronous=NORMAL')  # Reset to normal
            
            conn.close()
            print("✅ [DEBUG] Database sync forced successfully")
            return True
        except Exception as e:
            print(f"❌ [DEBUG] Error forcing database sync: {e}")
            return False
    
    def ensure_user_integrity(self, user_id):
        """Ensure user record integrity and fix any corruption issues"""
        print(f"🔧 [DEBUG] Ensuring user integrity for user_id: {user_id}")
        
        max_retries = 3
        retry_delay = 0.2
        
        for attempt in range(max_retries):
            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                
                # Check if user exists with a comprehensive query
                cursor.execute('''
                    SELECT id, email, password_hash, first_name, last_name, 
                           subscription_plan, subscription_status, subscription_expires,
                           gmail_token, gmail_email, api_usage_count, monthly_usage_limit,
                           created_at, last_login, is_active
                    FROM users WHERE id = ?
                ''', (user_id,))
                
                user_data = cursor.fetchone()
                
                if user_data:
                    print(f"✅ [DEBUG] User {user_id} integrity check passed (attempt {attempt + 1})")
                    print(f"   - Email: {user_data[1]}")
                    print(f"   - Active: {user_data[14]}")
                    print(f"   - Has Token: {'Yes' if user_data[8] else 'No'}")
                    conn.close()
                    return True
                else:
                    print(f"❌ [DEBUG] User {user_id} not found during integrity check (attempt {attempt + 1})")
                    
                    # Try to find the user with a different approach
                    cursor.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user_id,))
                    count = cursor.fetchone()[0]
                    print(f"   - User count for ID {user_id}: {count}")
                    
                    if count == 0:
                        # User truly doesn't exist
                        print(f"❌ [DEBUG] User {user_id} confirmed missing from database")
                        conn.close()
                        return False
                    else:
                        # User exists but query failed - database corruption?
                        print(f"⚠️ [DEBUG] User {user_id} exists but query failed - potential corruption")
                        if attempt < max_retries - 1:
                            conn.close()
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            conn.close()
                            return False
                
            except Exception as e:
                if 'conn' in locals():
                    conn.close()
                print(f"❌ [DEBUG] Error during user integrity check (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
        
        return False
    
    def repair_user_token_integrity(self, user_id, token_data=None, gmail_email=None):
        """Repair user token integrity issues by ensuring proper database state"""
        print(f"🔧 [DEBUG] Repairing token integrity for user_id: {user_id}")
        
        try:
            # First ensure user integrity
            if not self.ensure_user_integrity(user_id):
                print(f"❌ [DEBUG] Cannot repair token - user {user_id} integrity check failed")
                return False
            
            # Force database sync first
            self.force_database_sync()
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Check current user state
            cursor.execute('''
                SELECT id, email, gmail_token, gmail_email, subscription_plan, subscription_status 
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                print(f"❌ [DEBUG] User {user_id} not found - cannot repair")
                conn.close()
                return False
            
            print(f"🔍 [DEBUG] Current user state: ID={user_data[0]}, Email={user_data[1]}")
            print(f"🔍 [DEBUG] Current token: {'Present' if user_data[2] else 'Missing'}")
            print(f"🔍 [DEBUG] Current gmail_email: {user_data[3]}")
            
            if token_data and not user_data[2]:
                # Token is missing but we have it - restore it
                print("🔧 [DEBUG] Restoring missing token...")
                cursor.execute('BEGIN IMMEDIATE')
                
                cursor.execute('''
                    UPDATE users 
                    SET gmail_token = ?, gmail_email = ?, last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (token_data, gmail_email, user_id))
                
                if cursor.rowcount > 0:
                    cursor.execute('COMMIT')
                    print("✅ [DEBUG] Token restoration successful")
                else:
                    cursor.execute('ROLLBACK')
                    print("❌ [DEBUG] Token restoration failed")
                    conn.close()
                    return False
            
            # Verify final state
            cursor.execute('SELECT gmail_token FROM users WHERE id = ?', (user_id,))
            final_check = cursor.fetchone()
            
            if final_check and final_check[0]:
                print("✅ [DEBUG] Token integrity repair completed successfully")
                conn.close()
                return True
            else:
                print("❌ [DEBUG] Token integrity repair failed")
                conn.close()
                return False
                
        except Exception as e:
            print(f"❌ [DEBUG] Error during token integrity repair: {e}")
            return False

    def emergency_user_recovery(self, user_id, session_data=None):
        """Emergency recovery for missing user records that exist in session"""
        print(f"🚨 [EMERGENCY] Starting user recovery for user_id: {user_id}")
        
        try:
            # First, double-check if user really doesn't exist
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Check if user exists with comprehensive query
            cursor.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user_id,))
            user_count = cursor.fetchone()[0]
            
            if user_count > 0:
                print(f"✅ [EMERGENCY] User {user_id} actually exists - false alarm")
                conn.close()
                return True
            
            print(f"🚨 [EMERGENCY] User {user_id} confirmed missing - attempting recovery")
            
            # Check if we have session data to reconstruct the user
            if not session_data:
                print(f"❌ [EMERGENCY] No session data provided for user recovery")
                conn.close()
                return False
            
            # Extract user info from session
            email = session_data.get('user_email', f'recovered_user_{user_id}@unknown.com')
            name = session_data.get('user_name', 'Recovered User')
            plan = session_data.get('subscription_plan', 'free')
            status = session_data.get('subscription_status', 'active')
            
            print(f"🔧 [EMERGENCY] Reconstructing user with email: {email}, name: {name}")
            
            # Create emergency user record
            cursor.execute('BEGIN IMMEDIATE')
            
            cursor.execute('''
                INSERT INTO users (id, email, password_hash, first_name, last_name, 
                                 subscription_plan, subscription_status, subscription_expires,
                                 created_at, last_login, is_active, api_usage_count, monthly_usage_limit)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 0, 100)
            ''', (
                user_id, 
                email, 
                'EMERGENCY_RECOVERY_NO_PASSWORD',  # They'll need to reset password
                name.split()[0] if name else 'Recovered',
                ' '.join(name.split()[1:]) if len(name.split()) > 1 else 'User',
                plan,
                status
            ))
            
            # Verify the insert worked
            if cursor.rowcount > 0:
                cursor.execute('COMMIT')
                print(f"✅ [EMERGENCY] User {user_id} successfully recovered")
                
                # Verify the user can be retrieved
                cursor.execute('SELECT id, email FROM users WHERE id = ?', (user_id,))
                verification = cursor.fetchone()
                
                if verification:
                    print(f"✅ [EMERGENCY] Recovery verified: {verification[1]}")
                    conn.close()
                    return True
                else:
                    print(f"❌ [EMERGENCY] Recovery verification failed")
                    conn.close()
                    return False
            else:
                cursor.execute('ROLLBACK')
                print(f"❌ [EMERGENCY] User recovery insert failed")
                conn.close()
                return False
                
        except Exception as e:
            if 'conn' in locals():
                try:
                    cursor.execute('ROLLBACK')
                except:
                    pass
                conn.close()
            print(f"❌ [EMERGENCY] User recovery failed: {e}")
            return False
    
    def check_and_repair_user_session_mismatch(self, user_id, session_data=None):
        """Check for and repair user/session mismatches"""
        print(f"🔍 [DEBUG] Checking user/session mismatch for user_id: {user_id}")
        
        # First check if user exists
        if not self.ensure_user_integrity(user_id):
            print(f"⚠️ [DEBUG] User integrity check failed - attempting emergency recovery")
            
            if session_data:
                recovery_success = self.emergency_user_recovery(user_id, session_data)
                if recovery_success:
                    print(f"✅ [DEBUG] Emergency recovery successful")
                    return True
                else:
                    print(f"❌ [DEBUG] Emergency recovery failed")
                    return False
            else:
                print(f"❌ [DEBUG] No session data for emergency recovery")
                return False
        
        return True

    def count_users(self):
        """Return total number of users"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_users_paginated(self, offset=0, limit=20):
        """Return paginated list of users"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, email, first_name, last_name, subscription_plan, subscription_status, created_at, last_login
            FROM users WHERE is_active = 1
            ORDER BY id ASC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'email': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'subscription_plan': row[4],
                'subscription_status': row[5],
                'created_at': row[6],
                'last_login': row[7]
            })
        conn.close()
        return users

    def search_users(self, query):
        """Search users by email, first name, or last name (case-insensitive, partial match)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        like_query = f"%{query.lower()}%"
        cursor.execute('''
            SELECT id, email, first_name, last_name, subscription_plan, subscription_status, created_at, last_login
            FROM users WHERE is_active = 1 AND (
                LOWER(email) LIKE ? OR LOWER(first_name) LIKE ? OR LOWER(last_name) LIKE ?
            )
            ORDER BY id ASC
            LIMIT 50
        ''', (like_query, like_query, like_query))
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'email': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'subscription_plan': row[4],
                'subscription_status': row[5],
                'created_at': row[6],
                'last_login': row[7]
            })
        conn.close()
        return users

    def set_gmail_email(self, user_id, gmail_email):
        """Set or clear the user's linked Gmail email address"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET gmail_email = ? WHERE id = ?', (gmail_email, user_id))
        conn.commit()
        conn.close()

    def delete_gmail_token(self, user_id):
        """Delete user's Gmail token from both user_tokens and users tables"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM user_tokens WHERE user_id = ?', (user_id,))
            cursor.execute('UPDATE users SET gmail_token = NULL WHERE id = ?', (user_id,))
            conn.commit()
        finally:
            conn.close()
        return True

class SubscriptionPlan:
    """Subscription plan model"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_all_plans(self):
        """Get all active subscription plans"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, price_monthly, price_yearly, email_limit, features,
                   stripe_price_id_monthly, stripe_price_id_yearly
            FROM subscription_plans WHERE is_active = 1
            ORDER BY price_monthly
        ''')
        
        plans = []
        for row in cursor.fetchall():
            plans.append({
                'id': row[0],
                'name': row[1],
                'price_monthly': float(row[2]),
                'price_yearly': float(row[3]),
                'email_limit': row[4],
                'features': row[5].split(', ') if row[5] else [],
                'stripe_price_id_monthly': row[6],
                'stripe_price_id_yearly': row[7]
            })
        
        conn.close()
        return plans
    
    def get_plan_by_name(self, plan_name):
        """Get plan by name"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, price_monthly, price_yearly, email_limit, features,
                   stripe_price_id_monthly, stripe_price_id_yearly
            FROM subscription_plans WHERE name = ? AND is_active = 1
        ''', (plan_name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'price_monthly': float(row[2]),
                'price_yearly': float(row[3]),
                'email_limit': row[4],
                'features': row[5].split(', ') if row[5] else [],
                'stripe_price_id_monthly': row[6],
                'stripe_price_id_yearly': row[7]
            }
        return None

class PaymentRecord:
    """Payment record model"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_payment_record(self, user_id, stripe_payment_intent_id, amount, 
                            plan_name, billing_period, status='pending', currency='usd', payment_method='card'):
        """Create a new payment record"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payment_records 
            (user_id, stripe_payment_intent_id, amount, currency, plan_name, billing_period, status, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, stripe_payment_intent_id, amount, currency, plan_name, billing_period, status, payment_method))
        
        payment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return payment_id
    
    def update_payment_status(self, stripe_payment_intent_id, status):
        """Update payment status"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE payment_records 
            SET status = ? 
            WHERE stripe_payment_intent_id = ?
        ''', (status, stripe_payment_intent_id))
        
        conn.commit()
        conn.close()
    
    def get_user_payments(self, user_id):
        """Get all payments for a user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, stripe_payment_intent_id, amount, currency, status, 
                   plan_name, billing_period, payment_method, created_at
            FROM payment_records 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        payments = []
        for row in cursor.fetchall():
            payments.append({
                'id': row[0],
                'stripe_payment_intent_id': row[1],
                'amount': float(row[2]),
                'currency': row[3],
                'status': row[4],
                'plan_name': row[5],
                'billing_period': row[6],
                'payment_method': row[7],
                'created_at': row[8]
            })
        
        conn.close()
        return payments

    def get_payments_by_user(self, user_id):
        """Get all payments for a user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, stripe_payment_intent_id, amount, currency, status, 
                   plan_name, billing_period, payment_method, created_at
            FROM payment_records 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        
        payments = []
        for row in cursor.fetchall():
            payments.append({
                'id': row[0],
                'user_id': row[1],
                'stripe_payment_intent_id': row[2],
                'amount': float(row[3]),
                'currency': row[4],
                'status': row[5],
                'plan_name': row[6],
                'billing_period': row[7],
                'payment_method': row[8],
                'created_at': row[9]
            })
        
        conn.close()
        return payments

    def get_payment_by_reference(self, reference):
        """Get payment by reference (payment ID)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, stripe_payment_intent_id, amount, currency, status, 
                   plan_name, billing_period, payment_method, created_at
            FROM payment_records 
            WHERE stripe_payment_intent_id = ?
        ''', (reference,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'stripe_payment_intent_id': row[2],
                'amount': float(row[3]),
                'currency': row[4],
                'status': row[5],
                'plan_name': row[6],
                'billing_period': row[7],
                'payment_method': row[8],
                'created_at': row[9]
            }
        return None 