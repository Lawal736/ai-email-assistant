import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
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

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-this-in-production')

# Configure session for production vs development
if os.environ.get('K_SERVICE') or os.environ.get('CLOUD_RUN_SERVICE'):
    # Production environment (Cloud Run)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=30)
    )
    print("🔧 Production session configuration applied")
else:
    # Development environment
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=30)
    )
    print("🔧 Development session configuration applied")

CORS(app)

# Initialize database and services
try:
    db_manager = DatabaseManager()
    user_model = User(db_manager)
    plan_model = SubscriptionPlan(db_manager)
    payment_model = PaymentRecord(db_manager)
    payment_service = PaymentService()
    print("✅ Database and payment services initialized")
except Exception as e:
    print(f"⚠️ Database initialization failed: {e}")
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
    """Main page"""
    return render_template('index.html')

@app.route('/pricing')
def pricing():
    """Pricing page"""
    # Get user's IP address for currency detection
    user_ip = request.remote_addr
    
    # Detect user's currency
    user_currency = currency_service.detect_user_currency(user_ip)
    
    # Get plans from database
    if plan_model:
        plans = plan_model.get_all_plans()
    else:
        plans = []
    
    # Convert plan prices to user's currency
    converted_plans = currency_service.convert_plan_prices(plans, user_currency)
    
    # Get currency info
    currency_info = currency_service.get_currency_info(user_currency)
    
    # Save user's currency preference if logged in
    if session.get('user_id'):
        currency_service.save_user_currency_preference(session['user_id'], user_currency)
    
    return render_template('pricing.html', 
                         plans=converted_plans, 
                         currency_info=currency_info,
                         user_currency=user_currency)

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    user_id = session.get('user_id')
    user = user_model.get_user_by_id(user_id) if user_model else None
    if user:
        session['subscription_plan'] = user.get('subscription_plan', 'free')
        session['subscription_status'] = user.get('subscription_status', 'inactive')
        session['subscription_expires'] = user.get('subscription_expires')
    # Check if Gmail service is available
    if not gmail_service:
        flash('Gmail service is not available. Please check your configuration.', 'error')
        return redirect(url_for('index'))
    
    # Check if Gmail is authenticated for this user
    gmail_token = user_model.get_gmail_token(user_id) if user_model else None
    
    if not gmail_token:
        flash('Please connect your Gmail account first', 'warning')
        return redirect(url_for('connect_gmail'))
    
    # Set Gmail token for service
    try:
        if gmail_token:
            gmail_service.set_credentials_from_token(gmail_token)
    except Exception as e:
        flash('Gmail token expired. Please reconnect your account.', 'warning')
        return redirect(url_for('connect_gmail'))
    
    # Check if Gmail is authenticated
    if not gmail_service.is_authenticated():
        flash('Please connect your Gmail account first', 'warning')
        return redirect(url_for('connect_gmail'))
    
    # Ensure session variable is set if Gmail is authenticated
    if gmail_service.is_authenticated() and not session.get('gmail_authenticated'):
        session['gmail_authenticated'] = True
    
    try:
        # Get only 10 most recent emails for immediate display
        recent_emails = gmail_service.get_todays_emails(max_results=10)
        print(f"📧 Found {len(recent_emails)} recent emails")
        
        if len(recent_emails) == 0:
            # No emails found for today
            return render_template('dashboard.html', 
                                 emails=[], 
                                 email_threads={},
                                 summary="No emails found for today. Try checking a different date range or your Gmail connection.",
                                 action_items=[],
                                 recommendations=[],
                                 date=datetime.now().strftime('%B %d, %Y'),
                                 ai_processing=False)
        
        # Filter out newsletters and daily alerts (less aggressive)
        filtered_emails = email_processor.filter_emails(recent_emails)
        print(f"🔍 After filtering: {len(filtered_emails)} emails")
        
        # If no emails after filtering, show all emails
        if len(filtered_emails) == 0:
            print("⚠️ No emails after filtering, showing all emails")
            filtered_emails = recent_emails
        
        # Process emails with basic info only (no AI analysis yet)
        processed_emails = email_processor.process_emails_basic(filtered_emails)
        print(f"✅ Processed {len(processed_emails)} emails")
        
        # Group emails by sender and subject for thread analysis
        email_threads = email_processor.group_emails_by_thread(processed_emails)
        print(f"🧵 Created {len(email_threads)} email threads")
        
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
        auth_url = gmail_service.get_authorization_url()
        return render_template('auth_redirect.html', auth_url=auth_url)
    except Exception as e:
        flash(f'Error starting authentication: {str(e)}', 'error')
        return redirect(url_for('connect_gmail'))

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth callback"""
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
            user_model.update_gmail_token(user_id, json.dumps(token_data), gmail_email)
            print("✅ Gmail token and email saved to database")
        else:
            print("❌ Failed to save token - user_model or token_data is None")
        
        # Set session variable to indicate Gmail is authenticated
        session['gmail_authenticated'] = True
        print("✅ Session updated with Gmail authentication")
        flash('Gmail connected successfully!', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"❌ Error in OAuth callback: {str(e)}")
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
        
        # Remove Gmail token and email from database
        if user_model:
            user_model.update_gmail_token(user_id, None, None)
            print(f"✅ Gmail token and email removed for user {user_id}")
        
        # Clear Gmail authentication from session
        session.pop('gmail_authenticated', None)
        print(f"✅ Gmail authentication cleared from session for user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Gmail account disconnected successfully'
        })
    except Exception as e:
        print(f"❌ Error disconnecting Gmail: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to disconnect Gmail: {str(e)}'
        })

# Helper to ensure session currency is set
def ensure_session_currency():
    """Ensure session currency is set for logged-in users"""
    if session.get('user_id') and not session.get('user_currency'):
        try:
            # Try to get from database first
            user_currency = currency_service.get_user_currency_preference(session['user_id'])
            if not user_currency:
                # Fallback to NGN for Paystack compatibility
                user_currency = 'NGN'
            session['user_currency'] = user_currency
            print(f"🔍 [DEBUG] ensure_session_currency: Set to {user_currency}")
        except Exception as e:
            print(f"⚠️ [DEBUG] ensure_session_currency error: {e}")
            session['user_currency'] = 'NGN'
    elif not session.get('user_currency'):
        # Set default for non-logged in users
        session['user_currency'] = 'NGN'
        print(f"🔍 [DEBUG] ensure_session_currency: Set default to NGN")

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
    
    # Get user's currency preference
    user_currency = session.get('user_currency', 'USD')
    print(f"🔍 [DEBUG] Using currency: {user_currency}")
    
    from currency_service import currency_service
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
        from currency_service import currency_service
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

# User account routes
@app.route('/account')
@login_required
def account():
    """User account page"""
    user_id = session.get('user_id')
    # Always fetch the latest user data from the database
    user = user_model.get_user_by_id(user_id) if user_model else None
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
    
    # Get user's currency
    user_currency = currency_service.get_user_currency(user_id) if user_id else 'USD'
    currency_symbol = currency_service.get_currency_symbol(user_currency)
    # Get plan price in user's currency
    for plan in plans:
        plan['price_local'] = currency_service.convert_and_format(plan['price_monthly'], 'USD', user_currency)
        plan['currency_symbol'] = currency_symbol
    # Get user's quota for usage display
    plan_quota = None
    if user and user.get('subscription_plan'):
        user_plan = plan_model.get_plan_by_name(user['subscription_plan'])
        plan_quota = user_plan['email_limit'] if user_plan else None
    return render_template('account/subscription.html', user=user, plans=plans, user_currency=user_currency, currency_symbol=currency_symbol, plan_quota=plan_quota)

@app.route('/account/billing')
@login_required
def account_billing():
    """Billing history page"""
    user_id = session.get('user_id')
    payments = payment_model.get_user_payments(user_id) if payment_model else []
    # For each payment, use the actual paid currency and amount
    for payment in payments:
        payment_currency = payment.get('currency', 'USD')
        payment['formatted_amount'] = currency_service.format_amount(payment['amount'], payment_currency)
        payment['currency_symbol'] = currency_service.get_currency_symbol(payment_currency)
        payment['payment_method'] = payment.get('payment_method') or 'Credit Card'
        payment['description'] = f"{payment.get('plan_name', 'Subscription')} ({payment.get('billing_period', '').capitalize()})"
    return render_template('account/billing.html', payments=payments)

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
        
        emails = gmail_service.get_todays_emails()
        processed_emails = email_processor.process_emails(emails)
        
        # Track usage
        if user_model:
            user_model.increment_usage(user_id, 'email_fetch', len(emails))
        
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
        
        emails = gmail_service.get_todays_emails()
        processed_emails = email_processor.process_emails(emails)
        
        summary_result = ai_service.generate_daily_summary(processed_emails)
        
        # Track usage
        if user_model:
            user_model.increment_usage(user_id, 'ai_summary', len(emails))
        
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
@subscription_required('pro')  # Advanced AI analysis requires Pro subscription
def api_analyze_email():
    """API endpoint to analyze a single email with attachments"""
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
        
        data = request.get_json()
        email_id = data.get('email_id')
        analysis_type = data.get('type', 'summary')
        
        if not email_id:
            return jsonify({'error': 'Email ID is required'}), 400
        
        # Get the full email with attachments
        service = gmail_service._get_service()
        email_data = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        parsed_email = gmail_service._parse_email(email_data)
        if not parsed_email:
            return jsonify({'error': 'Email not found'}), 404
        
        # Process email with attachments if available
        if email_processor and document_processor and gmail_service:
            processed_email = email_processor.process_email_with_attachments(parsed_email)
        else:
            processed_email = email_processor._process_single_email(parsed_email)
        
        # Prepare content for AI analysis
        email_content = processed_email.get('body', '')
        subject = processed_email.get('subject', '')
        sender = processed_email.get('sender', '')
        
        # Include attachment analysis if available
        attachment_analysis = processed_email.get('attachment_analysis', '')
        if attachment_analysis:
            email_content += f"\n\nAttachment Analysis:\n{attachment_analysis}"
        
        # Generate analysis based on type
        try:
            print(f"🔍 Starting AI analysis for type: {analysis_type}")
            print(f"🔍 Email content length: {len(email_content)}")
            print(f"🔍 Subject: {subject}")
            print(f"🔍 Sender: {sender}")
            
            if analysis_type == 'summary':
                analysis_result = ai_service.generate_email_summary(email_content, subject, sender)
            elif analysis_type == 'action_items':
                analysis_result = ai_service.extract_action_items(email_content, subject, sender)
            elif analysis_type == 'recommendations':
                analysis_result = ai_service.generate_response_recommendations(email_content, subject, sender)
            else:
                analysis_result = ai_service.generate_email_summary(email_content, subject, sender)
            
            print(f"🔍 AI analysis result: {analysis_result}")
            
        except Exception as ai_error:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ AI analysis failed: {ai_error}")
            print(f"❌ AI error traceback: {error_details}")
            return jsonify({'error': f'AI analysis failed: {str(ai_error)}'}), 500
        
        # Track usage
        if user_model:
            user_model.increment_usage(user_id, 'email_analysis', 1)
        
        if analysis_result and analysis_result.get('success'):
            return jsonify({
                'success': True,
                'content': analysis_result['content'],
                'model_used': analysis_result.get('model_used', 'unknown'),
                'type': analysis_type
            })
        else:
            error_msg = analysis_result.get('error', 'Unknown AI analysis error') if analysis_result else 'AI analysis returned no result'
            print(f"❌ AI analysis failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Exception in analyze-email: {str(e)}")
        print(f"❌ Full traceback: {error_details}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

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
        
        # Track usage
        if user_model:
            user_model.increment_usage(user_id, 'comprehensive_analysis', len(important_emails))
        
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

# Legal pages
@app.route('/terms')
def terms():
    """Terms of Service"""
    return render_template('legal/terms.html')

@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html')

@app.route('/test-session')
def test_session():
    """Test session persistence"""
    if 'test_key' not in session:
        session['test_key'] = 'Session is working!'
        msg = 'Session variable set. Reload to check persistence.'
    else:
        msg = f"Session variable value: {session['test_key']}"
    return f'<h2>{msg}</h2>'

@app.route('/features')
def features():
    """Features page showing all app features organized by plan"""
    return render_template('features.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port) 