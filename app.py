import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, abort
from flask_cors import CORS
from dotenv import load_dotenv
from functools import wraps
from gmail_service import GmailService
from ai_service import HybridAIService
from email_processor import EmailProcessor
from document_processor import DocumentProcessor
from models import DatabaseManager, User, SubscriptionPlan, PaymentRecord
from payment_service import PaymentService
from currency_service import currency_service
import time
import re
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-this-in-production')

# Configure session for production vs development
# More robust detection for Digital Ocean App Platform
is_production = (
    os.environ.get('K_SERVICE') or
    os.environ.get('CLOUD_RUN_SERVICE') or
    os.environ.get('DIGITALOCEAN_APP_PLATFORM') or
    os.environ.get('APP_PLATFORM') or
    os.environ.get('PORT') == '8080' or  # Digital Ocean default
    os.environ.get('PORT') == '5001' or  # Your current port
    os.environ.get('FLASK_ENV') == 'production'
)

print(f"🔧 Environment detection:")
print(f"   - K_SERVICE: {os.environ.get('K_SERVICE')}")
print(f"   - CLOUD_RUN_SERVICE: {os.environ.get('CLOUD_RUN_SERVICE')}")
print(f"   - DIGITALOCEAN_APP_PLATFORM: {os.environ.get('DIGITALOCEAN_APP_PLATFORM')}")
print(f"   - APP_PLATFORM: {os.environ.get('APP_PLATFORM')}")
print(f"   - PORT: {os.environ.get('PORT')}")
print(f"   - FLASK_ENV: {os.environ.get('FLASK_ENV')}")
print(f"   - Is Production: {is_production}")

if is_production:
    # Production environment (Cloud Run or Digital Ocean)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        SESSION_COOKIE_DOMAIN=None,  # Let Flask determine the domain
        SESSION_COOKIE_PATH='/'
    )
    print("🔧 Production session configuration applied")
    print(f"🔧 SECRET_KEY set: {'Yes' if app.secret_key and app.secret_key != 'your-secret-key-here-change-this-in-production' else 'No'}")
    print(f"🔧 SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
    print(f"🔧 SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY')}")
    print(f"🔧 SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE')}")
else:
    # Development environment
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        SESSION_COOKIE_DOMAIN=None,
        SESSION_COOKIE_PATH='/'
    )
    print("🔧 Development session configuration applied")

CORS(app)

# Initialize database and services
try:
    # Check if we should use PostgreSQL
    database_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()
    
    if database_type == 'postgresql':
        # Import PostgreSQL models
        from models_postgresql import DatabaseManager as PGDatabaseManager, User as PGUser, SubscriptionPlan as PGSubscriptionPlan, PaymentRecord as PGPaymentRecord
        
        # Use PostgreSQL configuration
        pg_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 25060)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'sslmode': os.getenv('DB_SSLMODE', 'require')
        }
        
        print(f"🔧 Using PostgreSQL database: {pg_config['host']}:{pg_config['port']}")
        
        db_manager = PGDatabaseManager(pg_config)
        user_model = PGUser(db_manager)
        plan_model = PGSubscriptionPlan(db_manager)
        payment_model = PGPaymentRecord(db_manager)
    else:
        # Use SQLite (default)
        print("🔧 Using SQLite database")
        db_manager = DatabaseManager()
        user_model = User(db_manager)
        plan_model = SubscriptionPlan(db_manager)
        payment_model = PaymentRecord(db_manager)
    
    payment_service = PaymentService()
    print("✅ Database and payment services initialized")
except Exception as e:
    print(f"⚠️ Database initialization failed: {e}")
    print(f"   Error details: {type(e).__name__}: {e}")
    # Fallback to SQLite if PostgreSQL fails
    try:
        print("🔄 Falling back to SQLite...")
        db_manager = DatabaseManager()
        user_model = User(db_manager)
        plan_model = SubscriptionPlan(db_manager)
        payment_model = PaymentRecord(db_manager)
        payment_service = PaymentService()
        print("✅ SQLite fallback successful")
    except Exception as fallback_error:
        print(f"❌ SQLite fallback also failed: {fallback_error}")
        db_manager = None
        user_model = None
        plan_model = None
        payment_model = None
        payment_service = None

# Initialize Gmail and AI services
try:
    gmail_service = GmailService()
    print("✅ Gmail service initialized")
except Exception as e:
    print(f"⚠️ Gmail service initialization failed: {e}")
    gmail_service = None

try:
    ai_service = HybridAIService()
    print("✅ AI service initialized")
except Exception as e:
    print(f"⚠️ AI service initialization failed: {e}")
    ai_service = None

try:
    document_processor = DocumentProcessor()
    print("✅ Document processor initialized")
except Exception as e:
    print(f"⚠️ Document processor initialization failed: {e}")
    document_processor = None

try:
    email_processor = EmailProcessor(ai_service, document_processor, gmail_service)
    print("✅ Email processor initialized")
