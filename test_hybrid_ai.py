#!/usr/bin/env python3
"""
Test script for the Hybrid AI Service with Claude models.
This demonstrates the intelligent routing between Claude Sonnet and Claude Haiku.
"""

import os
from dotenv import load_dotenv
from ai_service import HybridAIService

load_dotenv()

def test_complexity_calculation():
    """Test email complexity calculation."""
    ai_service = HybridAIService()
    
    # Simple email
    simple_email = "Hi, just checking in on the project status. Thanks!"
    
    # Complex email
    complex_email = """
    Urgent: Database Integration Issue
    
    Hi team,
    
    We're experiencing critical issues with the database integration for the new API endpoints. 
    The authentication tokens are not being properly validated, and we're getting 500 errors 
    when users try to access the dashboard.
    
    Questions:
    1. Can you review the authentication flow in the middleware?
    2. Are there any recent changes to the database schema?
    3. Should we rollback to the previous version?
    
    This is affecting 50+ users and needs immediate attention.
    
    Please let me know your recommendations ASAP.
    
    Best regards,
    John
    """
    
    print("🔍 Testing Email Complexity Analysis")
    print("=" * 50)
    
    simple_complexity = ai_service._calculate_complexity(simple_email)
    complex_complexity = ai_service._calculate_complexity(complex_email)
    
    print(f"📧 Simple Email:")
    print(f"   Content: {simple_email}")
    print(f"   Complexity Score: {simple_complexity['score']}")
    print(f"   Is Complex: {simple_complexity['is_complex']}")
    print(f"   Recommended Model: {simple_complexity['recommended_model']}")
    print(f"   Factors: {simple_complexity['factors']}")
    print()
    
    print(f"📧 Complex Email:")
    print(f"   Content: {complex_email[:100]}...")
    print(f"   Complexity Score: {complex_complexity['score']}")
    print(f"   Is Complex: {complex_complexity['is_complex']}")
    print(f"   Recommended Model: {complex_complexity['recommended_model']}")
    print(f"   Factors: {complex_complexity['factors']}")
    print()

def test_ai_analysis():
    """Test AI analysis with different email types."""
    ai_service = HybridAIService()
    
    # Test emails
    test_emails = [
        {
            "name": "Simple Follow-up",
            "content": "Hi Sarah, just following up on our meeting yesterday. When can we schedule the next review? Thanks!"
        },
        {
            "name": "Complex Technical Issue",
            "content": """
            Critical: Production Deployment Failure
            
            Team,
            
            We're experiencing a major issue with the production deployment. The new microservice 
            architecture is causing cascading failures in the payment processing system.
            
            Issues identified:
            - Database connection timeouts
            - Memory leaks in the authentication service
            - API rate limiting not working properly
            
            Questions:
            1. Should we rollback to the previous stable version?
            2. Can we implement a hotfix for the authentication service?
            3. What's the impact on user data integrity?
            
            This is affecting 1000+ users and causing revenue loss.
            
            Urgent response needed.
            
            Best,
            Tech Lead
            """
        }
    ]
    
    print("🤖 Testing Hybrid AI Analysis")
    print("=" * 50)
    
    for email in test_emails:
        print(f"📧 Testing: {email['name']}")
        print(f"   Content: {email['content'][:100]}...")
        
        # Test different analysis types
        for analysis_type in ["summary", "action_items", "recommendations"]:
            print(f"\n   🔍 Analysis Type: {analysis_type}")
            
            try:
                result = ai_service.analyze_email(email['content'], analysis_type)
                
                if result['success']:
                    print(f"   ✅ Success: {result['model_used']} ({result['provider']})")
                    print(f"   📊 Complexity: {result['complexity']['score']} (Complex: {result['complexity']['is_complex']})")
                    print(f"   💰 Cost Optimized: {result.get('cost_optimized', False)}")
                    print(f"   📝 Response: {result['content'][:200]}...")
                    
                    if result.get('fallback_used'):
                        print(f"   ⚠️  Fallback used: {result.get('claude_error', 'Unknown error')}")
                else:
                    print(f"   ❌ Failed: {result['error']}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
        
        print("\n" + "-" * 50)

def test_daily_summary():
    """Test daily summary generation."""
    ai_service = HybridAIService()
    
    # Mock emails for testing
    mock_emails = [
        {
            "sender": "john@company.com",
            "subject": "Project Update",
            "content": "The new feature is ready for testing. Please review the documentation."
        },
        {
            "sender": "sarah@company.com", 
            "subject": "Meeting Reminder",
            "content": "Don't forget about the team meeting tomorrow at 2 PM."
        },
        {
            "sender": "tech@company.com",
            "subject": "Critical Bug Report",
            "content": "We found a critical security vulnerability in the authentication system. Immediate action required."
        }
    ]
    
    print("📊 Testing Daily Summary Generation")
    print("=" * 50)
    
    try:
        result = ai_service.generate_daily_summary(mock_emails)
        
        if result['success']:
            print(f"✅ Success: {result['model_used']} ({result['provider']})")
            print(f"📧 Email Count: {result['email_count']}")
            print(f"📊 Average Complexity: {result['avg_complexity']:.2f}")
            print(f"📝 Summary: {result['content'][:300]}...")
            
            if result.get('fallback_used'):
                print(f"⚠️  Fallback used due to Claude API issues")
        else:
            print(f"❌ Failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def main():
    """Main test function."""
    print("🚀 Hybrid AI Service Test Suite")
    print("=" * 60)
    
    # Check API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    print("🔑 API Key Status:")
    print(f"   Anthropic Claude: {'✅ Set' if anthropic_key else '❌ Missing'}")
    print(f"   OpenAI (Fallback): {'✅ Set' if openai_key else '❌ Missing'}")
    print()
    
    if not anthropic_key:
        print("⚠️  Warning: ANTHROPIC_API_KEY not found. Tests will fail.")
        print("   Get your key from: https://console.anthropic.com/")
        print()
    
    # Run tests
    test_complexity_calculation()
    test_ai_analysis()
    test_daily_summary()
    
    print("🎉 Test suite completed!")

if __name__ == "__main__":
    main() 