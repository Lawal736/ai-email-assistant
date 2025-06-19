import os
import json
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class HybridAIService:
    """
    Hybrid AI service that intelligently routes requests between multiple LLM providers
    based on email complexity and cost optimization.
    """
    
    def __init__(self):
        # API Keys
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Model configurations
        self.models = {
            'claude_sonnet': 'claude-3-5-sonnet-20241022',
            'claude_haiku': 'claude-3-haiku-20240307',
            'gpt_fallback': 'gpt-3.5-turbo',
            'deepseek_coder': 'deepseek-coder',
            'deepseek_chat': 'deepseek-chat',
            'gemini_pro': 'gemini-1.5-pro',
            'gemini_flash': 'gemini-1.5-flash'
        }
        
        # Provider configurations
        self.providers = {
            'claude': {
                'api_key': self.anthropic_api_key,
                'base_url': 'https://api.anthropic.com/v1/messages',
                'headers': {
                    "x-api-key": self.anthropic_api_key,
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01"
                } if self.anthropic_api_key else {}
            },
            'openai': {
                'api_key': self.openai_api_key,
                'base_url': 'https://api.openai.com/v1/chat/completions',
                'headers': {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                } if self.openai_api_key else {}
            },
            'deepseek': {
                'api_key': self.deepseek_api_key,
                'base_url': 'https://api.deepseek.com/v1/chat/completions',
                'headers': {
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json"
                } if self.deepseek_api_key else {}
            },
            'gemini': {
                'api_key': self.gemini_api_key,
                'base_url': 'https://generativelanguage.googleapis.com/v1beta/models',
                'headers': {
                    "Content-Type": "application/json"
                } if self.gemini_api_key else {}
            }
        }
        
        # Complexity thresholds
        self.complexity_threshold = 500  # characters
        self.max_tokens = {
            'claude_sonnet': 4000,
            'claude_haiku': 2000,
            'gpt_fallback': 1000,
            'deepseek_coder': 4000,
            'deepseek_chat': 4000,
            'gemini_pro': 8192,
            'gemini_flash': 4096
        }
        
        # Cost optimization settings
        self.use_haiku_for_simple = True
        self.use_sonnet_for_complex = True
        self.fallback_to_openai = True
        self.enable_deepseek = bool(self.deepseek_api_key)
        self.enable_gemini = bool(self.gemini_api_key)
        
        # Provider priority (for fallback)
        self.provider_priority = ['claude', 'deepseek', 'gemini', 'openai']
        
    def _calculate_complexity(self, email_content: str) -> Dict:
        """
        Calculate email complexity based on multiple factors.
        """
        content = email_content.lower()
        
        complexity_score = 0
        factors = {
            'length': len(email_content),
            'sentences': email_content.count('.') + email_content.count('!') + email_content.count('?'),
            'questions': content.count('?'),
            'action_words': sum(1 for word in ['urgent', 'asap', 'deadline', 'important', 'critical', 'review', 'approve', 'decide'] if word in content),
            'technical_terms': sum(1 for word in ['api', 'database', 'server', 'code', 'bug', 'feature', 'deployment', 'integration'] if word in content),
            'emotional_intensity': sum(1 for word in ['frustrated', 'concerned', 'excited', 'disappointed', 'pleased', 'worried'] if word in content)
        }
        
        # Weighted complexity calculation
        complexity_score = (
            factors['length'] * 0.3 +
            factors['sentences'] * 10 +
            factors['questions'] * 20 +
            factors['action_words'] * 30 +
            factors['technical_terms'] * 25 +
            factors['emotional_intensity'] * 15
        )
        
        return {
            'score': complexity_score,
            'factors': factors,
            'is_complex': complexity_score > self.complexity_threshold,
            'recommended_model': 'claude_sonnet' if complexity_score > self.complexity_threshold else 'claude_haiku'
        }
    
    def _call_claude_api(self, model: str, messages: List[Dict], max_tokens: int = None) -> Dict:
        """
        Make API call to Claude models.
        """
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        if max_tokens is None:
            max_tokens = self.max_tokens.get(model, 2000)
        
        headers = {
            "x-api-key": self.anthropic_api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Convert OpenAI-style messages to Claude format
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            elif msg['role'] == 'user':
                user_messages.append(msg['content'])
        
        # Combine user messages
        user_content = "\n\n".join(user_messages)
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        }
        
        if system_message:
            payload["system"] = system_message
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Claude API error: {str(e)}")
    
    def _call_openai_api(self, messages: List[Dict], max_tokens: int = 1000) -> Dict:
        """
        Fallback to OpenAI API if Claude fails.
        """
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.models['gpt_fallback'],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    def _call_deepseek_api(self, model: str, messages: List[Dict], max_tokens: int = 2000) -> Dict:
        """
        Make API call to DeepSeek models.
        """
        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"DeepSeek API error: {str(e)}")

    def _call_gemini_api(self, model: str, messages: List[Dict], max_tokens: int = 2048) -> Dict:
        """
        Make API call to Google Gemini models.
        """
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg['role'] == 'user':
                contents.append({
                    "parts": [{"text": msg['content']}]
                })
            elif msg['role'] == 'system':
                # Gemini doesn't have system messages, prepend to first user message
                if contents and contents[0].get('parts'):
                    contents[0]['parts'][0]['text'] = f"{msg['content']}\n\n{contents[0]['parts'][0]['text']}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7
            }
        }
        
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def _extract_response_content(self, response: Dict, provider: str) -> str:
        """
        Extract content from API response based on provider.
        """
        if provider == 'claude':
            return response['content'][0]['text']
        elif provider == 'openai':
            return response['choices'][0]['message']['content']
        elif provider == 'deepseek':
            return response['choices'][0]['message']['content']
        elif provider == 'gemini':
            return response['candidates'][0]['content']['parts'][0]['text']
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def analyze_email(self, email_content: str, analysis_type: str = "summary") -> Dict:
        """
        Analyze email using hybrid approach with intelligent model selection.
        """
        # Calculate complexity
        complexity = self._calculate_complexity(email_content)
        
        # Determine which model to use
        if complexity['is_complex'] and self.use_sonnet_for_complex:
            model = self.models['claude_sonnet']
            model_name = 'claude_sonnet'
        elif not complexity['is_complex'] and self.use_haiku_for_simple:
            model = self.models['claude_haiku']
            model_name = 'claude_haiku'
        else:
            model = self.models['claude_sonnet']
            model_name = 'claude_sonnet'
        
        # Prepare messages based on analysis type
        if analysis_type == "summary":
            system_prompt = """You are an AI email assistant. Analyze the email and provide a concise summary with key points, action items, and recommendations. Focus on the most important information."""
        elif analysis_type == "action_items":
            system_prompt = """Extract specific action items from the email. List them clearly with priorities and deadlines if mentioned."""
        elif analysis_type == "recommendations":
            system_prompt = """Provide smart response recommendations for this email. Suggest professional, helpful, and actionable responses."""
        elif analysis_type == "thread_analysis":
            system_prompt = """You are an AI email assistant analyzing an email thread. Focus ONLY on the content and context provided in the thread. Do not make assumptions or references to external information not mentioned in the emails.

Provide a comprehensive analysis in this exact format:

## Thread Summary
[Brief overview of the main discussion]

## Key Points
- [Point 1]
- [Point 2]
- [Point 3]

## Action Items
- [Action item 1 with priority and deadline if mentioned]
- [Action item 2 with priority and deadline if mentioned]

## Response Recommendations
- [Professional response suggestion 1]
- [Professional response suggestion 2]

## Follow-up Actions
- [Suggested follow-up action 1]
- [Suggested follow-up action 2]"""
        else:
            system_prompt = """You are an AI email assistant. Analyze the email and provide insights."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please analyze this email:\n\n{email_content}"}
        ]
        
        try:
            # Try Claude first
            response = self._call_claude_api(model, messages)
            content = self._extract_response_content(response, 'claude')
            print(f"✅ {analysis_type} generated using {model_name}")
            return {
                "content": content,
                "model_used": model_name,
                "complexity": complexity
            }
        except Exception as e:
            print(f"❌ Claude API failed for {analysis_type}: {str(e)}")
            
            if self.fallback_to_openai:
                try:
                    response = self._call_openai_api(messages)
                    content = self._extract_response_content(response, 'openai')
                    print(f"✅ {analysis_type} generated using OpenAI fallback")
                    return {
                        "content": content,
                        "model_used": "openai_fallback",
                        "complexity": complexity
                    }
                except Exception as fallback_error:
                    print(f"❌ OpenAI fallback also failed: {str(fallback_error)}")
                    raise Exception(f"All AI services failed for {analysis_type}: {str(e)}")
            else:
                raise e

    def generate_email_summary(self, email_content: str, subject: str = "", sender: str = "") -> Dict:
        """
        Generate a concise summary of an email.
        """
        try:
            # Enhance the prompt with subject and sender information
            enhanced_content = f"Subject: {subject}\nFrom: {sender}\n\nContent:\n{email_content}"
            result = self.analyze_email(enhanced_content, "summary")
            return {
                "success": True,
                "content": result["content"],
                "model_used": result["model_used"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": "Unable to generate summary"
            }

    def extract_action_items(self, email_content: str, subject: str = "", sender: str = "") -> Dict:
        """
        Extract action items from an email.
        """
        try:
            # Enhance the prompt with subject and sender information
            enhanced_content = f"Subject: {subject}\nFrom: {sender}\n\nContent:\n{email_content}"
            result = self.analyze_email(enhanced_content, "action_items")
            return {
                "success": True,
                "content": result["content"],
                "model_used": result["model_used"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": "Unable to extract action items"
            }

    def generate_response_recommendations(self, email_content: str, subject: str = "", sender: str = "") -> Dict:
        """
        Generate response recommendations for an email.
        """
        try:
            # Enhance the prompt with subject and sender information
            enhanced_content = f"Subject: {subject}\nFrom: {sender}\n\nContent:\n{email_content}"
            result = self.analyze_email(enhanced_content, "recommendations")
            return {
                "success": True,
                "content": result["content"],
                "model_used": result["model_used"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": "Unable to generate recommendations"
            }

    def analyze_email_thread(self, thread_content: str) -> str:
        """
        Analyze an email thread and provide comprehensive insights.
        """
        result = self.analyze_email(thread_content, "thread_analysis")
        return result["content"]

    def generate_daily_summary(self, emails: List[Dict]) -> Dict:
        """
        Generate daily summary using the most appropriate model based on email volume and complexity.
        """
        total_complexity = sum(self._calculate_complexity(email.get('content', ''))['score'] for email in emails)
        avg_complexity = total_complexity / len(emails) if emails else 0
        
        # Use Sonnet for complex summaries, Haiku for simple ones
        if avg_complexity > self.complexity_threshold or len(emails) > 10:
            model = self.models['claude_sonnet']
            model_name = 'claude_sonnet'
        else:
            model = self.models['claude_haiku']
            model_name = 'claude_haiku'
        
        system_prompt = """You are an AI email assistant. Create a comprehensive daily summary of the emails provided. Include:
