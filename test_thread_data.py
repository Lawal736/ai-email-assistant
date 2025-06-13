#!/usr/bin/env python3
"""
Test script to check email thread data structure
"""

import json
from email_processor import EmailProcessor
from gmail_service import GmailService

def test_thread_structure():
    """Test the structure of email threads"""
    print("🔍 Testing Email Thread Structure...")
    print("=" * 50)
    
    try:
        # Initialize services
        gmail_service = GmailService()
        email_processor = EmailProcessor()
        
        if not gmail_service.is_authenticated():
            print("❌ Gmail not authenticated")
            return
        
        # Get emails
        emails = gmail_service.get_todays_emails(max_results=10)
        print(f"📧 Found {len(emails)} emails")
        
        # Process emails
        processed_emails = email_processor.process_emails_basic(emails)
        print(f"✅ Processed {len(processed_emails)} emails")
        
        # Group into threads
        email_threads = email_processor.group_emails_by_thread(processed_emails)
        print(f"🧵 Created {len(email_threads)} threads")
        
        # Check each thread structure
        for thread_key, thread_data in email_threads.items():
            print(f"\n📋 Thread: {thread_key}")
            print(f"   Subject: {thread_data.get('subject', 'No Subject')}")
            print(f"   Sender: {thread_data.get('sender', 'Unknown')}")
            print(f"   Thread Count: {thread_data.get('thread_count', 0)}")
            print(f"   Emails Array Type: {type(thread_data.get('emails', []))}")
            print(f"   Emails Array Length: {len(thread_data.get('emails', []))}")
            
            # Check if emails is actually an array
            emails_array = thread_data.get('emails', [])
            if isinstance(emails_array, list):
                print(f"   ✅ Emails is a list with {len(emails_array)} items")
                for i, email in enumerate(emails_array):
                    print(f"      Email {i+1}: {email.get('subject', 'No Subject')} from {email.get('sender_clean', 'Unknown')}")
            else:
                print(f"   ❌ Emails is NOT a list! Type: {type(emails_array)}")
                print(f"   ❌ Emails content: {emails_array}")
        
        # Test JSON serialization
        print(f"\n🔧 Testing JSON serialization...")
        try:
            json_data = json.dumps(email_threads, default=str, indent=2)
            print(f"✅ JSON serialization successful")
            
            # Save to file for inspection
            with open('thread_data_debug.json', 'w') as f:
                f.write(json_data)
            print(f"💾 Saved thread data to thread_data_debug.json")
            
        except Exception as e:
            print(f"❌ JSON serialization failed: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_thread_structure() 