except Exception as e:
    print(f"⚠️ Email processor initialization failed: {e}")
    email_processor = None

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def subscription_required(plan_name='free'):
    """
    Enhanced subscription decorator that checks plan hierarchy:
    - free < pro < enterprise
    - Users with higher plans can access lower plan features
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('login'))
            
            user = user_model.get_user_by_id(session['user_id'])
            if not user:
                flash('User not found', 'error')
                return redirect(url_for('login'))
            
            user_plan = user.get('subscription_plan', 'free')
            
            # Define plan hierarchy (higher index = higher tier)
            plan_hierarchy = ['free', 'pro', 'enterprise']
            
            # Check if user has required subscription level
            required_index = plan_hierarchy.index(plan_name)
            user_index = plan_hierarchy.index(user_plan)
            
            if user_index < required_index:
                plan_display_names = {
                    'pro': 'Pro',
                    'enterprise': 'Enterprise'
                }
                required_plan = plan_display_names.get(plan_name, plan_name.title())
                flash(f'This feature requires a {required_plan} subscription. Please upgrade to access advanced features.', 'warning')
                return redirect(url_for('pricing'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or not session.get('is_admin', False):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('auth/login.html')
        
        user = user_model.authenticate_user(email, password)
        if user:
            session.clear()  # Clear any previous session data to prevent leakage
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            session['subscription_plan'] = user['subscription_plan']
            
            if remember:
                session.permanent = True
            
            flash(f'Welcome back, {session["user_name"] or user["email"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        terms = request.form.get('terms')
        
        # Validation
        if not all([email, password, confirm_password, terms]):
            flash('Please fill in all required fields', 'error')
            return render_template('auth/signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/signup.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('auth/signup.html')
        
        # Create user
        user_id = user_model.create_user(email, password, first_name, last_name)
        if user_id:
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already exists', 'error')
    
    return render_template('auth/signup.html')

@app.route('/logout')
def logout():
    """User logout"""
    # Clear Gmail credentials
    try:
        if gmail_service:
            gmail_service.logout()
    except Exception as e:
        print(f"⚠️ Error clearing Gmail credentials: {e}")
    
    # Clear all session data
    session.clear()
    
    # Create response to clear cookies
    response = redirect(url_for('index'))
    
    # Clear session cookie explicitly
    response.delete_cookie('session')
    
    flash('Logged out successfully', 'success')
    return response

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('auth/forgot_password.html')
        
        # Check if user exists
        user_data = user_model.get_user_by_email(email) if user_model else None
        
        if user_data:
            # Generate reset token
            import secrets
            import hashlib
            from datetime import datetime, timedelta
            
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)  # Token expires in 24 hours
            
            # Store reset token in database
            if user_model.create_password_reset_token(user_data['id'], reset_token, expires_at):
                # In a real implementation, you would send an email here
                # For now, we'll just show a success message
                flash('If an account with that email exists, a password reset link has been sent.', 'success')
            else:
                flash('Error creating reset token. Please try again.', 'error')
        else:
            # Don't reveal if email exists or not for security
            flash('If an account with that email exists, a password reset link has been sent.', 'success')
        
        return render_template('auth/forgot_password.html')
    
    return render_template('auth/forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password page"""
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or not confirm_password:
            flash('Please fill in all fields', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        # Verify the token is valid and not expired
        user_data = user_model.get_user_by_reset_token(token) if user_model else None
        
        if not user_data:
            flash('Invalid or expired reset token. Please request a new password reset.', 'error')
            return redirect(url_for('forgot_password'))
        
        # Update the user's password
        if user_model.update_password(user_data['id'], password):
            # Mark the token as used
            user_model.mark_reset_token_used(token)
            flash('Password has been reset successfully! You can now log in with your new password.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error updating password. Please try again.', 'error')
            return render_template('auth/reset_password.html', token=token)
    
    # For GET requests, verify the token is valid
    user_data = user_model.get_user_by_reset_token(token) if user_model else None
    
    if not user_data:
        flash('Invalid or expired reset token. Please request a new password reset.', 'error')
        return redirect(url_for('forgot_password'))
    
    return render_template('auth/reset_password.html', token=token)

# Main routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/pricing')
def pricing():
    """Pricing page"""
    try:
        # Get user's real IP address for currency detection (handle proxies/load balancers)
        user_ip = get_user_real_ip()
        
        print(f"🔍 Pricing - User IP: {user_ip}")
        
        # Detect user's currency
        user_currency = currency_service.detect_user_currency(user_ip)
        print(f"🌍 Detected currency: {user_currency}")
        
        # Get plans from database
        if plan_model:
            plans = plan_model.get_all_plans()
            print(f"📋 Found {len(plans)} plans")
        else:
            plans = []
            print("⚠️ Plan model not available")
        
        # Convert plan prices to user's currency
        converted_plans = currency_service.convert_plan_prices(plans, user_currency)
        print(f"💱 Converted {len(converted_plans)} plans to {user_currency}")
        
        # Get currency info
        currency_info = currency_service.get_currency_info(user_currency)
        
        # Save user's currency preference if logged in
        if session.get('user_id'):
            try:
                currency_service.save_user_currency_preference(session['user_id'], user_currency)
                print(f"✅ Saved currency preference for user {session['user_id']}: {user_currency}")
            except Exception as e:
                print(f"⚠️ Failed to save currency preference: {e}")
                # Continue without failing
        
        return render_template('pricing.html', 
                             plans=converted_plans, 
                             currency_info=currency_info,
                             user_currency=user_currency)
                             
    except Exception as e:
        print(f"❌ Error in pricing route: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: show pricing with default currency
        try:
            if plan_model:
                plans = plan_model.get_all_plans()
            else:
                plans = []
            
            # Use USD as fallback
            currency_info = currency_service.get_currency_info('USD')
            
            return render_template('pricing.html', 
                                 plans=plans, 
                                 currency_info=currency_info,
                                 user_currency='USD')
        except Exception as fallback_error:
            print(f"❌ Fallback pricing also failed: {fallback_error}")
            flash('Unable to load pricing information. Please try again later.', 'error')
            return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page with enhanced token recovery and emergency user recovery"""
    user_id = session.get('user_id')
    print(f"🔍 Dashboard - User ID: {user_id}")
    
    # Check database state for debugging
    if user_model:
        user_model.check_database_connectivity()
        user_model.check_database_state(user_id)
        
        # EMERGENCY: Check for user/session mismatch and attempt recovery
        session_data = {
            'user_email': session.get('user_email'),
            'user_name': session.get('user_name'), 
            'subscription_plan': session.get('subscription_plan', 'free'),
            'subscription_status': session.get('subscription_status', 'active')
        }
        
        print(f"🔍 [DEBUG] Session data for recovery: {session_data}")
        
        mismatch_fixed = user_model.check_and_repair_user_session_mismatch(user_id, session_data)
        if not mismatch_fixed:
            print(f"🚨 [EMERGENCY] Critical: User {user_id} recovery failed - clearing session")
            session.clear()
            flash('Your account data was corrupted. Please log in again.', 'error')
            return redirect(url_for('login'))
    
    user = user_model.get_user_by_id(user_id) if user_model else None
    if user:
        session['subscription_plan'] = user.get('subscription_plan', 'free')
        session['subscription_status'] = user.get('subscription_status', 'inactive')
        session['subscription_expires'] = user.get('subscription_expires')
    else:
        print(f"❌ [EMERGENCY] User {user_id} still not found after recovery attempt")
        session.clear()
        flash('Your account could not be recovered. Please contact support.', 'error')
        return redirect(url_for('login'))
    
    # Check if Gmail service is available
    if not gmail_service:
        print("❌ Gmail service not available")
        flash('Gmail service is not available. Please check your configuration.', 'error')
        return render_template('dashboard.html', 
                             emails=[], 
                             email_threads={},
                             summary="Gmail service unavailable. Please check your configuration.",
                             action_items=[],
                             recommendations=[],
                             date=datetime.now().strftime('%B %d, %Y'),
                             ai_processing=False)
    
    # Enhanced Gmail token retrieval with recovery
    gmail_token = None
    token_recovery_attempted = False
    
    if user_model:
        # First attempt to get token
        gmail_token = user_model.get_gmail_token(user_id)
        print(f"🔍 Gmail token from database: {'Found' if gmail_token else 'Not found'}")
        
        # If no token found, try recovery mechanisms
        if not gmail_token and not token_recovery_attempted:
            print("🔧 [DEBUG] Token not found, attempting recovery...")
            token_recovery_attempted = True
            
            # Force database sync and check again
            user_model.force_database_sync()
            time.sleep(0.2)
            gmail_token = user_model.get_gmail_token(user_id)
            
            if gmail_token:
                print("✅ [DEBUG] Token recovered after database sync")
            else:
                print("❌ [DEBUG] Token recovery failed - redirecting to connect Gmail")
    
    if not gmail_token:
        print("❌ No Gmail token found in database")
        # Instead of redirecting, render dashboard with no emails and not connected state
        return render_template('dashboard.html', 
                             emails=[], 
                             email_threads={},
                             summary="Gmail not connected. Please connect your Gmail account.",
                             action_items=[],
                             recommendations=[],
                             date=datetime.now().strftime('%B %d, %Y'),
                             ai_processing=False)
    
    try:
        # Validate the token before proceeding
        print("🔍 Setting Gmail credentials from token...")
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            print("❌ Gmail authentication failed - token may be expired")
            # Clear the invalid token
            user_model.update_gmail_token(user_id, None)
            flash('Your Gmail connection has expired. Please reconnect your Gmail account.', 'warning')
            return redirect(url_for('connect_gmail'))
        
        print("✅ Gmail authentication successful")
        
        # Update session to reflect Gmail authentication status
        session['gmail_authenticated'] = True
        if user and user.get('gmail_email'):
            session['gmail_email'] = user['gmail_email']
        
        # Get today's emails
        print("📧 Fetching today's emails...")
        plan = session.get('subscription_plan', user.get('subscription_plan', 'free'))
        print(f"🔍 [DEBUG] User plan for email fetching: {plan}")
        emails = gmail_service.get_todays_emails(max_results=50, user_plan=plan)
        print(f"📧 Found {len(emails)} emails for today")
        
        # Filter emails if needed
        filtered_emails = email_processor.filter_emails(emails) if email_processor else emails
        print(f"📧 After filtering: {len(filtered_emails)} emails")
        
        # Process emails with basic information
        print("⚙️ Processing emails...")
        processed_emails = email_processor.process_emails_basic(filtered_emails) if email_processor else filtered_emails
        print(f"✅ Processed {len(processed_emails)} emails")
        
        # Group emails by sender and subject for thread analysis
        email_threads = email_processor.group_emails_by_thread(processed_emails) if email_processor else {}
        print(f"\U0001f9f5 Created {len(email_threads)} email threads")

        # Apply per-thread FIFO limits based on user plan
        plan = session.get('subscription_plan', user.get('subscription_plan', 'free'))
        if plan == 'enterprise':
            thread_limit = 50
        elif plan == 'pro':
            thread_limit = 25
        else:
            thread_limit = 10
        print(f"\U0001f50d Applying per-thread limit: {thread_limit} emails for plan: {plan}")
        for thread_key, thread in email_threads.items():
            # Sort emails by date descending (most recent first)
            thread['emails'].sort(key=lambda x: x.get('date', ''), reverse=True)
            # Keep only the N most recent emails
            thread['emails'] = thread['emails'][:thread_limit]
            thread['thread_count'] = len(thread['emails'])
        
        # Get current date
        current_date = datetime.now().strftime('%B %d, %Y')
        
        # Return dashboard immediately with basic data
        return render_template('dashboard.html', 
                             emails=processed_emails, 
                             email_threads=email_threads,
                             summary="Ready to analyze emails with AI. Click 'Load AI Analysis' to get insights.",
                             action_items=[],
                             recommendations=[],
                             date=current_date,
                             ai_processing=False)
    
    except Exception as e:
        print(f"❌ Error in dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Check if it's an authentication error
        if "authentication" in str(e).lower() or "credentials" in str(e).lower():
            print("🔍 Authentication error detected, clearing token...")
            user_model.update_gmail_token(user_id, None)
            flash('Your Gmail connection has expired. Please reconnect your Gmail account.', 'warning')
            return redirect(url_for('connect_gmail'))
        
        flash(f'Error loading dashboard: {str(e)}', 'error')
        # Provide default values for template
        return render_template('dashboard.html', 
                             emails=[], 
                             email_threads={},
                             summary="Unable to load emails at this time. Please check your Gmail connection.",
                             action_items=[],
                             recommendations=[],
                             date=datetime.now().strftime('%B %d, %Y'),
                             ai_processing=False)

@app.route('/connect-gmail')
@login_required
def connect_gmail():
    """Gmail connection page"""
    return render_template('gmail_connect.html')

@app.route('/start-gmail-auth')
@login_required
def start_gmail_auth():
    """Start Gmail OAuth flow"""
    try:
        print("🔍 Starting Gmail OAuth flow...")
        print(f"🔍 User ID: {session.get('user_id')}")
        print(f"🔍 Environment variables:")
        print(f"   - PORT: {os.environ.get('PORT')}")
        print(f"   - DIGITALOCEAN_APP_PLATFORM: {os.environ.get('DIGITALOCEAN_APP_PLATFORM')}")
        print(f"   - APP_URL: {os.environ.get('APP_URL')}")
        print(f"   - APP_NAME: {os.environ.get('APP_NAME')}")
        
        auth_url = gmail_service.get_authorization_url()
        print(f"✅ Authorization URL generated: {auth_url[:100]}...")
        return render_template('auth_redirect.html', auth_url=auth_url)
    except Exception as e:
        print(f"❌ Error in start_gmail_auth: {str(e)}")
        print(f"❌ Exception type: {type(e).__name__}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        flash(f'Error starting authentication: {str(e)}', 'error')
        return redirect(url_for('connect_gmail'))

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth callback with enhanced token persistence"""
    try:
        print("🔍 OAuth callback received")
        print(f"🔍 Session data: {dict(session)}")
        print(f"🔍 Request args: {dict(request.args)}")
        
        # Get authorization code from query parameters
        code = request.args.get('code')
        if not code:
            print("❌ No authorization code received")
            flash('Authorization code not received', 'error')
            return redirect(url_for('connect_gmail'))
        print(f"✅ Authorization code received: {code[:20]}...")
        
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            print("❌ No user_id in session - user not logged in")
            flash('Please log in first', 'error')
            return redirect(url_for('login'))
        
        # Exchange code for tokens
        gmail_service.exchange_code_for_tokens(code)
        print("✅ Code exchanged for tokens")
        
        # Save Gmail token for user
        print(f"🔍 User ID from session: {user_id}")
        token_data = gmail_service.get_token_data()
        print(f"🔍 Token data received: {token_data is not None}")
        gmail_email = None
        
        # Fetch Gmail email address from profile
        try:
            profile = gmail_service.get_user_profile()
            gmail_email = profile.get('email') if profile else None
            print(f"✅ Gmail email fetched: {gmail_email}")
        except Exception as e:
            print(f"⚠️ Could not fetch Gmail email: {e}")
        
        if user_model and token_data:
            # Enhanced token saving with multiple recovery attempts
            token_data_json = json.dumps(token_data)
            
            # Attempt 1: Normal update
            print("🔧 [DEBUG] Attempting normal token update...")
            success = user_model.update_gmail_token(user_id, token_data_json, gmail_email)
            
            if not success:
                print("⚠️ [DEBUG] Normal token update failed, attempting database repair...")
                # Attempt 2: Force database sync and repair
                user_model.force_database_sync()
                repair_success = user_model.repair_user_token_integrity(user_id, token_data_json, gmail_email)
                
                if repair_success:
                    print("✅ [DEBUG] Token repair successful")
                    success = True
                else:
                    print("❌ [DEBUG] Token repair failed, attempting final recovery...")
                    # Attempt 3: Wait and retry with fresh connection
                    time.sleep(1)  # Wait for any pending operations
                    success = user_model.update_gmail_token(user_id, token_data_json, gmail_email)
            
            if success:
                print("✅ Gmail token and email saved to database")
                
                # Enhanced verification with multiple attempts
                print("🔧 [DEBUG] Performing enhanced token verification...")
                verification_success = False
                
                for verification_attempt in range(3):
                    # Force database sync before verification
                    user_model.force_database_sync()
                    time.sleep(0.2)  # Small delay to ensure sync
                    
                    verification_success = user_model.verify_gmail_token_persistence(user_id, token_data)
                    if verification_success:
                        print(f"✅ Gmail token verification successful on attempt {verification_attempt + 1}")
                        break
                    else:
                        print(f"⚠️ Gmail token verification failed on attempt {verification_attempt + 1}")
                        if verification_attempt < 2:
                            # Try to repair again
                            user_model.repair_user_token_integrity(user_id, token_data_json, gmail_email)
                
                if not verification_success:
                    print("❌ Gmail token verification failed after all attempts")
                    # Log the current database state for debugging
                    user_model.check_database_state(user_id)
                    flash('Gmail connection may be unstable. Please try reconnecting if you experience issues.', 'warning')
                else:
                    flash('Gmail connected successfully!', 'success')
                
                # Set session variable for Gmail authentication status
                session['gmail_authenticated'] = True
                session['gmail_email'] = gmail_email
                print("✅ Session updated with Gmail authentication")
            else:
                print("❌ Failed to save Gmail token after all recovery attempts")
                flash('Failed to save Gmail connection. Please try again.', 'error')
                return redirect(url_for('connect_gmail'))
        else:
            print("❌ Failed to save token - user_model or token_data is None")
            flash('Authentication failed. Please try again.', 'error')
            return redirect(url_for('connect_gmail'))
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"❌ Error in OAuth callback: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        flash(f'Error during authentication: {str(e)}', 'error')
        return redirect(url_for('connect_gmail'))

@app.route('/api/disconnect-gmail', methods=['POST'])
@login_required
def api_disconnect_gmail():
    """Disconnect Gmail account"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})
        
        # Clear Gmail service credentials
        if gmail_service:
            gmail_service.clear_credentials()
            print(f"✅ Gmail service credentials cleared for user {user_id}")
        
        # Remove token.json file to prevent caching issues
        token_path = 'token.json'
        if os.path.exists(token_path):
            os.remove(token_path)
            print(f"✅ Gmail token file removed: {token_path}")
        
        print(f"[DEBUG] /api/disconnect-gmail called for user_id: {user_id}")
        print(f"[DEBUG] Session info: {{'gmail_authenticated': {session.get('gmail_authenticated')}, 'gmail_email': {session.get('gmail_email')}}}")
        # Remove Gmail token and email from database
        if user_model:
            print(f"[DEBUG] Calling delete_gmail_token for user_id: {user_id}")
            user_model.delete_gmail_token(user_id)
            print(f"[DEBUG] Finished delete_gmail_token for user_id: {user_id}")
            user_model.set_gmail_email(user_id, None)
            print(f"[DEBUG] Gmail token and email removed for user {user_id}")
        # Clear Gmail authentication from session
        session.pop('gmail_authenticated', None)
        session.pop('gmail_email', None)
        print(f"✅ Gmail authentication cleared from session for user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Gmail account disconnected successfully',
            'reload': True  # Instruct frontend to reload page for session update
        })
    except Exception as e:
        print(f"❌ Error disconnecting Gmail: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to disconnect Gmail: {str(e)}'
        })

def get_user_real_ip():
    """Get user's real IP address, handling proxies and load balancers"""
    user_ip = request.headers.get('X-Forwarded-For', 
                                 request.headers.get('X-Real-IP', 
                                                   request.headers.get('CF-Connecting-IP', 
                                                                     request.remote_addr)))
    if user_ip and ',' in user_ip:
        # X-Forwarded-For can contain multiple IPs, take the first one (original client)
        user_ip = user_ip.split(',')[0].strip()
    
    return user_ip

def ensure_session_currency():
    """Ensure user has currency preference set based on their IP"""
    if not session.get('user_currency'):
        user_ip = get_user_real_ip()
        print(f"🔍 Setting session currency for IP: {user_ip}")
        
        detected_currency = currency_service.detect_user_currency(user_ip)
        session['user_currency'] = detected_currency
        
        print(f"🌍 Session currency set to: {detected_currency}")
        
        # Save to database if user is logged in
        if session.get('user_id'):
            currency_service.save_user_currency_preference(session['user_id'], detected_currency)

# Payment routes
@app.template_filter('thousands')
def thousands_filter(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return value

@app.route('/payment/checkout')
@login_required
def payment_checkout():
    ensure_session_currency()
    """Payment checkout page"""
    plan_name = request.args.get('plan', 'pro')
    billing_period = request.args.get('billing', 'monthly')
    
    # Debug logging
    print(f"🔍 [DEBUG] Payment checkout - Plan: {plan_name}, Billing: {billing_period}")
    print(f"🔍 [DEBUG] Session user_id: {session.get('user_id')}")
    print(f"🔍 [DEBUG] Session user_currency: {session.get('user_currency')}")
    
    plan = plan_model.get_plan_by_name(plan_name) if plan_model else None
    if not plan:
        flash('Plan not found', 'error')
        return redirect(url_for('pricing'))
    
    # Get user's currency preference with IP detection fallback
    user_id = session.get('user_id')
    user_currency = currency_service.get_user_currency_preference(user_id) if user_id else None
    
    if not user_currency:
        user_ip = get_user_real_ip()
        user_currency = currency_service.detect_user_currency(user_ip)
        print(f"🌍 Checkout - IP: {user_ip} -> Currency: {user_currency}")
        
        # Save detected currency to session and database
        session['user_currency'] = user_currency
        if user_id:
            currency_service.save_user_currency_preference(user_id, user_currency)
    
    print(f"🔍 [DEBUG] Using currency: {user_currency}")
    
    # Convert plan to user's currency (same as pricing page)
    converted_plan = currency_service.convert_plan_prices([plan], user_currency)[0]
    price = converted_plan['price_monthly'] if billing_period == 'monthly' else converted_plan['price_yearly']
    formatted_price = currency_service.format_price(price, user_currency)
    
    print(f"🔍 [DEBUG] Original plan price (USD): {plan.get('price_monthly' if billing_period == 'monthly' else 'price_yearly')}")
    print(f"🔍 [DEBUG] Converted price: {price}")
    print(f"🔍 [DEBUG] Formatted price: {formatted_price}")
    print(f"🔍 [DEBUG] Currency symbol: {converted_plan['currency_symbol']}")
    
    paystack_public_key = os.getenv('PAYSTACK_PUBLIC_KEY', '')
    return render_template('payment/checkout.html', 
                         plan=converted_plan, 
                         billing_period=billing_period,
                         paystack_public_key=paystack_public_key,
                         user_currency=user_currency,
                         formatted_price=formatted_price,
                         converted_price=price,
                         currency_symbol=converted_plan['currency_symbol'])

@app.route('/payment/process', methods=['POST'])
@login_required
def payment_process():
    ensure_session_currency()
    """Process payment with Paystack"""
    try:
        data = request.get_json()
        plan_name = data.get('plan')
        billing_period = data.get('billing_period', 'monthly')
        
        user_id = session.get('user_id')
        
        # Get user's currency preference
        user_currency = session.get('user_currency', 'USD')
        print(f"🔍 [DEBUG] Using currency for Paystack: {user_currency}")
        
        # Always fallback to NGN for Paystack if not set or not supported
        if not currency_service.is_paystack_supported(user_currency):
            print(f"⚠️ [DEBUG] Currency {user_currency} not supported by Paystack, forcing NGN")
            user_currency = 'NGN'
            session['user_currency'] = 'NGN'
        
        # Create Paystack checkout session
        result = payment_service.create_checkout_session(
            user_id, plan_name, billing_period, user_currency
        )
        
        print(f"🔍 [DEBUG] Paystack result: {result}")
        
        if result['success']:
            return jsonify({
                'success': True,
                'authorization_url': result['authorization_url'],
                'reference': result['reference'],
                'access_code': result['access_code'],
                'amount': result.get('amount'),
                'currency': result.get('currency')
            })
        else:
            return jsonify(result)
            
    except Exception as e:
        print(f"❌ [DEBUG] Payment process error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/payment/success')
@login_required
def payment_success():
    """Payment success page"""
    reference = request.args.get('reference')
    trxref = request.args.get('trxref')
    
    # Verify the transaction
    if reference and trxref:
        verification_result = payment_service.verify_paystack_transaction(reference)
        if verification_result.get('status'):
            # Transaction was successful
            data = verification_result.get('data', {})
            metadata = data.get('metadata', {})
            
            # Extract subscription details from metadata
            user_id = metadata.get('user_id')
            plan_name = metadata.get('plan_name')
            billing_period = metadata.get('billing_period', 'monthly')
            
            # Activate subscription if we have the required data
            if user_id and plan_name:
                print(f"🔍 [DEBUG] Activating subscription - User: {user_id}, Plan: {plan_name}, Billing: {billing_period}")
                success = payment_service.activate_subscription(
                    user_id=user_id,
                    plan_name=plan_name,
                    payment_method='paystack',
                    payment_id=reference,
                    billing_period=billing_period
                )
                
                if success and session.get('user_id') == user_id:
                    user = user_model.get_user_by_id(user_id)
                    session['subscription_plan'] = user.get('subscription_plan', 'free')
                    session['subscription_status'] = user.get('subscription_status', 'inactive')
                    session['subscription_expires'] = user.get('subscription_expires')
                print(f"✅ [DEBUG] Subscription activated successfully for user {user_id}")
                flash('Payment successful! Your subscription has been activated.', 'success')
            else:
                print(f"⚠️ [DEBUG] Missing metadata for subscription activation - User ID: {user_id}, Plan: {plan_name}")
                flash('Payment successful!', 'success')
            
            return render_template('payment/success.html', 
                                 reference=reference, 
                                 transaction_data=data)
    
    return render_template('payment/success.html', reference=reference)

@app.route('/payment/cancel')
@login_required
def payment_cancel():
    """Payment cancel page"""
    return render_template('payment/cancel.html')

@app.route('/webhooks/paystack', methods=['POST'])
def paystack_webhook():
    """Handle Paystack webhook events for automatic payment processing"""
    try:
        print("🔍 [WEBHOOK] Paystack webhook received")
        
        # Get the raw payload
        payload = request.get_json()
        
        # Get the signature from headers
        signature = request.headers.get('x-paystack-signature')
        
        print(f"🔍 [WEBHOOK] Event: {payload.get('event')}")
        print(f"🔍 [WEBHOOK] Data: {payload.get('data', {}).get('reference')}")
        
        # Process the webhook
        result = payment_service.handle_webhook(payload, signature)
        
        if result.get('success'):
            print(f"✅ [WEBHOOK] Successfully processed: {result.get('message')}")
            return jsonify({'status': 'success'}), 200
        else:
            print(f"❌ [WEBHOOK] Failed to process: {result.get('error')}")
            return jsonify({'status': 'error', 'message': result.get('error')}), 400
            
    except Exception as e:
        print(f"❌ [WEBHOOK] Webhook processing error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/payment/verify/<reference>')
@login_required
def verify_payment_manual(reference):
    """Manually verify and activate payment (for debugging/fixing failed webhooks)"""
    try:
        print(f"🔍 [DEBUG] Manual payment verification for reference: {reference}")
        
        # Verify the payment with Paystack
        verification_result = payment_service.verify_paystack_transaction(reference)
        
        if verification_result.get('status') and verification_result['data']['status'] == 'success':
            data = verification_result['data']
            metadata = data.get('metadata', {})
            
            user_id = metadata.get('user_id')
            plan_name = metadata.get('plan_name')
            billing_period = metadata.get('billing_period', 'monthly')
            payment_currency = metadata.get('currency', 'NGN')
            
            print(f"🔍 [DEBUG] Payment verified - User: {user_id}, Plan: {plan_name}")
            
            if user_id and plan_name:
                # Check if already processed
                existing_payment = payment_service.payment_model.get_payment_by_reference(reference)
                if existing_payment:
                    flash('Payment already processed!', 'info')
                    return redirect(url_for('account_subscription'))
                
                # Activate subscription
                success = payment_service.activate_subscription(
                    user_id, 
                    plan_name, 
                    payment_method='paystack',
                    payment_id=reference,
                    billing_period=billing_period,
                    currency=payment_currency
                )
                
                if success and session.get('user_id') == user_id:
                    user = user_model.get_user_by_id(user_id)
                    session['subscription_plan'] = user.get('subscription_plan', 'free')
                    session['subscription_status'] = user.get('subscription_status', 'inactive')
                    session['subscription_expires'] = user.get('subscription_expires')
                flash('Payment verified and subscription activated successfully!', 'success')
                return redirect(url_for('account_subscription'))
            else:
                flash('Invalid payment metadata. Please contact support.', 'error')
                return redirect(url_for('account_subscription'))
        else:
            flash('Payment verification failed. Please try again or contact support.', 'error')
            return redirect(url_for('account_subscription'))
            
    except Exception as e:
        print(f"❌ [DEBUG] Manual verification error: {e}")
        flash('Error verifying payment. Please contact support.', 'error')
        return redirect(url_for('account_subscription'))

# Admin endpoints for payment management
@app.route('/admin/retry-failed-payments')
def admin_retry_failed_payments():
    """Admin endpoint to retry failed payments"""
    try:
        print("🔧 Admin: Retrying failed payments...")
        
        # Retry failed payments
        success_count = payment_service.retry_failed_payments()
        
        return jsonify({
            'success': True,
            'message': f'Retry complete: {success_count} payments fixed',
            'fixed_count': success_count
        })
        
    except Exception as e:
        print(f"❌ Admin retry error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/check-missed-payments')
def admin_check_missed_payments():
    """Admin endpoint to check for missed payments by querying Paystack directly"""
    try:
        print("🔍 Admin: Checking for missed payments...")
        
        # Get all users
        conn = user_model.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, email FROM users WHERE subscription_plan = %s', ('free',))
        free_users = cursor.fetchall()
        conn.close()
        
        missed_payments = []
        fixed_count = 0
        
        for user_id, email in free_users:
            print(f"🔍 Checking {email} for missed payments...")
            
            # Check Paystack for recent successful payments
            paystack_secret = os.getenv('PAYSTACK_SECRET_KEY')
            if not paystack_secret:
                continue
                
            headers = {
                'Authorization': f'Bearer {paystack_secret}',
                'Content-Type': 'application/json'
            }
            
            # Get recent transactions for this customer
            url = 'https://api.paystack.co/transaction'
            params = {
                'customer': email,
                'status': 'success',
                'perPage': 5
            }
            
            try:
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    transactions = data.get('data', [])
                    
                    for txn in transactions:
                        reference = txn.get('reference', '')
                        amount = float(txn.get('amount', 0)) / 100
                        
                        # Check if this payment exists in our database
                        existing_payment = payment_service.payment_model.get_payment_by_reference(reference)
                        
                        if not existing_payment and amount >= 5000:  # Pro or Enterprise payment
                            print(f"🔍 Found missed payment: {reference} for {email}")
                            
                            # Determine plan from amount
                            if amount >= 15000:
                                plan_name = 'enterprise'
                            elif amount >= 5000:
                                plan_name = 'pro'
                            else:
                                continue
                            
                            # Process the missed payment
                            try:
                                # Create payment record
                                payment_service.payment_model.create_payment_record(
                                    user_id=user_id,
                                    stripe_payment_intent_id=reference,
                                    amount=amount,
                                    plan_name=plan_name,
                                    billing_period='monthly',
                                    status='completed',
                                    currency='NGN',
                                    payment_method='paystack'
                                )
                                
                                # Activate subscription
                                end_date = datetime.now() + timedelta(days=30)
                                success = user_model.update_subscription(
                                    user_id=user_id,
                                    plan_name=plan_name,
                                    stripe_customer_id=reference,
                                    expires_at=end_date
                                )
                                
                                if success:
                                    missed_payments.append({
                                        'email': email,
                                        'reference': reference,
                                        'amount': amount,
                                        'plan': plan_name,
                                        'status': 'fixed'
                                    })
                                    fixed_count += 1
                                    print(f"✅ Fixed missed payment for {email}")
                                
                            except Exception as e:
                                print(f"❌ Failed to fix payment {reference}: {e}")
                                missed_payments.append({
                                    'email': email,
                                    'reference': reference,
                                    'amount': amount,
                                    'plan': plan_name,
                                    'status': 'failed',
                                    'error': str(e)
                                })
                                
            except Exception as e:
                print(f"❌ Error checking Paystack for {email}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Missed payment check complete: {fixed_count} payments fixed',
            'fixed_count': fixed_count,
            'missed_payments': missed_payments
        })
        
    except Exception as e:
        print(f"❌ Admin missed payments error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/verify-payment/<reference>')
def admin_verify_payment(reference):
    """Admin endpoint to verify and fix a specific payment"""
    try:
        print(f"🔧 Admin: Verifying payment {reference}...")
        
        # Verify and fix payment
        success = payment_service.verify_and_fix_payment(reference)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Payment {reference} verified and fixed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to verify and fix payment {reference}'
            }), 400
        
    except Exception as e:
        print(f"❌ Admin verification error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/payment-status')
def admin_payment_status():
    """Admin endpoint to check payment and subscription status"""
    try:
        # Get all users with their payment status
        conn = payment_service.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.email, u.subscription_plan, u.subscription_status, u.subscription_expires,
                   COUNT(pr.id) as payment_count,
                   MAX(pr.created_at) as last_payment_date,
                   MAX(CASE WHEN pr.status = 'completed' THEN pr.plan_name END) as last_completed_plan
            FROM users u
            LEFT JOIN payment_records pr ON u.id = pr.user_id
            GROUP BY u.id, u.email, u.subscription_plan, u.subscription_status, u.subscription_expires
            ORDER BY u.id
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'email': row[1],
                'subscription_plan': row[2],
                'subscription_status': row[3],
                'subscription_expires': row[4],
                'payment_count': row[5],
                'last_payment_date': row[6],
                'last_completed_plan': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'users': users
        })
        
    except Exception as e:
        print(f"❌ Admin status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/fix-subscription/<int:user_id>')
def admin_fix_subscription(user_id):
    """Admin endpoint to fix subscription activation for a specific user"""
    try:
        print(f"🔧 Admin: Fixing subscription for user {user_id}...")
        
        # Get user details
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': f'User {user_id} not found'}), 404
        
        # Get user's payment history
        payments = payment_service.payment_model.get_user_payments(user_id)
        
        # Find the most recent successful payment for Pro/Enterprise
        recent_successful_payment = None
        for payment in payments:
            if payment['status'] == 'completed' and payment['plan_name'] in ['pro', 'enterprise']:
                recent_successful_payment = payment
                break
        
        if not recent_successful_payment:
            return jsonify({'error': f'No successful Pro/Enterprise payments found for user {user_id}'}), 400
        
        current_plan = user.get('subscription_plan', 'free')
        target_plan = recent_successful_payment['plan_name']
        
        print(f"🔍 User {user_id}: {user['email']}")
        print(f"   Current plan: {current_plan}")
        print(f"   Target plan: {target_plan}")
        print(f"   Payment: {recent_successful_payment['amount']} {recent_successful_payment['currency']}")
        
        if current_plan == target_plan:
            return jsonify({
                'success': True,
                'message': f'User {user_id} already has {target_plan} subscription activated',
                'current_plan': current_plan
            })
        
        # Calculate subscription end date
        billing_period = recent_successful_payment.get('billing_period', 'monthly')
        if billing_period == 'yearly':
            end_date = datetime.now() + timedelta(days=365)
        else:
            end_date = datetime.now() + timedelta(days=30)
        
        # Update subscription
        success = user_model.update_subscription(
            user_id=user_id,
            plan_name=target_plan,
            stripe_customer_id=recent_successful_payment.get('stripe_payment_intent_id'),
            expires_at=end_date
        )
        
        if success:
            # If this is the current session user, update session data
            if session.get('user_id') == user_id:
                updated_user = user_model.get_user_by_id(user_id)
                session['subscription_plan'] = updated_user.get('subscription_plan', 'free')
                session['subscription_status'] = updated_user.get('subscription_status', 'inactive')
                session['subscription_expires'] = updated_user.get('subscription_expires')
                print(f"✅ Updated session data for current user")
            
            return jsonify({
                'success': True,
                'message': f'Subscription activated successfully for user {user_id}',
                'previous_plan': current_plan,
                'new_plan': target_plan,
                'expires_at': end_date.isoformat(),
                'payment_reference': recent_successful_payment.get('stripe_payment_intent_id')
            })
        else:
            return jsonify({'error': f'Failed to update subscription for user {user_id}'}), 500
            
    except Exception as e:
        print(f"❌ Admin fix subscription error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/find-payments/<int:user_id>')
def admin_find_payments(user_id):
    """Admin endpoint to find Paystack payments for a user"""
    try:
        print(f"🔍 Admin: Finding Paystack payments for user {user_id}...")
        
        # Get user details
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': f'User {user_id} not found'}), 404
        
        user_email = user['email']
        
        # Check Paystack for recent payments
        paystack_secret = os.getenv('PAYSTACK_SECRET_KEY')
        if not paystack_secret:
            return jsonify({'error': 'Paystack secret key not configured'}), 500
        
        headers = {
            'Authorization': f'Bearer {paystack_secret}',
            'Content-Type': 'application/json'
        }
        
        # Get recent transactions for this customer
        url = 'https://api.paystack.co/transaction'
        params = {
            'customer': user_email,
            'status': 'success',
            'perPage': 20
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return jsonify({'error': f'Paystack API error: {response.status_code}'}), 500
        
        data = response.json()
        transactions = data.get('data', [])
        
        # Format transactions for display
        formatted_transactions = []
        for txn in transactions:
            amount = float(txn.get('amount', 0)) / 100
            currency = txn.get('currency', 'NGN')
            reference = txn.get('reference', '')
            created_at = txn.get('created_at', '')
            metadata = txn.get('metadata', {})
            
            formatted_transactions.append({
                'reference': reference,
                'amount': amount,
                'currency': currency,
                'created_at': created_at,
                'metadata': metadata,
                'plan_name': metadata.get('plan_name', 'Unknown'),
                'billing_period': metadata.get('billing_period', 'monthly')
            })
        
        return jsonify({
            'success': True,
            'user_email': user_email,
            'transactions_found': len(formatted_transactions),
            'transactions': formatted_transactions
        })
        
    except Exception as e:
        print(f"❌ Admin find payments error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/manual-activate-pro/<int:user_id>')
def admin_manual_activate_pro(user_id):
    """Emergency admin endpoint to manually activate Pro subscription"""
    try:
        print(f"🔧 EMERGENCY: Manually activating Pro for user {user_id}...")
        
        # Get user details
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': f'User {user_id} not found'}), 404
        
        # Calculate subscription end date (30 days)
        end_date = datetime.now() + timedelta(days=30)
        
        # Create a temporary payment record
        try:
            payment_id = payment_service.payment_model.create_payment_record(
                user_id=user_id,
                stripe_payment_intent_id=f'manual_fix_{int(datetime.now().timestamp())}',
                amount=15439.35,  # Pro monthly price in NGN
                plan_name='pro',
                billing_period='monthly',
                status='completed',
                currency='NGN',
                payment_method='manual_admin_fix'
            )
            print(f"✅ Created manual payment record with ID: {payment_id}")
        except Exception as e:
            print(f"⚠️ Payment record creation failed: {e}")
        
        # Update subscription
        success = user_model.update_subscription(
            user_id=user_id,
            plan_name='pro',
            stripe_customer_id=f'manual_fix_{user_id}',
            expires_at=end_date
        )
        
        if success:
            # Update session if this is the current user
            if session.get('user_id') == user_id:
                updated_user = user_model.get_user_by_id(user_id)
                session['subscription_plan'] = 'pro'
                session['subscription_status'] = 'active'
                session['subscription_expires'] = updated_user.get('subscription_expires')
                print(f"✅ Updated session data for current user")
            
            return jsonify({
                'success': True,
                'message': f'Pro subscription manually activated for user {user_id}',
                'user_email': user['email'],
                'plan_activated': 'pro',
                'expires_at': end_date.isoformat(),
                'note': 'This is a manual fix - payment verification will be done separately'
            })
        else:
            return jsonify({'error': 'Failed to activate subscription'}), 500
            
    except Exception as e:
        print(f"❌ Admin manual activation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/process-payment/<reference>')
def admin_process_payment(reference):
    """Admin endpoint to manually process a Paystack payment"""
    try:
        print(f"🔧 Admin: Processing payment {reference}...")
        
        # Verify payment with Paystack
        paystack_secret = os.getenv('PAYSTACK_SECRET_KEY')
        if not paystack_secret:
            return jsonify({'error': 'Paystack secret key not configured'}), 500
        
        headers = {
            'Authorization': f'Bearer {paystack_secret}',
            'Content-Type': 'application/json'
        }
        
        url = f'https://api.paystack.co/transaction/verify/{reference}'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return jsonify({'error': f'Paystack verification failed: {response.status_code}'}), 500
        
        verification_result = response.json()
        
        if not verification_result.get('status'):
            return jsonify({'error': 'Payment verification failed'}), 400
        
        data = verification_result.get('data', {})
        if data.get('status') != 'success':
            return jsonify({'error': f'Payment was not successful: {data.get("status")}'}), 400
        
        # Extract payment details
        amount = float(data.get('amount', 0)) / 100
        currency = data.get('currency', 'NGN')
        customer_email = data.get('customer', {}).get('email', '')
        metadata = data.get('metadata', {})
        
        # Find user
        user_id = metadata.get('user_id')
        if not user_id:
            user = user_model.get_user_by_email(customer_email)
            if user:
                user_id = user['id']
            else:
                return jsonify({'error': f'User not found for email: {customer_email}'}), 404
        
        # Determine plan
        plan_name = metadata.get('plan_name')
        if not plan_name:
            if amount >= 15000:
                plan_name = 'enterprise'
            elif amount >= 5000:
                plan_name = 'pro'
            else:
                return jsonify({'error': f'Cannot determine plan from amount: {amount}'}), 400
        
        billing_period = metadata.get('billing_period', 'monthly')
        
        # Check if payment already exists
        existing_payment = payment_service.payment_model.get_payment_by_reference(reference)
        if not existing_payment:
            # Create payment record
            payment_id = payment_service.payment_model.create_payment_record(
                user_id=user_id,
                stripe_payment_intent_id=reference,
                amount=amount,
                plan_name=plan_name,
                billing_period=billing_period,
                status='completed',
                currency=currency,
                payment_method='paystack'
            )
        
        # Activate subscription
        if billing_period == 'yearly':
            end_date = datetime.now() + timedelta(days=365)
        else:
            end_date = datetime.now() + timedelta(days=30)
        
        success = user_model.update_subscription(
            user_id=user_id,
            plan_name=plan_name,
            stripe_customer_id=reference,
            expires_at=end_date
        )
        
        if success:
            # Update session if this is the current user
            if session.get('user_id') == user_id:
                updated_user = user_model.get_user_by_id(user_id)
                session['subscription_plan'] = updated_user.get('subscription_plan', 'free')
                session['subscription_status'] = updated_user.get('subscription_status', 'inactive')
                session['subscription_expires'] = updated_user.get('subscription_expires')
            
            return jsonify({
                'success': True,
                'message': f'Payment {reference} processed successfully',
                'user_id': user_id,
                'user_email': customer_email,
                'plan_activated': plan_name,
                'amount': amount,
                'currency': currency,
                'expires_at': end_date.isoformat()
            })
        else:
            return jsonify({'error': 'Failed to activate subscription'}), 500
            
    except Exception as e:
        print(f"❌ Admin process payment error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/manual-process-enterprise')
def admin_manual_process_enterprise():
    """Admin endpoint to manually process the confirmed Enterprise payment"""
    try:
        print("🏢 Admin: Manually processing confirmed Enterprise payment...")
        
        # Payment details confirmed by user
        payment_amount = 46348.95  # NGN
        user_email = "lawalmoruf@gmail.com"
        plan_name = "enterprise"
        currency = "NGN"
        
        print(f"💰 Processing Enterprise payment: ₦{payment_amount:,.2f}")
        print(f"📧 User: {user_email}")
        
        # Find user
        user = user_model.get_user_by_email(user_email)
        if not user:
            return jsonify({'error': f'User not found: {user_email}'}), 404
        
        user_id = user['id']
        print(f"✅ Found user: ID {user_id}")
        
        # Generate a payment reference for this confirmed payment
        payment_reference = f"enterprise_manual_{user_id}_{int(datetime.now().timestamp())}"
        print(f"📋 Payment Reference: {payment_reference}")
        
        # Check if Enterprise payment already exists for this user
        existing_payments = payment_service.payment_model.get_user_payments(user_id)
        enterprise_payments = [p for p in existing_payments if p['plan_name'] == 'enterprise']
        
        # Check if we already have this exact amount
        matching_payment = None
        if enterprise_payments:
            matching_payment = next((p for p in enterprise_payments 
                                   if abs(p['amount'] - payment_amount) < 1.0), None)
        
        if matching_payment:
            print(f"✅ Payment of ₦{payment_amount:,.2f} already exists!")
            
            # Check if user subscription is correctly activated
            current_plan = user.get('subscription_plan', 'free')
            if current_plan == 'enterprise':
                return jsonify({
                    'success': True,
                    'message': f'User already has Enterprise subscription activated!',
                    'user_id': user_id,
                    'current_plan': current_plan,
                    'payment_amount': payment_amount
                })
            else:
                print(f"🔧 User has payment but subscription not activated. Current: {current_plan}")
                # Continue to activate subscription
        else:
            # Create payment record
            print(f"💳 Creating payment record...")
            try:
                payment_id = payment_service.payment_model.create_payment_record(
                    user_id=user_id,
                    stripe_payment_intent_id=payment_reference,
                    amount=payment_amount,
                    plan_name=plan_name,
                    billing_period='monthly',
                    status='completed',
                    currency=currency,
                    payment_method='paystack_manual'
                )
                print(f"✅ Payment record created with ID: {payment_id}")
            except Exception as e:
                print(f"⚠️ Payment record creation failed: {e}")
                # Continue to activate subscription anyway
        
        # Activate Enterprise subscription
        print(f"🏢 Activating Enterprise subscription...")
        
        # Calculate subscription end date (30 days for monthly)
        end_date = datetime.now() + timedelta(days=30)
        
        success = user_model.update_subscription(
            user_id=user_id,
            plan_name=plan_name,
            stripe_customer_id=payment_reference,
            expires_at=end_date
        )
        
        if success:
            print(f"✅ Enterprise subscription activated successfully!")
            
            # Update session if this is the current user
            if session.get('user_id') == user_id:
                updated_user = user_model.get_user_by_id(user_id)
                session['subscription_plan'] = updated_user.get('subscription_plan', 'free')
                session['subscription_status'] = updated_user.get('subscription_status', 'inactive')
                session['subscription_expires'] = updated_user.get('subscription_expires')
                print(f"✅ Updated session data for current user")
            
            # Calculate exchange rate analysis
            enterprise_usd = 49.99
            implied_rate = payment_amount / enterprise_usd
            
            return jsonify({
                'success': True,
                'message': f'Enterprise payment of ₦{payment_amount:,.2f} processed successfully',
                'user_id': user_id,
                'user_email': user_email,
                'plan_activated': plan_name,
                'amount': payment_amount,
                'currency': currency,
                'expires_at': end_date.isoformat(),
                'exchange_rate_used': round(implied_rate, 2),
                'enterprise_usd_price': enterprise_usd,
                'payment_status': 'Valid and confirmed by Paystack'
            })
        else:
            print(f"❌ Failed to activate Enterprise subscription!")
            return jsonify({'error': 'Failed to activate Enterprise subscription'}), 500
            
    except Exception as e:
        print(f"❌ Admin manual Enterprise processing error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# User account routes
@app.route('/account')
@login_required
def account():
    """User account page"""
    user_id = session.get('user_id')
    # Always fetch the latest user data from the database
    user = user_model.get_user_by_id(user_id) if user_model else None
    
    # If user is not found, handle gracefully
    if not user:
        print(f"❌ User not found in database for user_id: {user_id}")
        # Provide a default user structure to prevent template errors
        user = {
            'id': user_id,
            'email': session.get('user_email', 'Unknown'),
            'subscription_plan': 'free',
            'subscription_status': 'inactive',
            'api_usage_count': 0,
            'monthly_usage_limit': 100,  # Free plan limit - will be updated below
            'created_at': None,
            'last_login': None,
            'gmail_email': None
        }
    else:
        # Ensure required fields exist with defaults
        user.setdefault('api_usage_count', 0)
        user.setdefault('subscription_plan', 'free')
        user.setdefault('subscription_status', 'inactive')
    
    # Get the user's actual plan quota dynamically and update usage count
    if plan_model:
        user_plan_data = plan_model.get_plan_by_name(user.get('subscription_plan', 'free'))
        if user_plan_data:
            user['monthly_usage_limit'] = user_plan_data['email_limit']
            print(f"🔍 Dynamic quota set: {user['subscription_plan']} = {user['monthly_usage_limit']} emails/month")
        else:
            # Fallback to free plan if plan not found
            free_plan = plan_model.get_plan_by_name('free')
            user['monthly_usage_limit'] = free_plan['email_limit'] if free_plan else 100
            print(f"⚠️ Plan not found, using free plan quota: {user['monthly_usage_limit']}")
        
        # Get actual unique emails processed this month for accurate usage display
        if user_model:
            unique_emails_count = user_model.get_unique_emails_processed_this_month(user_id)
            user['api_usage_count'] = unique_emails_count
            print(f"📊 Account page: Updated usage count to {unique_emails_count} unique emails")
    else:
        # Final fallback if plan_model not available
        user['monthly_usage_limit'] = 100
        print(f"⚠️ Plan model not available, using fallback quota: {user['monthly_usage_limit']}")
    
    payments = payment_model.get_user_payments(user_id) if payment_model else []
    user_currency = currency_service.get_user_currency(user_id) if user_id else 'USD'
    currency_symbol = currency_service.get_currency_symbol(user_currency)
    
    # Format payment amounts in local currency for account overview
    for payment in payments:
        payment['formatted_amount'] = currency_service.format_amount(payment['amount'], payment.get('currency', user_currency))
        payment['currency_symbol'] = currency_service.get_currency_symbol(payment.get('currency', user_currency))
        payment['payment_method'] = payment.get('payment_method') or 'Credit Card'
        payment['description'] = f"{payment.get('plan_name', 'Subscription')} ({payment.get('billing_period', '').capitalize()})"
    
    # Format user dates
    if user:
        # Format created_at (member since)
        if user.get('created_at'):
            try:
                created_date = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                user['formatted_created_at'] = created_date.strftime('%B %d, %Y')
            except:
                user['formatted_created_at'] = user['created_at']
        else:
            user['formatted_created_at'] = 'Unknown'
        
        # Format last_login
        if user.get('last_login'):
            try:
                last_login_date = datetime.fromisoformat(user['last_login'].replace('Z', '+00:00'))
                user['formatted_last_login'] = last_login_date.strftime('%B %d, %Y at %I:%M %p')
            except:
                user['formatted_last_login'] = user['last_login']
        else:
            user['formatted_last_login'] = 'Never'
    
    # Get Gmail profile information if Gmail is connected
    gmail_profile = None
    if user and user.get('gmail_email'):
        gmail_token = user_model.get_gmail_token(user_id) if user_model else None
        if gmail_token:
            try:
                if gmail_service:
                    gmail_service.clear_credentials()
                gmail_service.set_credentials_from_token(gmail_token)
                if gmail_service.is_authenticated():
                    gmail_profile = gmail_service.get_user_profile()
            except Exception as e:
                print(f"Error getting Gmail profile: {e}")
    
    # Pass the up-to-date user object to the template
    return render_template('account.html', user=user, payments=payments, gmail_profile=gmail_profile)

@app.route('/account/subscription')
@login_required
def account_subscription():
    """Subscription management page"""
    user_id = session.get('user_id')
    user = user_model.get_user_by_id(user_id) if user_model else None
    if user:
        session['subscription_plan'] = user.get('subscription_plan', 'free')
        session['subscription_status'] = user.get('subscription_status', 'inactive')
        session['subscription_expires'] = user.get('subscription_expires')
    
    plans = plan_model.get_all_plans() if plan_model else []
    
    # Ensure currency is detected based on IP
    ensure_session_currency()
    
    # Get user's currency (prioritize saved preference, fallback to IP detection)
    user_currency = currency_service.get_user_currency_preference(user_id) if user_id else None
    if not user_currency:
        user_ip = get_user_real_ip()
        user_currency = currency_service.detect_user_currency(user_ip)
        print(f"🌍 Subscription page - IP: {user_ip} -> Currency: {user_currency}")
    
    currency_symbol = currency_service.get_currency_symbol(user_currency)
    
    # Convert plan prices to user's currency
    converted_plans = currency_service.convert_plan_prices(plans, user_currency)
    
    # Get user's quota for usage display
    plan_quota = None
    if user and user.get('subscription_plan'):
        user_plan = plan_model.get_plan_by_name(user['subscription_plan'])
        plan_quota = user_plan['email_limit'] if user_plan else None
    
    return render_template('account/subscription.html', 
                         user=user, 
                         plans=converted_plans, 
                         user_currency=user_currency, 
                         currency_symbol=currency_symbol, 
                         plan_quota=plan_quota)

@app.route('/account/billing')
@login_required
def account_billing():
    """Billing history page"""
    user_id = session.get('user_id')
    payments = payment_model.get_user_payments(user_id) if payment_model else []
    
    # Ensure currency is detected based on IP
    ensure_session_currency()
    
    # Get user's preferred currency
    user_currency = currency_service.get_user_currency_preference(user_id) if user_id else None
    if not user_currency:
        user_ip = get_user_real_ip()
        user_currency = currency_service.detect_user_currency(user_ip)
        print(f"🌍 Billing page - IP: {user_ip} -> Currency: {user_currency}")
    
    # Format payment amounts
    for payment in payments:
        payment_currency = payment.get('currency', 'USD')
        original_amount = payment.get('amount', 0)
        
        # If payment was made in a different currency, show both original and converted
        if payment_currency != user_currency:
            # Show original amount
            payment['original_formatted_amount'] = currency_service.format_amount(original_amount, payment_currency)
            payment['original_currency_symbol'] = currency_service.get_currency_symbol(payment_currency)
            
            # Convert and show in user's preferred currency
            converted_amount = currency_service.convert_amount(original_amount, payment_currency, user_currency)
            payment['formatted_amount'] = currency_service.format_amount(converted_amount, user_currency)
            payment['currency_symbol'] = currency_service.get_currency_symbol(user_currency)
            payment['show_conversion'] = True
        else:
            # Same currency, just format normally
            payment['formatted_amount'] = currency_service.format_amount(original_amount, payment_currency)
            payment['currency_symbol'] = currency_service.get_currency_symbol(payment_currency)
            payment['show_conversion'] = False
        
        payment['payment_method'] = payment.get('payment_method') or 'Credit Card'
        payment['description'] = f"{payment.get('plan_name', 'Subscription')} ({payment.get('billing_period', '').capitalize()})"
    
    return render_template('account/billing.html', 
                         payments=payments, 
                         user_currency=user_currency)

# Currency API routes
@app.route('/api/update-currency', methods=['POST'])
def update_currency():
    """Update user's currency preference"""
    try:
        data = request.get_json()
        currency = data.get('currency')
        
        print(f"🔍 [DEBUG] update_currency - Request data: {data}")
        print(f"🔍 [DEBUG] Currency requested: {currency}")
        print(f"🔍 [DEBUG] User ID in session: {session.get('user_id')}")
        
        if not currency:
            print(f"❌ [DEBUG] Currency not provided")
            return jsonify({'success': False, 'error': 'Currency not provided'})
        
        # Validate currency
        if currency not in currency_service.supported_currencies:
            print(f"❌ [DEBUG] Unsupported currency: {currency}")
            return jsonify({'success': False, 'error': 'Unsupported currency'})
        
        # Save user's currency preference if logged in
        if session.get('user_id'):
            print(f"🔍 [DEBUG] Saving currency preference for user {session['user_id']}: {currency}")
            currency_service.save_user_currency_preference(session['user_id'], currency)
        
        # Store currency in session for immediate use
        session['user_currency'] = currency
        print(f"🔍 [DEBUG] Currency saved to session: {currency}")
        
        return jsonify({'success': True, 'currency': currency})
        
    except Exception as e:
        print(f"❌ [DEBUG] Error updating currency: {e}")
        return jsonify({'success': False, 'error': 'Failed to update currency'})

# API routes with usage tracking
@app.route('/api/emails')
@login_required
def api_emails():
    """API endpoint to get emails"""
    user_id = session.get('user_id')
    
    # Check usage limits
    usage_info = user_model.check_usage_limit(user_id) if user_model else None
    if usage_info and usage_info['exceeded']:
        return jsonify({'error': 'Usage limit exceeded. Please upgrade your plan.'}), 429
    
    # Check Gmail authentication
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    if not gmail_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    try:
        # Set Gmail token
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            return jsonify({'error': 'Gmail authentication expired'}), 401
        
        # Get user plan for email limits
        user = user_model.get_user_by_id(user_id) if user_model else None
        user_plan = user.get('subscription_plan', 'free') if user else 'free'
        
        emails = gmail_service.get_todays_emails(user_plan=user_plan)
        processed_emails = email_processor.process_emails(emails)
        
        # Track usage for unique emails only
        if user_model and emails:
            email_ids = [email.get('id', '') for email in emails if email.get('id')]
            unique_count = user_model.increment_usage_for_unique_emails(user_id, 'email_fetch', email_ids)
            print(f"📊 Email fetch: processed {unique_count} unique emails out of {len(emails)} total")
        
        return jsonify(processed_emails)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary')
@login_required
def api_summary():
    """API endpoint to get AI summary"""
    user_id = session.get('user_id')
    
    # Check usage limits
    usage_info = user_model.check_usage_limit(user_id) if user_model else None
    if usage_info and usage_info['exceeded']:
        return jsonify({'error': 'Usage limit exceeded. Please upgrade your plan.'}), 429
    
    # Check Gmail authentication
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    if not gmail_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    try:
        # Set Gmail token
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            return jsonify({'error': 'Gmail authentication expired'}), 401
        
        # Get user plan for email limits  
        user = user_model.get_user_by_id(user_id) if user_model else None
        user_plan = user.get('subscription_plan', 'free') if user else 'free'
        
        emails = gmail_service.get_todays_emails(user_plan=user_plan)
        processed_emails = email_processor.process_emails(emails)
        
        summary_result = ai_service.generate_daily_summary(processed_emails)
        
        # Track usage for unique emails only
        if user_model and emails:
            email_ids = [email.get('id', '') for email in emails if email.get('id')]
            unique_count = user_model.increment_usage_for_unique_emails(user_id, 'ai_summary', email_ids)
            print(f"📊 AI summary: processed {unique_count} unique emails out of {len(emails)} total")
        
        if summary_result['success']:
            return jsonify({
                'summary': summary_result['content'],
                'model_used': summary_result['model_used'],
                'email_count': summary_result['email_count']
            })
        else:
            return jsonify({'error': summary_result['error']}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-email', methods=['POST'])
@login_required
def api_analyze_email():
    import traceback
    user_id = session.get('user_id')
    data = request.get_json()
    debug_info = {}
    print('STEP 1: Entered /api/analyze-email endpoint')
    try:
        # EMERGENCY: Check if user exists and recover if needed
        print('STEP 2: Checking user/session integrity')
        if user_model:
            session_data = {
                'user_email': session.get('user_email'),
                'user_name': session.get('user_name'), 
                'subscription_plan': session.get('subscription_plan', 'free'),
                'subscription_status': session.get('subscription_status', 'active')
            }
            mismatch_fixed = user_model.check_and_repair_user_session_mismatch(user_id, session_data)
            if not mismatch_fixed:
                print('STEP 2a: User/session mismatch not fixed')
                return jsonify({
                    'error': 'Your account data was corrupted. Please log in again.',
                    'requires_login': True
                }), 401
        print('STEP 3: Getting user subscription info')
        user = user_model.get_user_by_id(user_id) if user_model else None
        user_plan = user.get('subscription_plan', 'free') if user else 'free'
        print(f'STEP 3a: user_plan={user_plan}')
        analysis_type = data.get('type', 'summary')
        is_thread_analysis = analysis_type == 'thread_analysis'
        print(f'STEP 4: analysis_type={analysis_type}, is_thread_analysis={is_thread_analysis}')
        if not is_thread_analysis and user_plan == 'free':
            print('STEP 4a: Free user, advanced analysis blocked')
            return jsonify({
                'error': 'Advanced AI analysis requires a Pro subscription. Thread viewing is available for free users.',
                'requires_upgrade': True,
                'feature': 'Advanced AI Analysis'
            }), 403
        if user_plan == 'free':
            print('STEP 5: Checking usage limits for free user')
            usage_info = user_model.check_usage_limit(user_id) if user_model else None
            if usage_info and usage_info['exceeded']:
                print('STEP 5a: Usage limit exceeded')
                return jsonify({
                    'error': 'Monthly usage limit exceeded. Please upgrade to Pro for unlimited analysis.',
                    'requires_upgrade': True,
                    'feature': 'Usage Limit'
                }), 429
        print('STEP 6: Checking Gmail authentication')
        gmail_token = user_model.get_gmail_token(user_id) if user_model else None
        if not gmail_token:
            print('STEP 6a: Gmail not connected')
            return jsonify({'error': 'Gmail not connected. Please connect your Gmail account first.'}), 401
        print('STEP 7: Setting Gmail credentials')
        gmail_service.set_credentials_from_token(gmail_token)
        if not gmail_service.is_authenticated():
            print('STEP 7a: Gmail authentication expired')
            return jsonify({'error': 'Gmail authentication expired. Please reconnect your Gmail account.'}), 401
        email_id = data.get('email_id')
        if not email_id:
            print('STEP 8: Email ID missing')
            return jsonify({'error': 'Email ID is required'}), 400
        print(f'STEP 9: Fetching email {email_id}')
        service = gmail_service._get_service()
        email_data = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        print('STEP 10: Parsing email')
        parsed_email = gmail_service._parse_email(email_data)
        if not parsed_email:
            print('STEP 10a: Email not found or could not be parsed')
            return jsonify({'error': 'Email not found or could not be parsed'}), 404
        print('STEP 11: Processing email (attachments if Pro)')
        try:
            if user_plan != 'free' and email_processor and document_processor and gmail_service:
                processed_email = email_processor.process_email_with_attachments(parsed_email)
            else:
                processed_email = email_processor._process_single_email(parsed_email) if email_processor else parsed_email
        except Exception as processing_error:
            debug_info['processing_error'] = str(processing_error)
            debug_info['processing_traceback'] = traceback.format_exc()
            print(f"⚠️ Email processing error: {processing_error}")
            print(debug_info['processing_traceback'])
            processed_email = parsed_email
        print('STEP 12: Preparing content for AI analysis')
        email_content = processed_email.get('body', '')
        subject = processed_email.get('subject', '')
        sender = processed_email.get('sender', '')
        try:
            if email_content:
                import re
                email_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', email_content)
                email_content = email_content.encode('utf-8', errors='ignore').decode('utf-8')
            if subject:
                subject = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', subject)
                subject = subject.encode('utf-8', errors='ignore').decode('utf-8')
            if sender:
                sender = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', sender)
                sender = sender.encode('utf-8', errors='ignore').decode('utf-8')
        except Exception as cleaning_error:
            debug_info['cleaning_error'] = str(cleaning_error)
            debug_info['cleaning_traceback'] = traceback.format_exc()
            print(f"⚠️ Content cleaning error: {cleaning_error}")
            print(debug_info['cleaning_traceback'])
            email_content = str(processed_email.get('body', ''))[:1000]
            subject = str(processed_email.get('subject', ''))[:200]
            sender = str(processed_email.get('sender', ''))[:100]
        print('STEP 13: Checking for attachment analysis')
        attachment_analysis = processed_email.get('attachment_analysis', '')
        if attachment_analysis and user_plan != 'free':
            email_content += f"\n\nAttachment Analysis:\n{attachment_analysis}"
        if not email_content.strip():
            snippet = processed_email.get('snippet', '')
            if snippet.strip():
                email_content = f"Email preview: {snippet}"
                print(f"🔍 Using email snippet as fallback content: {len(snippet)} chars")
            else:
                if subject.strip() or sender.strip():
                    email_content = f"Subject: {subject}\nFrom: {sender}\n\nThis email could not be fully extracted, but basic information is available for analysis."
                    print(f"🔍 Using subject/sender as fallback content")
                else:
                    debug_info['content_error'] = 'Email content could not be extracted and no fallback information is available'
                    print('STEP 14: Email content could not be extracted and no fallback info')
                    return jsonify({
                        'error': 'Email content could not be extracted and no fallback information is available',
                        'suggestion': 'This email may have an unsupported format. Try opening it in Gmail directly.',
                        'debug': debug_info
                    }), 400
        print('STEP 15: Calling AI analysis')
        try:
            if is_thread_analysis and user_plan == 'free':
                analysis_result = {
                    'success': True,
                    'content': f"""
## Thread Summary
**Subject:** {subject}
**From:** {sender}

## Basic Analysis
This email thread contains important information that may require your attention. 

**Email Preview:** {email_content[:300]}{'...' if len(email_content) > 300 else ''}

## Upgrade for More
Upgrade to Pro for detailed AI analysis including:
- Comprehensive thread analysis
- Action item extraction
- Response recommendations
- Document processing
- Priority assessment

[Upgrade to Pro](/pricing) to unlock advanced AI insights!
""",
                    'model_used': 'basic'
                }
            else:
                print('STEP 15a: Calling ai_service.analyze_email')
                analysis_result = ai_service.analyze_email(email_content, analysis_type)
                analysis_result['success'] = True
            print('STEP 16: AI analysis call completed')
        except Exception as ai_error:
            debug_info['ai_error'] = str(ai_error)
            debug_info['ai_traceback'] = traceback.format_exc()
            print(f"❌ AI analysis failed: {ai_error}")
            print(debug_info['ai_traceback'])
            return jsonify({
                'error': f'AI analysis service unavailable. Please try again later.',
                'technical_error': str(ai_error) if user_plan != 'free' else None,
                'debug': debug_info
            }), 500
        print('STEP 17: Tracking usage for unique emails')
        if user_model:
            unique_count = user_model.increment_usage_for_unique_emails(user_id, 'email_analysis', [email_id])
            print(f"📊 Email analysis: processed {unique_count} unique email (ID: {email_id})")
        if analysis_result and analysis_result.get('success'):
            print('STEP 18: Returning successful analysis result')
            return jsonify({
                'success': True,
                'content': analysis_result['content'],
                'model_used': analysis_result.get('model_used', 'unknown'),
                'type': analysis_type,
                'user_plan': user_plan,
                'is_basic': user_plan == 'free' and is_thread_analysis,
                'debug': debug_info
            })
        else:
            error_msg = analysis_result.get('error', 'Unknown AI analysis error') if analysis_result else 'AI analysis returned no result'
            debug_info['analysis_error'] = error_msg
            print(f"❌ AI analysis failed: {error_msg}")
            print('STEP 19: Returning failed analysis result')
            return jsonify({
                'success': False, 
                'error': 'Analysis could not be completed. Please try again or contact support if the issue persists.',
                'technical_error': error_msg if user_plan != 'free' else None,
                'debug': debug_info
            }), 500
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"❌ Exception in analyze-email: {str(e)}")
        print(f"❌ Full traceback: {error_details}")
        print(f"❌ Request data: {data}")
        print('STEP 20: Exception handler reached')
        return jsonify({
            'error': 'Analysis service temporarily unavailable. Please try again later.',
            'technical_error': str(e),
            'traceback': error_details,
            'request_data': data
        }), 500

@app.route('/api/process-emails')
@login_required
@subscription_required('pro')  # Advanced email processing requires Pro subscription
def api_process_emails():
    """API endpoint to process emails with AI analysis (called asynchronously)"""
    user_id = session.get('user_id')
    
    # Check usage limits
    usage_info = user_model.check_usage_limit(user_id) if user_model else None
    if usage_info and usage_info['exceeded']:
        return jsonify({'error': 'Usage limit exceeded. Please upgrade your plan.'}), 429
    
    # Check Gmail authentication
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    if not gmail_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    try:
        # Set Gmail token
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            return jsonify({'error': 'Gmail authentication expired'}), 401
        
        # Get more emails for comprehensive analysis (up to 20)
        all_emails = gmail_service.get_todays_emails(max_results=20)
        
        # Filter out newsletters and daily alerts
        filtered_emails = email_processor.filter_emails(all_emails)
        
        # Process emails with AI analysis
        processed_emails = email_processor.process_emails(filtered_emails)
        
        # Generate daily summary using hybrid AI
        try:
            summary_result = ai_service.generate_daily_summary(processed_emails)
            if summary_result['success']:
                daily_summary = summary_result['content']
                print(f"✅ Daily summary generated using {summary_result['model_used']}")
            else:
                daily_summary = f"Unable to generate summary: {summary_result['error']}"
                print(f"❌ Daily summary failed: {summary_result['error']}")
        except Exception as e:
            print(f"Error generating daily summary: {e}")
            daily_summary = "Unable to generate summary at this time."
        
        # Generate action items and recommendations using hybrid AI
        action_items = []
        recommendations = []
        
        # Process only the most important emails for AI analysis (limit to 10)
        important_emails = processed_emails[:10]
        
        for email in important_emails:
            try:
                # Extract action items
                action_result = ai_service.extract_action_items(
                    email.get('body', ''), 
                    email.get('subject', ''), 
                    email.get('sender', '')
                )
                if action_result['success']:
                    action_items.append({
                        'email_id': email.get('id'),
                        'subject': email.get('subject'),
                        'sender': email.get('sender'),
                        'action_items': action_result['content']
                    })
                    print(f"✅ Action items extracted using {action_result['model_used']}")
                else:
                    print(f"Error extracting action items from email {email.get('id')}: {action_result['error']}")
                
                # Generate recommendations
                rec_result = ai_service.generate_response_recommendations(
                    email.get('body', ''), 
                    email.get('subject', ''), 
                    email.get('sender', '')
                )
                if rec_result['success']:
                    recommendations.append({
                        'email_id': email.get('id'),
                        'subject': email.get('subject'),
                        'sender': email.get('sender'),
                        'recommendations': rec_result['content']
                    })
                    print(f"✅ Recommendations generated using {rec_result['model_used']}")
                else:
                    print(f"Error generating recommendations for email {email.get('id')}: {rec_result['error']}")
                    
            except Exception as e:
                print(f"Error processing email {email.get('id')}: {e}")
                continue
        
        # Track usage for unique emails only
        if user_model and important_emails:
            email_ids = [email.get('id', '') for email in important_emails if email.get('id')]
            unique_count = user_model.increment_usage_for_unique_emails(user_id, 'comprehensive_analysis', email_ids)
            print(f"📊 Comprehensive analysis: processed {unique_count} unique emails out of {len(important_emails)} total")
        
        return jsonify({
            'summary': daily_summary,
            'action_items': action_items,
            'recommendations': recommendations,
            'email_count': len(processed_emails)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Pro-only features
@app.route('/api/pro/document-analysis', methods=['POST'])
@login_required
@subscription_required('pro')  # Document analysis requires Pro subscription
def api_document_analysis():
    """Pro feature: Advanced document processing and analysis"""
    user_id = session.get('user_id')
    
    # Check Gmail authentication
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    if not gmail_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    try:
        data = request.get_json()
        email_id = data.get('email_id')
        
        if not email_id:
            return jsonify({'error': 'Email ID is required'}), 400
        
        # Set Gmail token
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            return jsonify({'error': 'Gmail authentication expired'}), 401
        
        # Get email with attachments
        service = gmail_service._get_service()
        email_data = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        parsed_email = gmail_service._parse_email(email_data)
        if not parsed_email:
            return jsonify({'error': 'Email not found'}), 404
        
        # Process attachments if available
        document_analysis = {
            'attachments_found': 0,
            'documents_processed': 0,
            'analysis_results': [],
            'key_insights': [],
            'errors': []
        }
        
        if parsed_email.get('has_attachments') and parsed_email.get('attachments'):
            document_analysis['attachments_found'] = len(parsed_email['attachments'])
            
            for attachment in parsed_email['attachments']:
                try:
                    # Get attachment content
                    attachment_data = gmail_service.get_attachment_content(email_id, attachment['id'])
                    
                    if attachment_data and document_processor:
                        # Extract text from document
                        doc_result = document_processor.extract_document_text(
                            attachment_data, 
                            attachment['mime_type'], 
                            attachment['filename']
                        )
                        
                        if doc_result['success'] and doc_result['text']:
                            document_analysis['documents_processed'] += 1
                            
                            # Analyze document content
                            doc_analysis = document_processor.analyze_document_content(
                                doc_result['text'], 
                                attachment['filename']
                            )
                            
                            # Generate AI insights for the document
                            if ai_service and doc_analysis['success']:
                                doc_prompt = f"""
                                Analyze this document content and provide insights:
                                
                                Document: {attachment['filename']}
                                Type: {doc_analysis['document_type']}
                                Content: {doc_result['text'][:1000]}...
                                
                                Please provide:
                                1. Key information extracted
                                2. Important points and highlights
                                3. Action items or next steps
                                4. Risk assessment (if applicable)
                                5. Recommendations
                                """
                                
                                try:
                                    ai_insights = ai_service.analyze_text(doc_prompt)
                                    doc_analysis['ai_insights'] = ai_insights
                                except Exception as e:
                                    doc_analysis['ai_insights'] = f"Unable to generate AI insights: {str(e)}"
                            
                            document_analysis['analysis_results'].append({
                                'filename': attachment['filename'],
                                'mime_type': attachment['mime_type'],
                                'extraction_result': doc_result,
                                'content_analysis': doc_analysis
                            })
                            
                            # Add key points to overall insights
                            if doc_analysis.get('key_points'):
                                document_analysis['key_insights'].extend(doc_analysis['key_points'])
                        else:
                            document_analysis['errors'].append(
                                f"Failed to extract text from {attachment['filename']}: {doc_result.get('error', 'Unknown error')}"
                            )
                    else:
                        document_analysis['errors'].append(
                            f"Failed to retrieve attachment content for {attachment['filename']}"
                        )
                        
                except Exception as e:
                    document_analysis['errors'].append(
                        f"Error processing {attachment.get('filename', 'unknown')}: {str(e)}"
                    )
        
        return jsonify({
            'success': True,
            'document_analysis': document_analysis,
            'feature': 'pro_document_analysis'
        })
        
    except Exception as e:
        return jsonify({'error': f'Document analysis failed: {str(e)}'}), 500

@app.route('/api/pro/enhanced-email-analysis', methods=['POST'])
@login_required
@subscription_required('pro')  # Enhanced email analysis requires Pro subscription
def api_enhanced_email_analysis():
    """Pro feature: Enhanced email analysis with deeper insights"""
    user_id = session.get('user_id')
    
    # Check Gmail authentication
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    if not gmail_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    try:
        data = request.get_json()
        email_id = data.get('email_id')
        analysis_depth = data.get('depth', 'comprehensive')  # basic, detailed, comprehensive
        
        if not email_id:
            return jsonify({'error': 'Email ID is required'}), 400
        
        # Set Gmail token
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            return jsonify({'error': 'Gmail authentication expired'}), 401
        
        # Get email data
        service = gmail_service._get_service()
        email_data = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        parsed_email = gmail_service._parse_email(email_data)
        if not parsed_email:
            return jsonify({'error': 'Email not found'}), 404
        
        # Enhanced analysis
        enhanced_analysis = {
            'email_metadata': {
                'subject': parsed_email.get('subject', ''),
                'sender': parsed_email.get('sender', ''),
                'date': str(parsed_email.get('date', '')),
                'priority': parsed_email.get('priority', 'normal'),
                'has_attachments': parsed_email.get('has_attachments', False)
            },
            'content_analysis': {
                'word_count': len(parsed_email.get('body', '').split()),
                'sentiment': 'neutral',
                'urgency_level': 'normal',
                'complexity_score': 0,
                'key_topics': [],
                'entities_mentioned': []
            },
            'ai_insights': {
                'summary': '',
                'action_items': [],
                'recommendations': [],
                'context_analysis': '',
                'response_suggestions': []
            },
            'business_insights': {
                'meeting_requests': [],
                'deadlines': [],
                'follow_ups': [],
                'decisions_needed': []
            }
        }
        
        # Analyze email content
        email_content = parsed_email.get('body', '')
        subject = parsed_email.get('subject', '')
        sender = parsed_email.get('sender', '')
        
        # Basic content analysis
        content_lower = email_content.lower()
        subject_lower = subject.lower()
        
        # Detect urgency
        urgency_keywords = ['urgent', 'asap', 'emergency', 'deadline', 'important']
        urgency_score = sum(1 for keyword in urgency_keywords if keyword in subject_lower or keyword in content_lower)
        if urgency_score >= 2:
            enhanced_analysis['content_analysis']['urgency_level'] = 'high'
        elif urgency_score >= 1:
            enhanced_analysis['content_analysis']['urgency_level'] = 'medium'
        
        # Detect sentiment
        positive_words = ['great', 'excellent', 'good', 'pleased', 'happy', 'successful']
        negative_words = ['problem', 'issue', 'concern', 'disappointed', 'frustrated', 'urgent']
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if positive_count > negative_count:
            enhanced_analysis['content_analysis']['sentiment'] = 'positive'
        elif negative_count > positive_count:
            enhanced_analysis['content_analysis']['sentiment'] = 'negative'
        
        # Calculate complexity score
        sentences = email_content.count('.') + email_content.count('!') + email_content.count('?')
        questions = content_lower.count('?')
        technical_terms = sum(1 for term in ['api', 'database', 'server', 'code', 'bug', 'feature'] if term in content_lower)
        
        enhanced_analysis['content_analysis']['complexity_score'] = (
            len(email_content) * 0.1 + sentences * 5 + questions * 10 + technical_terms * 15
        )
        
        # Generate AI insights
        if ai_service:
            enhanced_prompt = f"""
            Provide comprehensive analysis for this email:
            
            Subject: {subject}
            From: {sender}
            Content: {email_content}
            
            Please provide:
            1. **Executive Summary**: Brief overview of the email's purpose and importance
            2. **Key Action Items**: Specific tasks or actions required
            3. **Context Analysis**: Background and context of the communication
            4. **Response Recommendations**: Suggested response approaches
            5. **Business Impact**: Potential impact on business or projects
            6. **Follow-up Actions**: Recommended next steps
            7. **Risk Assessment**: Any potential issues or concerns
            8. **Opportunities**: Potential opportunities or positive outcomes
            
            Format your response in clear sections with bullet points where appropriate.
            """
            
            try:
                ai_analysis = ai_service.analyze_text(enhanced_prompt)
                enhanced_analysis['ai_insights']['summary'] = ai_analysis
                
                # Extract specific insights
                if 'action items' in ai_analysis.lower():
                    enhanced_analysis['ai_insights']['action_items'] = [
                        line.strip() for line in ai_analysis.split('\n') 
                        if any(keyword in line.lower() for keyword in ['action', 'task', 'do', 'complete', 'follow'])
                    ]
                
                if 'recommendation' in ai_analysis.lower():
                    enhanced_analysis['ai_insights']['recommendations'] = [
                        line.strip() for line in ai_analysis.split('\n') 
                        if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'should', 'could'])
                    ]
                    
            except Exception as e:
                enhanced_analysis['ai_insights']['summary'] = f"Unable to generate AI analysis: {str(e)}"
        
        return jsonify({
            'success': True,
            'enhanced_analysis': enhanced_analysis,
            'feature': 'pro_enhanced_email_analysis'
        })
        
    except Exception as e:
        return jsonify({'error': f'Enhanced analysis failed: {str(e)}'}), 500

# Enterprise-only features
@app.route('/api/enterprise/team-analytics')
@login_required
@subscription_required('enterprise')  # Team analytics requires Enterprise subscription
def api_team_analytics():
    """Enterprise feature: Team collaboration analytics"""
    user_id = session.get('user_id')
    
    # Check Gmail authentication
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    if not gmail_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    try:
        # Set Gmail token
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            return jsonify({'error': 'Gmail authentication expired'}), 401
        
        # Get team emails (emails from colleagues/team members)
        team_emails = gmail_service.get_todays_emails(max_results=50)
        
        # Analyze team communication patterns
        team_analysis = {
            'total_team_emails': len(team_emails),
            'team_members': [],
            'communication_patterns': {},
            'project_insights': [],
            'collaboration_metrics': {}
        }
        
        # Extract team members and analyze communication
        team_members = set()
        for email in team_emails:
            sender = email.get('sender', '')
            if sender:
                team_members.add(sender)
                
                # Analyze communication patterns
                if sender not in team_analysis['communication_patterns']:
                    team_analysis['communication_patterns'][sender] = {
                        'email_count': 0,
                        'response_time': [],
                        'topics': []
                    }
                team_analysis['communication_patterns'][sender]['email_count'] += 1
        
        team_analysis['team_members'] = list(team_members)
        
        # Generate team insights using AI
        if ai_service and team_emails:
            team_content = "\n".join([f"From: {e.get('sender', '')}\nSubject: {e.get('subject', '')}\nBody: {e.get('body', '')[:200]}..." for e in team_emails[:10]])
            
            team_prompt = f"""
            Analyze this team communication data and provide insights:
            
            {team_content}
            
            Please provide:
            1. Team communication patterns
            2. Key projects or topics being discussed
            3. Collaboration opportunities
            4. Potential bottlenecks or issues
            5. Recommendations for improved team communication
            
            Format as a structured analysis with clear sections.
            """
            
            try:
                team_insights = ai_service.analyze_text(team_prompt)
                team_analysis['ai_insights'] = team_insights
            except Exception as e:
                team_analysis['ai_insights'] = f"Unable to generate AI insights: {str(e)}"
        
        return jsonify({
            'success': True,
            'team_analytics': team_analysis,
            'feature': 'enterprise_team_analytics'
        })
        
    except Exception as e:
        return jsonify({'error': f'Team analytics failed: {str(e)}'}), 500

@app.route('/api/pro/custom-insights', methods=['POST'])
@login_required
@subscription_required('pro')  # Custom insights require Pro subscription
def api_custom_insights():
    """Pro feature: Custom AI insights based on user-defined criteria"""
    user_id = session.get('user_id')
    
    # Check Gmail authentication
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    if not gmail_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    try:
        data = request.get_json()
        insight_type = data.get('type', 'general')
        custom_criteria = data.get('criteria', '')
        email_count = data.get('email_count', 20)
        
        # Set Gmail token
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            return jsonify({'error': 'Gmail authentication expired'}), 401
        
        # Get emails based on custom criteria
        all_emails = gmail_service.get_todays_emails(max_results=email_count)
        
        # Filter emails based on custom criteria
        filtered_emails = []
        for email in all_emails:
            email_content = f"{email.get('subject', '')} {email.get('body', '')}".lower()
            if any(criterion.lower() in email_content for criterion in custom_criteria.split(',')):
                filtered_emails.append(email)
        
        # Generate custom insights using AI
        if ai_service and filtered_emails:
            email_content = "\n\n".join([
                f"From: {e.get('sender', '')}\nSubject: {e.get('subject', '')}\nBody: {e.get('body', '')[:300]}..."
                for e in filtered_emails[:10]
            ])
            
            custom_prompt = f"""
            Generate custom insights based on the following criteria: {custom_criteria}
            
            Email data:
            {email_content}
            
            Please provide:
            1. Key insights related to the specified criteria
            2. Patterns and trends
            3. Actionable recommendations
            4. Risk assessment (if applicable)
            5. Opportunities identified
            
            Focus specifically on the criteria: {custom_criteria}
            """
            
            try:
                custom_analysis = ai_service.analyze_text(custom_prompt)
                return jsonify({
                    'success': True,
                    'custom_insights': custom_analysis,
                    'emails_analyzed': len(filtered_emails),
                    'criteria_used': custom_criteria,
                    'feature': 'pro_custom_insights'
                })
            except Exception as e:
                return jsonify({'error': f'Custom analysis failed: {str(e)}'}), 500
        else:
            return jsonify({'error': 'No emails found matching criteria'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Custom insights failed: {str(e)}'}), 500

@app.route('/api/enterprise/advanced-analytics')
@login_required
@subscription_required('enterprise')  # Advanced analytics require Enterprise subscription
def api_advanced_analytics():
    """Enterprise feature: Advanced email analytics and reporting"""
    user_id = session.get('user_id')
    
    # Check Gmail authentication
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    if not gmail_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    try:
        # Set Gmail token
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            return jsonify({'error': 'Gmail authentication expired'}), 401
        
        # Get comprehensive email data
        all_emails = gmail_service.get_todays_emails(max_results=100)
        
        # Advanced analytics
        analytics = {
            'email_volume': {
                'total_emails': len(all_emails),
                'emails_by_hour': {},
                'emails_by_sender': {},
                'emails_by_type': {}
            },
            'communication_patterns': {
                'response_times': [],
                'thread_lengths': [],
                'engagement_metrics': {}
            },
            'content_analysis': {
                'topics': [],
                'sentiment': {},
                'urgency_levels': {}
            },
            'productivity_insights': {
                'action_items': [],
                'deadlines': [],
                'follow_ups': []
            }
        }
        
        # Analyze email patterns
        for email in all_emails:
            # Time-based analysis
            email_date = email.get('date')
            if email_date:
                hour = email_date.hour if hasattr(email_date, 'hour') else 0
                analytics['email_volume']['emails_by_hour'][hour] = analytics['email_volume']['emails_by_hour'].get(hour, 0) + 1
            
            # Sender analysis
            sender = email.get('sender', '')
            if sender:
                analytics['email_volume']['emails_by_sender'][sender] = analytics['email_volume']['emails_by_sender'].get(sender, 0) + 1
            
            # Content analysis
            subject = email.get('subject', '').lower()
            body = email.get('body', '').lower()
            
            # Detect urgency
            urgency_keywords = ['urgent', 'asap', 'emergency', 'deadline', 'important']
            urgency_score = sum(1 for keyword in urgency_keywords if keyword in subject or keyword in body)
            if urgency_score > 0:
                analytics['content_analysis']['urgency_levels'][email.get('id')] = urgency_score
        
        # Generate AI-powered insights
        if ai_service and all_emails:
            email_summary = "\n".join([
                f"From: {e.get('sender', '')} | Subject: {e.get('subject', '')} | Date: {e.get('date', '')}"
                for e in all_emails[:20]
            ])
            
            analytics_prompt = f"""
            Provide advanced analytics insights for this email data:
            
            {email_summary}
            
            Please analyze:
            1. Communication efficiency patterns
            2. Productivity bottlenecks
            3. Time management insights
            4. Priority management recommendations
            5. Workflow optimization suggestions
            6. Risk assessment for missed communications
            
            Provide actionable insights and specific recommendations.
            """
            
            try:
                ai_insights = ai_service.analyze_text(analytics_prompt)
                analytics['ai_insights'] = ai_insights
            except Exception as e:
                analytics['ai_insights'] = f"Unable to generate AI insights: {str(e)}"
        
        return jsonify({
            'success': True,
            'advanced_analytics': analytics,
            'feature': 'enterprise_advanced_analytics'
        })
        
    except Exception as e:
        return jsonify({'error': f'Advanced analytics failed: {str(e)}'}), 500

@app.route('/test-session')
def test_session():
    """Test session functionality"""
    session['test_variable'] = 'Session is working!'
    return f"""
    <h2>Session Test</h2>
    <p><strong>Session variable value:</strong> {session.get('test_variable', 'Not set')}</p>
    <p><strong>User ID in session:</strong> {session.get('user_id', 'Not logged in')}</p>
    <p><strong>Session ID:</strong> {session.get('_id', 'No session ID')}</p>
    <p><strong>Session permanent:</strong> {session.get('_permanent', False)}</p>
    <p><strong>All session data:</strong> {dict(session)}</p>
    <p><strong>App config:</strong></p>
    <ul>
        <li>SECRET_KEY set: {'Yes' if app.secret_key and app.secret_key != 'your-secret-key-here-change-this-in-production' else 'No'}</li>
        <li>SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}</li>
        <li>SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY')}</li>
        <li>SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE')}</li>
        <li>SESSION_COOKIE_DOMAIN: {app.config.get('SESSION_COOKIE_DOMAIN')}</li>
        <li>SESSION_COOKIE_PATH: {app.config.get('SESSION_COOKIE_PATH')}</li>
    </ul>
    <p><strong>Environment:</strong></p>
    <ul>
        <li>DIGITALOCEAN_APP_PLATFORM: {os.environ.get('DIGITALOCEAN_APP_PLATFORM')}</li>
        <li>PORT: {os.environ.get('PORT')}</li>
        <li>FLASK_ENV: {os.environ.get('FLASK_ENV')}</li>
    </ul>
    <p><a href="/dashboard">Go to Dashboard</a></p>
    """

@app.route('/features')
def features():
    """Features page showing all app features organized by plan"""
    return render_template('features.html')

# Debug and diagnostic endpoints
@app.route('/debug/token-status')
@login_required
def debug_token_status():
    """Debug endpoint to check token status and integrity"""
    user_id = session.get('user_id')
    
    if not user_model:
        return jsonify({'error': 'User model not available'}), 500
    
    try:
        # Force database sync first
        user_model.force_database_sync()
        
        # Get comprehensive user state
        user_data = user_model.get_user_by_id(user_id)
        token_data = user_model.get_gmail_token(user_id)
        
        # Check database connectivity
        connectivity = user_model.check_database_connectivity()
        
        # Get raw database state
        user_model.check_database_state(user_id)
        
        status = {
            'user_id': user_id,
            'user_found': user_data is not None,
            'token_found': token_data is not None,
            'token_length': len(str(token_data)) if token_data else 0,
            'database_connectivity': connectivity,
            'user_email': user_data.get('email') if user_data else None,
            'gmail_email': user_data.get('gmail_email') if user_data else None,
            'session_authenticated': session.get('gmail_authenticated', False),
            'subscription_plan': user_data.get('subscription_plan') if user_data else None,
            'last_login': user_data.get('last_login') if user_data else None
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/repair-token', methods=['POST'])
@login_required 
def debug_repair_token():
    """Debug endpoint to manually repair token integrity"""
    user_id = session.get('user_id')
    
    if not user_model:
        return jsonify({'error': 'User model not available'}), 500
    
    try:
        # Attempt to repair token integrity
        repair_success = user_model.repair_user_token_integrity(user_id)
        
        if repair_success:
            return jsonify({
                'success': True,
                'message': 'Token integrity repair completed'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Token integrity repair failed - no token available to restore'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/emergency-recovery', methods=['POST'])
@login_required
def debug_emergency_recovery():
    """Emergency endpoint to recover missing user records"""
    user_id = session.get('user_id')
    
    if not user_model:
        return jsonify({'error': 'User model not available'}), 500
    
    try:
        # Get session data
        session_data = {
            'user_email': session.get('user_email'),
            'user_name': session.get('user_name'), 
            'subscription_plan': session.get('subscription_plan', 'free'),
            'subscription_status': session.get('subscription_status', 'active')
        }
        
        print(f"🚨 [EMERGENCY] Manual recovery requested for user {user_id}")
        print(f"🔍 [EMERGENCY] Session data: {session_data}")
        
        # Attempt emergency recovery
        recovery_success = user_model.emergency_user_recovery(user_id, session_data)
        
        if recovery_success:
            return jsonify({
                'success': True,
                'message': f'User {user_id} successfully recovered from session data',
                'user_email': session_data.get('user_email'),
                'recovery_method': 'emergency_session_reconstruction'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Emergency recovery failed for user {user_id}',
                'session_data': session_data
            })
            
    except Exception as e:
        print(f"❌ [EMERGENCY] Manual recovery error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/debug/user-status')
@login_required
def debug_user_status():
    """Enhanced debug endpoint to check user existence and session consistency"""
    user_id = session.get('user_id')
    
    if not user_model:
        return jsonify({'error': 'User model not available'}), 500
    
    try:
        # Check if user exists in database
        user_exists = user_model.ensure_user_integrity(user_id)
        user_data = user_model.get_user_by_id(user_id) if user_exists else None
        token_data = user_model.get_gmail_token(user_id) if user_exists else None
        
        # Get session data
        session_info = {
            'user_id': session.get('user_id'),
            'user_email': session.get('user_email'),
            'user_name': session.get('user_name'),
            'subscription_plan': session.get('subscription_plan'),
            'subscription_status': session.get('subscription_status'),
            'gmail_authenticated': session.get('gmail_authenticated')
        }
        
        status = {
            'user_id': user_id,
            'user_exists_in_db': user_exists,
            'user_data_found': user_data is not None,
            'token_found': token_data is not None,
            'session_info': session_info,
            'database_user_info': {
                'email': user_data.get('email') if user_data else None,
                'subscription_plan': user_data.get('subscription_plan') if user_data else None,
                'gmail_email': user_data.get('gmail_email') if user_data else None,
                'created_at': user_data.get('created_at') if user_data else None
            } if user_data else None,
            'issue_detected': not user_exists,
            'recovery_possible': bool(session_info.get('user_email'))
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/backup-database')
def backup_database_endpoint():
    """Admin endpoint to create database backup"""
    try:
        from database_backup import backup_database
        import tempfile
        import os
        
        # Create backup in temp directory
        db_path = user_model.db_manager.db_path if user_model else 'users.db'
        
        # Create temporary backup file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_backup_path = temp_file.name
        
        # Create backup using our utility
        backup_file = backup_database(db_path, temp_backup_path)
        
        if backup_file and os.path.exists(backup_file):
            # Read backup content
            with open(backup_file, 'r') as f:
                backup_content = f.read()
            
            # Clean up temp file
            os.unlink(backup_file)
            
            # Generate download filename
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            download_name = f'database_backup_{timestamp}.json'
            
            # Return as downloadable response
            from flask import Response
            return Response(
                backup_content,
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename={download_name}'}
            )
        else:
            return jsonify({'error': 'Backup failed'}), 500
            
    except Exception as e:
        print(f"❌ Backup endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/database-stats')
def database_stats_endpoint():
    """Admin endpoint to get database statistics"""
    try:
        import sqlite3
        import os
        
        db_path = user_model.db_manager.db_path if user_model else 'users.db'
        
        # Check if database exists
        if not os.path.exists(db_path):
            return jsonify({
                'error': 'Database file not found',
                'database_path': db_path
            }), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Get table counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count
        
        # Get database size
        db_size = os.path.getsize(db_path)
        
        conn.close()
        
        return jsonify({
            'database_path': db_path,
            'database_size_bytes': db_size,
            'database_size_mb': round(db_size / 1024 / 1024, 2),
            'table_counts': stats,
            'total_tables': len(stats),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-response', methods=['POST'])
@login_required
def api_generate_response():
    """API endpoint to generate an AI response for a given email"""
    import traceback
    
    print("🔍 [DEBUG] /api/generate-response called")
    
    user_id = session.get('user_id')
    print(f"🔍 [DEBUG] User ID: {user_id}")
    
    data = request.get_json()
    print(f"🔍 [DEBUG] Request data: {data}")
    
    email_id = data.get('email_id')
    if not email_id:
        print("❌ [DEBUG] Email ID missing from request")
        return jsonify({'success': False, 'error': 'Email ID is required'}), 400
    
    print(f"🔍 [DEBUG] Processing email ID: {email_id}")
    
    try:
        # Check Gmail authentication
        print("🔍 [DEBUG] Checking Gmail authentication...")
        gmail_token = user_model.get_gmail_token(user_id) if user_model else None
        if not gmail_token:
            print("❌ [DEBUG] No Gmail token found")
            return jsonify({'success': False, 'error': 'Gmail not connected'}), 401
        
        print("🔍 [DEBUG] Gmail token found, setting credentials...")
        gmail_service.set_credentials_from_token(gmail_token)
        
        if not gmail_service.is_authenticated():
            print("❌ [DEBUG] Gmail authentication failed")
            return jsonify({'success': False, 'error': 'Gmail authentication expired'}), 401
        
        print("✅ [DEBUG] Gmail authentication successful")
        
        # Fetch the email
        print(f"🔍 [DEBUG] Fetching email with ID: {email_id}")
        service = gmail_service._get_service()
        email_data = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        print(f"🔍 [DEBUG] Email data fetched, parsing...")
        parsed_email = gmail_service._parse_email(email_data)
        if not parsed_email:
            print("❌ [DEBUG] Failed to parse email data")
            return jsonify({'success': False, 'error': 'Email not found'}), 404
        
        print(f"✅ [DEBUG] Email parsed successfully")
        print(f"🔍 [DEBUG] Email subject: {parsed_email.get('subject', 'No subject')}")
        print(f"🔍 [DEBUG] Email sender: {parsed_email.get('sender', 'Unknown')}")
        
        email_content = parsed_email.get('body', '')
        subject = parsed_email.get('subject', '')
        sender = parsed_email.get('sender', '')
        
        print(f"🔍 [DEBUG] Email content length: {len(email_content)} characters")
        print(f"🔍 [DEBUG] Calling AI service to generate response...")
        
        # Generate AI response
        response_result = ai_service.generate_response_recommendations(email_content, subject, sender)
        
        print(f"🔍 [DEBUG] AI response result: {response_result}")
        
        if response_result.get('success'):
            print("✅ [DEBUG] AI response generated successfully")
            return jsonify({
                'success': True, 
                'response': response_result['content'], 
                'model_used': response_result.get('model_used', 'unknown'),
                'debug': {
                    'email_id': email_id,
                    'content_length': len(email_content),
                    'subject': subject,
                    'sender': sender
                }
            })
        else:
            print(f"❌ [DEBUG] AI response generation failed: {response_result.get('error')}")
            return jsonify({
                'success': False, 
                'error': response_result.get('error', 'Failed to generate response'),
                'debug': {
                    'email_id': email_id,
                    'ai_error': response_result.get('error'),
                    'ai_result': response_result
                }
            }), 500
            
    except Exception as e:
        print(f"❌ [DEBUG] Exception in /api/generate-response: {str(e)}")
        print(f"❌ [DEBUG] Exception type: {type(e).__name__}")
        print(f"❌ [DEBUG] Full traceback:")
        print(traceback.format_exc())
        
        return jsonify({
            'success': False, 
            'error': str(e),
            'debug': {
                'email_id': email_id,
                'exception_type': type(e).__name__,
                'exception_message': str(e),
                'traceback': traceback.format_exc()
            }
        }), 500

@app.route('/admin/user-count')
@admin_required
def admin_user_count():
    """Return total number of users"""
    count = user_model.count_users() if user_model else 0
    return jsonify({'user_count': count})

@app.route('/admin/users')
@admin_required
def admin_users():
    """Paginated list of users"""
    page = int(request.args.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    users = user_model.get_users_paginated(offset, per_page) if user_model else []
    return jsonify({'users': users, 'page': page, 'per_page': per_page})

@app.route('/admin/search-users')
@admin_required
def admin_search_users():
    """Search users by name or email"""
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Query required'}), 400
    users = user_model.search_users(query) if user_model else []
    return jsonify({'results': users, 'query': query})

@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    """Get details for a specific user"""
    user = user_model.get_user_by_id(user_id) if user_model else None
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port) 