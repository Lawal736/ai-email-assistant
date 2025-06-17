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
        """Get plan by name"""
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
                return dict(row)
            return None
        finally:
            conn.close()

class PaymentRecord:
    """Payment record model"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_payment_record(self, user_id, stripe_payment_intent_id, amount, 
                            plan_name, billing_period, status='pending', currency='usd', payment_method='card'):
        """Create payment record"""
        return 1  # Placeholder
    
    def get_user_payments(self, user_id):
        """Get user payments"""
        return []  # Placeholder
    
    def get_payments_by_user(self, user_id):
        """Alias for compatibility"""
        return self.get_user_payments(user_id) 