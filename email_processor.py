import re
from datetime import datetime
from typing import List, Dict, Any
from email.utils import parsedate_to_datetime

class EmailProcessor:
    """Class for processing and organizing email data"""
    
    def __init__(self):
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
        """Clean email body text"""
        if not body:
            return ''
        
        # Remove HTML tags
        body = re.sub(r'<[^>]+>', '', body)
        
        # Remove extra whitespace
        body = re.sub(r'\s+', ' ', body)
        
        # Remove common email signatures
        signature_patterns = [
            r'--\s*\n.*',
            r'Sent from my iPhone.*',
            r'Get Outlook for.*',
            r'This email was sent.*'
        ]
        
        for pattern in signature_patterns:
            body = re.sub(pattern, '', body, flags=re.IGNORECASE | re.DOTALL)
        
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
        
        body = email.get('body', '')
        
        # Extract dates
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{1,2}-\d{1,2}-\d{4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            dates = re.findall(pattern, body, re.IGNORECASE)
            info['dates_mentioned'].extend(dates)
        
        # Extract times
        time_patterns = [
            r'\b\d{1,2}:\d{2}\s*(?:AM|PM)?\b',
            r'\b(?:morning|afternoon|evening|night)\b'
        ]
        
        for pattern in time_patterns:
            times = re.findall(pattern, body, re.IGNORECASE)
            info['times_mentioned'].extend(times)
        
        # Extract URLs
        url_pattern = r'https?://[^\s]+'
        info['urls'] = re.findall(url_pattern, body)
        
        # Extract phone numbers
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        info['phone_numbers'] = re.findall(phone_pattern, body)
        
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