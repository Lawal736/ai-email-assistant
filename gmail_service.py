import os
import base64
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class GmailService:
    """Service class for Gmail API operations"""
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self):
        self.credentials = None
        self.service = None
        # Don't authenticate immediately - wait for user to connect
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from token.json if available"""
        token_path = 'token.json'
        if os.path.exists(token_path):
            try:
                self.credentials = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                
                # If credentials are invalid or expired, refresh them
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    try:
                        self.credentials.refresh(Request())
                        # Save refreshed credentials
                        with open(token_path, 'w') as token:
                            token.write(self.credentials.to_json())
                    except Exception as e:
                        print(f"Failed to refresh credentials: {e}")
                        # Remove invalid token file
                        if os.path.exists(token_path):
                            os.remove(token_path)
                        self.credentials = None
            except Exception as e:
                print(f"Error loading credentials: {e}")
                # Remove invalid token file
                if os.path.exists(token_path):
                    os.remove(token_path)
                self.credentials = None
    
    def is_authenticated(self):
        """Check if Gmail is authenticated"""
        return self.credentials is not None and self.credentials.valid
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
        creds_path = 'credentials.json'
        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                "credentials.json not found. Please download it from Google Cloud Console "
                "and place it in the project root directory."
            )
        
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, self.SCOPES)
        self.credentials = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open('token.json', 'w') as token:
            token.write(self.credentials.to_json())
    
    def get_authorization_url(self):
        """Get authorization URL for OAuth flow"""
        creds_path = 'credentials.json'
        if not os.path.exists(creds_path):
            raise FileNotFoundError("credentials.json not found")
        
        # Load credentials to determine type
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        
        # Check if it's a web application
        if 'web' in creds_data:
            # Use web application flow with redirect URI
            flow = Flow.from_client_secrets_file(
                creds_path,
                scopes=self.SCOPES,
                redirect_uri='http://localhost:5001/oauth2callback'
            )
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            return auth_url
        else:
            # Use desktop application flow
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, self.SCOPES)
            auth_url, _ = flow.authorization_url()
            return auth_url
    
    def exchange_code_for_tokens(self, code):
        """Exchange authorization code for tokens"""
        creds_path = 'credentials.json'
        
        # Load credentials to determine type
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        
        # Check if it's a web application
        if 'web' in creds_data:
            # Use web application flow with redirect URI
            flow = Flow.from_client_secrets_file(
                creds_path,
                scopes=self.SCOPES,
                redirect_uri='http://localhost:5001/oauth2callback'
            )
            
            # Exchange code for tokens
            flow.fetch_token(code=code)
            self.credentials = flow.credentials
        else:
            # Use desktop application flow
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, self.SCOPES)
            flow.fetch_token(code=code)
            self.credentials = flow.credentials
        
        # Save credentials
        with open('token.json', 'w') as token:
            token.write(self.credentials.to_json())
    
    def _get_service(self):
        """Get Gmail API service instance"""
        if not self.credentials:
            raise Exception("Gmail not authenticated. Please connect your Gmail account first.")
        
        if not self.service:
            self.service = build('gmail', 'v1', credentials=self.credentials)
        
        return self.service
    
    def get_todays_emails(self, max_results=50):
        """Get emails from today"""
        try:
            service = self._get_service()
            
            # Calculate date range for today
            today = datetime.now().date()
            start_date = today.strftime('%Y/%m/%d')
            end_date = (today + timedelta(days=1)).strftime('%Y/%m/%d')
            
            # Build query for today's emails
            query = f'after:{start_date} before:{end_date}'
            
            # Get email IDs
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            # Get full email details
            emails = []
            for message in messages:
                try:
                    email_data = service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    parsed_email = self._parse_email(email_data)
                    if parsed_email:
                        emails.append(parsed_email)
                
                except HttpError as error:
                    print(f'Error getting email {message["id"]}: {error}')
                    continue
            
            return emails
        
        except HttpError as error:
            print(f'Gmail API error: {error}')
            raise
    
    def _parse_email(self, email_data):
        """Parse email data into a structured format"""
        try:
            headers = email_data['payload']['headers']
            
            # Extract basic information
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Parse date
            try:
                date_obj = email.utils.parsedate_to_datetime(date_str)
            except:
                date_obj = datetime.now()
            
            # Extract email body
            body = self._extract_email_body(email_data['payload'])
            
            # Determine email type (work, personal, etc.)
            email_type = self._classify_email_type(sender, subject, body)
            
            # Determine priority
            priority = self._determine_priority(subject, body)
            
            return {
                'id': email_data['id'],
                'thread_id': email_data.get('threadId', ''),
                'subject': subject,
                'sender': sender,
                'date': date_obj.isoformat(),
                'body': body,
                'type': email_type,
                'priority': priority,
                'snippet': email_data.get('snippet', ''),
                'labels': email_data.get('labelIds', [])
            }
        
        except Exception as e:
            print(f'Error parsing email: {e}')
            return None
    
    def _extract_email_body(self, payload):
        """Extract email body from payload"""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        
        return ''
    
    def _classify_email_type(self, sender, subject, body):
        """Classify email type based on sender and content"""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        # Work-related keywords
        work_keywords = ['work', 'project', 'meeting', 'deadline', 'report', 'client', 'team']
        # Personal keywords
        personal_keywords = ['family', 'friend', 'personal', 'social', 'invitation']
        # Newsletter keywords
        newsletter_keywords = ['newsletter', 'subscribe', 'unsubscribe', 'marketing']
        
        # Check for work-related content
        if any(keyword in subject_lower or keyword in body_lower for keyword in work_keywords):
            return 'work'
        elif any(keyword in subject_lower or keyword in body_lower for keyword in personal_keywords):
            return 'personal'
        elif any(keyword in subject_lower or keyword in body_lower for keyword in newsletter_keywords):
            return 'newsletter'
        else:
            return 'other'
    
    def _determine_priority(self, subject, body):
        """Determine email priority based on content"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        # High priority keywords
        high_priority = ['urgent', 'asap', 'emergency', 'critical', 'deadline']
        # Medium priority keywords
        medium_priority = ['meeting', 'call', 'discussion', 'review', 'update']
        
        if any(keyword in subject_lower or keyword in body_lower for keyword in high_priority):
            return 'high'
        elif any(keyword in subject_lower or keyword in body_lower for keyword in medium_priority):
            return 'medium'
        else:
            return 'low'
    
    def send_email(self, to, subject, body, reply_to_message_id=None):
        """Send an email"""
        try:
            service = self._get_service()
            
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            msg = MIMEText(body)
            message.attach(msg)
            
            # If replying to a message, add references
            if reply_to_message_id:
                message['In-Reply-To'] = reply_to_message_id
                message['References'] = reply_to_message_id
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return True
        
        except HttpError as error:
            print(f'Error sending email: {error}')
            return False 