import os
import json
from openai import OpenAI
from typing import List, Dict, Any

class AIService:
    """Service class for AI-powered email analysis using OpenAI"""
    
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        # Try gpt-4 first, fallback to gpt-3.5-turbo
        self.model = "gpt-3.5-turbo"  # More accessible model
    
    def _is_quota_exceeded(self, error):
        """Check if the error is due to quota exceeded"""
        if hasattr(error, 'response') and error.response:
            return error.response.status_code == 429
        return False
    
    def _generate_fallback_summary(self, emails: List[Dict[str, Any]]) -> str:
        """Generate a basic summary without AI when quota is exceeded"""
        if not emails:
            return "No emails to summarize."
        
        # Count emails by type and priority
        email_count = len(emails)
        high_priority = len([e for e in emails if e.get('priority') == 'high'])
        medium_priority = len([e for e in emails if e.get('priority') == 'medium'])
        work_emails = len([e for e in emails if e.get('type') == 'work'])
        personal_emails = len([e for e in emails if e.get('type') == 'personal'])
        
        summary = f"""
<div class="fallback-summary">
    <div class="alert alert-warning mb-3">
        <i class="fas fa-exclamation-triangle me-2"></i>
        <strong>Daily Email Summary</strong> (AI Analysis Unavailable)
    </div>
    
    <div class="summary-section mb-3">
        <h6 class="fw-bold text-primary mb-2">
            <i class="fas fa-chart-pie me-2"></i>Email Overview
        </h6>
        <div class="row">
            <div class="col-md-6">
                <ul class="list-unstyled">
                    <li><i class="fas fa-envelope me-2 text-primary"></i><strong>Total emails:</strong> {email_count}</li>
                    <li><i class="fas fa-exclamation-triangle me-2 text-danger"></i><strong>High priority:</strong> {high_priority}</li>
                    <li><i class="fas fa-exclamation-circle me-2 text-warning"></i><strong>Medium priority:</strong> {medium_priority}</li>
                </ul>
            </div>
            <div class="col-md-6">
                <ul class="list-unstyled">
                    <li><i class="fas fa-briefcase me-2 text-info"></i><strong>Work-related:</strong> {work_emails}</li>
                    <li><i class="fas fa-user me-2 text-success"></i><strong>Personal:</strong> {personal_emails}</li>
                </ul>
            </div>
        </div>
    </div>
    
    <div class="summary-section mb-3">
        <h6 class="fw-bold text-info mb-2">
            <i class="fas fa-search me-2"></i>Key Insights
        </h6>
        <ul class="list-unstyled">
            <li><i class="fas fa-clock me-2 text-danger"></i>You have <strong>{high_priority}</strong> urgent emails that need immediate attention</li>
            <li><i class="fas fa-briefcase me-2 text-info"></i><strong>{work_emails}</strong> work-related emails require professional responses</li>
            <li><i class="fas fa-user me-2 text-success"></i><strong>{personal_emails}</strong> personal emails for your attention</li>
        </ul>
    </div>
    
    <div class="summary-section mb-3">
        <h6 class="fw-bold text-success mb-2">
            <i class="fas fa-lightbulb me-2"></i>Recommendation
        </h6>
        <div class="alert alert-success">
            <i class="fas fa-arrow-up me-2"></i>
            Focus on high-priority emails first, then work-related communications.
        </div>
    </div>
    
    <div class="alert alert-secondary">
        <i class="fas fa-info-circle me-2"></i>
        <small><em>Note: AI analysis is currently unavailable due to API quota limits. Please check your OpenAI billing or upgrade your plan for enhanced AI features.</em></small>
    </div>
</div>
        """
        
        return summary.strip()
    
    def generate_daily_summary(self, emails: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive daily email summary"""
        if not emails:
            return "No emails to summarize."
        
        # Prepare email data for AI analysis
        email_summaries = []
        for email in emails:
            summary = f"""
            From: {email['sender']}
            Subject: {email['subject']}
            Type: {email['type']}
            Priority: {email['priority']}
            Snippet: {email['snippet'][:200]}...
            """
            email_summaries.append(summary)
        
        prompt = f"""
        You are an AI email assistant. Analyze the following emails from today and provide a comprehensive daily summary.
        
        Focus on:
        1. Overall email volume and patterns
        2. Key themes and topics
        3. Urgent matters that need attention
        4. Important deadlines or meetings
        5. Communication patterns with different senders
        
        Emails to analyze:
        {chr(10).join(email_summaries)}
        
        Please provide a clear, concise summary that helps the user understand their email landscape for the day.
        Format the response in a professional but friendly tone.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful email assistant that provides clear, actionable summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Error generating daily summary: {e}")
            if self._is_quota_exceeded(e):
                return self._generate_fallback_summary(emails)
            return "Unable to generate summary due to an error."
    
    def _generate_fallback_action_items(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate basic action items without AI when quota is exceeded"""
        action_items = []
        
        for email in emails:
            # Skip low-priority emails for action items
            if email['priority'] == 'low' and email['type'] in ['newsletter', 'other']:
                continue
            
            # Create basic action item based on email priority and type
            action_description = f"Review email from {email['sender']} regarding '{email['subject']}'"
            
            if email['priority'] == 'high':
                action_description += " - <strong>URGENT:</strong> Requires immediate attention"
            elif email['priority'] == 'medium':
                action_description += " - Respond within 24 hours"
            
            # Create HTML formatted action items
            action_items.append({
                'email_id': email['id'],
                'email_subject': email['subject'],
                'email_sender': email['sender'],
                'action_items': f"""
                <div class="action-item-content">
                    <div class="action-main">
                        <i class="fas fa-tasks me-2 text-primary"></i>
                        {action_description}
                    </div>
                    <div class="action-details mt-2">
                        <span class="badge priority-{email['priority']} me-2">
                            <i class="fas fa-flag me-1"></i>Priority: {email['priority'].title()}
                        </span>
                        <span class="badge bg-secondary">
                            <i class="fas fa-tag me-1"></i>Type: {email['type'].title()}
                        </span>
                    </div>
                </div>
                """,
                'priority': email['priority'],
                'type': email['type']
            })
        
        return action_items
    
    def extract_action_items(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract actionable items from emails"""
        if not emails:
            return []
        
        action_items = []
        
        for email in emails:
            # Skip low-priority emails for action items
            if email['priority'] == 'low' and email['type'] in ['newsletter', 'other']:
                continue
            
            prompt = f"""
            Analyze this email and extract any actionable items or tasks that the recipient needs to do.
            
            Email Details:
            From: {email['sender']}
            Subject: {email['subject']}
            Body: {email['body'][:1000]}...
            
            For each action item, provide:
            1. A clear, actionable description
            2. Priority level (high/medium/low)
            3. Estimated time to complete
            4. Any deadlines mentioned
            5. Type of action (reply, follow-up, task, meeting, etc.)
            
            If there are no clear action items, respond with "No action items found."
            Otherwise, provide a structured list of action items.
            """
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an AI assistant that extracts actionable items from emails."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.5
                )
                
                content = response.choices[0].message.content.strip()
                
                if "No action items found" not in content:
                    action_items.append({
                        'email_id': email['id'],
                        'email_subject': email['subject'],
                        'email_sender': email['sender'],
                        'action_items': content,
                        'priority': email['priority'],
                        'type': email['type']
                    })
            
            except Exception as e:
                print(f"Error extracting action items from email {email['id']}: {e}")
                if self._is_quota_exceeded(e):
                    # Add basic action item for high/medium priority emails
                    if email['priority'] in ['high', 'medium']:
                        action_items.append({
                            'email_id': email['id'],
                            'email_subject': email['subject'],
                            'email_sender': email['sender'],
                            'action_items': f"• Review email from {email['sender']} regarding '{email['subject']}'\n• Priority: {email['priority']}\n• Type: {email['type']}",
                            'priority': email['priority'],
                            'type': email['type']
                        })
                continue
        
        # If no AI-generated action items, use fallback
        if not action_items:
            return self._generate_fallback_action_items(emails)
        
        return action_items
    
    def _generate_fallback_recommendations(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate basic response recommendations without AI when quota is exceeded"""
        recommendations = []
        
        for email in emails:
            # Skip newsletters and low-priority emails
            if email['type'] == 'newsletter' or email['priority'] == 'low':
                continue
            
            # Create basic recommendation based on email characteristics
            if email['priority'] == 'high':
                recommendation = f"""
                <div class="recommendation-content">
                    <div class="recommendation-main">
                        <i class="fas fa-exclamation-triangle me-2 text-danger"></i>
                        <strong>URGENT:</strong> Respond immediately to {email['sender']} regarding '{email['subject']}'
                    </div>
                    <div class="recommendation-details mt-2">
                        <p class="mb-1"><i class="fas fa-comment me-2 text-primary"></i>Use professional tone and address the urgency</p>
                        <p class="mb-0"><i class="fas fa-clock me-2 text-warning"></i>Response time: Immediate</p>
                    </div>
                </div>
                """
            elif email['type'] == 'work':
                recommendation = f"""
                <div class="recommendation-content">
                    <div class="recommendation-main">
                        <i class="fas fa-briefcase me-2 text-info"></i>
                        <strong>Professional response needed</strong> for {email['sender']} regarding '{email['subject']}'
                    </div>
                    <div class="recommendation-details mt-2">
                        <p class="mb-1"><i class="fas fa-comment me-2 text-primary"></i>Use appropriate business tone</p>
                        <p class="mb-0"><i class="fas fa-clock me-2 text-warning"></i>Response time: Within 24 hours</p>
                    </div>
                </div>
                """
            else:
                recommendation = f"""
                <div class="recommendation-content">
                    <div class="recommendation-main">
                        <i class="fas fa-user me-2 text-success"></i>
                        <strong>Consider responding</strong> to {email['sender']} regarding '{email['subject']}'
                    </div>
                    <div class="recommendation-details mt-2">
                        <p class="mb-1"><i class="fas fa-comment me-2 text-primary"></i>Use friendly tone</p>
                        <p class="mb-0"><i class="fas fa-clock me-2 text-warning"></i>Response time: Within 48 hours</p>
                    </div>
                </div>
                """
            
            recommendations.append({
                'email_id': email['id'],
                'email_subject': email['subject'],
                'email_sender': email['sender'],
                'recommendations': recommendation,
                'priority': email['priority'],
                'type': email['type']
            })
        
        return recommendations
    
    def generate_response_recommendations(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate response recommendations for emails"""
        if not emails:
            return []
        
        recommendations = []
        
        for email in emails:
            # Skip newsletters and low-priority emails
            if email['type'] == 'newsletter' or email['priority'] == 'low':
                continue
            
            prompt = f"""
            Analyze this email and provide response recommendations for the recipient.
            
            Email Details:
            From: {email['sender']}
            Subject: {email['subject']}
            Body: {email['body'][:1000]}...
            Type: {email['type']}
            Priority: {email['priority']}
            
            Provide:
            1. Whether a response is needed (yes/no/maybe)
            2. Recommended response tone (professional, friendly, formal, casual)
            3. Key points to address in the response
            4. Suggested response structure
            5. Any questions that should be asked
            6. Recommended response time (immediate, within 24 hours, within a week)
            
            Format your response in a clear, structured way.
            """
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an AI assistant that provides email response recommendations."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=400,
                    temperature=0.6
                )
                
                content = response.choices[0].message.content.strip()
                
                recommendations.append({
                    'email_id': email['id'],
                    'email_subject': email['subject'],
                    'email_sender': email['sender'],
                    'recommendations': content,
                    'priority': email['priority'],
                    'type': email['type']
                })
            
            except Exception as e:
                print(f"Error generating recommendations for email {email['id']}: {e}")
                if self._is_quota_exceeded(e):
                    # Add basic recommendation for high/medium priority emails
                    if email['priority'] in ['high', 'medium']:
                        recommendations.append({
                            'email_id': email['id'],
                            'email_subject': email['subject'],
                            'email_sender': email['sender'],
                            'recommendations': f"Consider responding to {email['sender']} regarding '{email['subject']}'. Priority: {email['priority']}, Type: {email['type']}",
                            'priority': email['priority'],
                            'type': email['type']
                        })
                continue
        
        # If no AI-generated recommendations, use fallback
        if not recommendations:
            return self._generate_fallback_recommendations(emails)
        
        return recommendations
    
    def generate_quick_response(self, email: Dict[str, Any], response_type: str = "professional") -> str:
        """Generate a quick response draft for a specific email"""
        prompt = f"""
        Generate a {response_type} email response to this email:
        
        From: {email['sender']}
        Subject: {email['subject']}
        Body: {email['body'][:800]}...
        
        Requirements:
        1. Keep it concise and professional
        2. Address the main points from the original email
        3. Use appropriate tone for the context
        4. Include a proper greeting and closing
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI assistant that generates professional email responses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Error generating quick response: {e}")
            if self._is_quota_exceeded(e):
                return f"""
Dear {email['sender'].split('<')[0].strip()},

Thank you for your email regarding "{email['subject']}".

I have received your message and will review it shortly. I appreciate you reaching out.

Best regards,
[Your name]

*Note: This is a basic response template. Please customize it based on the email content.*
                """.strip()
            return "Unable to generate response due to an error."
    
    def analyze_email_sentiment(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the sentiment and tone of an email"""
        prompt = f"""
        Analyze the sentiment and tone of this email:
        
        From: {email['sender']}
        Subject: {email['subject']}
        Body: {email['body'][:500]}...
        
        Provide analysis for:
        1. Overall sentiment (positive, negative, neutral)
        2. Tone (formal, informal, urgent, friendly, etc.)
        3. Emotional indicators
        4. Urgency level
        5. Professional vs personal nature
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes email sentiment and tone."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            analysis = response.choices[0].message.content.strip()
            
            return {
                'email_id': email['id'],
                'analysis': analysis,
                'sender': email['sender'],
                'subject': email['subject']
            }
        
        except Exception as e:
            print(f"Error analyzing email sentiment: {e}")
            if self._is_quota_exceeded(e):
                # Basic sentiment analysis based on keywords
                body_lower = email.get('body', '').lower()
                subject_lower = email.get('subject', '').lower()
                
                if any(word in body_lower or word in subject_lower for word in ['urgent', 'asap', 'emergency', 'critical']):
                    sentiment = "negative/urgent"
                elif any(word in body_lower or word in subject_lower for word in ['thank', 'appreciate', 'great', 'good']):
                    sentiment = "positive"
                else:
                    sentiment = "neutral"
                
                return {
                    'email_id': email['id'],
                    'analysis': f"Basic analysis: Sentiment appears {sentiment}. Priority: {email.get('priority', 'unknown')}. Type: {email.get('type', 'unknown')}",
                    'sender': email['sender'],
                    'subject': email['subject']
                }
            
            return {
                'email_id': email['id'],
                'analysis': "Unable to analyze sentiment due to an error.",
                'sender': email['sender'],
                'subject': email['subject']
            } 