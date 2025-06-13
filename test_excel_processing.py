#!/usr/bin/env python3
"""
Test script to verify improved Excel processing functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from document_processor import DocumentProcessor
import pandas as pd
import io

def create_test_excel():
    """Create a test Excel file with multiple sheets"""
    print("🧪 Creating test Excel file...")
    
    # Create sample data for CDF sheet (empty)
    cdf_data = pd.DataFrame()
    
    # Create sample data for Summary sheet (transaction data)
    summary_data = pd.DataFrame({
        'Date': ['2025-06-01', '2025-06-02', '2025-06-03', '2025-06-04', '2025-06-05'],
        'Transaction_ID': ['TXN001', 'TXN002', 'TXN003', 'TXN004', 'TXN005'],
        'Amount': [1000.50, 2500.75, 750.25, 3200.00, 1800.30],
        'Type': ['Credit', 'Debit', 'Credit', 'Debit', 'Credit'],
        'Description': ['Payment received', 'Service fee', 'Refund', 'Purchase', 'Commission']
    })
    
    # Create a larger dataset to simulate the real scenario
    large_data = []
    for i in range(1000):  # 1000 rows
        large_data.append({
            'Date': f'2025-06-{(i % 30) + 1:02d}',
            'Transaction_ID': f'TXN{i+1:06d}',
            'Amount': round(100 + (i * 10.5), 2),
            'Type': 'Credit' if i % 2 == 0 else 'Debit',
            'Description': f'Transaction {i+1}'
        })
    
    large_summary = pd.DataFrame(large_data)
    
    # Create Excel file in memory
    excel_buffer = io.BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        cdf_data.to_excel(writer, sheet_name='CDF', index=False)
        large_summary.to_excel(writer, sheet_name='Summary', index=False)
    
    excel_buffer.seek(0)
    return excel_buffer.getvalue()

def test_excel_processing():
    """Test the improved Excel processing"""
    print("🧪 Testing Improved Excel Processing...")
    
    processor = DocumentProcessor()
    
    # Create test Excel data
    excel_data = create_test_excel()
    
    # Test extraction
    result = processor.extract_document_text(
        excel_data, 
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'CWN as of 12th June, 2025.xlsx'
    )
    
    if result['success']:
        print("✅ Excel extraction successful!")
        print(f"📊 Word count: {result['word_count']}")
        print(f"📄 Document type: {result.get('document_type', 'unknown')}")
        
        # Analyze the extracted content
        analysis = processor.analyze_document_content(result['text'], 'CWN as of 12th June, 2025.xlsx')
        
        print(f"\n📋 Analysis Results:")
        print(f"Document type: {analysis['document_type']}")
        print(f"Analysis: {analysis['analysis']}")
        print(f"Key points:")
        for i, point in enumerate(analysis['key_points'], 1):
            print(f"  {i}. {point}")
        
        # Show a sample of the extracted text
        print(f"\n📝 Sample extracted text:")
        sample_text = result['text'][:500] + "..." if len(result['text']) > 500 else result['text']
        print(sample_text)
        
        return True
    else:
        print(f"❌ Excel extraction failed: {result.get('error', 'Unknown error')}")
        return False

def test_specific_scenarios():
    """Test specific Excel scenarios"""
    print("\n🧪 Testing Specific Excel Scenarios...")
    
    processor = DocumentProcessor()
    
    # Test 1: Empty sheet
    print("\n📊 Test 1: Empty sheet")
    empty_df = pd.DataFrame()
    empty_buffer = io.BytesIO()
    empty_df.to_excel(empty_buffer, sheet_name='Empty', index=False)
    empty_buffer.seek(0)
    
    result1 = processor.extract_document_text(
        empty_buffer.getvalue(),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'empty.xlsx'
    )
    
    if result1['success']:
        print("✅ Empty sheet handled correctly")
        analysis1 = processor.analyze_document_content(result1['text'], 'empty.xlsx')
        print(f"   Analysis: {analysis1['analysis']}")
    else:
        print("❌ Empty sheet processing failed")
    
    # Test 2: Large dataset
    print("\n📊 Test 2: Large dataset")
    large_df = pd.DataFrame({
        'Column_1': range(1000),
        'Column_2': [f'Data_{i}' for i in range(1000)],
        'Column_3': [i * 1.5 for i in range(1000)]
    })
    
    large_buffer = io.BytesIO()
    with pd.ExcelWriter(large_buffer, engine='openpyxl') as writer:
        large_df.to_excel(writer, sheet_name='LargeData', index=False)
    
    large_buffer.seek(0)
    
    result2 = processor.extract_document_text(
        large_buffer.getvalue(),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'large_data.xlsx'
    )
    
    if result2['success']:
        print("✅ Large dataset handled correctly")
        analysis2 = processor.analyze_document_content(result2['text'], 'large_data.xlsx')
        print(f"   Word count: {result2['word_count']}")
        print(f"   Key points: {len(analysis2['key_points'])}")
    else:
        print("❌ Large dataset processing failed")

def main():
    """Run all tests"""
    print("🚀 Starting Improved Excel Processing Tests...\n")
    
    tests = [
        test_excel_processing,
        test_specific_scenarios
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
        print("🎉 All tests passed! Excel processing is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main() 