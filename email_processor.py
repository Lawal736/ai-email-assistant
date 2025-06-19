import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from email.utils import parsedate_to_datetime

class EmailProcessor:
    """Class for processing and organizing email data"""
    
    def __init__(self, ai_service=None, document_processor=None, gmail_service=None):
        self.ai_service = ai_service
        self.document_processor = document_processor
        self.gmail_service = gmail_service
        
        self.priority_keywords = {
            'high': ['urgent', 'asap', 'emergency', 'critical', 'deadline', 'important'],
            'medium': ['meeting', 'call', 'discussion', 'review', 'update', 'follow-up'],
            'low': ['newsletter', 'promotion', 'marketing', 'update', 'notification']
        }
    
    def process_emails(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and enhance email data with additional analysis"""
        processed_emails = []
        
        for email in emails:
            processed_email = self._process_single_email(email)
            if processed_email:
                processed_emails.append(processed_email)
        
        # Sort emails by priority and date
        processed_emails.sort(key=lambda x: (
            self._priority_to_number(x['priority']),
            x['date']
        ), reverse=True)
        
        return processed_emails
    
    def _process_single_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single email with additional metadata"""
        try:
            # Clean and enhance email data
            processed_email = email.copy()
            
            # Clean sender information
            processed_email['sender_clean'] = self._clean_sender(email['sender'])
            processed_email['sender_domain'] = self._extract_domain(email['sender'])
            
            # Clean and truncate body
            processed_email['body_clean'] = self._clean_email_body(email['body'])
            processed_email['body_preview'] = self._create_preview(email['body'], 200)
            
            # Add processing metadata
            processed_email['processed_at'] = datetime.now().isoformat()
            processed_email['word_count'] = len(email['body'].split())
            processed_email['has_attachments'] = self._check_attachments(email)
            
            # Enhanced classification
            processed_email['category'] = self._categorize_email(email)
            processed_email['urgency_score'] = self._calculate_urgency_score(email)
            
            # Extract key information
            processed_email['extracted_info'] = self._extract_key_info(email)
            
            return processed_email
        
        except Exception as e:
            print(f"Error processing email {email.get('id', 'unknown')}: {e}")
            return email
    
    def _clean_sender(self, sender: str) -> str:
        """Clean sender information"""
        # Remove email addresses and keep only names
        if '<' in sender and '>' in sender:
            name_part = sender.split('<')[0].strip()
            return name_part.strip('"\'')
        return sender
    
    def _extract_domain(self, sender: str) -> str:
        """Extract domain from sender email"""
        email_match = re.search(r'<(.+?)>', sender)
        if email_match:
            email_address = email_match.group(1)
            return email_address.split('@')[-1] if '@' in email_address else ''
        return ''
    
    def _clean_email_body(self, body: str) -> str:
        """Clean email body text - comprehensive HTML/CSS removal while preserving structure"""
        if not body:
            return ''
        
        # Step 1: Preserve important structural elements before cleaning
        # Preserve headers with markers
        body = re.sub(r'<(h[1-6])[^>]*>([^<]*)</h[1-6]>', r'\n\n**\1**\2**\1**\n\n', body, flags=re.IGNORECASE)
        
        # Preserve paragraph breaks
        body = re.sub(r'</p>', '\n\n', body, flags=re.IGNORECASE)
        body = re.sub(r'<p[^>]*>', '\n', body, flags=re.IGNORECASE)
        
        # Preserve line breaks and div structures
        body = re.sub(r'</div>', '\n', body, flags=re.IGNORECASE)
        body = re.sub(r'<div[^>]*>', '\n', body, flags=re.IGNORECASE)
        body = re.sub(r'<br\s*/?>', '\n', body, flags=re.IGNORECASE)
        
        # Preserve links in readable format
        body = re.sub(r'<a[^>]*href\s*=\s*["\']([^"\']*)["\'][^>]*>([^<]*)</a>', r'\2 [\1]', body, flags=re.IGNORECASE)
        
        # Step 2: Remove style blocks and scripts completely
        body = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', body, flags=re.IGNORECASE)
        body = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', body, flags=re.IGNORECASE)
        
        # Step 3: Remove inline CSS and attributes
        body = re.sub(r'style\s*=\s*["\'][^"\']*["\']', '', body, flags=re.IGNORECASE)
        body = re.sub(r'class\s*=\s*["\'][^"\']*["\']', '', body, flags=re.IGNORECASE)
        body = re.sub(r'id\s*=\s*["\'][^"\']*["\']', '', body, flags=re.IGNORECASE)
        body = re.sub(r'width\s*=\s*["\'][^"\']*["\']', '', body, flags=re.IGNORECASE)
        body = re.sub(r'height\s*=\s*["\'][^"\']*["\']', '', body, flags=re.IGNORECASE)
        
        # Step 4: Remove all remaining HTML tags
        body = re.sub(r'<[^>]+>', '', body)
        
        # Step 5: Decode HTML entities
        html_entities = {
            '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"',
            '&#39;': "'", '&hellip;': '...', '&mdash;': '—', '&ndash;': '–',
            '&rsquo;': "'", '&lsquo;': "'", '&rdquo;': '"', '&ldquo;': '"'
        }
        for entity, replacement in html_entities.items():
            body = body.replace(entity, replacement)
        
        # Step 6: Clean up CSS remnants and orphaned style properties
        body = re.sub(r'\b\w+\s*:\s*[^;]+;', '', body)  # Remove CSS properties
        body = re.sub(r'\{[^}]*\}', '', body)  # Remove CSS blocks
        
        # Step 7: Clean up whitespace but preserve paragraph structure
        body = re.sub(r'[ \t]+', ' ', body)  # Multiple spaces/tabs to single space
        body = re.sub(r'\n[ \t]+', '\n', body)  # Remove spaces/tabs at start of lines
        body = re.sub(r'[ \t]+\n', '\n', body)  # Remove spaces/tabs at end of lines
        body = re.sub(r'\n{4,}', '\n\n\n', body)  # Max triple line breaks
        
        # Step 8: Remove common email signatures and footers
        signature_patterns = [
            r'--\s*\n.*',
            r'Sent from my iPhone.*',
            r'Get Outlook for.*',
            r'This email was sent.*',
            r'Unsubscribe.*',
            r'If you no longer wish to receive.*',
            r'This message was sent to.*'
        ]
        
        for pattern in signature_patterns:
            body = re.sub(pattern, '', body, flags=re.IGNORECASE | re.DOTALL)
        
        # Step 9: Restore header formatting
        body = re.sub(r'\*\*(h[1-6])\*\*([^*]*)\*\*h[1-6]\*\*', r'\n\2\n', body, flags=re.IGNORECASE)
        
        # Step 10: Final cleanup
        return body.strip()
    
    def _create_preview(self, text: str, max_length: int) -> str:
        """Create a preview of text"""
        if not text:
            return ''
        
        cleaned_text = self._clean_email_body(text)
        if len(cleaned_text) <= max_length:
            return cleaned_text
        
        # Try to break at sentence boundary
        preview = cleaned_text[:max_length]
        last_period = preview.rfind('.')
        if last_period > max_length * 0.7:  # If period is in last 30% of preview
            preview = preview[:last_period + 1]
        
        return preview + '...'
    
    def _check_attachments(self, email: Dict[str, Any]) -> bool:
        """Check if email has attachments"""
        # This would need to be implemented based on Gmail API response structure
        # For now, we'll check for common attachment indicators in the body
        body_lower = email.get('body', '').lower()
        attachment_indicators = [
            'attachment', 'attached', 'enclosed', 'file', 'document',
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'
        ]
        
        return any(indicator in body_lower for indicator in attachment_indicators)
    
    def _categorize_email(self, email: Dict[str, Any]) -> str:
        """Categorize email based on content and sender"""
        subject_lower = email.get('subject', '').lower()
        body_lower = email.get('body', '').lower()
        sender_lower = email.get('sender', '').lower()
        
        # Work-related categories
        if any(keyword in subject_lower or keyword in body_lower 
               for keyword in ['meeting', 'project', 'deadline', 'report', 'client']):
            return 'work'
        
        # Personal categories
        if any(keyword in subject_lower or keyword in body_lower 
               for keyword in ['family', 'friend', 'personal', 'invitation']):
            return 'personal'
        
        # Newsletter categories
        if any(keyword in subject_lower or keyword in body_lower 
               for keyword in ['newsletter', 'subscribe', 'unsubscribe', 'marketing']):
            return 'newsletter'
        
        # Notification categories
        if any(keyword in subject_lower or keyword in body_lower 
               for keyword in ['notification', 'alert', 'update', 'reminder']):
            return 'notification'
        
        # Financial categories
        if any(keyword in subject_lower or keyword in body_lower 
               for keyword in ['invoice', 'payment', 'bill', 'receipt', 'bank']):
            return 'financial'
        
        return 'other'
    
    def _calculate_urgency_score(self, email: Dict[str, Any]) -> int:
        """Calculate urgency score (1-10) for email"""
        score = 1  # Base score
        
        # Priority boost
        priority_boost = {'high': 3, 'medium': 1, 'low': 0}
        score += priority_boost.get(email.get('priority', 'low'), 0)
        
        # Keyword boost
        subject_lower = email.get('subject', '').lower()
        body_lower = email.get('body', '').lower()
        
        urgent_keywords = ['urgent', 'asap', 'emergency', 'critical', 'deadline']
        for keyword in urgent_keywords:
            if keyword in subject_lower:
                score += 2
            if keyword in body_lower:
                score += 1
        
        # Sender importance (could be enhanced with contact list)
        sender_domain = self._extract_domain(email.get('sender', ''))
        important_domains = ['company.com', 'work.com', 'business.com']  # Example domains
        if sender_domain in important_domains:
            score += 1
        
        return min(score, 10)  # Cap at 10
    
    def _extract_key_info(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key information from email"""
        info = {
            'dates_mentioned': [],
            'times_mentioned': [],
            'people_mentioned': [],
            'urls': [],
            'phone_numbers': []
        }
        
        # Extract dates
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        info['dates_mentioned'] = re.findall(date_pattern, email.get('body', ''))
        
        # Extract times
        time_pattern = r'\b\d{1,2}:\d{2}\s*(?:AM|PM)?\b'
        info['times_mentioned'] = re.findall(time_pattern, email.get('body', ''))
        
        # Extract URLs
        url_pattern = r'https?://[^\s]+'
        info['urls'] = re.findall(url_pattern, email.get('body', ''))
        
        # Extract phone numbers
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        info['phone_numbers'] = re.findall(phone_pattern, email.get('body', ''))
        
        return info
    
    def _priority_to_number(self, priority: str) -> int:
        """Convert priority string to number for sorting"""
        priority_map = {'high': 3, 'medium': 2, 'low': 1}
        return priority_map.get(priority, 1)
    
    def group_emails_by_sender(self, emails: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group emails by sender"""
        grouped = {}
        for email in emails:
            sender = email.get('sender_clean', email.get('sender', 'Unknown'))
            if sender not in grouped:
                grouped[sender] = []
            grouped[sender].append(email)
        
        return grouped
    
    def group_emails_by_category(self, emails: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group emails by category"""
        grouped = {}
        for email in emails:
            category = email.get('category', 'other')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(email)
        
        return grouped
    
    def get_email_statistics(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about emails"""
        if not emails:
            return {}
        
        stats = {
            'total_emails': len(emails),
            'by_priority': {},
            'by_category': {},
            'by_sender_domain': {},
            'avg_urgency_score': 0,
            'emails_with_attachments': 0,
            'total_word_count': 0
        }
        
        urgency_scores = []
        
        for email in emails:
            # Priority stats
            priority = email.get('priority', 'low')
            stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
            
            # Category stats
            category = email.get('category', 'other')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # Domain stats
            domain = email.get('sender_domain', 'unknown')
            stats['by_sender_domain'][domain] = stats['by_sender_domain'].get(domain, 0) + 1
            
            # Other stats
            if email.get('has_attachments', False):
                stats['emails_with_attachments'] += 1
            
            stats['total_word_count'] += email.get('word_count', 0)
            urgency_scores.append(email.get('urgency_score', 1))
        
        # Calculate averages
        if urgency_scores:
            stats['avg_urgency_score'] = sum(urgency_scores) / len(urgency_scores)
        
        return stats
    
    def filter_emails(self, emails: List[Dict[str, Any]], user_filters: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Filter out newsletters, daily alerts, and other non-essential emails, plus user-defined filters"""
        filtered_emails = []
        filtered_count = 0
        user_filters = user_filters or []
        for email in emails:
            subject = email.get('subject', '').lower()
            sender = email.get('sender', '').lower()
            body = email.get('body', '').lower()
            # Built-in filters (legacy)
            if any(keyword in subject for keyword in [
                'newsletter', 'subscribe', 'unsubscribe', 'marketing', 'promotion',
                'special offer', 'limited time', 'discount', 'sale', 'deal'
            ]):
                print(f"🚫 Filtered out newsletter: {subject[:50]}...")
                filtered_count += 1
                continue
            if any(keyword in subject for keyword in [
                'daily digest', 'daily summary', 'daily report', 'daily update',
                'weekly digest', 'weekly summary', 'weekly report',
                'monthly digest', 'monthly summary', 'monthly report'
            ]):
                print(f"🚫 Filtered out digest: {subject[:50]}...")
                filtered_count += 1
                continue
            if any(domain in sender for domain in [
                'noreply@', 'no-reply@', 'donotreply@', 'do-not-reply@',
                'notifications@', 'alerts@', 'updates@', 'system@'
            ]):
                print(f"🚫 Filtered out automated: {sender}")
                filtered_count += 1
                continue
            if any(keyword in sender for keyword in [
                'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com', 'youtube.com',
                'tiktok.com', 'snapchat.com', 'pinterest.com'
            ]):
                print(f"🚫 Filtered out social media: {sender}")
                filtered_count += 1
                continue
            if any(keyword in subject for keyword in [
                'order confirmation', 'shipping confirmation', 'delivery update',
                'tracking', 'receipt', 'invoice', 'payment confirmation'
            ]):
                print(f"🚫 Filtered out shopping: {subject[:50]}...")
                filtered_count += 1
                continue
            # User-defined filters
            filtered = False
            for f in user_filters:
                ftype = f.get('filter_type')
                pattern = f.get('pattern', '').lower()
                if not ftype or not pattern:
                    continue
                if ftype == 'sender' and pattern in sender:
                    print(f"🚫 User filter (sender): {sender} matches {pattern}")
                    filtered = True
                    break
                if ftype == 'subject' and pattern in subject:
                    print(f"🚫 User filter (subject): {subject} matches {pattern}")
                    filtered = True
                    break
                if ftype == 'keyword' and pattern in body:
                    print(f"🚫 User filter (keyword): {pattern} in body")
                    filtered = True
                    break
                if ftype == 'regex':
                    try:
                        if re.search(pattern, subject) or re.search(pattern, sender) or re.search(pattern, body):
                            print(f"🚫 User filter (regex): {pattern} matched email")
                            filtered = True
                            break
                    except Exception as e:
                        print(f"[Filter Error] Invalid regex: {pattern} - {e}")
                        continue
            if filtered:
                filtered_count += 1
                continue
            # Keep the email
            filtered_emails.append(email)
        print(f"📊 Email filtering: {len(emails)} total, {filtered_count} filtered, {len(filtered_emails)} kept")
        return filtered_emails
    
    def process_emails_basic(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process emails with basic information only (no AI analysis)"""
        processed_emails = []
        
        for email in emails:
            processed_email = self._process_single_email_basic(email)
            if processed_email:
                processed_emails.append(processed_email)
        
        # Sort emails by date (most recent first)
        processed_emails.sort(key=lambda x: x['date'], reverse=True)
        
        return processed_emails
    
    def _process_single_email_basic(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single email with basic metadata only"""
        try:
            # Clean and enhance email data
            processed_email = email.copy()
            
            # Clean sender information
            processed_email['sender_clean'] = self._clean_sender(email['sender'])
            processed_email['sender_domain'] = self._extract_domain(email['sender'])
            
            # Clean and truncate body
            processed_email['body_clean'] = self._clean_email_body(email['body'])
            processed_email['body_preview'] = self._create_preview(email['body'], 200)
            
            # Add basic metadata
            processed_email['processed_at'] = datetime.now().isoformat()
            processed_email['word_count'] = len(email['body'].split())
            processed_email['has_attachments'] = self._check_attachments(email)
            
            # Basic classification
            processed_email['category'] = self._categorize_email(email)
            processed_email['urgency_score'] = self._calculate_urgency_score(email)
            
            return processed_email
        
        except Exception as e:
            print(f"Error processing email {email.get('id', 'unknown')}: {e}")
            return email
    
    def group_emails_by_thread(self, emails: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group emails by sender and subject to identify email threads"""
        threads = {}
        
        for email in emails:
            sender = email.get('sender_clean', email.get('sender', 'Unknown'))
            subject = email.get('subject', 'No Subject')
            
            # Create a thread key based on sender and normalized subject
            thread_key = self._create_thread_key(sender, subject)
            
            if thread_key not in threads:
                threads[thread_key] = {
                    'sender': sender,
                    'subject': subject,
                    'emails': [],
                    'thread_count': 0,
                    'latest_date': email.get('date', ''),
                    'priority': email.get('priority', 'low')
                }
            
            threads[thread_key]['emails'].append(email)
            threads[thread_key]['thread_count'] += 1
            
            # Update latest date
            if email.get('date', '') > threads[thread_key]['latest_date']:
                threads[thread_key]['latest_date'] = email.get('date', '')
            
            # Update priority if this email has higher priority
            if self._priority_to_number(email.get('priority', 'low')) > self._priority_to_number(threads[thread_key]['priority']):
                threads[thread_key]['priority'] = email.get('priority', 'low')
        
        # Sort threads by priority and latest date
        sorted_threads = dict(sorted(
            threads.items(),
            key=lambda x: (
                self._priority_to_number(x[1]['priority']),
                x[1]['latest_date']
            ),
            reverse=True
        ))
        
        return sorted_threads
    
    def _create_thread_key(self, sender: str, subject: str) -> str:
        """Create a thread key based on sender and normalized subject"""
        # Normalize subject by removing common prefixes
        normalized_subject = subject.lower()
        
        # Remove common reply prefixes
        reply_prefixes = ['re:', 're :', 'fwd:', 'fwd :', 'fw:', 'fw :']
        for prefix in reply_prefixes:
            if normalized_subject.startswith(prefix):
                normalized_subject = normalized_subject[len(prefix):].strip()
        
        # Remove common email prefixes
        email_prefixes = ['[', '(', '{']
        for prefix in email_prefixes:
            if normalized_subject.startswith(prefix):
                # Find the closing bracket
                close_char = {'[': ']', '(': ')', '{': '}'}[prefix]
                end_pos = normalized_subject.find(close_char)
                if end_pos != -1:
                    normalized_subject = normalized_subject[end_pos + 1:].strip()
        
        # Clean sender and subject for safe key generation
        safe_sender = re.sub(r'[^a-zA-Z0-9]', '_', sender.lower())
        safe_subject = re.sub(r'[^a-zA-Z0-9\s]', '_', normalized_subject)
        
        # Create a hash-based thread key to avoid special character issues
        key_string = f"{safe_sender}_{safe_subject}"
        thread_key = hashlib.md5(key_string.encode()).hexdigest()[:16]
        
        return thread_key
    
    def analyze_email_thread(self, thread_emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze an email thread to understand the conversation flow"""
        if not thread_emails:
            return {}
        
        # Sort emails by date
        sorted_emails = sorted(thread_emails, key=lambda x: x.get('date', ''))
        
        analysis = {
            'thread_length': len(sorted_emails),
            'participants': set(),
            'timeline': [],
            'conversation_summary': '',
            'suggested_response': ''
        }
        
        # Extract participants
        for email in sorted_emails:
            sender = email.get('sender_clean', email.get('sender', 'Unknown'))
            analysis['participants'].add(sender)
        
        analysis['participants'] = list(analysis['participants'])
        
        # Create timeline
        for i, email in enumerate(sorted_emails):
            analysis['timeline'].append({
                'index': i + 1,
                'sender': email.get('sender_clean', email.get('sender', 'Unknown')),
                'date': email.get('date', ''),
                'preview': email.get('body_preview', '')[:100] + '...',
                'priority': email.get('priority', 'low')
            })
        
        # Create conversation summary
        if len(sorted_emails) > 1:
            latest_email = sorted_emails[-1]
            analysis['conversation_summary'] = f"Thread with {len(analysis['participants'])} participants, {len(sorted_emails)} messages. Latest from {latest_email.get('sender_clean', 'Unknown')}"
        else:
            analysis['conversation_summary'] = f"Single email from {sorted_emails[0].get('sender_clean', 'Unknown')}"
        
        return analysis
    
    def process_email_with_attachments(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Process email and analyze any attachments"""
        processed_email = self._process_single_email(email)
        
        if not processed_email:
            return email
        
        # Process attachments if available
        if (self.document_processor and self.gmail_service and 
            email.get('has_attachments') and email.get('attachments')):
            
            attachment_analysis = self._analyze_attachments(email)
            processed_email['attachment_analysis'] = attachment_analysis
            
            # If we have AI service, enhance the analysis
            if self.ai_service and attachment_analysis.get('extracted_text'):
                enhanced_analysis = self._enhance_analysis_with_attachments(
                    email, attachment_analysis
                )
                processed_email['enhanced_analysis'] = enhanced_analysis
        
        return processed_email
    
    def _analyze_attachments(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze email attachments"""
        attachment_analysis = {
            'total_attachments': len(email.get('attachments', [])),
            'processed_attachments': 0,
            'extracted_text': '',
            'document_summaries': [],
            'key_points': [],
            'errors': []
        }
        
        for attachment in email.get('attachments', []):
            try:
                # Get attachment content
                attachment_data = self.gmail_service.get_attachment_content(
                    email['id'], attachment['id']
                )
                
                if attachment_data:
                    # Extract text from document
                    doc_result = self.document_processor.extract_document_text(
                        attachment_data, 
                        attachment['mime_type'], 
                        attachment['filename']
                    )
                    
                    if doc_result['success'] and doc_result['text']:
                        attachment_analysis['processed_attachments'] += 1
                        attachment_analysis['extracted_text'] += f"\n\n--- {attachment['filename']} ---\n"
                        attachment_analysis['extracted_text'] += doc_result['text']
                        
                        # Analyze document content
                        doc_analysis = self.document_processor.analyze_document_content(
                            doc_result['text'], 
                            attachment['filename']
                        )
                        
                        if doc_analysis['success']:
                            attachment_analysis['document_summaries'].append({
                                'filename': attachment['filename'],
                                'type': doc_analysis['document_type'],
                                'word_count': doc_analysis['word_count'],
                                'key_points': doc_analysis['key_points'],
                                'analysis': doc_analysis['analysis']
                            })
                            
                            # Add key points to overall list
                            attachment_analysis['key_points'].extend(doc_analysis['key_points'])
                    else:
                        attachment_analysis['errors'].append(
                            f"Failed to extract text from {attachment['filename']}: {doc_result.get('error', 'Unknown error')}"
                        )
                else:
                    attachment_analysis['errors'].append(
                        f"Failed to retrieve attachment content for {attachment['filename']}"
                    )
                    
            except Exception as e:
                attachment_analysis['errors'].append(
                    f"Error processing {attachment.get('filename', 'unknown')}: {str(e)}"
                )
        
        return attachment_analysis
    
    def _enhance_analysis_with_attachments(self, email: Dict[str, Any], attachment_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to enhance email analysis with attachment content"""
        try:
            # Prepare context for AI analysis
            email_context = f"""
Email Subject: {email.get('subject', '')}
Email Sender: {email.get('sender', '')}
Email Body: {email.get('body', '')}

Attachments Found: {attachment_analysis['total_attachments']}
Processed Attachments: {attachment_analysis['processed_attachments']}

Document Summaries:
{self._format_document_summaries(attachment_analysis['document_summaries'])}

Key Points from Attachments:
{self._format_key_points(attachment_analysis['key_points'])}

Extracted Text from Attachments:
{attachment_analysis['extracted_text'][:2000]}...
"""
            
            # Generate enhanced analysis using AI
            enhanced_prompt = f"""
Based on the email content and attached documents, provide a comprehensive analysis:

{email_context}

Please provide:
1. **Email Context Analysis**: What is the main purpose of this email?
2. **Document Relevance**: How do the attached documents relate to the email content?
3. **Key Information**: What are the most important points from both email and attachments?
4. **Action Items**: What actions are required based on the email and documents?
5. **Priority Assessment**: How urgent is this email considering the document content?
6. **Response Recommendations**: What should be included in a response?

Format your response in clear sections with bullet points where appropriate.
"""
            
            if self.ai_service:
                enhanced_response = self.ai_service.analyze_text(enhanced_prompt)
                return {
                    'enhanced_analysis': enhanced_response,
                    'context_used': email_context[:500] + "...",
                    'attachments_considered': attachment_analysis['processed_attachments']
                }
            else:
                return {
                    'enhanced_analysis': 'AI service not available for enhanced analysis',
                    'context_used': email_context[:500] + "...",
                    'attachments_considered': attachment_analysis['processed_attachments']
                }
                
        except Exception as e:
            return {
                'enhanced_analysis': f'Error generating enhanced analysis: {str(e)}',
                'context_used': '',
                'attachments_considered': 0
            }
    
    def _format_document_summaries(self, summaries: List[Dict[str, Any]]) -> str:
        """Format document summaries for AI prompt"""
        if not summaries:
            return "No documents processed."
        
        formatted = ""
        for summary in summaries:
            formatted += f"- {summary['filename']} ({summary['type']}): {summary['word_count']} words\n"
            formatted += f"  Analysis: {summary['analysis']}\n"
        
        return formatted
    
    def _format_key_points(self, key_points: List[str]) -> str:
        """Format key points for AI prompt"""
        if not key_points:
            return "No key points extracted."
        
        formatted = ""
        for i, point in enumerate(key_points[:5], 1):  # Limit to top 5
            formatted += f"{i}. {point}\n"
        
        return formatted
    
    def _extract_email_address(self, sender: str) -> str:
        """Extract the email address from a sender string"""
        match = re.search(r'<(.+?)>', sender)
        if match:
            return match.group(1).strip().lower()
        return sender.strip().lower()

    def process_emails_hybrid(self, emails: List[Dict[str, Any]], user: Dict[str, Any], ai_priority_toggle: bool) -> List[Dict[str, Any]]:
        processed_emails = []
        user_plan = (user or {}).get('subscription_plan', 'free')
        vip_senders = set((user or {}).get('vip_senders', []))  # Assume this is a list of emails/names
        vip_senders = set(e.strip().lower() for e in vip_senders)
        print(f"[DEBUG] VIP senders for user: {vip_senders}")
        for email in emails:
            processed_email = email.copy()
            print(f"[DEBUG] Processing email from sender: {processed_email.get('sender')}")
            sender_email = self._extract_email_address(processed_email.get('sender', ''))
            use_llm = self._should_use_llm_priority(processed_email, user_plan, ai_priority_toggle, vip_senders)
            print(f"[DEBUG] use_llm for sender {processed_email.get('sender')}: {use_llm}")
            if use_llm and self.ai_service:
                # Call LLM for priority
                prompt_prefix = ''
                if sender_email in vip_senders:
                    prompt_prefix = 'The following email is from a VIP sender. Always assign it a HIGH or URGENT priority unless it is clearly spam or irrelevant.\n\n'
                prompt = f"""{prompt_prefix}You are an AI email assistant. Given the following email, assign a priority (urgent, high, normal, low) and explain your reasoning.\nEmail:\nSubject: {processed_email.get('subject','')}\nFrom: {processed_email.get('sender','')}\nBody: {processed_email.get('body','')}\nOutput JSON: {{\"priority\": \"...\", \"reason\": \"...\"}}\n"""
                try:
                    llm_result = self.ai_service.assign_priority(prompt)
                    if llm_result and isinstance(llm_result, dict):
                        # VIP override: if sender is VIP and priority is not high/urgent, force high
                        priority = llm_result.get('priority', 'normal').lower()
                        if sender_email in vip_senders and priority not in ['high', 'urgent']:
                            print(f"[VIP OVERRIDE] Forcing priority to 'high' for VIP sender: {sender_email}")
                            priority = 'high'
                            llm_result['reason'] = f"VIP sender override: {llm_result.get('reason', '')}"
                        processed_email['ai_priority'] = priority
                        processed_email['ai_priority_reason'] = llm_result.get('reason', '')
                        processed_email['priority'] = priority
                    else:
                        processed_email['priority'] = self._keyword_priority(processed_email)
                except Exception as e:
                    print(f"[LLM Priority Error] {e}")
                    processed_email['priority'] = self._keyword_priority(processed_email)
            else:
                processed_email['priority'] = self._keyword_priority(processed_email)
            processed_emails.append(processed_email)
        processed_emails.sort(key=lambda x: (self._priority_to_number(x['priority']), x['date']), reverse=True)
        return processed_emails

    def _should_use_llm_priority(self, email, user_plan, ai_priority_toggle, vip_senders):
        # Only for Pro/Enterprise with toggle on
        if user_plan not in ['pro', 'enterprise'] or not ai_priority_toggle:
            return False
        # Skip obvious low-priority
        subject = (email.get('subject') or '').lower()
        sender = (email.get('sender') or '').lower()
        print(f"[DEBUG] Checking if sender '{sender}' is in VIP senders: {vip_senders}")
        if any(kw in subject for kw in ['newsletter', 'promotion', 'unsubscribe', 'marketing', 'sale', 'offer']):
            return False
        # VIP senders or focus threads always use LLM
        if sender in vip_senders:
            print(f"[DEBUG] VIP prioritization triggered for sender: {sender}")
            return True
        # Otherwise, use LLM for new emails (no ai_priority cached)
        if not email.get('ai_priority'):
            return True
        return False

    def _keyword_priority(self, email):
        subject = (email.get('subject') or '').lower()
        body = (email.get('body') or '').lower()
        high_priority = ['urgent', 'asap', 'emergency', 'critical', 'deadline']
        medium_priority = ['meeting', 'call', 'discussion', 'review', 'update']
        if any(kw in subject or kw in body for kw in high_priority):
            return 'high'
        elif any(kw in subject or kw in body for kw in medium_priority):
            return 'medium'
        else:
            return 'low' 