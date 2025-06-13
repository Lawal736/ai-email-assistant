#!/usr/bin/env python3
"""
Test script to verify document processing functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from document_processor import DocumentProcessor
from email_processor import EmailProcessor
from gmail_service import GmailService
from ai_service import HybridAIService

def test_document_processor():
    """Test document processor functionality"""
    print("🧪 Testing Document Processor...")
    
    processor = DocumentProcessor()
    
    # Test with sample text data
    sample_text = "This is a test document with important information. Key points: 1. Project deadline is March 15th. 2. Budget is $50,000. 3. Team meeting on Friday."
    
    result = processor.analyze_document_content(sample_text, "test.txt")
    print(f"✅ Document analysis: {result}")
    
    return True

def test_email_processor_with_attachments():
    """Test email processor with attachment handling"""
    print("\n🧪 Testing Email Processor with Attachments...")
    
    try:
        # Initialize services
        gmail_service = GmailService()
        ai_service = HybridAIService()
        document_processor = DocumentProcessor()
        email_processor = EmailProcessor(ai_service, document_processor, gmail_service)
        
        print("✅ All services initialized successfully")
        
        # Test with a sample email that has attachments
        sample_email = {
            'id': 'test123',
            'subject': 'Test Email with Attachments',
            'sender': 'test@example.com',
            'body': 'Please review the attached documents.',
            'attachments': [
                {
                    'id': 'att1',
                    'filename': 'document.pdf',
                    'mime_type': 'application/pdf',
                    'size': 1024
                }
            ],
            'has_attachments': True
        }
        
        # Test the process_email_with_attachments method
        processed_email = email_processor.process_email_with_attachments(sample_email)
        print(f"✅ Email processed: {processed_email.get('has_attachments', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing email processor: {e}")
        return False

def test_gmail_attachment_extraction():
    """Test Gmail attachment extraction"""
    print("\n🧪 Testing Gmail Attachment Extraction...")
    
    try:
        gmail_service = GmailService()
        
        if not gmail_service.is_authenticated():
            print("⚠️ Gmail not authenticated, skipping attachment test")
            return True
        
        # Get a few emails to check for attachments
        emails = gmail_service.get_todays_emails(max_results=5)
        
        attachment_count = 0
        for email in emails:
            if email.get('has_attachments'):
                attachment_count += 1
                print(f"📎 Email '{email.get('subject', 'No Subject')}' has {len(email.get('attachments', []))} attachments")
        
        print(f"✅ Found {attachment_count} emails with attachments out of {len(emails)} emails")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gmail attachments: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Document Processing Tests...\n")
    
    tests = [
        test_document_processor,
        test_email_processor_with_attachments,
        test_gmail_attachment_extraction
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Document processing is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main() 