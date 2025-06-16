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
        # Don't automatically load credentials to prevent caching issues
        # Credentials will be loaded explicitly when needed
        print("✅ Gmail service initialized (no auto-load)")
    
    def _get_redirect_uri(self):
        """Get the OAuth redirect URI based on environment"""
        # Check if we're in production (Cloud Run or Digital Ocean)
        if (os.environ.get('K_SERVICE') or 
            os.environ.get('CLOUD_RUN_SERVICE') or 
            os.environ.get('DIGITALOCEAN_APP_PLATFORM') or
            os.environ.get('APP_PLATFORM') or
            os.environ.get('PORT') == '8080'):  # Digital Ocean uses port 8080
            
            # Production environment - use the actual domain
            # Try to get domain from environment or use the Digital Ocean app URL
            domain = os.environ.get('DOMAIN') or os.environ.get('APP_URL')
            
            # If no domain set, try to construct from Digital Ocean app name
            if not domain:
                app_name = os.environ.get('APP_NAME', 'ai-email-assistant')
                domain = f"{app_name}-dszjy.ondigitalocean.app"
            
            redirect_uri = f'https://{domain}/oauth2callback'
            print(f"🔗 Production OAuth redirect URI: {redirect_uri}")
            return redirect_uri
        
        # Local development
        # Try to get port from multiple sources
        port = None
        
        # Check environment variables
        port = os.environ.get('FLASK_RUN_PORT') or os.environ.get('PORT')
        
        # If not found, try to detect from running Flask app
        if not port:
            try:
                import requests
                # Try common ports
                for test_port in ['5004', '5003', '5002', '5001', '5000']:
                    try:
                        response = requests.get(f'http://localhost:{test_port}/', timeout=1)
                        if response.status_code == 200:
                            port = test_port
                            break
                    except:
                        continue
            except:
                pass
        
        # Default to 5004 if no port detected
        if not port:
            port = '5004'
        
        redirect_uri = f'http://localhost:{port}/oauth2callback'
        print(f"🔗 Local OAuth redirect URI: {redirect_uri}")
        return redirect_uri
    
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
    
    def _get_credentials_data(self):
        """Get credentials data from environment variable or file"""
        # First try to get from environment variable (for Cloud Run)
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if credentials_json:
            try:
                return json.loads(credentials_json)
            except json.JSONDecodeError as e:
                print(f"Error parsing GOOGLE_CREDENTIALS_JSON: {e}")
        
        # Fallback to file (for local development)
        creds_path = 'credentials.json'
        if os.path.exists(creds_path):
            try:
                with open(creds_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading credentials file: {e}")
        
        raise FileNotFoundError(
            "Google credentials not found. Please set GOOGLE_CREDENTIALS_JSON environment variable "
            "or place credentials.json in the project root directory."
        )
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
        try:
            credentials_data = self._get_credentials_data()
            
            # Create a temporary file for the credentials
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(credentials_data, temp_file)
                temp_file_path = temp_file.name
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(temp_file_path, self.SCOPES)
                self.credentials = flow.run_local_server(port=0)
                
                # Save credentials for future use
                with open('token.json', 'w') as token:
                    token.write(self.credentials.to_json())
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            raise FileNotFoundError(
                f"Failed to authenticate with Gmail API: {e}. Please ensure credentials are properly configured."
            )
    
    def get_authorization_url(self):
        """Get authorization URL for OAuth flow"""
        try:
            print("🔍 Getting authorization URL...")
            credentials_data = self._get_credentials_data()
            print(f"✅ Credentials data loaded: {len(str(credentials_data))} characters")
            
            # Create a temporary file for the credentials
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(credentials_data, temp_file)
                temp_file_path = temp_file.name
            
            try:
                # Check if it's a web application
                if 'web' in credentials_data:
                    print("🔍 Using web application flow")
                    # Use web application flow with dynamic redirect URI
                    redirect_uri = self._get_redirect_uri()
                    print(f"🔗 Using OAuth redirect URI: {redirect_uri}")
                    
                    flow = Flow.from_client_secrets_file(
                        temp_file_path,
                        scopes=self.SCOPES,
                        redirect_uri=redirect_uri
                    )
                    
                    # Generate authorization URL
                    auth_url, _ = flow.authorization_url(
                        access_type='offline',
                        include_granted_scopes='true',
                        prompt='consent'  # Force consent to get refresh token
                    )
                    
                    print(f"✅ Authorization URL generated successfully")
                    return auth_url
                else:
                    print("🔍 Using desktop application flow")
                    # Use desktop application flow
                    flow = InstalledAppFlow.from_client_secrets_file(temp_file_path, self.SCOPES)
                    auth_url, _ = flow.authorization_url()
                    print(f"✅ Authorization URL generated successfully")
                    return auth_url
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            print(f"❌ Error in get_authorization_url: {str(e)}")
            print(f"❌ Exception type: {type(e).__name__}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            raise FileNotFoundError(f"Failed to get authorization URL: {e}")
    
    def exchange_code_for_tokens(self, code):
        """Exchange authorization code for tokens"""
        try:
            credentials_data = self._get_credentials_data()
            
            # Create a temporary file for the credentials
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(credentials_data, temp_file)
                temp_file_path = temp_file.name
            
            try:
                # Check if it's a web application
                if 'web' in credentials_data:
                    # Use web application flow with dynamic redirect URI
                    redirect_uri = self._get_redirect_uri()
                    print(f"🔄 Exchanging code using redirect URI: {redirect_uri}")
                    
                    flow = Flow.from_client_secrets_file(
                        temp_file_path,
                        scopes=self.SCOPES,
                        redirect_uri=redirect_uri
                    )
                    
                    # Exchange code for tokens
                    flow.fetch_token(code=code)
                    self.credentials = flow.credentials
                else:
                    # Use desktop application flow
                    flow = InstalledAppFlow.from_client_secrets_file(temp_file_path, self.SCOPES)
                    flow.fetch_token(code=code)
                    self.credentials = flow.credentials
                
                # Save credentials
                with open('token.json', 'w') as token:
                    token.write(self.credentials.to_json())
                
                print("✅ OAuth tokens saved successfully")
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            raise FileNotFoundError(f"Failed to exchange code for tokens: {e}")
    
    def get_token_data(self):
        """Get the current token data as a dictionary"""
        if not self.credentials:
            return None
        
        return {
            'token': self.credentials.token,
            'refresh_token': self.credentials.refresh_token,
            'token_uri': self.credentials.token_uri,
            'client_id': self.credentials.client_id,
            'client_secret': self.credentials.client_secret,
            'scopes': self.credentials.scopes
        }
    
    def set_credentials_from_token(self, token_data):
        """Set credentials from token data dictionary or JSON string"""
        if not token_data:
            self.credentials = None
            return

        # If token_data is a string, parse it as JSON
        if isinstance(token_data, str):
            try:
                import json
                token_data = json.loads(token_data)
            except Exception as e:
                print(f"Error parsing token JSON: {e}")
                self.credentials = None
                return

        try:
            self.credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
        except Exception as e:
            print(f"Error setting credentials from token: {e}")
            self.credentials = None
    
    def _get_service(self):
        """Get Gmail API service instance"""
        if not self.credentials:
            raise Exception("Gmail not authenticated. Please connect your Gmail account first.")
        
        if not self.service:
            self.service = build('gmail', 'v1', credentials=self.credentials)
        
        return self.service
    
    def get_todays_emails(self, max_results=50, user_plan='free'):
        """Get emails from today with subscription-aware limits"""
        try:
            service = self._get_service()
            
            # Apply subscription-based limits
            if user_plan == 'free':
                # Free users: max 10 emails per load
                effective_max_results = min(max_results, 10)
                print(f"🔍 Free user limit applied: {effective_max_results} emails max")
            else:
                # Pro/Enterprise users: use requested limit
                effective_max_results = max_results
                print(f"🔍 {user_plan.capitalize()} user: {effective_max_results} emails max")
            
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
                maxResults=effective_max_results
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
            
            # Extract attachments
            attachments = self._extract_attachments(email_data['payload'])
            
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
                'labels': email_data.get('labelIds', []),
                'attachments': attachments,
                'has_attachments': len(attachments) > 0
            }
        
        except Exception as e:
            print(f'Error parsing email: {e}')
            return None
    
    def _extract_email_body(self, payload):
        """Extract email body from payload with robust MIME handling"""
        try:
            # First, try direct body access
            if 'body' in payload and payload['body'].get('data'):
                decoded = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
                if decoded.strip():
                    return decoded
            
            # If no direct body, recursively search parts
            if 'parts' in payload:
                text_content = self._extract_from_parts(payload['parts'])
                if text_content.strip():
                    return text_content
            
            # Fallback: use snippet if available
            return ''
            
        except Exception as e:
            print(f"Error extracting email body: {e}")
            return ''
    
    def _extract_from_parts(self, parts):
        """Recursively extract text from email parts"""
        text_content = ''
        html_content = ''
        
        for part in parts:
            try:
                mime_type = part.get('mimeType', '')
                
                # Handle nested parts recursively
                if 'parts' in part:
                    nested_content = self._extract_from_parts(part['parts'])
                    if nested_content.strip():
                        text_content += nested_content + '\n'
                
                # Extract text from current part
                elif 'body' in part and part['body'].get('data'):
                    try:
                        decoded = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        
                        if mime_type == 'text/plain' and decoded.strip():
                            text_content += decoded + '\n'
                        elif mime_type == 'text/html' and decoded.strip():
                            html_content += decoded + '\n'
                        elif 'text/' in mime_type and decoded.strip():
                            # Handle other text types
                            text_content += decoded + '\n'
                            
                    except Exception as decode_error:
                        print(f"Error decoding part with MIME type {mime_type}: {decode_error}")
                        continue
                        
            except Exception as part_error:
                print(f"Error processing email part: {part_error}")
                continue
        
        # Prefer plain text, fall back to HTML
        if text_content.strip():
            return text_content.strip()
        elif html_content.strip():
            return html_content.strip()
        else:
            return ''
    
    def _extract_attachments(self, payload):
        """Extract attachment information from email payload"""
        attachments = []
        
        def process_parts(parts):
            for part in parts:
                if part.get('filename') and part.get('body', {}).get('attachmentId'):
                    attachment_info = {
                        'id': part['body']['attachmentId'],
                        'filename': part['filename'],
                        'mime_type': part.get('mimeType', 'application/octet-stream'),
                        'size': part.get('body', {}).get('size', 0)
                    }
                    attachments.append(attachment_info)
                elif 'parts' in part:
                    process_parts(part['parts'])
        
        if 'parts' in payload:
            process_parts(payload['parts'])
        
        return attachments
    
    def get_attachment_content(self, message_id, attachment_id):
        """Get attachment content by message ID and attachment ID"""
        try:
            service = self._get_service()
            
            attachment = service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            if 'data' in attachment:
                return base64.urlsafe_b64decode(attachment['data'])
            else:
                return None
                
        except HttpError as error:
            print(f'Error getting attachment {attachment_id}: {error}')
            return None
    
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
    
    def get_user_profile(self):
        """Get Gmail user's profile information including email address"""
        try:
            service = self._get_service()
            
            # Get user profile
            profile = service.users().getProfile(userId='me').execute()
            
            return {
                'email': profile.get('emailAddress'),
                'messages_total': profile.get('messagesTotal'),
                'threads_total': profile.get('threadsTotal'),
                'history_id': profile.get('historyId')
            }
        except HttpError as error:
            print(f'Error getting Gmail profile: {error}')
            return None
        except Exception as e:
            print(f'Error getting Gmail profile: {e}')
            return None
    
    def logout(self):
        """Clear Gmail credentials and service state"""
        try:
            # Clear credentials
            self.credentials = None
            self.service = None
            
            # Remove token file if it exists
            token_path = 'token.json'
            if os.path.exists(token_path):
                os.remove(token_path)
                print(f"✅ Gmail token file removed: {token_path}")
            
            print("✅ Gmail service logged out successfully")
        except Exception as e:
            print(f"⚠️ Error during Gmail logout: {e}")
    
    def clear_credentials(self):
        """Clear credentials without removing token file (for temporary disconnection)"""
        self.credentials = None
        self.service = None
        print("✅ Gmail credentials cleared") 