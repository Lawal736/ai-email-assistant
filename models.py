from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import threading
import time

class DatabaseManager:
    """Database manager for user authentication and payments"""
    
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrency
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA cache_size=10000')
        cursor.execute('PRAGMA temp_store=MEMORY')
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                gmail_token TEXT,
                gmail_email TEXT,
                subscription_plan TEXT DEFAULT 'free',
                subscription_status TEXT DEFAULT 'active',
                subscription_expires TIMESTAMP,
                stripe_customer_id TEXT,
                api_usage_count INTEGER DEFAULT 0,
                monthly_usage_limit INTEGER DEFAULT 100
            )
        ''')
        
        # Subscription plans table
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
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Payment records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stripe_payment_intent_id TEXT,
                amount DECIMAL(10,2) NOT NULL,
                currency TEXT DEFAULT 'usd',
                status TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                billing_period TEXT NOT NULL,
                payment_method TEXT DEFAULT 'card',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Usage tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                email_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Password reset tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                currency TEXT DEFAULT 'USD',
                timezone TEXT DEFAULT 'UTC',
                language TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id)
            )
        ''')
        
        # Insert default subscription plans
        cursor.execute('''
            INSERT OR IGNORE INTO subscription_plans 
            (name, price_monthly, price_yearly, email_limit, features, stripe_price_id_monthly, stripe_price_id_yearly)
            VALUES 
            ('free', 0.00, 0.00, 50, 'Basic email analysis, Daily summaries, Action items', NULL, NULL),
            ('pro', 9.99, 99.99, 500, 'Advanced AI analysis, Document processing, Priority support, Custom insights', 'price_monthly_pro', 'price_yearly_pro'),
            ('enterprise', 29.99, 299.99, 2000, 'Unlimited analysis, Team collaboration, API access, Custom integrations', 'price_monthly_enterprise', 'price_yearly_enterprise')
        ''')
        
        conn.commit()
        conn.close()
    
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
        """Update user's Gmail token and optionally Gmail email address"""
        print(f"🔍 [DEBUG] update_gmail_token called for user_id: {user_id}")
        print(f"🔍 [DEBUG] token_data length: {len(str(token_data)) if token_data else 0}")
        print(f"🔍 [DEBUG] gmail_email: {gmail_email}")
        
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                
                # Always update both fields - if gmail_email is None, it will clear the field
                cursor.execute('UPDATE users SET gmail_token = ?, gmail_email = ? WHERE id = ?', (token_data, gmail_email, user_id))
                
                rows_affected = cursor.rowcount
                print(f"🔍 [DEBUG] Rows affected by update: {rows_affected}")
                
                conn.commit()
                conn.close()
                
                print(f"✅ [DEBUG] Gmail token update completed for user_id: {user_id}")
                return True
                
            except sqlite3.OperationalError as e:
                conn.close() if 'conn' in locals() else None
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️ Database locked during update, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"❌ [DEBUG] Database error in update_gmail_token: {e}")
                    raise
            except Exception as e:
                conn.close() if 'conn' in locals() else None
                print(f"❌ [DEBUG] Error in update_gmail_token: {e}")
                raise
        
        print(f"❌ [DEBUG] Failed to update Gmail token after {max_retries} attempts")
        return False
    
    def get_gmail_token(self, user_id):
        """Get user's Gmail token with retry logic"""
        print(f"🔍 [DEBUG] get_gmail_token called for user_id: {user_id}")
        
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT gmail_token FROM users WHERE id = ?', (user_id,))
                result = cursor.fetchone()
                conn.close()
                
                token_found = result[0] if result else None
                print(f"🔍 [DEBUG] Token found: {'Yes' if token_found else 'No'}")
                if token_found:
                    print(f"🔍 [DEBUG] Token length: {len(str(token_found))}")
                
                return token_found
                
            except sqlite3.OperationalError as e:
                conn.close() if 'conn' in locals() else None
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️ Database locked during retrieval, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"❌ [DEBUG] Database error in get_gmail_token: {e}")
                    raise
            except Exception as e:
                conn.close() if 'conn' in locals() else None
                print(f"❌ [DEBUG] Error in get_gmail_token: {e}")
                raise
        
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
        """Update user's subscription"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET subscription_plan = ?, subscription_status = 'active', 
                    subscription_expires = ?, stripe_customer_id = ?
                WHERE id = ?
            ''', (plan_name, expires_at, stripe_customer_id, user_id))
            
            conn.commit()
            conn.close()
            
            # Check if any rows were affected
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"❌ [DEBUG] Error in update_subscription: {e}")
            return False
    
    def increment_usage(self, user_id, action_type, email_count=1):
        """Increment user's API usage"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Add usage record
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
    
    def check_usage_limit(self, user_id):
        """Check if user has exceeded their usage limit"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT api_usage_count, monthly_usage_limit, subscription_plan
            FROM users WHERE id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            usage_count, limit, plan = result
            return {
                'usage_count': usage_count,
                'limit': limit,
                'plan': plan,
                'remaining': max(0, limit - usage_count),
                'exceeded': usage_count >= limit
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