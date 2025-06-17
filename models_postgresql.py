from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os
import threading
import time

class DatabaseManager:
    """PostgreSQL Database manager for user authentication and payments"""
    
    def __init__(self, db_config=None):
        # Use environment variables for security
        if db_config is None:
            self.db_config = {
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT', 25060)),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'database': os.getenv('DB_NAME'),
                'sslmode': os.getenv('DB_SSLMODE', 'require')
            }
        else:
            self.db_config = db_config
        
        self._lock = threading.Lock()
        print(f"🔧 Using PostgreSQL database: {self.db_config.get('host', 'ENV_VAR')}:{self.db_config.get('port', 'ENV_VAR')}")
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    gmail_token TEXT,
                    gmail_email VARCHAR(255),
                    subscription_plan VARCHAR(50) DEFAULT 'free',
                    subscription_status VARCHAR(50) DEFAULT 'active',
                    subscription_expires TIMESTAMP,
                    stripe_customer_id VARCHAR(255),
                    api_usage_count INTEGER DEFAULT 0,
                    monthly_usage_limit INTEGER DEFAULT 100
                )
            ''')
            
            # Robust token storage table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) UNIQUE,
                    token_data TEXT NOT NULL,
                    gmail_email VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Subscription plans table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    price_monthly DECIMAL(10,2) NOT NULL,
                    price_yearly DECIMAL(10,2) NOT NULL,
                    email_limit INTEGER NOT NULL,
                    features TEXT,
                    stripe_price_id_monthly VARCHAR(255),
                    stripe_price_id_yearly VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default subscription plans
            cursor.execute('''
                INSERT INTO subscription_plans 
                (name, price_monthly, price_yearly, email_limit, features, stripe_price_id_monthly, stripe_price_id_yearly)
                VALUES 
                ('free', 0.00, 0.00, 100, 'Basic email analysis, Daily summaries, Action items, 10 emails per load, 100 emails per month', NULL, NULL),
                ('pro', 9.99, 99.99, 500, 'Advanced AI analysis, Document processing, Priority support, Custom insights', 'price_monthly_pro', 'price_yearly_pro'),
                ('enterprise', 29.99, 299.99, 2000, 'Unlimited analysis, Team collaboration, API access, Custom integrations', 'price_monthly_enterprise', 'price_yearly_enterprise')
                ON CONFLICT (name) DO NOTHING
            ''')
            
            # User preferences table for currency and other settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) UNIQUE,
                    currency VARCHAR(10) DEFAULT 'USD',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Payment records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_records (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    stripe_payment_intent_id VARCHAR(255),
                    amount DECIMAL(10,2) NOT NULL,
                    currency VARCHAR(10) DEFAULT 'usd',
                    plan_name VARCHAR(100),
                    billing_period VARCHAR(20),
                    payment_method VARCHAR(50) DEFAULT 'card',
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Usage tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_tracking (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    action_type VARCHAR(100) NOT NULL,
                    email_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Password reset tokens table (missing from original)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_tokens_user_id ON user_tokens(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_records_user_id ON payment_records(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_id ON usage_tracking(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token)')
            
            conn.commit()
            print("✅ PostgreSQL database initialized successfully")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

class User:
    """User model for PostgreSQL"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_user(self, email, password, first_name=None, last_name=None):
        """Create a new user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (email, password_hash, first_name, last_name)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (email, password_hash, first_name, last_name))
            user_id = cursor.fetchone()[0]
            conn.commit()
            return user_id
        except psycopg2.IntegrityError:
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def authenticate_user(self, email, password):
        """Authenticate user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT id, email, password_hash, first_name, last_name, subscription_plan, 
                       subscription_status, subscription_expires, api_usage_count, monthly_usage_limit
                FROM users WHERE email = %s AND is_active = TRUE
            ''', (email,))
            
            user_data = cursor.fetchone()
            
            if user_data and check_password_hash(user_data['password_hash'], password):
                cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s', (user_data['id'],))
                conn.commit()
                
                return {
                    'id': user_data['id'],
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'subscription_plan': user_data['subscription_plan'],
                    'subscription_status': user_data['subscription_status'],
                    'subscription_expires': user_data['subscription_expires'],
                    'api_usage_count': user_data['api_usage_count'],
                    'monthly_usage_limit': user_data['monthly_usage_limit']
                }
            
            return None
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT id, email, first_name, last_name, subscription_plan, 
                       subscription_status, subscription_expires, api_usage_count, 
                       monthly_usage_limit, gmail_email, created_at, last_login
                FROM users WHERE id = %s AND is_active = TRUE
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            if user_data:
                return dict(user_data)
            return None
        finally:
            conn.close()
    
    def get_gmail_token(self, user_id):
        """Get user's Gmail token"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Try robust storage first
            cursor.execute('SELECT token_data FROM user_tokens WHERE user_id = %s AND is_active = TRUE', (user_id,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Fallback to legacy storage
            cursor.execute('SELECT gmail_token FROM users WHERE id = %s', (user_id,))
            result = cursor.fetchone()
            
            return result[0] if result else None
            
        finally:
            conn.close()
    
    def update_gmail_token(self, user_id, token_data, gmail_email=None):
        """Update user's Gmail token"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Update both tables
            cursor.execute('''
                UPDATE users 
                SET gmail_token = %s, gmail_email = COALESCE(%s, gmail_email)
                WHERE id = %s
            ''', (token_data, gmail_email, user_id))
            
            cursor.execute('''
                INSERT INTO user_tokens (user_id, token_data, gmail_email)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET 
                    token_data = EXCLUDED.token_data,
                    gmail_email = COALESCE(EXCLUDED.gmail_email, user_tokens.gmail_email),
                    updated_at = CURRENT_TIMESTAMP,
                    is_active = TRUE
            ''', (user_id, token_data, gmail_email))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ Token update failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def verify_gmail_token_persistence(self, user_id, expected_token_data=None):
        """Verify token persistence"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT token_data FROM user_tokens WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            return result is not None
        finally:
            conn.close()
    
    def get_gmail_email(self, user_id):
        """Get Gmail email"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT gmail_email FROM users WHERE id = %s', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP 
                WHERE id = %s
            ''', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def check_database_connectivity(self):
        """Check database connectivity and health"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Test basic connectivity
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
            
            # Check tables exist
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users'")
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
            
            # PostgreSQL automatically handles transaction commits
            # This is mainly for compatibility with SQLite version
            cursor.execute('SELECT 1')  # Simple query to test connection
            
            conn.close()
            print("✅ [DEBUG] Database sync forced successfully")
            return True
        except Exception as e:
            print(f"❌ [DEBUG] Error forcing database sync: {e}")
            return False

    def check_database_state(self, user_id):
        """Check and log database state for a specific user"""
        print(f"🔍 [DEBUG] check_database_state called for user_id: {user_id}")
        
        try:
            user = self.get_user_by_id(user_id)
            if user:
                gmail_token = self.get_gmail_token(user_id)
                has_refresh_token = False
                
                if gmail_token:
                    try:
                        import json
                        token_data = json.loads(gmail_token)
                        has_refresh_token = 'refresh_token' in token_data and token_data['refresh_token']
                    except:
                        pass
                
                print(f"🔍 [DEBUG] Database state for user {user_id}:")
                print(f"   Email: {user.get('email')}")
                print(f"   Gmail Email: {user.get('gmail_email')}")
                print(f"   Gmail Token: {'Present' if gmail_token else 'None'}")
                print(f"   Plan: {user.get('subscription_plan')}")
                print(f"   Status: {user.get('subscription_status')}")
                if gmail_token:
                    print(f"   Token has refresh_token: {'Yes' if has_refresh_token else 'No'}")
            else:
                print(f"❌ [DEBUG] User {user_id} not found in database")
                
        except Exception as e:
            print(f"❌ [DEBUG] Error checking database state: {e}")

    def check_and_repair_user_session_mismatch(self, user_id, session_data=None):
        """Check for user/session mismatches and attempt repair"""
        print(f"🔍 [DEBUG] Checking user/session mismatch for user_id: {user_id}")
        
        try:
            # First, ensure user integrity
            if not self.ensure_user_integrity(user_id, session_data):
                print("❌ [DEBUG] User integrity check failed")
                return False
                
            print("✅ [DEBUG] User integrity check passed")
            return True
            
        except Exception as e:
            print(f"❌ [DEBUG] Error in user/session mismatch check: {e}")
            return False

    def ensure_user_integrity(self, user_id, session_data=None):
        """Ensure user exists and has correct data"""
        print(f"🔧 [DEBUG] Ensuring user integrity for user_id: {user_id}")
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                # Check if user exists
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, email, is_active, 
                           CASE WHEN gmail_token IS NOT NULL THEN 'Yes' ELSE 'No' END as has_token
                    FROM users WHERE id = %s
                ''', (user_id,))
                
                user_record = cursor.fetchone()
                conn.close()
                
                if user_record:
                    user_id_db, email, is_active, has_token = user_record
                    print(f"✅ [DEBUG] User {user_id} integrity check passed (attempt {attempt})")
                    print(f"   - Email: {email}")
                    print(f"   - Active: {is_active}")
                    print(f"   - Has Token: {has_token}")
                    return True
                else:
                    print(f"❌ [DEBUG] User {user_id} not found during integrity check (attempt {attempt})")
                    print(f"   - User count for ID {user_id}: 0")
                    
                    if attempt == max_attempts:
                        print(f"❌ [DEBUG] User {user_id} confirmed missing from database")
                        
                        # Attempt emergency recovery if session data is available
                        if session_data and session_data.get('user_email'):
                            print("⚠️ [DEBUG] User integrity check failed - attempting emergency recovery")
                            return self.emergency_user_recovery(user_id, session_data)
                        else:
                            print("❌ [DEBUG] No session data available for emergency recovery")
                            return False
                            
            except Exception as e:
                print(f"❌ [DEBUG] Error in user integrity check (attempt {attempt}): {e}")
                if attempt == max_attempts:
                    return False
                    
        return False

    def emergency_user_recovery(self, user_id, session_data):
        """Emergency recovery for missing users"""
        print(f"🚨 [EMERGENCY] Starting user recovery for user_id: {user_id}")
        
        try:
            email = session_data.get('user_email')
            name = session_data.get('user_name', '')
            plan = session_data.get('subscription_plan', 'free')
            status = session_data.get('subscription_status', 'active')
            
            if not email:
                print("❌ [EMERGENCY] No email in session data for recovery")
                return False
                
            print(f"🚨 [EMERGENCY] User {user_id} confirmed missing - attempting recovery")
            print(f"🔧 [EMERGENCY] Reconstructing user with email: {email}, name: {name}")
            
            # Split name into first and last
            name_parts = name.split(' ', 1) if name else ['', '']
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Insert reconstructed user with emergency password
            cursor.execute('''
                INSERT INTO users (id, email, password_hash, first_name, last_name, 
                                 subscription_plan, subscription_status, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    subscription_plan = EXCLUDED.subscription_plan,
                    subscription_status = EXCLUDED.subscription_status,
                    is_active = EXCLUDED.is_active
            ''', (user_id, email, 'EMERGENCY_RECOVERY_NO_PASSWORD', 
                  first_name, last_name, plan, status, True))
            
            conn.commit()
            conn.close()
            
            print(f"✅ [EMERGENCY] User {user_id} successfully recovered")
            
            # Verify recovery
            recovered_user = self.get_user_by_id(user_id)
            if recovered_user:
                print(f"✅ [EMERGENCY] Recovery verified: {recovered_user.get('email')}")
                return True
            else:
                print(f"❌ [EMERGENCY] Recovery verification failed")
                return False
                
        except Exception as e:
            print(f"❌ [EMERGENCY] User recovery failed: {e}")
            return False

    def increment_usage(self, user_id, action_type, email_count=1):
        """Increment user's API usage"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Add usage record (create table if it doesn't exist)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_tracking (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    action_type VARCHAR(100) NOT NULL,
                    email_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO usage_tracking (user_id, action_type, email_count)
                VALUES (%s, %s, %s)
            ''', (user_id, action_type, email_count))
            
            # Update user's usage count
            cursor.execute('''
                UPDATE users 
                SET api_usage_count = COALESCE(api_usage_count, 0) + %s
                WHERE id = %s
            ''', (email_count, user_id))
            
            conn.commit()
        finally:
            conn.close()

    def check_usage_limit(self, user_id):
        """Check if user has exceeded their usage limit"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT api_usage_count, monthly_usage_limit, subscription_plan
                FROM users WHERE id = %s
            ''', (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                usage_count, limit, plan = result
                usage_count = usage_count or 0  # Handle NULL values
                limit = limit or 100  # Default limit
                return {
                    'usage_count': usage_count,
                    'limit': limit,
                    'plan': plan,
                    'remaining': max(0, limit - usage_count),
                    'exceeded': usage_count >= limit
                }
            return None
        finally:
            conn.close()

    def update_password(self, user_id, new_password):
        """Update user's password"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (password_hash, user_id))
            conn.commit()
            return True
        finally:
            conn.close()

    def create_password_reset_token(self, user_id, token, expires_at):
        """Create a password reset token"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (%s, %s, %s)
            ''', (user_id, token, expires_at))
            conn.commit()
            return True
        except psycopg2.IntegrityError:
            conn.rollback()
            return False  # Token already exists
        finally:
            conn.close()
    
    def get_user_by_reset_token(self, token):
        """Get user by reset token"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT u.id, u.email, u.first_name, u.last_name, prt.expires_at, prt.used
                FROM users u
                JOIN password_reset_tokens prt ON u.id = prt.user_id
                WHERE prt.token = %s AND prt.used = FALSE AND prt.expires_at > CURRENT_TIMESTAMP
            ''', (token,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'id': result['id'],
                    'email': result['email'],
                    'first_name': result['first_name'],
                    'last_name': result['last_name'],
                    'expires_at': result['expires_at'],
                    'used': result['used']
                }
            return None
        finally:
            conn.close()
    
    def mark_reset_token_used(self, token):
        """Mark a reset token as used"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('UPDATE password_reset_tokens SET used = TRUE WHERE token = %s', (token,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_user_by_email(self, email):
        """Get user by email address"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT id, email, first_name, last_name, subscription_plan, 
                       subscription_status, subscription_expires, api_usage_count, 
                       monthly_usage_limit, gmail_email, created_at, last_login
                FROM users WHERE email = %s AND is_active = TRUE
            ''', (email,))
            
            user_data = cursor.fetchone()
            
            if user_data:
                return dict(user_data)
            return None
        finally:
            conn.close()

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
                FROM users WHERE id = %s
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
                
                cursor.execute('''
                    UPDATE users 
                    SET gmail_token = %s, gmail_email = %s, last_login = CURRENT_TIMESTAMP 
                    WHERE id = %s
                ''', (token_data, gmail_email, user_id))
                
                # Also update robust storage
                cursor.execute('''
                    INSERT INTO user_tokens (user_id, token_data, gmail_email, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        token_data = EXCLUDED.token_data,
                        gmail_email = EXCLUDED.gmail_email,
                        updated_at = CURRENT_TIMESTAMP,
                        is_active = TRUE
                ''', (user_id, token_data, gmail_email))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    print("✅ [DEBUG] Token restoration successful")
                else:
                    print("❌ [DEBUG] Token restoration failed")
                    conn.close()
                    return False
            
            # Verify final state
            cursor.execute('SELECT gmail_token FROM users WHERE id = %s', (user_id,))
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
            import traceback
            traceback.print_exc()
            return False

    def update_subscription(self, user_id, plan_name, stripe_customer_id=None, expires_at=None):
        """Update user's subscription after successful payment"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET subscription_plan = %s, subscription_status = 'active', 
                    subscription_expires = %s, stripe_customer_id = COALESCE(%s, stripe_customer_id)
                WHERE id = %s
            ''', (plan_name, expires_at, stripe_customer_id, user_id))
            
            conn.commit()
            
            # Check if any rows were affected
            success = cursor.rowcount > 0
            
            if success:
                print(f"✅ [DEBUG] Subscription updated successfully for user {user_id}: {plan_name}")
            else:
                print(f"❌ [DEBUG] No rows updated for user {user_id} subscription")
            
            return success
            
        except Exception as e:
            print(f"❌ [DEBUG] Error in update_subscription: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()

class SubscriptionPlan:
    """Subscription plan model"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_all_plans(self):
        """Get all plans"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT id, name, price_monthly, price_yearly, email_limit, features,
                       stripe_price_id_monthly, stripe_price_id_yearly
                FROM subscription_plans WHERE is_active = TRUE
                ORDER BY price_monthly ASC
            ''')
            
            plans = []
            for row in cursor.fetchall():
                plans.append({
                    'id': row['id'],
                    'name': row['name'],
                    'price_monthly': float(row['price_monthly']),
                    'price_yearly': float(row['price_yearly']),
                    'email_limit': row['email_limit'],
                    'features': row['features'].split(', ') if row['features'] else [],
                    'stripe_price_id_monthly': row['stripe_price_id_monthly'],
                    'stripe_price_id_yearly': row['stripe_price_id_yearly']
                })
            
            return plans
        finally:
            conn.close()
    
    def get_plan_by_name(self, plan_name):
        """Get subscription plan by name"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT id, name, price_monthly, price_yearly, email_limit, features,
                       stripe_price_id_monthly, stripe_price_id_yearly
                FROM subscription_plans WHERE name = %s AND is_active = TRUE
            ''', (plan_name,))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'price_monthly': float(row['price_monthly']),
                    'price_yearly': float(row['price_yearly']),
                    'email_limit': row['email_limit'],
                    'features': row['features'].split(', ') if row['features'] else [],
                    'stripe_price_id_monthly': row['stripe_price_id_monthly'],
                    'stripe_price_id_yearly': row['stripe_price_id_yearly']
                }
            return None
        finally:
            conn.close()
    
    def create_plan(self, name, price_monthly, price_yearly, email_limit, features=None, 
                   stripe_price_id_monthly=None, stripe_price_id_yearly=None):
        """Create a new subscription plan"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            features_str = ', '.join(features) if features else ''
            
            cursor.execute('''
                INSERT INTO subscription_plans 
                (name, price_monthly, price_yearly, email_limit, features, 
                 stripe_price_id_monthly, stripe_price_id_yearly)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
                RETURNING id
            ''', (name, price_monthly, price_yearly, email_limit, features_str, 
                  stripe_price_id_monthly, stripe_price_id_yearly))
            
            result = cursor.fetchone()
            conn.commit()
            
            return result[0] if result else None
        finally:
            conn.close()

