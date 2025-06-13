#!/usr/bin/env python3
"""
Test script to verify thread key generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_processor import EmailProcessor

def test_thread_keys():
    """Test thread key generation with various inputs"""
    processor = EmailProcessor()
    
    test_cases = [
        ("John Doe <john.doe@example.com>", "Re: Project Update"),
        ("Jane Smith <jane.smith@company.com>", "Fwd: Meeting Tomorrow"),
        ("Support Team <support@service.com>", "[Ticket #12345] Issue Report"),
        ("Newsletter <news@newsletter.com>", "Weekly Digest"),
        ("User <user@domain.com>", "Subject with special chars: @#$%^&*()"),
        ("Test User <test@test.com>", "Normal Subject"),
    ]
    
    print("🔍 Testing Thread Key Generation:")
    print("=" * 50)
    
    for sender, subject in test_cases:
        thread_key = processor._create_thread_key(sender, subject)
        print(f"Sender: {sender}")
        print(f"Subject: {subject}")
        print(f"Thread Key: {thread_key}")
        print(f"Key Length: {len(thread_key)}")
        print(f"Safe for JS: {'Yes' if thread_key.isalnum() else 'No'}")
        print("-" * 30)
    
    # Test with actual email data structure
    print("\n🧵 Testing Thread Grouping:")
    print("=" * 50)
    
    test_emails = [
        {
            'id': '1',
            'sender': 'John Doe <john@example.com>',
            'subject': 'Re: Project Update',
            'date': '2024-01-01T10:00:00',
            'body': 'Test email 1',
            'priority': 'high'
        },
        {
            'id': '2',
            'sender': 'John Doe <john@example.com>',
            'subject': 'Re: Project Update',
            'date': '2024-01-01T11:00:00',
            'body': 'Test email 2',
            'priority': 'medium'
        },
        {
            'id': '3',
            'sender': 'Jane Smith <jane@example.com>',
            'subject': 'Meeting Tomorrow',
            'date': '2024-01-01T12:00:00',
            'body': 'Test email 3',
            'priority': 'low'
        }
    ]
    
    # Process emails
    processed_emails = []
    for email in test_emails:
        processed_email = processor._process_single_email_basic(email)
        processed_emails.append(processed_email)
    
    # Group by thread
    threads = processor.group_emails_by_thread(processed_emails)
    
    print(f"Created {len(threads)} threads:")
    for thread_key, thread_data in threads.items():
        print(f"\nThread Key: {thread_key}")
        print(f"Subject: {thread_data['subject']}")
        print(f"Sender: {thread_data['sender']}")
        print(f"Thread Count: {thread_data['thread_count']}")
        print(f"Emails Array Type: {type(thread_data['emails'])}")
        print(f"Emails Array Length: {len(thread_data['emails'])}")
        print(f"Emails IDs: {[email['id'] for email in thread_data['emails']]}")

if __name__ == "__main__":
    test_thread_keys() 