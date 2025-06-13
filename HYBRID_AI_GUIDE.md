# 🤖 Hybrid AI Approach Guide

This guide explains the intelligent hybrid AI system that uses Claude models with cost optimization and fallback mechanisms.

## 🎯 **Overview**

The hybrid approach intelligently routes email analysis between:
- **Claude Haiku** - Fast, cost-effective for simple emails
- **Claude Sonnet** - Powerful, comprehensive for complex emails  
- **OpenAI GPT** - Fallback when Claude is unavailable

## 🧠 **How It Works**

### **1. Email Complexity Analysis**

The system analyzes each email using multiple factors:

```python
complexity_factors = {
    'length': len(email_content),
    'sentences': number_of_sentences,
    'questions': number_of_questions,
    'action_words': urgent/important_terms,
    'technical_terms': technical_vocabulary,
    'emotional_intensity': emotional_words
}
```

### **2. Intelligent Model Selection**

```python
if email.complexity > threshold:
    use Claude_Sonnet()  # For complex, technical, urgent emails
else:
    use Claude_Haiku()   # For simple, routine emails
```

### **3. Fallback Strategy**

```python
try:
    result = claude_api_call()
except ClaudeError:
    result = openai_api_call()  # Fallback to OpenAI
```

## 📊 **Model Comparison**

| Model | Use Case | Cost | Speed | Capability |
|-------|----------|------|-------|------------|
| **Claude Haiku** | Simple emails, routine tasks | Low | Fast | Good |
| **Claude Sonnet** | Complex emails, technical issues | Medium | Medium | Excellent |
| **OpenAI GPT** | Fallback when Claude fails | Medium | Medium | Good |

## ⚙️ **Configuration**

### **Environment Variables**

```bash
# Primary AI Provider
ANTHROPIC_API_KEY=your_anthropic_api_key

# Fallback Provider  
OPENAI_API_KEY=your_openai_api_key

# Optional Configuration
COMPLEXITY_THRESHOLD=500
USE_HAIKU_FOR_SIMPLE=true
USE_SONNET_FOR_COMPLEX=true
FALLBACK_TO_OPENAI=true
```

### **Complexity Thresholds**

```python
# Default settings
COMPLEXITY_THRESHOLD = 500  # Characters
SIMPLE_EMAIL_LENGTH = 200   # Characters
COMPLEX_EMAIL_LENGTH = 1000 # Characters
```

## 🧪 **Testing the System**

### **1. Run the Test Suite**

```bash
python test_hybrid_ai.py
```

### **2. Test Complexity Calculation**

```python
from ai_service import HybridAIService

ai_service = HybridAIService()

# Test simple email
simple_email = "Hi, how are you?"
complexity = ai_service._calculate_complexity(simple_email)
print(f"Model: {complexity['recommended_model']}")  # claude_haiku

# Test complex email  
complex_email = "Urgent: Critical database issue affecting 1000+ users..."
complexity = ai_service._calculate_complexity(complex_email)
print(f"Model: {complexity['recommended_model']}")  # claude_sonnet
```

### **3. Test Analysis Types**

```python
# Different analysis types
result = ai_service.analyze_email(email_content, "summary")
result = ai_service.analyze_email(email_content, "action_items")  
result = ai_service.analyze_email(email_content, "recommendations")
```

## 💰 **Cost Optimization**

### **Cost Comparison (Approximate)**

| Model | Input Tokens | Output Tokens | Cost |
|-------|-------------|---------------|------|
| Claude Haiku | 1,000 | 500 | ~$0.00025 |
| Claude Sonnet | 1,000 | 500 | ~$0.003 |
| OpenAI GPT-3.5 | 1,000 | 500 | ~$0.002 |

### **Savings Strategy**

- **Simple emails** → Claude Haiku (10x cheaper than Sonnet)
- **Complex emails** → Claude Sonnet (better quality)
- **Fallback** → OpenAI (reliability)

## 🔧 **Customization**

### **Adjust Complexity Threshold**

```python
ai_service = HybridAIService()
ai_service.complexity_threshold = 300  # More aggressive Haiku usage
```

### **Custom Complexity Factors**