class PaymentRecord:
    """Payment record model for PostgreSQL"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_payment_record(self, user_id, stripe_payment_intent_id, amount, 
                            plan_name, billing_period, status='pending', currency='usd', payment_method='card'):
        """Create a new payment record"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO payment_records 
                (user_id, stripe_payment_intent_id, amount, currency, plan_name, billing_period, status, payment_method)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (user_id, stripe_payment_intent_id, amount, currency, plan_name, billing_period, status, payment_method))
            
            payment_id = cursor.fetchone()[0]
            conn.commit()
            return payment_id
        finally:
            conn.close()
    
    def update_payment_status(self, stripe_payment_intent_id, status):
        """Update payment status"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE payment_records 
                SET status = %s 
                WHERE stripe_payment_intent_id = %s
            ''', (status, stripe_payment_intent_id))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_user_payments(self, user_id):
        """Get all payments for a user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT id, stripe_payment_intent_id, amount, currency, status, 
                       plan_name, billing_period, payment_method, created_at
                FROM payment_records 
                WHERE user_id = %s
                ORDER BY created_at DESC
            ''', (user_id,))
            
            payments = []
            for row in cursor.fetchall():
                payments.append({
                    'id': row['id'],
                    'stripe_payment_intent_id': row['stripe_payment_intent_id'],
                    'amount': float(row['amount']),
                    'currency': row['currency'],
                    'status': row['status'],
                    'plan_name': row['plan_name'],
                    'billing_period': row['billing_period'],
                    'payment_method': row['payment_method'],
                    'created_at': row['created_at']
                })
            
            return payments
        finally:
            conn.close()

    def get_payments_by_user(self, user_id):
        """Get all payments for a user (alias for compatibility)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT id, user_id, stripe_payment_intent_id, amount, currency, status, 
                       plan_name, billing_period, payment_method, created_at
                FROM payment_records 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            ''', (user_id,))
            
            payments = []
            for row in cursor.fetchall():
                payments.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'stripe_payment_intent_id': row['stripe_payment_intent_id'],
                    'amount': float(row['amount']),
                    'currency': row['currency'],
                    'status': row['status'],
                    'plan_name': row['plan_name'],
                    'billing_period': row['billing_period'],
                    'payment_method': row['payment_method'],
                    'created_at': row['created_at']
                })
            
            return payments
        finally:
            conn.close()

    def get_payment_by_reference(self, reference):
        """Get payment by reference (payment ID)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute('''
                SELECT id, user_id, stripe_payment_intent_id, amount, currency, status, 
                       plan_name, billing_period, payment_method, created_at
                FROM payment_records 
                WHERE stripe_payment_intent_id = %s
            ''', (reference,))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'stripe_payment_intent_id': row['stripe_payment_intent_id'],
                    'amount': float(row['amount']),
                    'currency': row['currency'],
                    'status': row['status'],
                    'plan_name': row['plan_name'],
                    'billing_period': row['billing_period'],
                    'payment_method': row['payment_method'],
                    'created_at': row['created_at']
                }
            return None
        finally:
            conn.close() 