1. Key themes and topics
2. Important action items
3. Urgent matters requiring attention
4. Recommendations for follow-up
Format the summary in a clear, structured way."""
        
        email_summaries = []
        for email in emails:
            email_summaries.append(f"From: {email.get('sender', 'Unknown')}\nSubject: {email.get('subject', 'No subject')}\nContent: {email.get('content', '')[:500]}...")
        
        user_content = f"Please analyze these {len(emails)} emails and provide a daily summary:\n\n" + "\n\n---\n\n".join(email_summaries)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        try:
            response = self._call_claude_api(model, messages, max_tokens=3000)
            content = self._extract_response_content(response, 'claude')
            
            return {
                "success": True,
                "content": content,
                "model_used": model_name,
                "email_count": len(emails),
                "avg_complexity": avg_complexity,
                "provider": "claude"
            }
            
        except Exception as claude_error:
            if self.fallback_to_openai:
                try:
                    response = self._call_openai_api(messages, max_tokens=2000)
                    content = self._extract_response_content(response, 'openai')
                    
                    return {
                        "success": True,
                        "content": content,
                        "model_used": "gpt_fallback",
                        "email_count": len(emails),
                        "avg_complexity": avg_complexity,
                        "provider": "openai",
                        "fallback_used": True
                    }
                except Exception as openai_error:
                    return {
                        "success": False,
                        "error": f"Both APIs failed. Claude: {claude_error}, OpenAI: {openai_error}",
                        "email_count": len(emails)
                    }
            else:
                return {
                    "success": False,
                    "error": f"Claude API failed: {claude_error}",
                    "email_count": len(emails)
                }

    def analyze_text(self, prompt: str, max_tokens: int = 1500) -> str:
        """
        Analyze arbitrary text prompt using hybrid AI model selection.
        Returns the generated content as a string.
        """
        # Calculate complexity and select provider
        complexity = self._calculate_complexity(prompt)
        
        # Try providers in order of preference
        for provider in self.provider_priority:
            try:
                if provider == 'claude' and self.anthropic_api_key:
                    provider_name, model_name, model_id = self._select_provider_and_model(complexity)
                    if provider_name == 'claude':
                        messages = [{"role": "user", "content": prompt}]
                        response = self._call_claude_api(model_id, messages, max_tokens=max_tokens)
                        content = self._extract_response_content(response, 'claude')
                        print(f"✅ analyze_text generated using {model_name}")
                        return content
                
                elif provider == 'deepseek' and self.enable_deepseek:
                    provider_name, model_name, model_id = self._select_provider_and_model(complexity)
                    if provider_name == 'deepseek':
                        messages = [{"role": "user", "content": prompt}]
                        response = self._call_deepseek_api(model_id, messages, max_tokens=max_tokens)
                        content = self._extract_response_content(response, 'deepseek')
                        print(f"✅ analyze_text generated using {model_name}")
                        return content
                
                elif provider == 'gemini' and self.enable_gemini:
                    provider_name, model_name, model_id = self._select_provider_and_model(complexity)
                    if provider_name == 'gemini':
                        messages = [{"role": "user", "content": prompt}]
                        response = self._call_gemini_api(model_id, messages, max_tokens=max_tokens)
                        content = self._extract_response_content(response, 'gemini')
                        print(f"✅ analyze_text generated using {model_name}")
                        return content
                
                elif provider == 'openai' and self.openai_api_key:
                    messages = [{"role": "user", "content": prompt}]
                    response = self._call_openai_api(messages, max_tokens=max_tokens)
                    content = self._extract_response_content(response, 'openai')
                    print(f"✅ analyze_text generated using OpenAI fallback")
                    return content
                    
            except Exception as e:
                print(f"❌ {provider.capitalize()} API failed: {str(e)}")
                continue
        
        # If all providers fail
        raise Exception(f"All AI providers failed for analyze_text. Please check your API keys and network connection.")

    def assign_priority(self, prompt: str) -> dict:
        """
        Assign a priority to an email using the LLM. Expects a JSON response with 'priority' and 'reason'.
        """
        try:
            result = self.analyze_text(prompt, max_tokens=300)
            import json
            try:
                parsed = json.loads(result)
                return {
                    'priority': parsed.get('priority', 'normal'),
                    'reason': parsed.get('reason', '')
                }
            except Exception:
                # Fallback: try to extract priority from text
                lower = result.lower()
                if 'high' in lower:
                    return {'priority': 'high', 'reason': result}
                elif 'medium' in lower:
                    return {'priority': 'medium', 'reason': result}
                elif 'low' in lower:
                    return {'priority': 'low', 'reason': result}
                elif 'urgent' in lower:
                    return {'priority': 'urgent', 'reason': result}
                else:
                    return {'priority': 'normal', 'reason': result}
        except Exception as e:
            print(f"[assign_priority ERROR] {e}")
            return {'priority': 'normal', 'reason': str(e)}

    def _select_provider_and_model(self, complexity: Dict, task_type: str = "general") -> tuple:
        """
        Intelligently select the best provider and model based on complexity and task type.
        Returns (provider, model_name, model_id)
        """
        is_complex = complexity['is_complex']
        
        # Define model selection logic
        if task_type == "coding" and self.enable_deepseek:
            # DeepSeek Coder is excellent for coding tasks
            return ('deepseek', 'deepseek_coder', self.models['deepseek_coder'])
        
        if is_complex:
            # Complex tasks: prefer Claude Sonnet, then DeepSeek Chat, then Gemini Pro
            if self.anthropic_api_key:
                return ('claude', 'claude_sonnet', self.models['claude_sonnet'])
            elif self.enable_deepseek:
                return ('deepseek', 'deepseek_chat', self.models['deepseek_chat'])
            elif self.enable_gemini:
                return ('gemini', 'gemini_pro', self.models['gemini_pro'])
            elif self.openai_api_key:
                return ('openai', 'gpt_fallback', self.models['gpt_fallback'])
        else:
            # Simple tasks: prefer Claude Haiku, then Gemini Flash, then DeepSeek Chat
            if self.anthropic_api_key:
                return ('claude', 'claude_haiku', self.models['claude_haiku'])
            elif self.enable_gemini:
                return ('gemini', 'gemini_flash', self.models['gemini_flash'])
            elif self.enable_deepseek:
                return ('deepseek', 'deepseek_chat', self.models['deepseek_chat'])
            elif self.openai_api_key:
                return ('openai', 'gpt_fallback', self.models['gpt_fallback'])
        
        # Fallback to any available provider
        for provider in self.provider_priority:
            if provider == 'claude' and self.anthropic_api_key:
                return ('claude', 'claude_sonnet', self.models['claude_sonnet'])
            elif provider == 'deepseek' and self.enable_deepseek:
                return ('deepseek', 'deepseek_chat', self.models['deepseek_chat'])
            elif provider == 'gemini' and self.enable_gemini:
                return ('gemini', 'gemini_pro', self.models['gemini_pro'])
            elif provider == 'openai' and self.openai_api_key:
                return ('openai', 'gpt_fallback', self.models['gpt_fallback'])
        
        raise Exception("No AI providers available. Please configure at least one API key.")

# Legacy OpenAI service for backward compatibility
class AIService:
    """
    Legacy OpenAI service - kept for backward compatibility.
    Consider migrating to HybridAIService for better cost optimization.
    """
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = None  # Will be initialized if needed
        self.model = "gpt-3.5-turbo"
    
    def analyze_email(self, email_content: str, analysis_type: str = "summary") -> Dict:
        """Legacy method - use HybridAIService instead"""
        return {"success": False, "error": "Legacy OpenAI service. Please use HybridAIService for better performance."}
    
    def generate_daily_summary(self, emails: List[Dict]) -> Dict:
        """Legacy method - use HybridAIService instead"""
        return {"success": False, "error": "Legacy OpenAI service. Please use HybridAIService for better performance."}

# Default export
AIService = HybridAIService 