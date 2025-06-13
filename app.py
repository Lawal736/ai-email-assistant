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

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-this-in-production')
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
            
            # Check if user has required subscription
            if user['subscription_plan'] == 'free' and plan_name != 'free':
                flash(f'This feature requires a {plan_name} subscription', 'warning')
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
    except:
        pass
    
    # Clear session
    session.clear()
    
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

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
    if plan_model:
        plans = plan_model.get_all_plans()
    else:
        plans = []
    return render_template('pricing.html', plans=plans)

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    # Check if Gmail service is available
    if not gmail_service:
        flash('Gmail service is not available. Please check your configuration.', 'error')
        return redirect(url_for('index'))
    
    # Check if Gmail is authenticated for this user
    user_id = session.get('user_id')
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
@login_required
def oauth2callback():
    """Handle OAuth callback"""
    try:
        print("🔍 OAuth callback received")
        
        # Get authorization code from query parameters
        code = request.args.get('code')
        if not code:
            print("❌ No authorization code received")
            flash('Authorization code not received', 'error')
            return redirect(url_for('connect_gmail'))
        
        print(f"✅ Authorization code received: {code[:20]}...")
        
        # Exchange code for tokens
        gmail_service.exchange_code_for_tokens(code)
        print("✅ Code exchanged for tokens")
        
        # Save Gmail token for user
        user_id = session.get('user_id')
        print(f"🔍 User ID from session: {user_id}")
        
        token_data = gmail_service.get_token_data()
        print(f"🔍 Token data received: {token_data is not None}")
        
        if user_model and token_data:
            user_model.update_gmail_token(user_id, json.dumps(token_data))
            print("✅ Gmail token saved to database")
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

# Payment routes
@app.route('/payment/checkout')
@login_required
def payment_checkout():
    """Payment checkout page"""
    plan_name = request.args.get('plan', 'pro')
    billing_period = request.args.get('billing', 'monthly')
    
    plan = plan_model.get_plan_by_name(plan_name) if plan_model else None
    if not plan:
        flash('Plan not found', 'error')
        return redirect(url_for('pricing'))
    
    stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY', '')
    
    return render_template('payment/checkout.html', 
                         plan=plan, 
                         billing_period=billing_period,
                         stripe_public_key=stripe_public_key)

@app.route('/payment/process', methods=['POST'])
@login_required
def payment_process():
    """Process payment"""
    try:
        data = request.get_json()
        payment_method_id = data.get('payment_method_id')
        plan_name = data.get('plan')
        billing_period = data.get('billing_period')
        
        user_id = session.get('user_id')
        
        # Create payment session
        result = payment_service.create_one_time_payment_session(
            user_id, plan_name, billing_period
        )
        
        if result['success']:
            # Confirm payment
            import stripe
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            payment_intent = stripe.PaymentIntent.confirm(
                result['payment_intent_id'],
                payment_method=payment_method_id
            )
            
            if payment_intent.status == 'succeeded':
                # Update user subscription
                user_model.update_subscription(user_id, plan_name)
                session['subscription_plan'] = plan_name
                
                return jsonify({
                    'success': True,
                    'session_id': result['payment_intent_id']
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Payment failed'
                })
        else:
            return jsonify(result)
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/payment/success')
@login_required
def payment_success():
    """Payment success page"""
    session_id = request.args.get('session_id')
    return render_template('payment/success.html', session_id=session_id)

@app.route('/payment/cancel')
@login_required
def payment_cancel():
    """Payment cancel page"""
    return render_template('payment/cancel.html')