```python
def custom_complexity_calculation(email_content):
    # Add your own complexity factors
    factors = {
        'length': len(email_content) * 0.3,
        'urgency': email_content.count('urgent') * 50,
        'technical': email_content.count('api') * 30,
        # Add more factors...
    }
    return sum(factors.values())
```

### **Model Selection Rules**

```python
# Custom model selection logic
def select_model(email_content, user_preference):
    if user_preference == 'speed':
        return 'claude_haiku'
    elif user_preference == 'quality':
        return 'claude_sonnet'
    else:
        return ai_service._calculate_complexity(email_content)['recommended_model']
```

## 🚀 **Deployment Considerations**

### **1. API Key Management**

```bash
# Production environment
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Development environment  
ANTHROPIC_API_KEY=sk-ant-test-...
OPENAI_API_KEY=sk-test-...
```

### **2. Rate Limiting**

```python
# Implement rate limiting
import time

class RateLimitedAIService(HybridAIService):
    def __init__(self):
        super().__init__()
        self.last_call = 0
        self.min_interval = 1  # seconds
    
    def analyze_email(self, content, analysis_type):
        # Rate limiting
        time.sleep(max(0, self.min_interval - (time.time() - self.last_call)))
        self.last_call = time.time()
        
        return super().analyze_email(content, analysis_type)
```

### **3. Error Handling**

```python
# Robust error handling
try:
    result = ai_service.analyze_email(email_content)
    if result['success']:
        process_result(result['content'])
    else:
        handle_error(result['error'])
except Exception as e:
    log_error(e)
    use_fallback_analysis()
```

## 📈 **Monitoring & Analytics**

### **Usage Tracking**

```python
class AnalyticsAIService(HybridAIService):
    def analyze_email(self, content, analysis_type):
        result = super().analyze_email(content, analysis_type)
        
        # Track usage
        self.log_usage({
            'model_used': result['model_used'],
            'complexity_score': result['complexity']['score'],
            'cost_optimized': result.get('cost_optimized', False),
            'fallback_used': result.get('fallback_used', False),
            'analysis_type': analysis_type
        })
        
        return result
```

### **Performance Metrics**

- **Model Usage Distribution**: Track which models are used most
- **Complexity Distribution**: Monitor email complexity patterns
- **Cost Savings**: Calculate money saved with hybrid approach
- **Fallback Rate**: Monitor how often fallback is needed

## 🔒 **Security Considerations**

### **API Key Security**

```bash
# Never commit API keys to git
.env
credentials.json
*.key

# Use environment variables in production
heroku config:set ANTHROPIC_API_KEY=sk-ant-...
```

### **Data Privacy**

- Email content is processed in memory only
- No data is stored permanently
- API calls are made securely over HTTPS
- Consider data residency requirements

## 🎯 **Best Practices**

### **1. Start with Defaults**

```python
# Use default configuration initially
ai_service = HybridAIService()
```

### **2. Monitor and Adjust**

```python
# Adjust based on usage patterns
if fallback_rate > 0.1:  # More than 10% fallback
    increase_complexity_threshold()
```

### **3. Test Regularly**

```bash
# Run tests before deployment
python test_hybrid_ai.py
python -m pytest tests/
```

### **4. Keep Fallback Ready**

```python
# Always have OpenAI as backup
if not openai_api_key:
    print("Warning: No OpenAI fallback available")
```

## 🚀 **Migration from OpenAI**

### **Step 1: Get Anthropic API Key**

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create account and get API key
3. Add to environment variables

### **Step 2: Update Code**

```python
# Old OpenAI-only approach
from ai_service import AIService  # Legacy

# New hybrid approach  
from ai_service import HybridAIService
ai_service = HybridAIService()
```

### **Step 3: Test and Deploy**

```bash
# Test the new system
python test_hybrid_ai.py

# Deploy with confidence
git push heroku main
```

## 📞 **Support**

- **Anthropic Documentation**: https://docs.anthropic.com/
- **API Status**: https://status.anthropic.com/
- **Cost Calculator**: https://www.anthropic.com/pricing

---

**🎉 The hybrid approach gives you the best of both worlds: cost efficiency and reliability!** 