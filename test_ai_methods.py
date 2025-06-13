#!/usr/bin/env python3
"""
Test script to verify AI methods are working correctly
"""

from ai_service import HybridAIService

def test_ai_methods():
    """Test the AI methods"""
    print("🧪 Testing AI Methods...")
    print("=" * 50)
    
    # Initialize the AI service
    try:
        ai_service = HybridAIService()
        print("✅ AI service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize AI service: {e}")
        return
    
    # Test email content
    test_email = """
    Hi Team,
    
    I wanted to follow up on the project deadline we discussed last week. 
    The client is asking for an update on the progress and wants to know 
    if we can deliver by the end of this month.
    
    Please let me know:
    1. Current status of the development
    2. Any blockers we're facing
    3. Estimated completion date
    
    This is quite urgent as the client has other projects waiting.
    
    Best regards,
    John
    """
    
    print("\n📧 Testing generate_email_summary...")
    try:
        result = ai_service.generate_email_summary(test_email, "Project Update Request", "john@company.com")
        if result['success']:
            print("✅ generate_email_summary: SUCCESS")
            print(f"   Model used: {result['model_used']}")
            print(f"   Content preview: {result['content'][:100]}...")
        else:
            print(f"❌ generate_email_summary: FAILED - {result['error']}")
    except Exception as e:
        print(f"❌ generate_email_summary: EXCEPTION - {e}")
    
    print("\n📋 Testing extract_action_items...")
    try:
        result = ai_service.extract_action_items(test_email, "Project Update Request", "john@company.com")
        if result['success']:
            print("✅ extract_action_items: SUCCESS")
            print(f"   Model used: {result['model_used']}")
            print(f"   Content preview: {result['content'][:100]}...")
        else:
            print(f"❌ extract_action_items: FAILED - {result['error']}")
    except Exception as e:
        print(f"❌ extract_action_items: EXCEPTION - {e}")
    
    print("\n💡 Testing generate_response_recommendations...")
    try:
        result = ai_service.generate_response_recommendations(test_email, "Project Update Request", "john@company.com")
        if result['success']:
            print("✅ generate_response_recommendations: SUCCESS")
            print(f"   Model used: {result['model_used']}")
            print(f"   Content preview: {result['content'][:100]}...")
        else:
            print(f"❌ generate_response_recommendations: FAILED - {result['error']}")
    except Exception as e:
        print(f"❌ generate_response_recommendations: EXCEPTION - {e}")
    
    print("\n📊 Testing generate_daily_summary...")
    try:
        mock_emails = [
            {
                'sender': 'john@company.com',
                'subject': 'Project Update Request',
                'content': test_email
            },
            {
                'sender': 'sarah@company.com',
                'subject': 'Meeting Schedule',
                'content': 'Hi, let\'s schedule a meeting for next week to discuss the project.'
            }
        ]
        result = ai_service.generate_daily_summary(mock_emails)
        if result['success']:
            print("✅ generate_daily_summary: SUCCESS")
            print(f"   Model used: {result['model_used']}")
            print(f"   Email count: {result['email_count']}")
            print(f"   Content preview: {result['content'][:100]}...")
        else:
            print(f"❌ generate_daily_summary: FAILED - {result['error']}")
    except Exception as e:
        print(f"❌ generate_daily_summary: EXCEPTION - {e}")
    
    print("\n" + "=" * 50)
    print("🎉 AI Methods Test Complete!")

if __name__ == "__main__":
    test_ai_methods() 