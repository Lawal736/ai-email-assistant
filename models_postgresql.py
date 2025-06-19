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
                    user_id INTEGER NOT NULL UNIQUE,
                    token_data TEXT NOT NULL,
                    gmail_email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
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
            
            # Create processed_emails table for unique email tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    email_id TEXT NOT NULL,
                    email_hash TEXT NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            
            # Create user_vip_senders table for VIP sender management
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_vip_senders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    vip_email VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, vip_email)
                )
            ''')
            
            # Create index for VIP sender lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_vip_senders_lookup 
                ON user_vip_senders(user_id)
            ''')
            
            # Create user_email_filters table for user-level email filtering
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_email_filters (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    filter_type VARCHAR(32) NOT NULL, -- sender, subject, keyword, regex
                    pattern TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, filter_type, pattern)
                )
            ''')
            # Create index for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_email_filters_lookup 
                ON user_email_filters(user_id)
            ''')
            
            # Create user_email_analysis table for caching AI analysis results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_email_analysis (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    email_id VARCHAR(255) NOT NULL,
                    ai_priority VARCHAR(32),
                    ai_priority_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, email_id)
                )
            ''')
            # Create index for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_email_analysis_lookup ON user_email_analysis (user_id, email_id)')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_tokens_user_id ON user_tokens(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_records_user_id ON payment_records(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_id ON usage_tracking(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token)')
            
            # Insert default subscription plans if they don't exist
            cursor.execute('''
                    INSERT INTO subscription_plans 
                      (name, price_monthly, price_yearly, email_limit, features, stripe_price_id_monthly, stripe_price_id_yearly)
                      VALUES 
                               ('free', 0.00, 0.00, 100, 'Basic email analysis, Daily AI-generated summaries, Action items extraction, Email limit: 100/month', NULL, NULL),
                ('pro', 19.99, 199.99, 500, 'Everything in Free plus Advanced AI analysis, Document processing, Priority support, Custom insights, Email limit: 500/month', NULL, NULL),
                ('enterprise', 49.99, 499.99, 2000, 'Everything in Pro plus Unlimited AI-powered analysis, Team collaboration, API access, Custom integrations, Email limit: 2,000/month', NULL, NULL)
                    ON CONFLICT (name) DO NOTHING
             ''')
            
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
        """Track usage with backward compatibility"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Legacy usage tracking (for backwards compatibility)
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

    def increment_usage_for_unique_emails(self, user_id, action_type, email_ids):
        """Track usage for unique emails only - each email counted once per month"""
        if not email_ids:
            return 0
            
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
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
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (user_id, email_id, email_hash, current_month, action_type))
                    
                    # If successful, this is a new unique email
                    new_emails_count += 1
                    
                except psycopg2.IntegrityError:
                    # Email already processed this month for this action type
                    conn.rollback()
                    continue
            
            if new_emails_count > 0:
                # Legacy usage tracking (for backwards compatibility) 
                cursor.execute('''
                    INSERT INTO usage_tracking (user_id, action_type, email_count)
                    VALUES (%s, %s, %s)
                ''', (user_id, action_type, new_emails_count))
                
                # Update user's usage count with only new emails
                cursor.execute('''
                    UPDATE users 
                    SET api_usage_count = COALESCE(api_usage_count, 0) + %s
                    WHERE id = %s
                ''', (new_emails_count, user_id))
                
                print(f"✅ Tracked {new_emails_count} new unique emails for user {user_id} ({action_type})")
            else:
                print(f"📊 No new unique emails to track for user {user_id} ({action_type}) - all already processed this month")
            
            conn.commit()
            return new_emails_count
            
        finally:
            conn.close()

    def get_unique_emails_processed_this_month(self, user_id, action_type=None):
        """Get count of unique emails processed this month"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')
            
            if action_type:
                cursor.execute('''
                    SELECT COUNT(DISTINCT email_id) 
                    FROM processed_emails 
                    WHERE user_id = %s AND month_year = %s AND action_type = %s
                ''', (user_id, current_month, action_type))
            else:
                cursor.execute('''
                    SELECT COUNT(DISTINCT email_id) 
                    FROM processed_emails 
                    WHERE user_id = %s AND month_year = %s
                ''', (user_id, current_month))
            
            result = cursor.fetchone()
            return result[0] if result else 0
            
        finally:
            conn.close()

    def check_usage_limit(self, user_id):
        """Check if user has exceeded their usage limit using unique emails processed this month"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT subscription_plan
                FROM users WHERE id = %s
            ''', (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                plan = result[0]
                
                # Get actual unique emails processed this month
                unique_emails_count = self.get_unique_emails_processed_this_month(user_id)
                
                # Get dynamic limit from subscription plan
                from models_postgresql import SubscriptionPlan
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
        """Update user's subscription after successful payment and automatically set correct quota"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get the correct email limit for the plan
            from models_postgresql import SubscriptionPlan
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
                SET subscription_plan = %s, subscription_status = 'active', 
                    subscription_expires = %s, stripe_customer_id = COALESCE(%s, stripe_customer_id),
                    monthly_usage_limit = %s
                WHERE id = %s
            ''', (plan_name, expires_at, stripe_customer_id, email_limit, user_id))
            
            conn.commit()
            
            # Check if any rows were affected
            success = cursor.rowcount > 0
            
            if success:
                print(f"✅ [DEBUG] Subscription updated successfully for user {user_id}: {plan_name} with {email_limit} emails/month quota")
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

    def set_gmail_email(self, user_id, gmail_email):
        """Set or clear the user's linked Gmail email address (PostgreSQL)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET gmail_email = %s WHERE id = %s', (gmail_email, user_id))
        conn.commit()
        conn.close()

    def delete_gmail_token(self, user_id):
        """Delete user's Gmail token from both user_tokens and users tables"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM user_tokens WHERE user_id = %s', (user_id,))
            cursor.execute('UPDATE users SET gmail_token = NULL WHERE id = %s', (user_id,))
            conn.commit()
        finally:
            conn.close()
        return True

    def get_vip_senders(self, user_id):
        """Get list of VIP senders for a user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT vip_email, created_at 
                FROM user_vip_senders 
                WHERE user_id = %s 
                ORDER BY created_at ASC
            ''', (user_id,))
            vip_senders = [row[0] for row in cursor.fetchall()]
            return vip_senders
        finally:
            conn.close()

    def add_vip_sender(self, user_id, vip_email):
        """Add a VIP sender for a user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO user_vip_senders (user_id, vip_email)
                VALUES (%s, %s)
            ''', (user_id, vip_email.lower().strip()))
            conn.commit()
            return True
        except psycopg2.IntegrityError:
            conn.rollback()
            return False  # Already exists
        finally:
            conn.close()

    def remove_vip_sender(self, user_id, vip_email):
        """Remove a VIP sender for a user"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                DELETE FROM user_vip_senders 
                WHERE user_id = %s AND vip_email = %s
            ''', (user_id, vip_email.lower().strip()))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_email_filters(self, user_id):
        """Get list of email filters for a user (PostgreSQL)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT filter_type, pattern, created_at 
                FROM user_email_filters 
                WHERE user_id = %s 
                ORDER BY created_at ASC
            ''', (user_id,))
            filters = [
                {'filter_type': row[0], 'pattern': row[1], 'created_at': row[2]} for row in cursor.fetchall()
            ]
            return filters
        finally:
            conn.close()

    def add_email_filter(self, user_id, filter_type, pattern):
        """Add an email filter for a user (PostgreSQL)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO user_email_filters (user_id, filter_type, pattern)
                VALUES (%s, %s, %s)
            ''', (user_id, filter_type, pattern.strip()))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False  # Already exists or error
        finally:
            conn.close()

    def remove_email_filter(self, user_id, filter_type, pattern):
        """Remove an email filter for a user (PostgreSQL)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                DELETE FROM user_email_filters 
                WHERE user_id = %s AND filter_type = %s AND pattern = %s
            ''', (user_id, filter_type, pattern.strip()))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_email_analysis(self, user_id, email_id):
        """Get cached AI analysis for an email (PostgreSQL)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT ai_priority, ai_priority_reason, created_at 
                FROM user_email_analysis 
                WHERE user_id = %s AND email_id = %s
            ''', (user_id, email_id))
            result = cursor.fetchone()
            if result:
                return {
                    'ai_priority': result[0],
                    'ai_priority_reason': result[1],
                    'created_at': result[2]
                }
            return None
        finally:
            conn.close()

    def save_email_analysis(self, user_id, email_id, ai_priority, ai_priority_reason):
        """Save AI analysis results for an email (PostgreSQL)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO user_email_analysis 
                (user_id, email_id, ai_priority, ai_priority_reason, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, email_id) 
                DO UPDATE SET 
                    ai_priority = EXCLUDED.ai_priority,
                    ai_priority_reason = EXCLUDED.ai_priority_reason,
                    created_at = CURRENT_TIMESTAMP
            ''', (user_id, email_id, ai_priority, ai_priority_reason))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving email analysis: {e}")
            return False
        finally:
            conn.close()

    def clear_email_analysis(self, user_id, email_id=None):
        """Clear cached AI analysis for a user (or specific email) (PostgreSQL)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            if email_id:
                cursor.execute('''
                    DELETE FROM user_email_analysis 
                    WHERE user_id = %s AND email_id = %s
                ''', (user_id, email_id))
            else:
                cursor.execute('''
                    DELETE FROM user_email_analysis 
                    WHERE user_id = %s
                ''', (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error clearing email analysis: {e}")
            return False
        finally:
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

    def get_database_stats(self):
        """Get database statistics"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get database size
                    cur.execute("""
                        SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                               pg_database_size(current_database()) as size_bytes
                    """)
                    size_data = cur.fetchone()
                    
                    # Get table counts
                    cur.execute("""
                        SELECT COUNT(*) as table_count 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                    table_count = cur.fetchone()[0]
                    
                    return {
                        'size_formatted': size_data[0],
                        'size_bytes': size_data[1],
                        'table_count': table_count
                    }
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}
            
    def get_table_stats(self):
        """Get statistics for each table"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            relname as table_name,
                            n_live_tup as row_count,
                            pg_size_pretty(pg_total_relation_size(quote_ident(relname))) as size
                        FROM pg_stat_user_tables
                        ORDER BY n_live_tup DESC
                    """)
                    return cur.fetchall()
        except Exception as e:
            print(f"❌ Error getting table stats: {e}")
            return []
            
    def get_total_users(self):
        """Get total number of users"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM users")
                    return cur.fetchone()[0]
        except Exception as e:
            print(f"❌ Error getting total users: {e}")
            return 0
            
    def get_active_subscriptions_count(self):
        """Get count of active subscriptions"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM users 
                        WHERE subscription_status = 'active'
                    """)
                    return cur.fetchone()[0]
        except Exception as e:
            print(f"❌ Error getting active subscriptions count: {e}")
            return 0
            
    def get_emails_processed_count(self, date):
        """Get count of emails processed on a specific date"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM email_processing_log 
                        WHERE DATE(processed_at) = %s
                    """, (date,))
                    return cur.fetchone()[0]
        except Exception as e:
            print(f"❌ Error getting emails processed count: {e}")
            return 0
            
    def get_recent_activity(self, limit=10):
        """Get recent user activity"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            a.timestamp,
                            u.email as user_email,
                            a.action,
                            a.details
                        FROM activity_log a
                        LEFT JOIN users u ON a.user_id = u.id
                        ORDER BY a.timestamp DESC
                        LIMIT %s
                    """, (limit,))
                    
                    activities = []
                    for row in cur.fetchall():
                        activities.append({
                            'timestamp': row[0],
                            'user': row[1],
                            'action': row[2],
                            'details': row[3]
                        })
                    return activities
        except Exception as e:
            print(f"❌ Error getting recent activity: {e}")
            return []
            
    def get_users_paginated(self, page=1, search='', per_page=50):
        """Get paginated list of users with optional search"""
        try:
            offset = (page - 1) * per_page
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    if search:
                        cur.execute("""
                            SELECT 
                                id, email, subscription_plan, subscription_status,
                                created_at, last_login
                            FROM users
                            WHERE email ILIKE %s OR first_name ILIKE %s OR last_name ILIKE %s
                            ORDER BY created_at DESC
                            LIMIT %s OFFSET %s
                        """, (f'%{search}%', f'%{search}%', f'%{search}%', per_page, offset))
                    else:
                        cur.execute("""
                            SELECT 
                                id, email, subscription_plan, subscription_status,
                                created_at, last_login
                            FROM users
                            ORDER BY created_at DESC
                            LIMIT %s OFFSET %s
                        """, (per_page, offset))
                    
                    users = []
                    for row in cur.fetchall():
                        users.append({
                            'id': row[0],
                            'email': row[1],
                            'subscription_plan': row[2],
                            'subscription_status': row[3],
                            'created_at': row[4],
                            'last_login': row[5]
                        })
                    return users
        except Exception as e:
            print(f"❌ Error getting paginated users: {e}")
            return []
            
    def get_subscription_history(self, user_id):
        """Get user's subscription history"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            plan_name,
                            status,
                            started_at,
                            ended_at,
                            payment_method
                        FROM subscription_history
                        WHERE user_id = %s
                        ORDER BY started_at DESC
                    """, (user_id,))
                    
                    history = []
                    for row in cur.fetchall():
                        history.append({
                            'plan': row[0],
                            'status': row[1],
                            'started_at': row[2],
                            'ended_at': row[3],
                            'payment_method': row[4]
                        })
                    return history
        except Exception as e:
            print(f"❌ Error getting subscription history: {e}")
            return []
            
    def get_payment_history(self, user_id):
        """Get user's payment history"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            amount,
                            currency,
                            status,
                            payment_method,
                            created_at,
                            reference
                        FROM payments
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                    """, (user_id,))
                    
                    history = []
                    for row in cur.fetchall():
                        history.append({
                            'amount': row[0],
                            'currency': row[1],
                            'status': row[2],
                            'payment_method': row[3],
                            'date': row[4],
                            'reference': row[5]
                        })
                    return history
        except Exception as e:
            print(f"❌ Error getting payment history: {e}")
            return []
            
    def get_user_email_stats(self, user_id):
        """Get user's email processing statistics"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_processed,
                            COUNT(CASE WHEN DATE(processed_at) = CURRENT_DATE THEN 1 END) as processed_today,
                            MAX(processed_at) as last_processed
                        FROM email_processing_log
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    row = cur.fetchone()
                    return {
                        'total_processed': row[0],
                        'processed_today': row[1],
                        'last_processed': row[2]
                    }
        except Exception as e:
            print(f"❌ Error getting user email stats: {e}")
            return {
                'total_processed': 0,
                'processed_today': 0,
                'last_processed': None
            }
            
    def get_logs_paginated(self, page=1, log_type='all', per_page=100):
        """Get paginated application logs"""
        try:
            offset = (page - 1) * per_page
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    if log_type != 'all':
                        cur.execute("""
                            SELECT 
                                timestamp,
                                level,
                                message,
                                details
                            FROM application_logs
                            WHERE level = %s
                            ORDER BY timestamp DESC
                            LIMIT %s OFFSET %s
                        """, (log_type, per_page, offset))
                    else:
                        cur.execute("""
                            SELECT 
                                timestamp,
                                level,
                                message,
                                details
                            FROM application_logs
                            ORDER BY timestamp DESC
                            LIMIT %s OFFSET %s
                        """, (per_page, offset))
                    
                    logs = []
                    for row in cur.fetchall():
                        logs.append({
                            'timestamp': row[0],
                            'level': row[1],
                            'message': row[2],
                            'details': row[3]
                        })
                    return logs
        except Exception as e:
            print(f"❌ Error getting paginated logs: {e}")
            return [] 