import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_cors import CORS
from dotenv import load_dotenv
from gmail_service import GmailService
from ai_service import HybridAIService
from email_processor import EmailProcessor

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key
CORS(app)

# Initialize services
gmail_service = GmailService()
ai_service = HybridAIService()
email_processor = EmailProcessor()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/connect-gmail')
def connect_gmail():
    """Gmail connection page"""
    return render_template('gmail_connect.html')

@app.route('/start-gmail-auth')
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
        # Get authorization code from query parameters
        code = request.args.get('code')
        if not code:
            flash('Authorization code not received', 'error')
            return redirect(url_for('connect_gmail'))
        
        # Exchange code for tokens
        gmail_service.exchange_code_for_tokens(code)
        
        # Set session variable to indicate Gmail is authenticated
        session['gmail_authenticated'] = True
        
        flash('Gmail connected successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        flash(f'Error during authentication: {str(e)}', 'error')
        return redirect(url_for('connect_gmail'))

@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    # Check if Gmail is authenticated
    if not gmail_service.is_authenticated():
        flash('Please connect your Gmail account first', 'warning')
        return redirect(url_for('connect_gmail'))
    
    # Ensure session variable is set if Gmail is authenticated
    if gmail_service.is_authenticated() and not session.get('gmail_authenticated'):
        session['gmail_authenticated'] = True
    
    try:
        # Get today's emails
        emails = gmail_service.get_todays_emails(max_results=20)
        
        # Process emails with AI
        processed_emails = email_processor.process_emails(emails)
        
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
        
        for email in processed_emails:
            try:
                # Extract action items for each email
                action_result = ai_service.analyze_email(email.get('content', ''), 'action_items')
                if action_result['success']:
                    action_items.append({
                        'email_id': email.get('id'),
                        'subject': email.get('subject'),
                        'action_items': action_result['content'],
                        'model_used': action_result['model_used']
                    })
                    print(f"✅ Action items extracted using {action_result['model_used']}")
                else:
                    print(f"❌ Action items failed: {action_result['error']}")
                
                # Generate recommendations for each email
                rec_result = ai_service.analyze_email(email.get('content', ''), 'recommendations')
                if rec_result['success']:
                    recommendations.append({
                        'email_id': email.get('id'),
                        'subject': email.get('subject'),
                        'recommendations': rec_result['content'],
                        'model_used': rec_result['model_used']
                    })
                    print(f"✅ Recommendations generated using {rec_result['model_used']}")
                else:
                    print(f"❌ Recommendations failed: {rec_result['error']}")
                    
            except Exception as e:
                print(f"Error processing email {email.get('id')}: {e}")
        
        # Get current date
        current_date = datetime.now().strftime('%B %d, %Y')
        
        return render_template('dashboard.html', 
                             emails=processed_emails, 
                             summary=daily_summary,
                             action_items=action_items,
                             recommendations=recommendations,
                             date=current_date)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        # Provide default values for template
        return render_template('dashboard.html', 
                             emails=[], 
                             summary="Unable to load emails at this time.",
                             action_items=[],
                             recommendations=[],
                             date=datetime.now().strftime('%B %d, %Y'))

@app.route('/email/<email_id>')
def view_email(email_id):
    """View individual email"""
    if not gmail_service.is_authenticated():
        flash('Please connect your Gmail account first', 'warning')
        return redirect(url_for('connect_gmail'))
    
    try:
        # Get email details
        service = gmail_service._get_service()
        email_data = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        parsed_email = gmail_service._parse_email(email_data)
        if parsed_email:
            processed_email = email_processor._process_single_email(parsed_email)
            return render_template('email_detail.html', email=processed_email)
        else:
            flash('Email not found', 'error')
            return redirect(url_for('dashboard'))
    
    except Exception as e:
        flash(f'Error loading email: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/send-email', methods=['POST'])
def send_email():
    """Send email"""
    if not gmail_service.is_authenticated():
        flash('Please connect your Gmail account first', 'warning')
        return redirect(url_for('connect_gmail'))
    
    try:
        to = request.form.get('to')
        subject = request.form.get('subject')
        body = request.form.get('body')
        reply_to = request.form.get('reply_to')
        
        if not all([to, subject, body]):
            flash('Please fill in all required fields', 'error')
            return redirect(request.referrer)
        
        success = gmail_service.send_email(to, subject, body, reply_to)
        
        if success:
            flash('Email sent successfully!', 'success')
        else:
            flash('Failed to send email', 'error')
        
        return redirect(request.referrer)
    
    except Exception as e:
        flash(f'Error sending email: {str(e)}', 'error')
        return redirect(request.referrer)

@app.route('/api/emails')
def api_emails():
    """API endpoint to get emails"""
    if not session.get('gmail_authenticated'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        emails = gmail_service.get_todays_emails()
        processed_emails = email_processor.process_emails(emails)
        return jsonify(processed_emails)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary')
def api_summary():
    """API endpoint to get AI summary"""
    if not session.get('gmail_authenticated'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        emails = gmail_service.get_todays_emails()
        processed_emails = email_processor.process_emails(emails)
        
        summary_result = ai_service.generate_daily_summary(processed_emails)
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
def api_analyze_email():
    """API endpoint to analyze a single email"""
    if not session.get('gmail_authenticated'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        email_content = data.get('content', '')
        analysis_type = data.get('type', 'summary')
        
        result = ai_service.analyze_email(email_content, analysis_type)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    """Logout and clear session"""
    # Clear Gmail credentials
    try:
        gmail_service.logout()
    except:
        pass
    
    # Clear session
    session.clear()
    
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 