@app.route('/payment/webhook', methods=['POST'])
def payment_webhook():
    """Stripe webhook handler"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    result = payment_service.handle_webhook(payload, sig_header)
    
    if result['success']:
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error', 'message': result['error']}), 400

@app.route('/payment/crypto/checkout', methods=['GET', 'POST'])
def crypto_checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        plan_name = request.form.get('plan')
        billing_period = request.form.get('billing_period', 'monthly')  # Default to monthly
        user_id = session['user_id']
        
        # Get plan details
        plan = payment_service.plan_model.get_plan_by_name(plan_name)
        if not plan:
            flash('Invalid plan selected', 'error')
            return redirect(url_for('pricing'))
        
        # Determine the correct price based on billing period
        if billing_period == 'yearly':
            amount_usd = plan['price_yearly']
        else:
            amount_usd = plan['price_monthly']
        
        # Create crypto payment session
        payment_session = payment_service.create_crypto_payment_session(
            amount_usd=amount_usd,
            user_id=user_id,
            plan_type=plan_name,
            billing_period=billing_period
        )
        
        if 'error' in payment_session:
            flash(f'Error creating payment session: {payment_session["error"]}', 'error')
            return redirect(url_for('pricing'))
        
        # Store payment session in session for verification
        session['crypto_payment_session'] = payment_session
        
        return render_template('payment/crypto_checkout.html', 
                             payment_session=payment_session,
                             plan=plan,
                             billing_period=billing_period)
    
    return redirect(url_for('pricing'))

@app.route('/payment/crypto/verify', methods=['POST'])
def verify_crypto_payment():
    if 'user_id' not in session or 'crypto_payment_session' not in session:
        return jsonify({'success': False, 'error': 'No active payment session'})
    
    user_wallet_address = request.form.get('wallet_address')
    if not user_wallet_address:
        return jsonify({'success': False, 'error': 'Wallet address required'})
    
    payment_session = session['crypto_payment_session']
    
    # Verify the payment
    verification_result = payment_service.verify_usdt_payment(
        payment_session, 
        user_wallet_address
    )
    
    if 'error' in verification_result:
        return jsonify({'success': False, 'error': verification_result['error']})
    
    if verification_result.get('verified'):
        # Process successful payment
        user_id = session['user_id']
        plan_name = payment_session['plan_type']
        
        # Update user subscription
        success = payment_service.activate_subscription(
            user_id, 
            plan_name, 
            payment_method='crypto',
            payment_id=payment_session['payment_id'],
            billing_period=payment_session.get('billing_period', 'monthly')
        )
        
        if success:
            # Clear payment session
            session.pop('crypto_payment_session', None)
            return jsonify({
                'success': True, 
                'message': 'Payment verified and subscription activated!',
                'redirect': url_for('dashboard')
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to activate subscription'})
    
    return jsonify({'success': False, 'error': 'Payment verification failed'})

@app.route('/payment/methods')
def get_payment_methods():
    """Get available payment methods"""
    methods = payment_service.get_payment_methods()
    return jsonify({'methods': methods})

# User account routes
@app.route('/account')
@login_required
def account():
    """User account page"""
    user_id = session.get('user_id')
    user = user_model.get_user_by_id(user_id) if user_model else None
    payments = payment_model.get_user_payments(user_id) if payment_model else []
    
    # Get Gmail profile information if Gmail is connected
    gmail_profile = None
    if user:
        gmail_token = user_model.get_gmail_token(user_id) if user_model else None
        if gmail_token:
            try:
                gmail_service.set_credentials_from_token(gmail_token)
                if gmail_service.is_authenticated():
                    gmail_profile = gmail_service.get_user_profile()
            except Exception as e:
                print(f"Error getting Gmail profile: {e}")
    
    return render_template('account.html', user=user, payments=payments, gmail_profile=gmail_profile)

@app.route('/account/subscription')
@login_required
def account_subscription():
    """Subscription management page"""
    user_id = session.get('user_id')
    user = user_model.get_user_by_id(user_id) if user_model else None
    plans = plan_model.get_all_plans() if plan_model else []
    
    return render_template('account/subscription.html', user=user, plans=plans)

@app.route('/account/billing')
@login_required
def account_billing():
    """Billing history page"""
    user_id = session.get('user_id')
    payments = payment_model.get_user_payments(user_id) if payment_model else []
    
    return render_template('account/billing.html', payments=payments)

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

# Legal pages
@app.route('/terms')
def terms():
    """Terms of Service"""
    return render_template('legal/terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy"""
    return render_template('legal/privacy.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5004) 