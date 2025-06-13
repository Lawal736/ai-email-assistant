#!/usr/bin/env python3
"""
Test script to debug dashboard issues
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gmail_service import GmailService
from email_processor import EmailProcessor

def test_email_loading():
    """Test email loading and processing"""
    print("🧪 Testing Email Loading and Processing")
    print("=" * 50)
    
    try:
        # Initialize services
        print("📧 Initializing Gmail Service...")
        gmail_service = GmailService()
        
        if not gmail_service.is_authenticated():
            print("❌ Gmail not authenticated!")
            print("Please run the app and authenticate with Gmail first.")
            return
        
        print("✅ Gmail authenticated successfully!")
        
        # Test email loading
        print("\n📥 Loading recent emails...")
        recent_emails = gmail_service.get_todays_emails(max_results=10)
        print(f"📧 Found {len(recent_emails)} recent emails")
        
        if len(recent_emails) == 0:
            print("⚠️ No emails found for today!")
            return
        
        # Show first few emails
        for i, email in enumerate(recent_emails[:3]):
            print(f"\n📨 Email {i+1}:")
            print(f"   Subject: {email.get('subject', 'No Subject')}")
            print(f"   From: {email.get('sender', 'Unknown')}")
            print(f"   Date: {email.get('date', 'Unknown')}")
            print(f"   Priority: {email.get('priority', 'low')}")
        
        # Test email processing
        print("\n🔧 Testing email processing...")
        email_processor = EmailProcessor()
        
        # Test filtering
        print("🔍 Testing email filtering...")
        filtered_emails = email_processor.filter_emails(recent_emails)
        print(f"📊 After filtering: {len(filtered_emails)} emails")
        
        # Test basic processing
        print("⚙️ Testing basic email processing...")
        processed_emails = email_processor.process_emails_basic(filtered_emails)
        print(f"✅ Processed {len(processed_emails)} emails")
        
        # Test thread grouping
        print("🧵 Testing thread grouping...")
        email_threads = email_processor.group_emails_by_thread(processed_emails)
        print(f"📋 Created {len(email_threads)} email threads")
        
        # Show thread info
        for i, (thread_key, thread) in enumerate(list(email_threads.items())[:3]):
            print(f"\n🧵 Thread {i+1}:")
            print(f"   Subject: {thread['subject']}")
            print(f"   Sender: {thread['sender']}")
            print(f"   Messages: {thread['thread_count']}")
            print(f"   Priority: {thread['priority']}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_email_loading() 